from arclet.alconna import Alconna, Args, Subcommand, Option, Arpamar
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain
from loguru import logger

from app.core.commander import CommandDelegateManager
from app.core.config import Config
from app.core.settings import CONFIG
from app.entities.game import BotGame
from app.plugin.base import Plugin
from app.util.dao import MysqlDao
from app.util.network import general_request

num = {
    # c: cost
    'normal': {'c': 10},
    'search': {'c': 15}
}

manager: CommandDelegateManager = CommandDelegateManager.get_instance()


@manager.register(
    entry='setu',
    brief_help='涩图',
    alc=Alconna(
        headers=manager.headers,
        command='setu',
        options=[
            Option('--uid|-u', help_text='指定作者信息', args=Args['uid', str]),
            Option('--tag|-t', help_text='指定标签(多个相似标签使用 | 分隔', args=Args['tag', str]),
            Subcommand('r18', help_text='开关R-18模式(慎用)[默认关闭]', args=Args['r18', bool, False])
        ],
        help_text='消耗10资金随机获取一张setu, 消耗15资金指定特定信息搜索'
    ))
async def process(self: Plugin, command: Arpamar, alc: Alconna):
    _user_id = (getattr(self, 'friend', None) or getattr(self, 'group', None)).id
    R18 = CONFIG[str(_user_id)]['setu_R18'] if CONFIG.__contains__(str(_user_id)) and CONFIG[
        str(_user_id)].__contains__('setu_R18') else 0
    components = command.options.copy()
    components.update(command.subcommands)
    try:
        if r18 := components.get('r18', False):
            if not hasattr(self, 'group'):
                return
            config = Config()
            if self.member.id != int(config.MASTER_QQ):
                return self.not_admin()
            with MysqlDao() as db:
                if db.update(
                        'REPLACE INTO config(name, uid, value) VALUES (%s, %s, %s)',
                        ['setu_R18', self.group.id, r18['r18']]
                ):
                    if not CONFIG.__contains__(str(self.group.id)):
                        CONFIG.update({str(self.group.id): {}})
                    CONFIG[str(self.group.id)].update({'setu_R18': r18['r18']})
                    return MessageChain([Plain('设置成功！')])
        else:
            # 判断积分是否足够，如果无，要求报错并返回
            the_one = BotGame((getattr(self, 'friend', None) or getattr(self, 'member', None)).id)
            if await the_one.get_coins() < num['normal']['c']:
                return self.point_not_enough()
            keyword = {'r18': R18}
            if uid := components.get('uid'):
                keyword.update({'uid': uid['uid']})
            if tag := components.get('tag'):
                keyword.update({'tag': tag['tag']})
            response = await general_request(
                url='https://api.lolicon.app/setu/v2',
                method='GET',
                _type='JSON',
                params=keyword,
                headers={'Content-Type': 'application/json'}
            )
            if response['data']:
                await the_one.update_coin(-num['normal']['c'])
                return MessageChain([
                    Image(url=response['data'][0]['urls']['original'].replace('i.pixiv.cat', 'pixiv.a-f.workers.dev'))
                ])
            else:
                return MessageChain([Plain('setu: 获取失败')])
    except Exception as e:
        logger.exception(e)
        return self.unkown_error()
