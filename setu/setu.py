from arclet.alconna import Alconna, Args, Subcommand, Option, Arpamar
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain
from loguru import logger

from app.api.doHttp import doHttpRequest
from app.core.command_manager import CommandManager
from app.core.config import Config
from app.core.settings import CONFIG
from app.entities.user import *
from app.plugin.base import Plugin
from app.util.dao import MysqlDao


class Module(Plugin):
    entry = 'setu'
    brief_help = '涩图'
    manager: CommandManager = CommandManager.get_command_instance()
    num = {
        # c: cost
        'normal': {'c': 10},
        'search': {'c': 15}
    }

    @manager(Alconna(
        headers=manager.headers,
        command=entry,
        options=[
            Option('--uid', alias='-u', help_text='指定作者信息', args=Args['uid': str]),
            Option('--tag', alias='-t', help_text='指定标签(多个相似标签使用 | 分隔', args=Args['tag': str]),
            Subcommand('r18', help_text='开关R-18模式(慎用)[默认关闭]', args=Args['r18': bool:False])
        ],
        help_text='消耗10资金随机获取一张setu, 消耗15资金指定特定信息搜索'
    ))
    async def process(self, command: Arpamar, alc: Alconna):
        _user_id = (getattr(self, 'friend', None) or getattr(self, 'group', None)).id
        R18 = CONFIG[str(_user_id)]['setu_R18'] if CONFIG.__contains__(str(_user_id)) and CONFIG[
            str(_user_id)].__contains__('setu_R18') else 0
        try:
            if command.subcommands['r18']:
                if not hasattr(self, 'group'):
                        return
                config = Config()
                if self.member.id != int(config.MASTER_QQ):
                    return self.not_admin()
                with MysqlDao() as db:
                    if db.update(
                            'REPLACE INTO config(name, uid, value) VALUES (%s, %s, %s)',
                            ['setu_R18', self.group.id, command.other_args['r18']]
                    ):
                        if not CONFIG.__contains__(str(self.group.id)):
                            CONFIG.update({str(self.group.id): {}})
                        CONFIG[str(self.group.id)].update({'setu_R18': command.other_args['r18']})
                        return MessageChain.create([Plain('设置成功！')])
            else:
                # 判断积分是否足够，如果无，要求报错并返回
                the_one = BotUser((getattr(self, 'friend', None) or getattr(self, 'member', None)).id)
                if int(the_one.get_points()) < self.num['normal']['c']:
                    return self.point_not_enough()
                keyword = {'r18': R18}
                if command.other_args.__contains__('uid'):
                    keyword.update({'uid': command.other_args['uid']})
                if command.other_args.__contains__('tag'):
                    keyword.update({'tag': command.other_args['tag']})
                response = await doHttpRequest(
                    url='https://api.lolicon.app/setu/v2',
                    method='GET',
                    _type='JSON',
                    params=keyword,
                    headers={'Content-Type': 'application/json'}
                )
                if response['data']:
                    the_one.update_point(-self.num['normal']['c'])
                    return MessageChain.create([
                        Image(url=response['data'][0]['urls']['original'].replace('i.pixiv.cat', 'pixiv.a-f.workers.dev'))
                    ])
                else:
                    return MessageChain.create([Plain('setu: 获取失败')])
        except Exception as e:
            logger.exception(e)
            return self.unkown_error()
