import asyncio
import contextlib
import json
import random
from pathlib import Path
from typing import Union

from loguru import logger
from prettytable import PrettyTable

from app.core.config import Config
from app.entities.game import BotGame
from app.plugin.basic.__11_game.database.database import Game as DBGame
from app.util.alconna import Subcommand, Arpamar, Commander
from app.util.control import Permission
from app.util.graia import (
    Ariadne,
    GroupMessage,
    At,
    Group,
    Member,
    MessageChain,
    Friend,
    FunctionWaiter,
    message,
)
from app.util.phrases import *
from app.util.text2image import create_image
from app.util.tools import to_thread
from .database.database import WordDict as DBWordDict

BOOK_ID = {
    "CET4luan_1": {"name": "四级真题核心词", "id": "1"},
    "CET6luan_1": {"name": "六级真题核心词", "id": "2"},
    "KaoYanluan_1": {"name": "考研必考词汇", "id": "3"},
    "Level4luan_1": {"name": "专四真题高频词", "id": "4"},
    "Level8_1": {"name": "专八真题高频词", "id": "5"},
    "IELTSluan_2": {"name": "雅思词汇", "id": "6"},
    "TOEFL_2": {"name": "TOEFL 词汇", "id": "7"},
    "ChuZhongluan_2": {"name": "中考必备词汇", "id": "8"},
    "GaoZhongluan_2": {"name": "高考必备词汇", "id": "9"},
    "PEPXiaoXue3_1": {"name": "人教版小学英语-三年级上册（你真的确定要选这个吗", "id": "10"},
    "PEPChuZhong7_1": {"name": "人教版初中英语-七年级上册", "id": "11"},
    "PEPGaoZhong": {"name": "人教版高中英语-必修", "id": "12"},
    "ChuZhong_2": {"name": "初中英语词汇", "id": "13"},
    "GaoZhong_2": {"name": "高中英语词汇", "id": "14"},
    "BEC_2": {"name": "商务英语词汇", "id": "15"},
}

BOOK_LIST = [
    f"{value['id']}. {BOOK_ID[book]['name']}" for book, value in BOOK_ID.items()
]

Process = [1, 2, 3, 4]

RUNNING = {}

# 答对奖励（包含连续答对）
reward = {1: 2, 2: 3, 3: 5, 4: 8, 5: 12, 6: 17, 7: 23, 8: 30, 9: 39}
# 答错惩罚（包含连续答错）
punishment = {1: -1, 2: -2, 3: -4, 4: -7, 5: -11}

config: Config = Config()
command = Commander(
    "背单词",
    "背单词",
    Subcommand("排行", help_text="显示群内成员答题排行榜"),
    Subcommand("更新", help_text="更新词库: 仅主人可用"),
    help_text="开启一轮背单词",
)


@command.no_match(events=[GroupMessage])
async def start(target: Member, sender: Group):
    async def confirm(
        waiter_group: Group, waiter_member: Member, waiter_message: MessageChain
    ):
        if all([waiter_group.id == sender.id, waiter_member.id == target.id]):
            waiter_saying = waiter_message.display
            if waiter_saying == "取消":
                return False
            with contextlib.suppress(ValueError):
                confirm_book_id = int(waiter_saying)
                if 1 <= confirm_book_id <= 15:
                    return confirm_book_id
            message("请输入1-15以内的数字").target(sender).send()

    async def waiter(
        waiter_group: Group, waiter_member: Member, waiter_message: MessageChain
    ):
        if waiter_group.id != sender.id:
            return
        waiter_saying = waiter_message.display
        if waiter_saying == "取消":
            return False
        if not waiter_saying.startswith("#"):
            return
        waiter_user = waiter_member.id
        if waiter_saying[1:].strip() == RUNNING[sender.id]:
            if waiter_user in answer_record and answer_record[waiter_user][0]:
                answer_record[waiter_user][1] += 1
            else:
                answer_record[waiter_user] = [True, 1]
            return waiter_user
        else:
            if waiter_user in answer_record and not answer_record[waiter_user][0]:
                answer_record[waiter_user][1] += 1
            else:
                answer_record[waiter_user] = [False, 1]
            await BotGame(waiter_user).update_coin(
                punishment.get(answer_record[waiter_user][1], -15)
            )
            if answer_record[waiter_user][1] == 1:
                _msg = "你答错了哦，"
            else:
                _msg = f"你连续答错了{answer_record[waiter_user][1]}题了哦，"
            _msg += f"惩罚你{punishment.get(answer_record[waiter_user][1], -15)}金币"
            message(_msg).target(waiter_group).at(waiter_member).send()

    if sender.id in RUNNING:
        return

    RUNNING[sender.id] = None
    message(
        [
            Plain("请输入你想要选择的词库ID"),
            Image(data_bytes=await create_image("\n".join(BOOK_LIST))),
        ]
    ).target(sender).send()

    try:
        book_id = await FunctionWaiter(confirm, [GroupMessage]).wait(30)
        if not book_id:
            del RUNNING[sender.id]
            return message("已取消").target(sender).send()
    except asyncio.TimeoutError:
        del RUNNING[sender.id]
        return message("等待超时").target(sender).send()

    message("已开启本次答题，可随时发送取消终止进程").target(sender).send()

    answer_record = {}  # 答题记录，用于奖励

    while True:
        word_data = await random_word(book_id)
        RUNNING[sender.id] = word_data.word
        pos = word_data.pos.split("&")
        if pos == "":
            pos = ["/"]
        tran = word_data.tran.split("&")
        word_len = len(word_data.word)
        wordinfo = []
        tran_num = 0
        for p in pos:
            wordinfo.append(f"[ {p} ] {tran[tran_num]}")
            tran_num += 1
        message(
            [
                Plain("本回合题目：\n"),
                Plain("\n".join(wordinfo)),
                Plain("\n答题请输入 # 开头"),
            ]
        ).target(sender).send()
        for __process in Process:
            try:
                answer_qq = await FunctionWaiter(waiter, [GroupMessage]).wait(15)
                if answer_qq:
                    user = BotGame(answer_qq)
                    await user.update_english_answer(1)
                    await user.update_coin(reward.get(answer_record[answer_qq][1], 40))
                    __msg = ""
                    if answer_record[answer_qq][1] != 1:
                        __msg = f"你连续答对了{answer_record[answer_qq][1]}题，太棒了，"
                    __msg += f"奖励你{reward.get(answer_record[answer_qq][1], 40)}金币"
                    message(
                        [
                            Plain("恭喜 "),
                            At(answer_qq),
                            Plain(f" 回答正确 {word_data[0]}，\n"),
                            Plain(__msg),
                        ]
                    ).target(sender).send()
                    await asyncio.sleep(2)
                    break
                else:
                    del RUNNING[sender.id]
                    return message("已结束本次答题").target(sender).send()

            except asyncio.TimeoutError:
                if __process == 1:
                    message(f"提示1\n这个单词由 {word_len} 个字母构成").target(sender).send()
                elif __process == 2:
                    message(f"提示2\n这个单词的首字母是 {word_data[0][0]}").target(sender).send()
                elif __process == 3:
                    half = int(word_len / 2)
                    message(f"提示3\n这个单词的前半部分为\n{word_data[0][:half]}").target(
                        sender
                    ).send()
                elif __process == 4:
                    del RUNNING[sender.id]
                    message(f"本次答案为：{word_data[0]}\n答题已结束，请重新开启").target(sender).send()
                    return


@command.parse("排行", events=[GroupMessage])
async def rank(app: Ariadne, sender: Group):
    members = await app.get_member_list(sender.id)
    group_user = {item.id: item.name for item in members}
    resp = MessageChain([Plain("群内英语答题排行：\r\n")])
    index = 1
    msg = PrettyTable()
    msg.field_names = ["序号", "群昵称", "答题数量"]
    for res in DBGame.select().order_by(DBGame.english_answer.desc()):
        if res.english_answer == 0 or int(res.qid) not in group_user.keys():
            continue
        msg.add_row([index, group_user[int(res.qid)], res.english_answer])
        index += 1
    msg.align = "r"
    msg.align["群昵称"] = "l"
    resp.extend(MessageChain([Image(data_bytes=await create_image(msg.get_string()))]))
    message(resp).target(sender).send()


@command.parse("更新", permission=Permission.MASTER)
async def update(sender: Union[Friend, Group]):
    message("正在更新题库，所需时间可能较长，请耐心等待").target(sender).send()
    message(await to_thread(update_english_test)).target(sender).send()


async def random_word(book_id):
    """随机获取一个单词"""
    p = DBWordDict.select(DBWordDict.word, DBWordDict.pos, DBWordDict.tran).where(
        DBWordDict.book_id == book_id
    )
    return random.choice(p)


def update_english_test():
    def replaceFran(text):
        fr_en = [
            ["é", "e"],
            ["ê", "e"],
            ["è", "e"],
            ["ë", "e"],
            ["à", "a"],
            ["â", "a"],
            ["ç", "c"],
            ["î", "i"],
            ["ï", "i"],
            ["ô", "o"],
            ["ù", "u"],
            ["û", "u"],
            ["ü", "u"],
            ["ÿ", "y"],
        ]
        for i in fr_en:
            text = text.replace(i[0], i[1])
        return text

    try:
        for file in Path(__file__).parent.joinpath("worddict").glob("*.json"):
            with open(file, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    words = line.strip()
                    word_json = json.loads(words)
                    word_pop = []
                    word_tran = []
                    for tran in word_json["content"]["word"]["content"]["trans"]:
                        if "pos" in tran:
                            word_pop.append(tran["pos"])
                        word_tran.append(tran["tranCn"])
                    data = [
                        replaceFran(word_json["headWord"]),
                        "&".join(word_pop),
                        "&".join(word_tran),
                        BOOK_ID[word_json["bookId"]]["id"],
                    ]
                    DBWordDict.replace(
                        word=data[0], pos=data[1], tran=data[2], book_id=data[3]
                    ).execute()
        return MessageChain([Plain("题库更新完成！")])
    except Exception as e:
        logger.exception(e)
        return MessageChain([Plain(f"题库更新异常: {e}")])
