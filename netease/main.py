import base64
import hashlib
import json
from typing import Union

import requests
from Crypto.Cipher import AES
from arclet.alconna import Alconna, Subcommand, Args, Arpamar
from graia.ariadne.app import Ariadne
from graia.ariadne.model import Friend, Member, Group
from graia.scheduler import GraiaScheduler, timers
from loguru import logger

from app.core.app import AppCore
from app.core.commander import CommandDelegateManager
from app.util.dao import MysqlDao
from app.util.network import general_request
from app.util.phrases import *

core: AppCore = AppCore()
app: Ariadne = core.get_app()
sche: GraiaScheduler = core.get_scheduler()
manager: CommandDelegateManager = CommandDelegateManager()


@manager.register(
    entry='wyy',
    brief_help='网易云',
    alc=Alconna(
        headers=manager.headers,
        command='wyy',
        options=[
            Subcommand('rp', help_text='网易云热评'),
            Subcommand('qd', help_text='立即进行一次签到', args=Args['phone', int]['password', str]),
            Subcommand('add', help_text='添加自动签到', args=Args['phone', int]['password', str]),
            Subcommand('remove', help_text='移除指定账号的自动签到', args=Args['phone', int]),
            Subcommand('list', help_text='列出你添加的自动签到账号')
        ],
        help_text='网易云: 为保证账号安全, 签到服务仅私发有效'
    ))
async def process(target: Union[Friend, Member], sender: Union[Friend, Group], command: Arpamar, alc: Alconna):
    components = command.options.copy()
    components.update(command.subcommands)
    if not components:
        return await print_help(alc.get_help())
    try:
        if qd := components.get('qd'):
            if not isinstance(sender, Friend):
                return MessageChain([Plain('请私聊使用该命令!')])
            await NetEase_process_event(target.id, qd['phone'], qd['password'])
        elif add := components.get('add'):
            if not isinstance(sender, Friend):
                return MessageChain([Plain('请私聊使用该命令!')])
            with MysqlDao() as db:
                if not db.query('SELECT * FROM Plugin_NetEase_Account WHERE phone=%s', [add['phone']]):
                    if not db.update(
                            'INSERT INTO Plugin_NetEase_Account (qid, phone, pwd) VALUES (%s, %s, %s)',
                            [target.id, add['phone'], add['password']]
                    ):
                        raise Exception()
                    return MessageChain([Plain('添加成功')])
                else:
                    return MessageChain([Plain('该账号已存在！')])
        elif remove := components.get('remove'):
            if not isinstance(sender, Friend):
                return MessageChain([Plain('请私聊使用该命令!')])
            with MysqlDao() as db:
                if db.query('SELECT * FROM Plugin_NetEase_Account WHERE qid=%s and phone=%s',
                            [target.id, remove['phone']]):
                    if db.update('DELETE FROM Plugin_NetEase_Account WHERE qid=%s and phone=%s',
                                 [target.id, remove['phone']]):
                        return MessageChain([Plain('移除成功！')])
                else:
                    return MessageChain([Plain('该账号不存在！')])
        elif command.find('list'):
            if not isinstance(sender, Friend):
                return MessageChain([Plain('请私聊使用该命令!')])
            with MysqlDao() as db:
                res = db.query('SELECT phone FROM Plugin_NetEase_Account WHERE qid=%s', [target.id])
                return MessageChain([Plain('\n'.join([f'{phone[0]}' for phone in res]))])
        elif command.find('rp'):
            req = await general_request('https://v.api.aa1.cn/api/api-wenan-wangyiyunreping/index.php?aa1=text', 'GET')
            return MessageChain(req.strip('<p>').strip('</p>'))
        else:
            return args_error()
    except Exception as e:
        logger.exception(e)
        return unknown_error()


@sche.schedule(timers.crontabify('0 8 * * * 0'))
async def tasker():
    with MysqlDao() as db:
        accounts = db.query(
            'SELECT qid, phone, pwd FROM Plugin_NetEase_Account'
        )
        for (qid, phone, pwd) in accounts:
            await app.send_friend_message(int(qid), MessageChain([
                Plain("正在进行账号" + phone + "的自动签到任务\r\n下次运行时间为：8:00")
            ]))
            await NetEase_process_event(int(qid), phone, pwd)


def encrypt(key, text):
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
    crypted_str = str(base64.b64encode(ciphertext), encoding='utf-8')
    return crypted_str


def md5(text):
    hl = hashlib.md5()
    hl.update(text.encode(encoding='utf-8'))
    return hl.hexdigest()


def protect(text):
    return {"params": encrypt('TA3YiYCfY2dDJQgg', encrypt('0CoJUm6Qyw8W8jud', text)),
            "encSecKey": "84ca47bca10bad09a6b04c5c927ef077d9b9f1e37098aa3eac6ea70eb59df0aa28b691b7e75e4f1f9831754919ea784c8f74fbfadf2898b0be17849fd656060162857830e241aba44991601f137624094c114ea8d17bce815b0cd4e5b8e2fbaba978c6d1d14dc3d1faf852bdd28818031ccdaaa13a6018e1024e2aae98844210"}


async def NetEase_process_event(qid, phone, pwd):
    s = requests.Session()
    header = {}
    url = "https://music.163.com/weapi/login/cellphone"
    url2 = "https://music.163.com/weapi/point/dailyTask"
    url3 = "https://music.163.com/weapi/v1/discovery/recommend/resource"
    logindata = {
        "phone": phone,
        "countrycode": "86",
        "password": md5(pwd),
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

    res = s.post(url=url, data=protect(json.dumps(logindata)), headers=headers2)
    temp_cookie = res.cookies
    object = json.loads(res.text)
    if object['code'] == 200:
        await app.send_friend_message(qid, MessageChain([
            Plain(phone + "：登录成功！")
        ]))
    else:
        await app.send_friend_message(qid, MessageChain([
            Plain(phone + "：登录失败！请检查密码是否正确！" + str(object['code']))
        ]))
        return object['code']

    res = s.post(url=url2, data=protect('{"type":0}'), headers=headers)
    object = json.loads(res.text)
    if object['code'] != 200 and object['code'] != -2:
        await app.send_friend_message(qid, MessageChain([
            Plain(phone + "：签到时发生错误：" + object['msg'])
        ]))
    else:
        if object['code'] == 200:
            await app.send_friend_message(qid, MessageChain([
                Plain(phone + "：签到成功，经验+" + str(object['point']))
            ]))
        else:
            await app.send_friend_message(qid, MessageChain([
                Plain(phone + "：重复签到")
            ]))

    res = s.post(url=url3,
                 data=protect(
                     '{"csrf_token":"' + requests.utils.dict_from_cookiejar(temp_cookie)['__csrf'] + '"}'),
                 headers=headers)
    object = json.loads(res.text, strict=False)
    for x in object['recommend']:
        url = 'https://music.163.com/weapi/v3/playlist/detail?csrf_token=' + \
              requests.utils.dict_from_cookiejar(temp_cookie)[
                  '__csrf']
        data = {
            'id': x['id'],
            'n': 1000,
            'csrf_token': requests.utils.dict_from_cookiejar(temp_cookie)['__csrf'],
        }
        res = s.post(url, protect(json.dumps(data)), headers=headers)
        object = json.loads(res.text, strict=False)
        buffer = []
        count = 0
        for j in object['playlist']['trackIds']:
            data2 = {"action": "play", "json": {}}
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
    res = s.post(url, protect(json.dumps(postdata)))
    object = json.loads(res.text, strict=False)
    if object['code'] == 200:
        await app.send_friend_message(qid, MessageChain([
            Plain(phone + "：刷单成功！共" + str(count) + "首")
        ]))
        return
    else:
        await app.send_friend_message(qid, MessageChain([
            Plain(phone + "：发生错误：" + str(object['code']) + object['message'])
        ]))
        return object['code']
