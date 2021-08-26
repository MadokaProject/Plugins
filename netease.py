import asyncio
import base64
import hashlib
import json

import requests
from Crypto.Cipher import AES
from graia.application import MessageChain
from graia.application.message.elements.internal import Plain

from app.api.doHttp import doHttpRequest
from app.plugin.base import Plugin, Schedule
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
                if not message_source(self):
                    await Tasker(self.app).NetEase_process_event(self.friend.id, self.msg[1], self.msg[2])
            elif isstartswith(self.msg[0], 'add'):
                assert len(self.msg) == 3 and self.msg[1].isdigit()
                if not message_source(self):
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
                if not message_source(self):
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
                if not message_source(self):
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


class Tasker(Schedule):
    cron = '0 8 * * * 0'

    async def process(self):
        with MysqlDao() as db:
            accounts = db.query(
                'SELECT qid, phone, pwd FROM netease'
            )
            for (qid, phone, pwd) in accounts:
                await self.app.sendFriendMessage(int(qid), MessageChain.create([
                    Plain("正在进行账号" + phone + "的自动签到任务\r\n下次运行时间为：8:00")
                ]))
                await self.NetEase_process_event(int(qid), phone, pwd)

    def encrypt(self, key, text):
        cryptor = AES.new(key.encode('utf8'), AES.MODE_CBC, b'0102030405060708')
        length = 16
        count = len(text.encode('utf-8'))
        if count % length != 0:
            add = length - (count % length)
        else:
            add = 16
        pad = chr(add)
        text1 = text + (pad * add)
        ciphertext = cryptor.encrypt(text1.encode('utf8'))
        cryptedStr = str(base64.b64encode(ciphertext), encoding='utf-8')
        return cryptedStr

    def md5(self, str):
        hl = hashlib.md5()
        hl.update(str.encode(encoding='utf-8'))
        return hl.hexdigest()

    def protect(self, text):
        return {"params": self.encrypt('TA3YiYCfY2dDJQgg', self.encrypt('0CoJUm6Qyw8W8jud', text)),
                "encSecKey": "84ca47bca10bad09a6b04c5c927ef077d9b9f1e37098aa3eac6ea70eb59df0aa28b691b7e75e4f1f9831754919ea784c8f74fbfadf2898b0be17849fd656060162857830e241aba44991601f137624094c114ea8d17bce815b0cd4e5b8e2fbaba978c6d1d14dc3d1faf852bdd28818031ccdaaa13a6018e1024e2aae98844210"}

    async def NetEase_process_event(self, qid, phone, pwd):
        s = requests.Session()
        header = {}
        url = "https://music.163.com/weapi/login/cellphone"
        url2 = "https://music.163.com/weapi/point/dailyTask"
        url3 = "https://music.163.com/weapi/v1/discovery/recommend/resource"
        logindata = {
            "phone": phone,
            "countrycode": "86",
            "password": self.md5(pwd),
            "rememberLogin": "true",
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36',
            "Referer": "http://music.163.com/",
            "Accept-Encoding": "gzip, deflate",
        }
        headers2 = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36',
            "Referer": "http://music.163.com/",
            "Accept-Encoding": "gzip, deflate",
            "Cookie": "os=pc; osver=Microsoft-Windows-10-Professional-build-10586-64bit; appver=2.0.3.131777; channel=netease; __remember_me=true;"
        }

        res = s.post(url=url, data=self.protect(json.dumps(logindata)), headers=headers2)
        tempcookie = res.cookies
        object = json.loads(res.text)
        if object['code'] == 200:
            await self.app.sendFriendMessage(qid, MessageChain.create([
                Plain(phone + "：登录成功！")
            ]))
        else:
            await self.app.sendFriendMessage(qid, MessageChain.create([
                Plain(phone + "：登录失败！请检查密码是否正确！" + str(object['code']))
            ]))
            return object['code']

        res = s.post(url=url2, data=self.protect('{"type":0}'), headers=headers)
        object = json.loads(res.text)
        if object['code'] != 200 and object['code'] != -2:
            await self.app.sendFriendMessage(qid, MessageChain.create([
                Plain(phone + "：签到时发生错误：" + object['msg'])
            ]))
        else:
            if object['code'] == 200:
                await self.app.sendFriendMessage(qid, MessageChain.create([
                    Plain(phone + "：签到成功，经验+" + str(object['point']))
                ]))
            else:
                await self.app.sendFriendMessage(qid, MessageChain.create([
                    Plain(phone + "：重复签到")
                ]))

        res = s.post(url=url3,
                     data=self.protect(
                         '{"csrf_token":"' + requests.utils.dict_from_cookiejar(tempcookie)['__csrf'] + '"}'),
                     headers=headers)
        object = json.loads(res.text, strict=False)
        for x in object['recommend']:
            url = 'https://music.163.com/weapi/v3/playlist/detail?csrf_token=' + \
                  requests.utils.dict_from_cookiejar(tempcookie)[
                      '__csrf']
            data = {
                'id': x['id'],
                'n': 1000,
                'csrf_token': requests.utils.dict_from_cookiejar(tempcookie)['__csrf'],
            }
            res = s.post(url, self.protect(json.dumps(data)), headers=headers)
            object = json.loads(res.text, strict=False)
            buffer = []
            count = 0
            for j in object['playlist']['trackIds']:
                data2 = {}
                data2["action"] = "play"
                data2["json"] = {}
                data2["json"]["download"] = 0
                data2["json"]["end"] = "playend"
                data2["json"]["id"] = j["id"]
                data2["json"]["sourceId"] = ""
                data2["json"]["time"] = "240"
                data2["json"]["type"] = "song"
                data2["json"]["wifi"] = 0
                buffer.append(data2)
                count += 1
                if count >= 310:
                    break
            if count >= 310:
                break
        url = "http://music.163.com/weapi/feedback/weblog"
        postdata = {
            "logs": json.dumps(buffer)
        }
        res = s.post(url, self.protect(json.dumps(postdata)))
        object = json.loads(res.text, strict=False)
        if object['code'] == 200:
            await self.app.sendFriendMessage(qid, MessageChain.create([
                Plain(phone + "：刷单成功！共" + str(count) + "首")
            ]))
            return
        else:
            await self.app.sendFriendMessage(qid, MessageChain.create([
                Plain(phone + "：发生错误：" + str(object['code']) + object['message'])
            ]))
            return object['code']


if __name__ == '__main__':
    a = NetEase(MessageChain.create([Plain('.wyy rp')]))
    asyncio.run(a.get_resp())
    print(a.resp)
