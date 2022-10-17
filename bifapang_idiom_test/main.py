import random
import asyncio

from app.entities.game import BotGame
from app.util.alconna import Commander
from app.util.graia import At, Group, Member, MessageChain, GroupMessage, FunctionWaiter, message

from .data import data

RUNNING = {}
command = Commander("背成语", "背成语")


@command.no_match(events=[GroupMessage])
async def group_learn(group: Group):
    async def waiter(
            waiter_group: Group, waiter_member: Member, waiter_message: MessageChain
    ):
        if waiter_group.id == group.id:
            waiter_saying = waiter_message.display.strip()
            if waiter_saying == "取消":
                return False
            elif waiter_saying == RUNNING[group.id]:
                return waiter_member.id

    if group.id in RUNNING:
        return

    RUNNING[group.id] = None

    while True:
        word_data = random.choice(data)
        RUNNING[group.id] = word_data["word"]

        message(
            f"本回合题目：\n该成语释义：{word_data['explanation']}\n",
            f"出处：{word_data['derivation'].replace(word_data['word'], '*' * len(word_data['word']))}",
        ).target(group).send()
        try:
            answer_qq = await FunctionWaiter(waiter, events=[GroupMessage]).wait(60)
            if answer_qq:
                await BotGame(str(answer_qq)).update_english_answer(1)
                message([
                    "恭喜 ",
                    At(answer_qq),
                    f" 回答正确 {word_data['word']}",
                ]).target(group).send()

                await asyncio.sleep(2)
            else:
                del RUNNING[group.id]
                return message("已结束本次答题").target(group).send()

        except asyncio.TimeoutError:
            del RUNNING[group.id]
            return message(
                    f"本次成语为：{word_data['word']}\n",
                    f"这个成语出自：{word_data['derivation']}\n",
                    f"释义：{word_data['explanation']}\n",
                    f"读音：{word_data['pinyin']}\n",
                    "答题已结束，请重新开启",
            ).target(group).send()
