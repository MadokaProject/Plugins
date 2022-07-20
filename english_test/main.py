import asyncio
import json
import random
from pathlib import Path
from typing import Union

from arclet.alconna import Alconna, Subcommand, Arpamar
from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.element import At
from graia.ariadne.util.interrupt import FunctionWaiter
from graia.ariadne.model import Group, Member, Friend
from loguru import logger
from prettytable import PrettyTable

from app.core.commander import CommandDelegateManager
from app.core.config import Config
from app.entities.game import BotGame
from app.util.dao import MysqlDao
from app.util.phrases import *
from app.util.text2image import create_image

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

BOOK_LIST = []
for book in BOOK_ID:
    BOOK_LIST.append(f"{BOOK_ID[book]['id']}. {BOOK_ID[book]['name']}")

Process = [1, 2, 3, 4]

RUNNING = {}

# 答对奖励（包含连续答对）
reward = {
    1: 2,
    2: 3,
    3: 5,
    4: 8,
    5: 12,
    6: 17,
    7: 23,
    8: 30,
    9: 39
}
# 答错惩罚（包含连续答错）
punishment = {
    1: -1,
    2: -2,
    3: -4,
    4: -7,
    5: -11
}

config: Config = Config()
manager: CommandDelegateManager = CommandDelegateManager()


@manager.register(
    entry='背单词',
    brief_help='背单词',
    alc=Alconna(
        headers=manager.headers,
        command='背单词',
        options=[
            Subcommand('排行', help_text='显示群内成员答题排行榜'),
            Subcommand('更新', help_text='更新词库: 仅主人可用')
        ],
        help_text='开启一轮背单词'
    )
)
async def process(app: Ariadne, target: Union[Friend, Member], sender: Union[Friend, Group], command: Arpamar):
    if not isinstance(sender, Group):
        return MessageChain([Plain('请在群聊内使用该命令!')])
    if not command.subcommands:
        """开始背诵单词"""
        try:
            async def confirm(waiter_group: Group, waiter_member: Member, waiter_message: MessageChain):
                if all([waiter_group.id == sender.id, waiter_member.id == target.id]):
                    waiter_saying = waiter_message.display
                    if waiter_saying == "取消":
                        return False
                    else:
                        try:
                            confirm_book_id = int(waiter_saying)
                            if 1 <= confirm_book_id <= 15:
                                return confirm_book_id
                        except:
                            await app.send_group_message(sender, MessageChain([
                                Plain("请输入1-15以内的数字")
                            ]))

            async def waiter(waiter_group: Group, waiter_member: Member, waiter_message: MessageChain):
                if waiter_group.id == sender.id:
                    waiter_saying = waiter_message.display
                    if waiter_saying == "取消":
                        return False
                    elif waiter_saying[0] == '#':
                        waiter_user = waiter_member.id
                        if waiter_saying.strip('#') == RUNNING[sender.id]:
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
                            await BotGame(waiter_user).update_coin(punishment.get(answer_record[waiter_user][1], -15))
                            if answer_record[waiter_user][1] == 1:
                                _msg = '你答错了哦，'
                            else:
                                _msg = f'你连续答错了{answer_record[waiter_user][1]}题了哦，'
                            _msg += f'惩罚你{punishment.get(answer_record[waiter_user][1], -15)}金币'
                            await app.send_group_message(waiter_group, MessageChain([
                                At(waiter_user), Plain(_msg)
                            ]))

            if sender.id in RUNNING:
                return

            RUNNING[sender.id] = None
            await app.send_group_message(sender, MessageChain([
                Plain("请输入你想要选择的词库ID"),
                Image(data_bytes=await create_image("\n".join(BOOK_LIST)))
            ]))

            try:
                book_id = await FunctionWaiter(confirm, [GroupMessage]).wait(30)
                if not book_id:
                    del RUNNING[sender.id]
                    return await app.send_group_message(sender, MessageChain([Plain("已取消")]))
            except asyncio.TimeoutError:
                del RUNNING[sender.id]
                return await app.send_group_message(sender, MessageChain([Plain("等待超时")]))

            await app.send_group_message(sender, MessageChain([Plain("已开启本次答题，可随时发送取消终止进程")]))

            answer_record = {}  # 答题记录，用于奖励

            while True:
                word_data = await random_word(book_id)
                RUNNING[sender.id] = word_data[0]
                pop = word_data[1].split("&")
                if pop == "":
                    pop = ["/"]
                tran = word_data[2].split("&")
                word_len = len(word_data[0])
                wordinfo = []
                tran_num = 0
                for p in pop:
                    wordinfo.append(f"[ {p} ] {tran[tran_num]}")
                    tran_num += 1
                await app.send_group_message(sender, MessageChain([
                    Plain("本回合题目：\n"),
                    Plain("\n".join(wordinfo)),
                    Plain("\n答题请输入 # 开头")
                ]))
                for __process in Process:
                    try:
                        answer_qq = await FunctionWaiter(waiter, [GroupMessage]).wait(15)
                        if answer_qq:
                            user = BotGame(answer_qq)
                            await user.update_english_answer(1)
                            await user.update_coin(reward.get(answer_record[answer_qq][1], 40))
                            __msg = ""
                            if answer_record[answer_qq][1] != 1:
                                __msg = f'你连续答对了{answer_record[answer_qq][1]}题，太棒了，'
                            __msg += f'奖励你{reward.get(answer_record[answer_qq][1], 40)}金币'
                            await app.send_group_message(sender, MessageChain([
                                Plain("恭喜 "),
                                At(answer_qq),
                                Plain(f" 回答正确 {word_data[0]}，\n"),
                                Plain(__msg)
                            ]))
                            await asyncio.sleep(2)
                            break
                        else:
                            del RUNNING[sender.id]
                            return await app.send_group_message(sender, MessageChain([Plain("已结束本次答题")]))

                    except asyncio.TimeoutError:
                        if __process == 1:
                            await app.send_group_message(sender, MessageChain([
                                Plain(f"提示1\n这个单词由 {word_len} 个字母构成")
                            ]))
                        elif __process == 2:
                            await app.send_group_message(sender, MessageChain([
                                Plain(f"提示2\n这个单词的首字母是 {word_data[0][0]}")
                            ]))
                        elif __process == 3:
                            half = int(word_len / 2)
                            await app.send_group_message(sender, MessageChain([
                                Plain(f"提示3\n这个单词的前半部分为\n{word_data[0][:half]}")]))
                        elif __process == 4:
                            del RUNNING[sender.id]
                            await app.send_group_message(sender, MessageChain([
                                Plain(f"本次答案为：{word_data[0]}\n答题已结束，请重新开启")
                            ]))
                            return
        except Exception as e:
            logger.exception(e)
            return unknown_error()
    if command.find('排行'):
        """排行"""
        try:
            with MysqlDao() as db:
                res = db.query(
                    "SELECT qid, english_answer FROM game ORDER BY english_answer DESC"
                )
                members = await app.get_member_list(sender.id)
                group_user = {item.id: item.name for item in members}
                resp = MessageChain([Plain('群内英语答题排行：\r\n')])
                index = 1
                msg = PrettyTable()
                msg.field_names = ['序号', '群昵称', '答题数量']
                for qid, english_answer in res:
                    if english_answer == 0 or int(qid) not in group_user.keys():
                        continue
                    msg.add_row([index, group_user[int(qid)], english_answer])
                    index += 1
                msg.align = 'r'
                msg.align['群昵称'] = 'l'
                resp.extend(MessageChain([
                    Image(data_bytes=await create_image(msg.get_string()))
                ]))
                return resp
        except Exception as e:
            logger.exception(e)
            return unknown_error()
    elif command.find('更新'):
        """更新题库"""
        if target.id != config.MASTER_QQ:
            return not_admin()
        await app.send_group_message(sender, MessageChain([
            Plain('正在更新题库，所需时间可能较长，请耐心等待')
        ]))
        await asyncio.gather(update_english_test())
    else:
        return args_error()


async def random_word(book_id):
    with MysqlDao() as __db:
        p = __db.query('SELECT * FROM word_dict WHERE bookId=%s', [str(book_id)])
        data = random.choice(p)
        return [data[0], data[1], data[2]]


async def update_english_test():
    with MysqlDao() as db:
        def replaceFran(text):
            fr_en = [['é', 'e'], ['ê', 'e'],
                     ['è', 'e'], ['ë', 'e'],
                     ['à', 'a'], ['â', 'a'],
                     ['ç', 'c'], ['î', 'i'],
                     ['ï', 'i'], ['ô', 'o'],
                     ['ù', 'u'], ['û', 'u'],
                     ['ü', 'u'], ['ÿ', 'y']]
            for i in fr_en:
                text = text.replace(i[0], i[1])
            return text

        try:
            for file in Path(__file__).parent.joinpath('worddict').glob('*.json'):
                with open(file, 'r', encoding='utf-8') as f:
                    for line in f.readlines():
                        words = line.strip()
                        word_json = json.loads(words)
                        word_pop = []
                        word_tran = []
                        for tran in word_json['content']['word']['content']['trans']:
                            if 'pos' in tran:
                                word_pop.append(tran['pos'])
                            word_tran.append(tran['tranCn'])
                        data = [
                            replaceFran(word_json["headWord"]),
                            "&".join(word_pop),
                            "&".join(word_tran),
                            BOOK_ID[word_json['bookId']]['id']
                        ]
                        db.update(
                            'INSERT INTO word_dict(word, pos, tran, bookId) VALUES(%s, %s, %s, %s)',
                            [data[0], data[1], data[2], data[3]]
                        )
            return MessageChain([Plain('题库更新完成！')])
        except Exception as e:
            logger.exception(e)
            return MessageChain([Plain(f'题库更新异常: {e}')])
