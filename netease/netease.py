import asyncio
import base64
import hashlib
import json

import requests
from arclet.alconna import Alconna, Subcommand, Args, Arpamar
from Crypto.Cipher import AES
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from loguru import logger

from app.api.doHttp import doHttpRequest
from app.core.command_manager import CommandManager
from app.plugin.base import Plugin, Scheduler, InitDB
from app.util.dao import MysqlDao


class Module(Plugin):
    entry = 'wyy'
    brief_help = '网易云'
    manager: CommandManager = CommandManager.get_command_instance()

    @manager(Alconna(
        headers=manager.headers,
        command=entry,
        options=[
            Subcommand('rp', help_text='网易云热评'),
            Subcommand('qd', help_text='立即进行一次签到', args=Args['phone': int, 'password': str]),
            Subcommand('add', help_text='添加自动签到', args=Args['phone': int, 'password': str]),
            Subcommand('remove', help_text='移除指定账号的自动签到', args=Args['phone': int]),
            Subcommand('list', help_text='列出你添加的自动签到账号')
        ],
        help_text='网易云: 为保证账号安全, 签到服务仅私发有效'
    ))
    async def process(self, command: Arpamar, alc: Alconna):
        subcommand = command.subcommands
        other_args = command.other_args
        if not subcommand:
            return await self.print_help(alc.get_help())
        try:
            if subcommand.__contains__('qd'):
                if not hasattr(self, 'friend'):
                    return MessageChain.create([Plain('请私聊使用该命令!')])
                await Tasker(self.app).NetEase_process_event(self.friend.id, other_args['phone'], other_args['password'])
            elif subcommand.__contains__('add'):
                if not hasattr(self, 'friend'):
                    return MessageChain.create([Plain('请私聊使用该命令!')])
                with MysqlDao() as db:
                    if not db.query('SELECT * FROM Plugin_NetEase_Account WHERE phone=%s', [other_args['phone']]):
                        if not db.update(
                            'INSERT INTO Plugin_NetEase_Account (qid, phone, pwd) VALUES (%s, %s, %s)',
                            [self.friend.id, other_args['phone'], other_args['password']]
                        ):
                            raise Exception()
                        return MessageChain.create([Plain('添加成功')])
                    else:
                        return MessageChain.create([Plain('该账号已存在！')])
            elif subcommand.__contains__('remove'):
                if not hasattr(self, 'friend'):
                    return MessageChain.create([Plain('请私聊使用该命令!')])
                with MysqlDao() as db:
                    if db.query('SELECT * FROM Plugin_NetEase_Account WHERE qid=%s and phone=%s', [self.friend.id, other_args['phone']]):
                        if db.update('DELETE FROM Plugin_NetEase_Account WHERE qid=%s and phone=%s', [self.friend.id, other_args['phone']]):
                            return MessageChain.create([Plain('移除成功！')])
                    else:
                        return MessageChain.create([Plain('该账号不存在！')])
            elif subcommand.__contains__('list'):
                if not hasattr(self, 'friend'):
                    return MessageChain.create([Plain('请私聊使用该命令!')])
                with MysqlDao() as db:
                    res = db.query('SELECT phone FROM Plugin_NetEase_Account WHERE qid=%s', [self.friend.id])
                    return MessageChain.create([Plain('\n'.join([f'{phone[0]}' for phone in res]))])
            elif subcommand.__contains__('rp'):
                req = json.loads(await doHttpRequest('https://api.muxiaoguo.cn/api/163reping', 'GET'))
                ans = req['data']
                return MessageChain.create([
                    Plain('歌曲：%s\r\n' % ans['songName']),
                    Plain('昵称：%s\r\n' % ans['nickname']),
                    Plain('评论：%s' % ans['content'])
                ])
            else:
                return self.args_error()
        except Exception as e:
            logger.exception(e)
            return self.unkown_error()


class Tasker(Scheduler):
    cron = '0 8 * * * 0'

    async def process(self):
        with MysqlDao() as db:
            accounts = db.query(
                'SELECT qid, phone, pwd FROM Plugin_NetEase_Account'
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


class DB(InitDB):

    async def process(self):
        with MysqlDao() as __db:
            __db.update(
                "create table if not exists Plugin_NetEase_Account( \
                    qid char(12) not null comment 'QQ号', \
                    phone char(11) not null comment '登录手机', \
                    pwd char(20) not null comment '登录密码')"
            )


if __name__ == '__main__':
    a = Module(MessageChain.create([Plain('.wyy rp')]))
    asyncio.run(a.get_resp())
    print(a.resp)
