import asyncio
import random
from io import BytesIO
from typing import Union

from PIL import Image as IMG, ImageDraw, ImageFont
from arclet.alconna import Alconna, Subcommand, Arpamar
from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.element import At
from graia.ariadne.model import Group, Member, Friend
from graia.ariadne.util.interrupt import FunctionWaiter
from loguru import logger

from app.core.commander import CommandDelegateManager
from app.core.settings import *
from app.entities.game import BotGame
from app.util.phrases import *
from app.util.send_message import safeSendGroupMessage
from app.util.tools import to_thread, app_path

FONT_PATH = app_path().joinpath('resource/font')
font24 = ImageFont.truetype(str(FONT_PATH.joinpath("sarasa-mono-sc-semibold.ttf")), 24)

config: Config = Config()
manager: CommandDelegateManager = CommandDelegateManager()


@manager.register(
    entry='hr',
    brief_help='赛马小游戏',
    alc=Alconna(
        headers=manager.headers,
        command='hr',
        options=[
            Subcommand('start', help_text='开始一局赛马小游戏')
        ],
        help_text='赛马小游戏'
    ))
async def process(app: Ariadne, target: Union[Friend, Member], sender: Union[Friend, Group], command: Arpamar,
                  alc: Alconna):
    async def waiter1(
            waiter1_group: Group, waiter1_member: Member, waiter1_message: MessageChain
    ):
        if waiter1_group.id == sender.id:
            if waiter1_message.display == "加入赛马":
                if waiter1_member.id in GROUP_GAME_PROCESS[sender.id]["members"]:
                    await safeSendGroupMessage(
                        sender, MessageChain("你已经参与了本轮游戏，请不要重复加入")
                    )
                else:
                    if await BotGame(waiter1_member.id).reduce_coin(5):
                        GROUP_GAME_PROCESS[sender.id]["members"].append(
                            waiter1_member.id
                        )
                        waiter1_player_list = GROUP_GAME_PROCESS[sender.id]["members"]
                        waiter1_player_count = len(waiter1_player_list)
                        if 6 > waiter1_player_count > 1:
                            GROUP_GAME_PROCESS[sender.id]["status"] = "pre_start"
                            add_msg = "，发起者可发送“提前开始”来强制开始本场游戏"
                        else:
                            GROUP_GAME_PROCESS[sender.id]["status"] = "waiting"
                            add_msg = ""
                        await safeSendGroupMessage(
                            sender,
                            MessageChain(
                                At(waiter1_member.id),
                                Plain(
                                    f" 你已成功加入本轮游戏，当前共有 {waiter1_player_count} / 6 人参与{add_msg}"
                                ),
                            ),
                        )
                        if waiter1_player_count == 6:
                            GROUP_GAME_PROCESS[sender.id]["status"] = "running"
                            return True
                    else:
                        await safeSendGroupMessage(
                            sender, MessageChain(f"你的{config.COIN_NAME}不足，无法参加游戏")
                        )
            elif waiter1_message.display == "退出赛马":
                if waiter1_member.id == target.id:
                    for waiter1_player in GROUP_GAME_PROCESS[sender.id]["members"]:
                        await BotGame(waiter1_player).update_coin(5)
                    MEMBER_RUNING_LIST.remove(target.id)
                    GROUP_RUNING_LIST.remove(sender.id)
                    del GROUP_GAME_PROCESS[sender.id]
                    await safeSendGroupMessage(
                        sender, MessageChain("由于您是房主，本场房间已解散")
                    )
                    return False
                elif waiter1_member.id in GROUP_GAME_PROCESS[sender.id]["members"]:
                    GROUP_GAME_PROCESS[sender.id]["members"].remove(waiter1_member.id)
                    waiter1_player_list = GROUP_GAME_PROCESS[sender.id]["members"]
                    waiter1_player_count = len(waiter1_player_list)
                    if 6 > waiter1_player_count > 1:
                        GROUP_GAME_PROCESS[sender.id]["status"] = "pre_start"
                    else:
                        GROUP_GAME_PROCESS[sender.id]["status"] = "waiting"
                    await safeSendGroupMessage(
                        sender,
                        MessageChain(
                            At(waiter1_member.id),
                            Plain(f" 你已退出本轮游戏，当前共有 {waiter1_player_count} / 6 人参与"),
                        ),
                    )
                else:
                    await safeSendGroupMessage(
                        sender, MessageChain("你未参与本场游戏，无法退出")
                    )
            elif waiter1_message.display == "提前开始":
                if waiter1_member.id == target.id:
                    if GROUP_GAME_PROCESS[sender.id]["status"] == "pre_start":
                        await safeSendGroupMessage(
                            sender,
                            MessageChain(
                                At(waiter1_member.id),
                                Plain(" 已强制开始本场游戏"),
                            ),
                        )
                        GROUP_GAME_PROCESS[sender.id]["status"] = "running"
                        return True
                    else:
                        await safeSendGroupMessage(
                            sender,
                            MessageChain(
                                At(waiter1_member.id),
                                Plain(" 当前游戏人数不足，无法强制开始"),
                            ),
                        )
                else:
                    await safeSendGroupMessage(
                        sender,
                        MessageChain(
                            At(waiter1_member.id),
                            Plain(" 你不是本轮游戏的发起者，无法强制开始本场游戏"),
                        ),
                    )

    if not command.subcommands:
        return await print_help(alc.get_help())
    try:
        if not isinstance(sender, Group):
            return MessageChain([Plain('请在群聊中使用本命令')])
        if command.find('start'):
            if sender.id in GROUP_RUNING_LIST:
                if GROUP_GAME_PROCESS[sender.id]["status"] != "running":
                    return await safeSendGroupMessage(
                        sender,
                        MessageChain(
                            At(target),
                            " 本轮游戏已经开始，请等待其他人结束后再开始新的一局",
                        ),
                    )
                else:
                    return await safeSendGroupMessage(
                        sender, MessageChain(At(target), " 本群的游戏还未开始，请输入“加入赛马”参与游戏")
                    )
            elif target.id in MEMBER_RUNING_LIST:
                return await safeSendGroupMessage(
                    sender, MessageChain(" 你已经参与了其他群的游戏，请等待游戏结束")
                )

            if await BotGame(target.id).reduce_coin(5):
                MEMBER_RUNING_LIST.append(target.id)
                GROUP_RUNING_LIST.append(sender.id)
                GROUP_GAME_PROCESS[sender.id] = {
                    "status": "waiting",
                    "members": [target.id],
                }
                await safeSendGroupMessage(
                    sender, MessageChain("赛马小游戏开启成功，正在等待其他群成员加入，发送“加入赛马”参与游戏")
                )
            else:
                return await safeSendGroupMessage(
                    sender, MessageChain(f"你的{config.COIN_NAME}不足，无法开始游戏")
                )

            try:
                result = await FunctionWaiter(waiter1, [GroupMessage]).wait(120)
                if result:
                    GROUP_GAME_PROCESS[sender.id]["status"] = "running"
                else:
                    return

            except asyncio.TimeoutError:
                for player in GROUP_GAME_PROCESS[sender.id]["members"]:
                    await BotGame(player).update_coin(5)
                MEMBER_RUNING_LIST.remove(target.id)
                GROUP_RUNING_LIST.remove(sender.id)
                del GROUP_GAME_PROCESS[sender.id]
                return await safeSendGroupMessage(sender, MessageChain("等待玩家加入超时，请重新开始"))

            await asyncio.sleep(2)
            # 开始游戏
            player_list = GROUP_GAME_PROCESS[sender.id]["members"]
            random.shuffle(player_list)
            game_data = {
                "player": {
                    player: {
                        "horse": i,
                        "score": 0,
                        "name": (await app.get_member(sender.id, player)).name,
                    }
                    for i, player in enumerate(player_list, 1)
                },
                "winer": None,
            }
            gif_frames = [IMG.open(await to_thread(draw_game, game_data))]

            while True:
                game_data = run_game(game_data.copy())
                winer = [
                    player
                    for player, data in game_data["player"].items()
                    if data["score"] >= 100
                ]
                if winer:
                    if len(winer) != 1:
                        winer = sorted(
                            game_data["player"].items(),
                            key=lambda x: x[1]["score"],
                            reverse=True,
                        )[0][0]
                        game_data["winer"] = winer
                    else:
                        game_data["winer"] = winer[0]
                    break
                else:
                    gif_frames.append(IMG.open(await to_thread(draw_game, game_data)))

            # 结束游戏
            for player, data in game_data["player"].items():
                if data["score"] >= 100:
                    game_data["player"][player].update({"score": 102})
            gif_frames.append(IMG.open(await to_thread(draw_game, game_data)))
            image = BytesIO()
            gif_frames[0].save(
                image,
                format='GIF',
                append_images=gif_frames[1:],
                save_all=True,
                duration=1500,
                loop=0,
                optimize=False
            )
            await safeSendGroupMessage(
                sender,
                MessageChain([Image(data_bytes=image.getvalue())]),
            )
            player_count = len(game_data["player"])
            gold_count = (player_count * 5) - player_count
            await asyncio.sleep(15)
            await safeSendGroupMessage(
                sender,
                MessageChain([
                    Plain("游戏结束，获胜者是："),
                    At(game_data["winer"]),
                    Plain(f"已获得 {gold_count} {config.COIN_NAME}")
                ]))
            await BotGame(game_data["winer"]).update_coin(gold_count)
            MEMBER_RUNING_LIST.remove(target.id)
            GROUP_RUNING_LIST.remove(sender.id)
            del GROUP_GAME_PROCESS[sender.id]
        else:
            return args_error()
    except AssertionError as e:
        logger.exception(e)
        return args_error()
    except Exception as e:
        logger.exception(e)
        return unknown_error()


def draw_game(data):
    player_count = len(data["player"])
    arena_size = (500, (player_count * 50))
    name_size = (player_count * 26) + ((player_count - 1) * 4)
    img_size = (arena_size[0], arena_size[1] + name_size + 60)
    name_text = "\n".join(
        [
            f"{player['horse']} 号马：{player['name']}"
            for _, player in data["player"].items()
        ]
    )
    grass_color = [
        (108, 177, 0),
        (127, 185, 36),
        (108, 177, 0),
        (127, 185, 36),
        (108, 177, 0),
        (127, 185, 36),
    ]
    horse_name = ["①", "②", "③", "④", "⑤", "⑥"]
    image = IMG.new("RGB", img_size, (255, 255, 255))
    draw = ImageDraw.Draw(image)

    for i, player in enumerate(data["player"], 0):
        draw.rectangle(
            (20, 20 + (50 * i), 480, 20 + (50 * (i + 1))), fill=grass_color[i]
        )
        for n in range(11):
            draw.line(
                (
                    20 + (46 * n),
                    20 + (50 * i),
                    20 + (46 * n),
                    20 + (50 * (i + 1)),
                ),
                fill=(80, 80, 80),
            )
        draw.text(
            (32 + (data["player"][player]["score"] * 4.14), 32 + (50 * i)),
            horse_name[data["player"][player]["horse"] - 1],
            font=font24,
            fill=(0, 0, 0),
        )
    draw.line((20, 20, 480, 20), fill=(80, 80, 80))
    draw.line(
        (20, 20 + (50 * player_count), 480, 20 + (50 * player_count)), fill=(80, 80, 80)
    )
    draw.line(
        (0, arena_size[1] + 40, img_size[0], arena_size[1] + 40), fill="black", width=2
    )
    draw.text((10, arena_size[1] + 45), name_text, (0, 0, 0), font=font24)
    bio = BytesIO()
    image.save(bio, "jpeg")
    return bio


def run_game(data):
    for player in data["player"]:
        data["player"][player]["score"] += random.randint(8, 18) * random.uniform(
            0.7, 1.2
        )
    return data
