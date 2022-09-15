import asyncio
import random
from typing import Union, Dict, Tuple

from arclet.alconna import Alconna, Args, Subcommand, Option, Arpamar
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain, Source
from graia.ariadne.model import Friend, Group, Member
from graia.ariadne.util.interrupt import FunctionWaiter
from loguru import logger

from app.core.commander import CommandDelegateManager
from app.util.control import Permission
from app.util.online_config import save_config, get_config
from app.util.phrases import print_help, unknown_error, not_admin, args_error


manager: CommandDelegateManager = CommandDelegateManager()


@manager.register(
    entry='vote',
    brief_help='投票管理',
    alc=Alconna(
        headers=manager.headers,
        command='vote',
        options=[
            Subcommand('mute', help_text='投票禁言'),
            Subcommand('kick', help_text='投票踢出'),
            Subcommand('user', help_text='投票成员管理(仅管理可用)'),
            Option('--add', help_text='添加'),
            Option('--delete', help_text='删除'),
            Option('--list', help_text='列出'),
            Option('--config', help_text='设置投票通过比例', args=Args['proportion;O', float]),
        ],
        main_args=Args['member;O', [At, int]]['time;O', int, 5],
        help_text='投票管理'
    )
)
async def process(app: Ariadne, target: Union[Friend, Member], sender: Union[Friend, Group], cmd: Arpamar,
                  alc: Alconna):
    if not cmd.subcommands and not cmd.options:
        return await print_help(alc.get_help())
    if isinstance(sender, Friend):
        return MessageChain('请在群内使用')
    try:
        if vote_config := await get_config('myyueyue_vote', sender):
            # 获取拥有投票权限的成员
            vote_admin_users = vote_config['user'] if 'user' in vote_config else []
        else:
            vote_config = {}
            vote_admin_users = []

        if cmd.find('user'):
            if not Permission.manual(target, Permission.GROUP_ADMIN):
                return not_admin()
            if cmd.find('list'):
                return MessageChain([
                    Plain('可投票成员:'),
                    Plain('\n'.join(str(i) for i in vote_admin_users))
                ])
            if member := cmd.query('member'):
                if isinstance(member, At):
                    member = member.target
                if cmd.find('add'):
                    if member in vote_admin_users:
                        return MessageChain('该用户已存在')
                    vote_admin_users.append(int(member))
                    await save_config('myyueyue_vote', sender, {
                        'user': vote_admin_users
                    }, model='add')
                    return MessageChain('添加用户成功')
                elif cmd.find('delete'):
                    if member not in vote_admin_users:
                        return MessageChain('该用户不存在')
                    vote_admin_users.remove(int(member))
                    await save_config('myyueyue_vote', sender, {
                        'user': vote_admin_users
                    }, model='add')
                    return MessageChain('删除用户成功')
                else:
                    return args_error()
            else:
                return MessageChain('缺少 member 参数')

        elif cmd.find('config'):
            if not Permission.manual(target, Permission.GROUP_ADMIN):
                return not_admin()
            if cmd.find('list'):
                return MessageChain([
                    Plain('配置信息:\n'),
                    Plain('\n'.join(f'{k}: {v}' for k,
                          v in vote_config.items() if k != 'user'))
                ])
            if cmd.find('mute'):
                _type = 'mute'
            elif cmd.find('kick'):
                _type = 'kick'
            else:
                return MessageChain('缺少 mute 或 kick 参数')
            proportion = cmd.query('proportion')
            if 0 < proportion <= 1:
                await save_config('myyueyue_vote', sender, {_type: proportion}, model='add')
                return MessageChain('设置成功！')
            else:
                return MessageChain('比例应在 0-1 之间')

        vote_mark = random.randint(1, 99999999)
        vote_result: Dict[int, bool] = {}

        async def voter(vote_member: Member, vote_group: Group, vote_message: MessageChain, vote_source: Source):
            """投票器"""
            vote_message = vote_message.display.replace(
                '：', ':').replace(' ', '')
            if all([sender.id == vote_group.id, vote_member.id in vote_admin_users]):
                if vote_message == f'同意:{vote_mark}':
                    vote_result[vote_member.id] = True
                    await app.send_group_message(vote_group, MessageChain('你投了同意票'), quote=vote_source)
                elif vote_message == f'反对:{vote_mark}':
                    vote_result[vote_member.id] = False
                    await app.send_group_message(vote_group, MessageChain('你投了反对票'), quote=vote_source)
                if len(vote_result) == len(vote_admin_users):
                    return True

        async def vote(vote_user: int, _type: str) -> Tuple[float, bool]:
            """投票

            :param vote_user: 投票目标
            :param _type: 投票类型
            """
            try:
                await app.send_group_message(sender, MessageChain([
                    Plain('投票发起成功，请拥有投票权限者在90秒内投票！（重复投票可覆盖）\n'),
                    Plain('投票目标: '),
                    At(vote_user),
                    Plain(f'\n标识号: {vote_mark}\n'),
                    Plain(f'请输入: 同意:{vote_mark} | 反对:{vote_mark}')
                ]))
                await FunctionWaiter(voter, [GroupMessage]).wait(90)
            except asyncio.TimeoutError:
                pass
            _proportion = len(
                [i for i in vote_result.values() if i]) / len(vote_result)
            if _type not in vote_config:
                vote_config[_type] = 0.7
            if _proportion > vote_config[_type]:
                vote_ret = _proportion, True
            else:
                vote_ret = _proportion, False
            await app.send_group_message(sender, MessageChain([
                Plain(f'投票结果: {vote_ret[1]}\n'),
                Plain(f'同意比例: {vote_ret[0]:.2%}')
            ]))
            return vote_ret

        if target.id not in vote_admin_users:
            return not_admin()
        
        if not cmd.find('member'):
            return MessageChain('缺少 member 参数')

        if cmd.find('mute'):
            user = cmd.query('member')
            if isinstance(user, At):
                user = user.target
            ret = await vote(user, 'mute')
            if ret[1]:
                await app.mute_member(sender, user, cmd.query('time') * 60)
        elif cmd.find('kick'):
            user = cmd.query('member')
            if isinstance(user, At):
                user = user.target
            ret = await vote(user, 'kick')
            if ret[1]:
                await app.kick_member(sender, user, cmd.query('time') * 60)
        else:
            return args_error()
    except Exception as e:
        logger.error(e)
        return unknown_error()
