from typing import Union

from app.entities.game import BotGame
from app.util.alconna import Args, Subcommand, Option, Arpamar, Commander
from app.util.graia import Friend, Member, Group, GroupMessage, message
from app.util.control import Permission
from app.util.network import general_request
from app.util.online_config import save_config, get_config
from app.util.phrases import *

num = {
    # c: cost
    "normal": {"c": 10},
    "search": {"c": 15},
}

command = Commander(
    "setu",
    "涩图",
    Option("--uid|-u", help_text="指定作者信息", args=Args["uid", str]),
    Option("--tag|-t", help_text="指定标签(多个相似标签使用 | 分隔", args=Args["tag", str]),
    Subcommand("r18", help_text="开关R-18模式(慎用)[默认关闭]", args=Args["r18", bool, False]),
    help_text="消耗10资金随机获取一张setu, 消耗15资金指定特定信息搜索",
)


@command.no_match()
async def get_setu(
    target: Union[Friend, Member],
    sender: Union[Friend, Group],
    cmd: Arpamar,
):
    r18 = await get_config("setu_R18", sender) or 0
    the_one = BotGame(target.id)
    if await the_one.coins < num["normal"]["c"]:
        return point_not_enough(sender)
    keyword = {"r18": r18}
    if uid := cmd.query("uid"):
        keyword["uid"] = uid
    if tag := cmd.query("tag"):
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
        message(
            Image(
                url=response["data"][0]["urls"]["original"].replace(
                    "i.pixiv.cat", "pixiv.a-f.workers.dev"
                )
            )
        ).target(sender).send()
    else:
        message("setu: 获取失败").target(sender).send()


@command.parse("r18", events=[GroupMessage], permission=Permission.MASTER)
async def set_r18(sender: Group, cmd: Arpamar):
    await save_config("setu_R18", sender.id, cmd.query("r18"))
    message("设置成功！").target(sender).send()
