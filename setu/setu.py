from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Plain
from loguru import logger

from app.api.doHttp import doHttpRequest
from app.core.config import Config
from app.core.settings import CONFIG
from app.entities.user import *
from app.plugin.base import Plugin
from app.util.tools import isstartswith


class Module(Plugin):
    entry = ['.setu', '.涩图']
    brief_help = '涩图'
    full_help = {
        '无参数': '消耗10资金随机获取一张setu',
        '搜': {
            '消耗15资金根据关键词搜索一张setu': '',
            'uid=[uid]': '指定作者信息',
            'tag=[tag]': '指定标签(多个相似标签使用`|`分隔)'
        },
        'R18': {
            '开关R-18模式(慎用)[默认关闭]': '',
            '[0 / 关]': '关闭R-18模式',
            '[1 / 开]': '开启R-18模式'
        }
    }

    num = {
        # c: cost
        'normal': {'c': 10},
        'search': {'c': 15}
    }

    async def process(self):
        _user_id = (getattr(self, 'friend', None) or getattr(self, 'group', None)).id
        R18 = CONFIG[str(_user_id)]['setu_R18'] if CONFIG.__contains__(str(_user_id)) and CONFIG[
            str(_user_id)].__contains__('setu_R18') else 0
        if not self.msg:
            # 判断积分是否足够，如果无，要求报错并返回
            the_one = BotUser((getattr(self, 'friend', None) or getattr(self, 'member', None)).id)
            if int(the_one.get_points()) < self.num['normal']['c']:
                self.point_not_enough()
                return
            response = await doHttpRequest(
                url='https://api.lolicon.app/setu/v2',
                method='GET',
                _type='JSON',
                params={'r18': R18},
                headers={'Content-Type': 'application/json'}
            )
            if response['data']:
                the_one.update_point(-self.num['normal']['c'])
                self.resp = MessageChain.create([
                    Image(url=response['data'][0]['urls']['original'].replace('i.pixiv.cat', 'pixiv.a-f.workers.dev'))
                ])
            else:
                self.resp = MessageChain.create([
                    Plain('setu: 获取失败')
                ])
            return
        try:
            if isstartswith(self.msg[0], '搜'):
                assert len(self.msg) > 1
                # 判断积分是否足够，如果无，要求报错并返回
                the_one = BotUser((getattr(self, 'friend', None) or getattr(self, 'member', None)).id)
                if int(the_one.get_points()) < self.num['search']['c']:
                    self.point_not_enough()
                    return
                keyword = {i.split('=')[0]: i.split('=')[1] for i in self.msg[1:] if
                           i.split('=')[0] in ['uid', 'tag'] and i.split('=')[1] is not None}
                response = await doHttpRequest(
                    url='https://api.lolicon.app/setu/v2',
                    method='GET',
                    _type='JSON',
                    params=keyword.update({'r18': R18}),
                    headers={'Content-Type': 'application/json'}
                )
                if response['data']:
                    the_one.update_point(-self.num['search']['c'])
                    self.resp = MessageChain.create([
                        Image(
                            url=response['data'][0]['urls']['original'].replace('i.pixiv.cat', 'pixiv.a-f.workers.dev'))
                    ])
                else:
                    self.resp = MessageChain.create([
                        Plain('setu: 搜索失败')
                    ])
            elif isstartswith(self.msg[0], 'R18'):
                if not hasattr(self, 'group'):
                    return
                config = Config()
                if self.member.id != int(config.MASTER_QQ):
                    self.not_admin()
                    return
                assert len(self.msg) == 2 and self.msg[1] in ['0', '1', '关', '开']
                with MysqlDao() as db:
                    if db.update(
                            'REPLACE INTO config(name, uid, value) VALUES (%s, %s, %s)',
                            ['setu_R18', self.group.id, '0' if self.msg[1] in ['0', '关'] else '1']
                    ):
                        if not CONFIG.__contains__(str(self.group.id)):
                            CONFIG.update({str(self.group.id): {}})
                        CONFIG[str(self.group.id)].update({'setu_R18': 0 if self.msg[1] in ['0', '关'] else 1})
                        self.resp = MessageChain.create([Plain('设置成功！')])
            else:
                self.args_error()
                return
        except AssertionError as e:
            print(e)
            self.args_error()
        except Exception as e:
            logger.exception(e)
            self.unkown_error()
