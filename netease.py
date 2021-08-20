import asyncio

from graia.application import MessageChain
from graia.application.message.elements.internal import Plain

from app.api.doHttp import doHttpRequest
from app.extend.NetEaseCloudMusicAction import NetEase_process_event
from app.plugin.base import Plugin
from app.util.dao import MysqlDao
from app.util.tools import isstartswith, message_source


class NetEase(Plugin):
    entry = ['.wyy', '.网易云']
    brief_help = '\r\n▶网易云: wyy'
    full_help = \
        '.wyy rp\t网易云热评\r\n' \
        '.wyy qd [phone] [password]\t网易云签到\r\n' \
        '.wyy add [phone] [password]\t添加网易云自动签到\r\n' \
        '.wyy remove [phone]\t移除该账号的网易云自动签到\r\n' \
        '.wyy list\t列出您添加的网易云自动签到账号\r\n' \
        '============\r\n' \
        '为保证账号安全，签到服务仅私发有效'

    async def process(self):
        if not self.msg:
            self.print_help()
            return
        try:
            if isstartswith(self.msg[0], 'qd'):
                assert len(self.msg) == 3 and self.msg[1].isdigit()
                if not message_source:
                    await NetEase_process_event(self.app, self.friend.id, self.msg[1], self.msg[2])
            elif isstartswith(self.msg[0], 'add'):
                assert len(self.msg) == 3 and self.msg[1].isdigit()
                if not message_source:
                    with MysqlDao() as db:
                        res = db.query(
                            'SELECT * FROM netease WHERE phone=%s',
                            [self.msg[1]]
                        )
                        if not res:
                            res = db.update(
                                'INSERT INTO netease (qid, phone, pwd) VALUES (%s, %s, %s)',
                                [self.friend.id, self.msg[1], self.msg[2]]
                            )
                            if not res:
                                raise Exception()
                            self.resp = MessageChain.create([
                                Plain('添加成功')
                            ])
                        else:
                            self.resp = MessageChain.create([
                                Plain('该账号已存在！')
                            ])
            elif isstartswith(self.msg[0], 'remove'):
                assert len(self.msg) == 2 and self.msg[1].isdigit()
                if not message_source:
                    with MysqlDao() as db:
                        res = db.query(
                            'SELECT * FROM netease WHERE qid=%s and phone=%s',
                            [self.friend.id, self.msg[1]]
                        )
                        print(str(res) + '\n 1')
                        if res:
                            res = db.update(
                                'DELETE FROM netease WHERE qid=%s and phone=%s',
                                [self.friend.id, self.msg[1]]
                            )
                            print(str(res) + '\n 2')
                            if res:
                                self.resp = MessageChain.create([
                                    Plain('移除成功！')
                                ])
                        else:
                            self.resp = MessageChain.create([
                                Plain('该账号不存在！')
                            ])
            elif isstartswith(self.msg[0], 'list'):
                if not message_source:
                    with MysqlDao() as db:
                        res = db.query(
                            'SELECT phone FROM netease WHERE qid=%s',
                            [self.friend.id]
                        )
                        self.resp = MessageChain.create([
                            Plain('\n'.join([f'{phone[0]}' for phone in res]))
                        ])
            elif isstartswith(self.msg[0], 'rp'):
                req = json.loads(await doHttpRequest('https://api.muxiaoguo.cn/api/163reping', 'GET'))
                ans = req['data']
                self.resp = MessageChain.create([
                    Plain('歌曲：%s\r\n' % ans['songName']),
                    Plain('昵称：%s\r\n' % ans['nickname']),
                    Plain('评论：%s' % ans['content'])
                ])
            else:
                self.args_error()
                return
        except AssertionError as e:
            print(e)
            self.args_error()
        except Exception as e:
            print(e)
            self.unkown_error()


if __name__ == '__main__':
    a = NetEase(MessageChain.create([Plain('.wyy rp')]))
    asyncio.run(a.get_resp())
    print(a.resp)
