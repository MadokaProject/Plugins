from typing import Union

from arclet.alconna import Alconna, Option, Arpamar
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.model import Friend, Group, Member
from graia.scheduler import GraiaScheduler, timers
from loguru import logger

from app.core.app import AppCore
from app.core.config import Config
from app.core.commander import CommandDelegateManager
from app.util.control import Permission
from app.util.network import general_request
from app.util.phrases import print_help, unknown_error, not_admin
from .database.database import News


core: AppCore = AppCore()
app: Ariadne = core.get_app()
sche: GraiaScheduler = core.get_scheduler()
manager: CommandDelegateManager = CommandDelegateManager()


@manager.register(
    entry="news",
    brief_help="新闻",
    alc=Alconna(
        headers=manager.headers,
        command="news",
        options=[Option("on", help_text="开启新闻推送"), Option("off", help_text="关闭新闻推送")],
        help_text="新闻",
    ),
)
async def process(
    target: Union[Friend, Member],
    sender: Union[Friend, Group],
    cmd: Arpamar,
    alc: Alconna,
):
    if not cmd.options:
        return await print_help(alc.get_help())
    try:
        if isinstance(sender, Friend):
            model = "friend"
        elif Permission.manual(target, level=Permission.GROUP_ADMIN):
            model = "group"
        else:
            return await not_admin()
        News.replace(uid=sender.id, model=model, status=cmd.find("on")).execute()
        return MessageChain("设置成功！" + "将于每日 8:00 推送日报" if cmd.find("on") else "")
    except Exception as e:
        logger.error(e)
        return await unknown_error()


@sche.schedule(timers.crontabify("0 8 * * * 0"))
async def send_60s_news():
    logger.info("Sending 60s news...")
    await app.send_friend_message(Config().MASTER_QQ, MessageChain("正在推送每日早报"))
    msg = MessageChain(
        [
            Image(
                data_bytes=await general_request(
                    "http://bjb.yunwj.top/php/tp/1.jpg", _type="byte"
                )
            )
        ]
    )
    for news in News.select().where(News.status == True):
        if news.model == "friend":
            await app.send_friend_message(news.uid, msg)
        else:
            await app.send_group_message(news.uid, msg)
