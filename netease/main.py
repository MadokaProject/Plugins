import base64
import hashlib
import json
from typing import Union

import requests
from Crypto.Cipher import AES
from peewee import IntegrityError

from app.core.app import AppCore
from app.util.alconna import Subcommand, Args, Arpamar, Commander
from app.util.graia import (
    Ariadne,
    Friend,
    FriendMessage,
    Group,
    GraiaScheduler,
    timers,
    message,
)
from app.util.network import general_request
from app.util.phrases import *
from .database.database import PluginNeteaseAccount as DBNetease

core: AppCore = AppCore()
app: Ariadne = core.get_app()
sche: GraiaScheduler = core.get_scheduler()
command = Commander(
    "wyy",
    "网易云",
    Subcommand("rp", help_text="网易云热评"),
    Subcommand("qd", help_text="立即进行一次签到", args=Args["phone", int]["password", str]),
    Subcommand("add", help_text="添加自动签到", args=Args["phone", int]["password", str]),
    Subcommand("remove", help_text="移除指定账号的自动签到", args=Args["phone", int]),
    Subcommand("list", help_text="列出你添加的自动签到账号"),
    help_text="网易云: 为保证账号安全, 签到服务仅私发有效",
)


@command.parse("qd", events=[FriendMessage])
async def qd_netease(sender: Friend, cmd: Arpamar):
    await NetEase_process_event(sender.id, cmd.query("phone"), cmd.query("password"))


@command.parse("add", events=[FriendMessage])
async def add_netease(sender: Friend, cmd: Arpamar):
    try:
        DBNetease.create(
            qid=sender.id, phone=cmd.query("phone"), pwd=cmd.query("password")
        )
        message("添加成功").target(sender).send()
    except IntegrityError:
        message("该账号已存在").target(sender).send()


@command.parse("remove", events=[FriendMessage])
async def remove_netease(sender: Friend, cmd: Arpamar):
    if DBNetease.get_or_none(qid=sender.id, phone=cmd.query("phone")):
        DBNetease.delete().where(
            DBNetease.qid == sender.id, DBNetease.phone == cmd.query("phone")
        ).execute()
        message("移除成功！").target(sender).send()
    else:
        message("该账号不存在！").target(sender).send()


@command.parse("list", events=[FriendMessage])
async def list_netease(sender: Friend):
    message(
        "\n".join(
            res.phone for res in DBNetease.select().where(DBNetease.qid == sender.id)
        )
    ).target(sender).send()


@command.parse("rp")
async def rp_netease(sender: Union[Friend, Group]):
    req = await general_request(
        "https://v.api.aa1.cn/api/api-wenan-wangyiyunreping/index.php?aa1=text", "GET"
    )
    message(req.strip("<p>").strip("</p>")).target(sender).send()


@sche.schedule(timers.crontabify("0 8 * * * 0"))
async def tasker():
    for res in DBNetease.select():
        message(f"正在进行账号{res.phone}" + "的自动签到任务\r\n下次运行时间为: 8:00").target(
            res.qid
        ).send()
        await NetEase_process_event(int(res.qid), res.phone, res.pwd)


def encrypt(key, text):
    cryptor = AES.new(key.encode("utf8"), AES.MODE_CBC, b"0102030405060708")
    length = 16
    count = len(text.encode("utf-8"))
    add = length - (count % length) if count % length != 0 else 16
    pad = chr(add)
    text1 = text + (pad * add)
    ciphertext = cryptor.encrypt(text1.encode("utf8"))
    return str(base64.b64encode(ciphertext), encoding="utf-8")


def md5(text):
    hl = hashlib.md5()
    hl.update(text.encode(encoding="utf-8"))
    return hl.hexdigest()


def protect(text):
    return {
        "params": encrypt("TA3YiYCfY2dDJQgg", encrypt("0CoJUm6Qyw8W8jud", text)),
        "encSecKey": "84ca47bca10bad09a6b04c5c927ef077d9b9f1e37098aa3eac6ea70eb59df0aa28b691b7e75e4f1f9831754919ea784c8f74fbfadf2898b0be17849fd656060162857830e241aba44991601f137624094c114ea8d17bce815b0cd4e5b8e2fbaba978c6d1d14dc3d1faf852bdd28818031ccdaaa13a6018e1024e2aae98844210",
    }


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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36",
        "Referer": "http://music.163.com/",
        "Accept-Encoding": "gzip, deflate",
    }
    headers2 = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36",
        "Referer": "http://music.163.com/",
        "Accept-Encoding": "gzip, deflate",
        "Cookie": "os=pc; osver=Microsoft-Windows-10-Professional-build-10586-64bit; appver=2.0.3.131777; channel=netease; __remember_me=true;",
    }

    res = s.post(url=url, data=protect(json.dumps(logindata)), headers=headers2)
    temp_cookie = res.cookies
    obj = json.loads(res.text)
    if obj["code"] == 200:
        message(f"{phone}：登录成功！").target(qid).send()
    else:
        message(f"{phone}：登录失败！请检查密码是否正确！" + str(obj["code"])).target(qid).send()
        return obj["code"]

    res = s.post(url=url2, data=protect('{"type":0}'), headers=headers)
    obj = json.loads(res.text)
    if obj["code"] == 200:
        message(f"{phone}：签到成功，经验+" + str(obj["point"])).target(qid).send()
    elif obj["code"] == -2:
        message(f"{phone}：重复签到").target(qid).send()

    else:
        message(f"{phone}：签到时发生错误：" + obj["msg"]).target(qid).send()
    res = s.post(
        url=url3,
        data=protect(
            '{"csrf_token":"'
            + requests.utils.dict_from_cookiejar(temp_cookie)["__csrf"]
            + '"}'
        ),
        headers=headers,
    )
    obj = json.loads(res.text, strict=False)
    for x in obj["recommend"]:
        url = (
            "https://music.163.com/weapi/v3/playlist/detail?csrf_token="
            + requests.utils.dict_from_cookiejar(temp_cookie)["__csrf"]
        )
        data = {
            "id": x["id"],
            "n": 1000,
            "csrf_token": requests.utils.dict_from_cookiejar(temp_cookie)["__csrf"],
        }
        res = s.post(url, protect(json.dumps(data)), headers=headers)
        obj = json.loads(res.text, strict=False)
        buffer = []
        count = 0
        for j in obj["playlist"]["trackIds"]:
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
    postdata = {"logs": json.dumps(buffer)}
    res = s.post(url, protect(json.dumps(postdata)))
    obj = json.loads(res.text, strict=False)
    if obj["code"] == 200:
        message(f"{phone}：刷单成功！共{str(count)}首").target(qid).send()
        return
    else:
        message(f"{phone}：发生错误：" + str(obj["code"]) + obj["message"]).target(qid).send()
        return obj["code"]
