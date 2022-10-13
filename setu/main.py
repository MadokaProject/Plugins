from typing import Union

from arclet.alconna import Alconna, Args, Subcommand, Option, Arpamar
from graia.ariadne.model import Friend, Member, Group
from loguru import logger

from app.core.commander import CommandDelegateManager
from app.core.settings import CONFIG
from app.entities.game import BotGame
from app.util.control import Permission
from app.util.network import general_request
from app.util.online_config import save_config
from app.util.phrases import *

num = {
    # c: cost
    "normal": {"c": 10},
    "search": {"c": 15},
}

manager: CommandDelegateManager = CommandDelegateManager()


@manager.register(
    entry="setu",
    brief_help="涩图",
    alc=Alconna(
        headers=manager.headers,
        command="setu",
        options=[
            Option("--uid|-u", help_text="指定作者信息", args=Args["uid", str]),
            Option("--tag|-t", help_text="指定标签(多个相似标签使用 | 分隔", args=Args["tag", str]),
            Subcommand(
                "r18", help_text="开关R-18模式(慎用)[默认关闭]", args=Args["r18", bool, False]
            ),
        ],
        help_text="消耗10资金随机获取一张setu, 消耗15资金指定特定信息搜索",
    ),
)
async def process(
    target: Union[Friend, Member], sender: Union[Friend, Group], command: Arpamar
):
    sender_id = str(sender.id)
    r18 = (
        CONFIG[str(sender_id)]["setu_R18"]
        if sender_id in CONFIG and "setu_R18" in CONFIG[sender_id]
        else 0
    )
    try:
        if _r18 := command.query("r18"):
            if not isinstance(sender, Group):
                return
            if not Permission.manual(target, Permission.MASTER):
                return not_admin()
            await save_config("setu_R18", sender.id, _r18)
            if sender_id not in CONFIG:
                CONFIG[sender_id] = {}
            CONFIG[str(sender.id)].update({"setu_R18": _r18})
            return MessageChain([Plain("设置成功！")])
        else:
            # 判断积分是否足够，如果无，要求报错并返回
            the_one = BotGame(target.id)
            if await the_one.coins < num["normal"]["c"]:
                return point_not_enough()
            keyword = {"r18": r18}
            if uid := command.query("uid"):
                keyword["uid"] = uid
            if tag := command.query("tag"):
                keyword["tag"] = tag
            response = await general_request(
                url="https://api.lolicon.app/setu/v2",
                method="GET",
                _type="JSON",
                params=keyword,
                headers={"Content-Type": "application/json"},
            )
            if response["data"]:
                await the_one.update_coin(-num["normal"]["c"])
                return MessageChain(
                    [
                        Image(
                            url=response["data"][0]["urls"]["original"].replace(
                                "i.pixiv.cat", "pixiv.a-f.workers.dev"
                            )
                        )
                    ]
                )
            else:
                return MessageChain([Plain("setu: 获取失败")])
    except Exception as e:
        logger.exception(e)
        return unknown_error()
