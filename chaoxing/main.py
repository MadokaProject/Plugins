import asyncio
from datetime import datetime
from typing import List, Dict

from loguru import logger
from prettytable import PrettyTable

from app.core.app import AppCore
from app.util.alconna import Subcommand, Args, Arpamar, Commander
from app.util.graia import (
    Ariadne,
    FriendMessage,
    Friend,
    FunctionWaiter,
    MessageChain,
    GraiaScheduler,
    timers,
    message,
)
from app.util.phrases import *
from app.util.text2image import create_image
from .database.database import ChaoxingSign as DBChaoxingSign
from .sign import AutoSign

core: AppCore = AppCore()
app: Ariadne = core.get_app()
sche: GraiaScheduler = core.get_scheduler()
command = Commander(
    "xxt",
    "学习通",
    Subcommand("签到", help_text="立即进行一次签到操作"),
    Subcommand("自动签到", args=Args["status", [0, 1]], help_text="开关自动签到"),
    Subcommand("配置", help_text="配置学习通账号信息"),
    help_text="学习通签到工具",
)


@command.parse("签到", events=[FriendMessage])
async def signin_chaoxing(sender: Friend):
    info = await get_config(sender.id)
    if not info:
        return message("你还未配置账号信息，请私聊我进行配置").target(sender).send()
    auto_sign = AutoSign(
        username=info.username,
        password=info.password,
        latitude=info.latitude,
        longitude=info.longitude,
        clientip=info.clientip,
        address=info.address,
    )
    results: List[List[Dict]] = await auto_sign.start_sign_task()
    await auto_sign.close_session()
    message(
        Image(data_bytes=await create_image((await send_message(results)).get_string()))
        if results
        else Plain("暂无签到任务")
    ).target(sender).send()


@command.parse("自动签到", events=[FriendMessage])
async def auto_chaoxing(sender: Friend, cmd: Arpamar):
    if not await get_config(sender.id):
        return message("你还未配置账号信息，请私聊我进行配置").target(sender).send()
    DBChaoxingSign.update(auto_sign=cmd.query("status")).where(
        DBChaoxingSign.qid == sender.id
    )
    message("开启成功" if cmd.query("status") else "关闭成功").target(sender).send()


@command.parse("配置", events=[FriendMessage])
async def setting_config(sender: Friend):
    async def waiter(waiter_friend: Friend, waiter_message: MessageChain):
        if waiter_friend.id == sender.id:
            waiter_saying = waiter_message.display
            if waiter_saying == "取消":
                raise asyncio.CancelledError
            return waiter_saying

    async def answer_waiter(waiter_friend: Friend, waiter_message: MessageChain):
        if waiter_friend.id == sender.id:
            waiter_saying = waiter_message.display
            if waiter_saying == "是":
                return True
            elif waiter_saying == "否":
                return False
            else:
                await message("请回答：是 / 否").target(waiter_friend).immediately_send()

    try:
        if await get_config(sender.id):
            await message("你已经配置了账号信息，是否重新配置？").target(sender).immediately_send()
            if not await FunctionWaiter(answer_waiter, [FriendMessage]).wait(15):
                return
        await message("开始配置，若想中途退出配置请发送：取消").target(sender).immediately_send()
        await message("请输入用户名（手机号）").immediately_send()
        username = await FunctionWaiter(waiter, [FriendMessage]).wait(60)
        await message("请输入密码").target(sender).immediately_send()
        password = await FunctionWaiter(waiter, [FriendMessage]).wait(60)
        await message("请输入定位纬度").target(sender).immediately_send()
        latitude = await FunctionWaiter(waiter, [FriendMessage]).wait(60)
        await message("请输入定位经度").target(sender).immediately_send()
        longitude = await FunctionWaiter(waiter, [FriendMessage]).wait(60)
        await message("请输入你的IP地址").target(sender).immediately_send()
        clientip = await FunctionWaiter(waiter, [FriendMessage]).wait(60)
        await message("请输入定位地址名").target(sender).immediately_send()
        address = await FunctionWaiter(waiter, [FriendMessage]).wait(60)
        await message(
            [
                Plain("配置完成，请检查你的配置信息\r\n"),
                Plain(f"用户名：{username}\r\n密码：{password}\r\n纬度：{latitude}\r\n"),
                Plain(f"经度：{longitude}\r\nIP地址：{clientip}\r\n地址名：{address}\r\n"),
                Plain("是否保存？"),
            ]
        ).target(sender).immediately_send()
        if await FunctionWaiter(answer_waiter, [FriendMessage]).wait(30):
            DBChaoxingSign.replace(
                qid=sender.id,
                username=username,
                password=password,
                latitude=latitude,
                longitude=longitude,
                clientip=clientip,
                address=address,
            ).execute()
            return message("配置成功！").target(sender).send()
    except asyncio.TimeoutError:
        return message("等待超时").target(sender).send()
    except asyncio.CancelledError:
        return message("取消配置!").target(sender).send()


async def get_config(user_id):
    return DBChaoxingSign.get_or_none(DBChaoxingSign.qid == user_id)


async def gen_run(info: dict) -> List[List[Dict]]:
    auto_sign = AutoSign(
        username=info["username"],
        password=info["password"],
        latitude=info["latitude"],
        longitude=info["longitude"],
        clientip=info["clientip"],
        address=info.get("address", None),
    )
    result: List[List[Dict]] = await auto_sign.start_sign_task()
    await auto_sign.close_session()
    return result


async def send_message(datas):
    msg = PrettyTable()
    msg.field_names = ["课程名", "签到时间", "签到状态"]
    for data in datas:
        if data:
            msg.add_row([data["name"], data["date"], data["status"]])
    msg.align = "r"
    return msg


@sche.schedule(timers.crontabify("* 8-17 * * * 10"))
@logger.catch()
async def tasker():
    logger.info("chaoxing tasker is running ...")
    for user in DBChaoxingSign.select().where(
        DBChaoxingSign.expiration_time >= datetime.now(), DBChaoxingSign.auto_sign == 1
    ):
        if result := await gen_run(
            {
                "username": user.username,
                "password": user.password,
                "latitude": user.latitude,
                "longitude": user.longitude,
                "clientip": user.clientip,
                "address": user.address,
            }
        ):
            message(
                Image(
                    data_bytes=await create_image(
                        (await send_message(result)).get_string()
                    )
                )
            ).target(int(user.qid)).send()
