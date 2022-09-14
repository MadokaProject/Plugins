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
            Subcommand('mute', help_text='投票禁言', args=Args['member', [At, int]]),
            Subcommand('kick', help_text='投票踢出', args=Args['member', [At, int]]),
            Subcommand('config', help_text='设置投票通过比例', args=Args['type;O', ['mute', 'kick']]['proportion;O', int]),
            Subcommand('user', help_text='投票成员管理(仅管理可用)', args=Args['member;O', [At, int]]),
            Option('--add', help_text='添加'),
            Option('--delete', help_text='删除'),
            Option('--list', help_text='列出')
        ],
        help_text='投票管理'
    )
)
async def process(app: Ariadne, target: Union[Friend, Member], sender: Union[Friend, Group], cmd: Arpamar,
                  alc: Alconna):
    if not cmd.subcommands:
        return print_help(alc.get_help())
    try:
        vote_config: dict = await get_config('myyueyue_vote', sender)
        # 获取拥有投票权限的成员
        vote_admin_users = vote_config['user']
        if cmd.find('user'):
            if not Permission.manual(target, Permission.GROUP_ADMIN):
                return await not_admin()
            if cmd.find('list'):
                return MessageChain('\n'.join(str(i) for i in vote_admin_users))
            if member := cmd.query('member'):
                if cmd.find('add'):
                    if member in vote_admin_users:
                        return MessageChain('该用户已存在')
                    await save_config('myyueyue_vote', sender, {
                        'user': vote_admin_users.append(int(member))
                    }, model='add')
                    return MessageChain('添加用户成功')
                elif cmd.find('delete'):
                    if member not in vote_admin_users:
                        return MessageChain('该用户不存在')
                    await save_config('myyueyue_vote', sender, {
                        'user': vote_admin_users.remove(int(member))
                    }, model='add')
                else:
                    return await args_error()
            else:
                return MessageChain('缺少 member 参数')

        elif cmd.find('config'):
            if not Permission.manual(target, Permission.GROUP_ADMIN):
                return await not_admin()
            if cmd.find('list'):
                return MessageChain('\n'.join(f'{k}: {v}' for k, v in vote_config.items() if k != 'user'))
            if all([_type := cmd.query('type'), proportion := cmd.query('proportion')]):
                await save_config('myyueyue_vote', sender, {_type: proportion}, model='add')
                return MessageChain('设置成功！')
            else:
                return MessageChain('缺少参数!')

        vote_mark = random.randint(1, 99999999)
        vote_result: Dict[int, bool] = {}
        if target.id not in vote_admin_users:
            return not_admin()

        async def voter(vote_member: Member, vote_group: Group, vote_message: MessageChain, vote_source: Source):
            """投票器"""
            vote_message = vote_message.display.replace('：', ':').replace(' ', '')
            if all([sender.id == vote_group.id, vote_member.id in vote_admin_users]):
                if vote_message == f'同意:{vote_mark}':
                    vote_result[vote_member.id] = True
                    await app.send_group_message(vote_group, MessageChain('你投了同意票'), quote=vote_source)
                elif vote_message == f'反对:{vote_mark}':
                    vote_result[vote_member.id] = False
                    await app.send_group_message(vote_group, MessageChain('你投了反对票'), quote=vote_source)
                else:
                    await app.send_group_message(vote_group, MessageChain(
                        f'请输入 同意:{vote_mark} / 反对:{vote_mark}'
                    ), quote=vote_source)

        async def vote(vote_user: int, _type: str) -> Tuple[float, bool]:
            """投票

            :param vote_user: 投票目标
            :param _type: 投票类型
            """
            try:
                await app.send_group_message(sender, MessageChain([
                    Plain('投票发起成功，请拥有投票权限者在180内投票！（重复投票可覆盖）\n'),
                    Plain('投票目标: '),
                    At(vote_user),
                    Plain(f'\n标识号: {vote_mark}\n'),
                    Plain(f'请输入 同意:{vote_mark} / 反对:{vote_mark}')
                ]))
                await FunctionWaiter(voter, [GroupMessage]).wait(180)
            except asyncio.TimeoutError:
                _proportion = len([i for i in vote_result.values() if i]) / len(vote_result)
                if _proportion > vote_config[_type]:
                    vote_ret = _proportion, True
                else:
                    vote_ret = _proportion, False
                await app.send_group_message(sender, MessageChain([
                    Plain(f'投票结果: {ret[1]}\n'),
                    Plain(f'同意比例: {ret[0]:.2%}')
                ]))
                return vote_ret

        if user := cmd.query('mute'):
            user = user['user']
            if isinstance(user, At):
                user = user.target
            ret = await vote(user, 'mute')
            if ret[1]:
                await app.mute_member(sender, user)
        elif user := cmd.query('kick'):
            user = user['user']
            if isinstance(user, At):
                user = user.target
            ret = await vote(user, 'kick')
            if ret[1]:
                await app.kick_member(sender, user)
        else:
            return await args_error()
    except Exception as e:
        logger.error(e)
        return await unknown_error()
