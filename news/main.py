from typing import Union

from loguru import logger

from app.core.app import AppCore
from app.core.config import Config
from app.util.alconna import Option, Arpamar, Commander
from app.util.graia import (
    Ariadne,
    Image,
    Friend,
    Group,
    Member,
    GraiaScheduler,
    timers,
    message,
)
from app.util.control import Permission
from app.util.network import general_request
from app.util.phrases import not_admin
from .database.database import News


core: AppCore = AppCore()
app: Ariadne = core.get_app()
sche: GraiaScheduler = core.get_scheduler()
command = Commander(
    "news",
    "新闻",
    Option("on", help_text="开启新闻推送"),
    Option("off", help_text="关闭新闻推送"),
)


@command.parse(["on", "off"])
async def process(
    target: Union[Friend, Member],
    sender: Union[Friend, Group],
    cmd: Arpamar,
):
    if isinstance(sender, Friend):
        model = "friend"
    elif Permission.manual(target, level=Permission.GROUP_ADMIN):
        model = "group"
    else:
        return await not_admin(sender)
    News.replace(uid=sender.id, model=model, status=cmd.find("on")).execute()
    message("设置成功！" + "将于每日 8:00 推送日报" if cmd.find("on") else "").target(sender).send()


@sche.schedule(timers.crontabify("0 8 * * * 0"))
async def send_60s_news():
    logger.info("Sending 60s news...")
    message("正在推送每日早报").target(Config.master_qq).send()
    msg = Image(
        data_bytes=await general_request(
            "http://bjb.yunwj.top/php/tp/1.jpg", _type="byte"
        )
    )
    for news in News.select().where(News.status == True):
        message(msg).target(news.uid).send()
