import time
import asyncio
import numpy as np

from io import BytesIO
from loguru import logger
from pyzbar import pyzbar
from PIL import Image as IMG
from arclet.alconna import AllParam

from app.core.config import Config
from app.core.settings import BANNED_USER
from app.entities.user import BotUser
from app.entities.game import BotGame
from app.util.alconna import Commander, Args, Subcommand, Option, Arpamar
from app.util.baidu_ai import text_moderation_async, image_moderation_async
from app.util.graia import At, Image, Plain, Source, Group, Member, GroupMessage, MessageChain, FunctionWaiter, message
from app.util.control import Permission
from app.util.network import general_request
from app.util.text2image import create_image
from app.util.tools import data_path

from .db import (
    get_bottle,
    throw_bottle,
    clear_bottle,
    count_bottle,
    delete_bottle,
    get_my_bottles,
    get_bottle_by_id,
    add_bottle_score,
    add_bottle_discuss,
    get_bottle_discuss,
    get_bottle_score_avg,
)

IMAGE_PATH = data_path("extension_data", "drifting_bottle", "image")
IMAGE_PATH.mkdir(parents=True, exist_ok=True)


command = Commander(
    "plp",
    "漂流瓶",
    Subcommand(
        "丢",
        help_text="丢一个漂流瓶",
        args=Args["content;O", AllParam],
        options=[Option("--pic|-P|-p", help_text="手动发送图片"), Option("--skip-review|-s", help_text="跳过审核")],
    ),
    Subcommand("捞", help_text="捞一个漂流瓶"),
    Subcommand("评分", help_text="对一个漂流瓶进行评分", args=Args["bottleid", int]["score", int]),
    Subcommand("评论", help_text="对一个漂流瓶进行评论", args=Args["bottleid", int]["comment", AllParam]),
    Subcommand("查", help_text="查看漂流瓶", args=Args["bottleid;O", int]),
    Subcommand("删", help_text="删除一个漂流瓶", args=Args["bottleid", int]),
    Subcommand("清空", help_text="清空漂流瓶"),
)


@command.parse("丢", events=[GroupMessage], friend_limit=30)
async def throw_bottle_handler(group: Group, member: Member, source: Source, cmd: Arpamar):
    async def image_waiter(waiter1_group: Group, waiter1_member: Member, waiter1_message: MessageChain):
        if waiter1_group.id == group.id and waiter1_member.id == member.id:
            if waiter1_message.has(Image):
                return await waiter1_message.get_first(Image).get_bytes()
            else:
                return False

    text = None
    image_name = None
    image = None
    if message_chain := cmd.query("content"):
        message_chain = MessageChain(message_chain)
        if message_chain.has(Plain):
            text = MessageChain(message_chain.get(Plain)).merge().display.strip()
            if text:
                for i in ["magnet:", "http"]:
                    if i in text:
                        return message("您？").target(group).quote(source).send()
                if cmd.find("丢.skip-review") and Permission.manual(member, Permission.SUPER_ADMIN):
                    logger.info("跳过审核")
                else:
                    logger.info("开始审核")
                    moderation = await text_moderation_async(text)
                    if moderation["status"] == "error":
                        return message("漂流瓶内容审核失败，请稍后重新丢漂流瓶！").target(group).quote(source).send()
                    elif not moderation["status"]:
                        return (
                            message(f"你的漂流瓶内可能包含违规内容: {moderation['message']}，请检查后重新丢漂流瓶！")
                            .target(group)
                            .quote(source)
                            .send()
                        )
            elif len(text) > 400:
                return message("你的漂流瓶内容过长（400）！").target(group).quote(source).send()

        if message_chain.has(Image):
            if cmd.find("丢.pic"):
                return message("使用手动发图参数后不可附带图片").target(group).quote(source).send()
            elif len(message_chain.get(Image)) > 1:
                return message("丢漂流瓶只能携带一张图片哦！").target(group).quote(source).send()
            else:
                image = await message_chain.get_first(Image).get_bytes()

    if cmd.find("丢.pic"):
        message("请在 30 秒内发送你要附带的图片").target(group).quote(source).send()
        try:
            image = await FunctionWaiter(image_waiter, events=[GroupMessage]).wait(30)
            if image:
                message("图片已接收，请稍等").target(group).quote(source).send()
            else:
                return message("你发送的不是“一张”图片，请重试").target(group).quote(source).send()
        except asyncio.TimeoutError:
            return message("图片等待超时").target(group).quote(source).send()

    if image:
        if cmd.find("丢.skip-review") and Permission.manual(member, Permission.SUPER_ADMIN):
            logger.info("跳过审核")
        else:
            logger.info("开始审核")
            moderation = await image_moderation_async(image)
            if not moderation["status"]:
                return message(f"你的漂流瓶包含违规内容: {moderation['message']}，请检查后重新丢漂流瓶！").target(group).quote(source).send()
            elif moderation["status"] == "error":
                return message("图片审核失败，请稍后重试！").target(group).quote(source).send()

        image_name = f"{time.time()}.jfif"
        IMAGE_PATH.joinpath(image_name).write_bytes(image)
        if image:
            if cmd.find("丢.skip-review") and Permission.manual(member, Permission.SUPER_ADMIN):
                logger.info("跳过审核")
            else:
                if qrdecode(image):
                    if Permission.manual(member):
                        await BotUser(member).grant_level(0)
                        BANNED_USER.append(member.id)
                    return message("漂流瓶不能携带二维码哦！你已被拉黑").target(group).at(member).send()
        else:
            return message("图片异常，请稍后重试！").target(group).at(member).send()

    if text or image_name:
        if await BotGame(member.id).reduce_coin(8):
            bottle = throw_bottle(member, text, image_name)
            in_bottle_text = "一段文字" if text else ""
            in_bottle_image = "一张图片" if image_name else ""
            in_bottle_and = "和" if in_bottle_text and in_bottle_image else ""
            in_bottle = in_bottle_text + in_bottle_and + in_bottle_image
            message(f" 成功购买漂流瓶并丢出！\n瓶子里有{in_bottle}\n瓶子编号为: {bottle}").target(group).quote(source).at(member).send()
        else:
            message(f"你的{Config.coin_settings.name}不足，无法丢漂流瓶！").target(group).quote(source).send()
    else:
        return message("丢漂流瓶请加上漂流瓶的内容！").target(group).quote(source).send()


@command.parse("捞", events=[GroupMessage], friend_limit=30)
async def pick_bottle_handler(group: Group, member: Member):
    bottle = get_bottle()

    if bottle is None:
        return message("没有漂流瓶可以捡哦！").target(group).at(member).send()
    if not await BotGame(member.id).reduce_coin(2):
        return message(f"你的{Config.coin_settings.name}不足，无法捞漂流瓶！").target(group).at(member).send()
    bottle_score = get_bottle_score_avg(bottle["id"])
    bottle_discuss = get_bottle_discuss(bottle["id"])
    score_msg = f"瓶子的评分为：{bottle_score}" if bottle_score else "本漂流瓶目前还没有评分"
    discuss_msg = f"\n这个瓶子当前有 {len(bottle_discuss)} 条评论\n" if bottle_discuss else "\n本漂流瓶目前还没有评论"

    times = bottle["fishing_times"]
    times_msg = f"本漂流瓶已经被捞了{str(times)}次" if times > 0 else "本漂流瓶还没有被捞到过"
    msg = [
        At(member),
        f" 你捡到了一个漂流瓶！\n瓶子编号为：{bottle['id']}\n{times_msg}\n{score_msg}\n" "漂流瓶内容为：\n",
    ]
    if bottle["text"] is not None:
        image = await create_image(bottle["text"])
        msg.append(Image(data_bytes=image))
    if bottle["image"] is not None:
        if bottle["text"]:
            msg.append("\n")
        msg.append(Image(path=IMAGE_PATH.joinpath(bottle["image"])))
    msg.append(discuss_msg)
    if bottle_discuss:
        discuss_img = [
            f"{i} 楼. {discuss.discuss_time} | {discuss.member}：\n      > {discuss.discuss}"
            for i, discuss in enumerate(bottle_discuss, start=1)
        ]

        discuss_img = await create_image("\n".join(discuss_img))
        msg.append(Image(data_bytes=discuss_img))
    message(msg).target(group).send()


@command.parse("清空", events=[GroupMessage], permission=Permission.MASTER)
async def clear_bottle_handler(group: Group):
    clear_bottle()
    message("漂流瓶已经清空！").target(group).send()


@command.parse("查", events=[GroupMessage])
async def drifting_bottle_handler(group: Group, member: Member, source: Source, cmd: Arpamar):
    if bottle_id := cmd.query("bottleid"):
        bottle = get_bottle_by_id(bottle_id)

        if not bottle:
            return message("没有这个漂流瓶！").target(group).send()

        bottle = bottle[0]
        if Permission.manual(member, Permission.MASTER) or bottle.member == member.id:
            bottle_score = get_bottle_score_avg(bottle_id)
            bottle_discuss = get_bottle_discuss(bottle_id)
            score_msg = f"瓶子的评分为：{bottle_score}" if bottle_score else "本漂流瓶目前还没有评分"
            discuss_msg = f"\n这个瓶子当前有 {len(bottle_discuss)} 条评论\n" if bottle_discuss else "\n本漂流瓶目前还没有评论"

            msg = [
                Plain(
                    f"漂流瓶编号为：{bottle.id}\n"
                    f"丢出时间为：{bottle.send_date}\n"
                    f"漂流瓶来自 {bottle.group} 群的 {bottle.member}\n{score_msg}\n"
                )
            ]
            if bottle.text is not None:
                image = await create_image(bottle.text)
                msg.append(Image(data_bytes=image))
            if bottle.image is not None:
                if bottle.text:
                    msg.append("\n")
                msg.append(Image(path=IMAGE_PATH.joinpath(bottle.image)))
            msg.append(discuss_msg)
            if bottle_discuss:
                discuss_img = [
                    f"{i} 楼. {discuss.discuss_time} | {discuss.member}：\n      > {discuss.discuss}"
                    for i, discuss in enumerate(bottle_discuss, start=1)
                ]
                discuss_img = await create_image("\n".join(discuss_img))
                msg.append(Image(data_bytes=discuss_img))
            message(msg).target(group).quote(source).send()
        else:
            message("你没有权限查看这个漂流瓶！").target(group).at(member).send()
    else:
        count = count_bottle()
        my_bottles = get_my_bottles(member)
        msg = [
            f"目前有 {count} 个漂流瓶在漂流" if count > 0 else "目前没有漂流瓶在漂流",
            "\n漂流瓶可以使用“.plp 捞”命令捞到，也可以使用“.plp 丢”命令丢出”\n可以使用“.plp 评分”为漂流瓶添加评分",
        ]
        if my_bottles:
            msg.append(f"\n截至目前你共丢出 {len(my_bottles)} 个漂流瓶：\n")
            my_bottles_str = "\n".join([f"编号：{x}，日期{x.send_date}，群号：{x.group}" for x in my_bottles])
            msg.append(Image(data_bytes=await create_image(my_bottles_str)))
        else:
            msg.append("\n截至目前你还没有丢出过漂流瓶")
        message(msg).target(group).quote(source).send()


@command.parse("删", events=[GroupMessage])
async def delete_bottle_handler(group: Group, member: Member, source: Source, cmd: Arpamar):
    bottle_id = cmd.query("bottleid")
    bottle = get_bottle_by_id(bottle_id)
    if not bottle:
        return message("没有这个漂流瓶！").target(group).quote(source).send()
    bottle = bottle[0]
    if Permission.manual(member, Permission.MASTER) or bottle.member == member.id:
        delete_bottle(bottle_id)
        message("漂流瓶已经删除！").target(group).quote(source).send()
    else:
        message("你没有权限删除这个漂流瓶！").target(group).quote(source).send()


def qrdecode(img):
    image = IMG.open(BytesIO(img))
    image_array = np.array(image)
    image_data = pyzbar.decode(image_array)
    return len(image_data)


@command.parse("评分", events=[GroupMessage], friend_limit=5)
async def bottle_score_handler(group: Group, member: Member, source: Source, cmd: Arpamar):
    bottle_id = cmd.query("bottleid")
    score = cmd.query("score")
    if get_bottle_by_id(bottle_id):
        if 1 <= score <= 5:
            if add_bottle_score(bottle_id, member, score):
                bottle_score = get_bottle_score_avg(bottle_id)
                message(f" 漂流瓶评分成功，当前评分{bottle_score}").target(group).quote(source).send()
            else:
                message(" 你已对该漂流瓶评过分，请勿重复评分").target(group).quote(source).send()
        else:
            message(" 评分仅可为1-5分").target(group).quote(source).send()
    else:
        message(" 没有这个漂流瓶").target(group).quote(source).send()


@command.parse("评论", events=[GroupMessage], friend_limit=5)
async def bottle_discuss_handler(group: Group, member: Member, source: Source, cmd: Arpamar):
    message_chain = MessageChain(cmd.query("comment"))
    if message_chain.has(Image):
        return message("不支持图片评论！").target(group).at(member).send()
    bottle_id = cmd.query("bottleid")
    discuss = message_chain.display
    if get_bottle_by_id(bottle_id):
        if 3 <= len(discuss) <= 500:
            moderation = await text_moderation_async(discuss)
            if moderation["status"] == "error":
                return message("评论内容审核失败，请稍后重新评论！").target(group).quote(source).send()
            elif not moderation["status"]:
                return message(f"你的评论内可能包含违规内容{moderation['message']}，请检查后重新评论！").target(group).quote(source).send()
            if add_bottle_discuss(bottle_id, member, discuss):
                bottle_discuss = get_bottle_discuss(bottle_id)
                message(f"漂流瓶评论成功，当前共有 {len(bottle_discuss)} 条评论").target(group).quote(source).send()
            else:
                message("你已对该漂流瓶发表过 3 条评论，无法再次发送").target(group).quote(source).send()
        else:
            message(" 评论字数需在 3-500 字之间").target(group).quote(source).send()
    else:
        message(" 没有这个漂流瓶").target(group).quote(source).send()
