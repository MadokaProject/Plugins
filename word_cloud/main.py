import re
import datetime
from io import BytesIO
from pathlib import Path
from typing import Union

import jieba.analyse
import numpy
from PIL import Image as IMG
from arclet.alconna import Alconna, Subcommand, Arpamar
from graia.ariadne.message.element import At
from graia.ariadne.model import Friend, Member, Group
from loguru import logger
from matplotlib import pyplot
from wordcloud import WordCloud, ImageColorGenerator

from app.core.commander import CommandDelegateManager
from app.plugin.basic.__01_sys.database.database import Msg as DBMsg
from app.util.phrases import *
from app.util.send_message import safeSendGroupMessage
from app.util.tools import to_thread

BASEPATH = Path(__file__).parent
MASK = numpy.array(IMG.open(BASEPATH.joinpath("wordcloud.jpg")))
FONT_PATH = Path("./app/resource/font").joinpath("sarasa-mono-sc-regular.ttf")
STOPWORDS = BASEPATH.joinpath("stopwords")

RUNNING = 0
RUNNING_LIST = []

manager: CommandDelegateManager = CommandDelegateManager()


@manager.register(
    entry='词云',
    brief_help='词云',
    alc=Alconna(
        headers=manager.headers,
        command='词云',
        options=[
            Subcommand('个人', help_text='查看个人词云'),
            Subcommand('本群', help_text='查看本群词云')
        ],
        help_text='词云'
    ))
async def process(target: Union[Friend, Member], sender: Union[Friend, Group], command: Arpamar, alc: Alconna):
    global RUNNING, RUNNING_LIST
    if not command.subcommands:
        return await print_help(alc.get_help())
    try:
        if not isinstance(sender, Group):
            return MessageChain([Plain('请在群组使用该命令！')])
        if RUNNING < 5:
            RUNNING += 1
            RUNNING_LIST.append(target.id)
            if command.find('个人'):
                talk_list = DBMsg.select(DBMsg.content).where(
                    DBMsg.uid == sender.id,
                    DBMsg.qid == target.id,
                    DBMsg.datetime >= datetime.datetime.now() - datetime.timedelta(days=7)
                )
            else:
                talk_list = DBMsg.select(DBMsg.content).where(
                    DBMsg.uid == sender.id,
                    DBMsg.datetime >= datetime.datetime.now() - datetime.timedelta(days=7)
                )
            talk_list = [re.sub(r'[0-9]+', '', talk.content).strip('@') for talk in talk_list if
                         talk.content not in ['[图片]']]
            if len(talk_list) < 10:
                await safeSendGroupMessage(sender, MessageChain([Plain("当前样本量较少，无法制作")]))
                RUNNING -= 1
                RUNNING_LIST.remove(target.id)
                return
            await safeSendGroupMessage(sender, MessageChain(
                [At(target.id), Plain(f" 正在制作词云，一周内共 {len(talk_list)} 条记录")]
            ))
            words = await get_frequencies(talk_list)
            image = await to_thread(make_wordcloud, words)
            await safeSendGroupMessage(sender, MessageChain([
                At(target.id), Plain(f" 已成功制作{'个人' if command.find('个人') else '本群'}词云"), Image(data_bytes=image)]
            ))
            RUNNING -= 1
            RUNNING_LIST.remove(target.id)
        else:
            await safeSendGroupMessage(sender, MessageChain([Plain("词云生成进程正忙，请稍后")]))
    except Exception as e:
        logger.exception(e)
        return unknown_error()


async def get_frequencies(msg_list):
    text = "\n".join(msg_list)
    words = jieba.analyse.extract_tags(text, topK=800, withWeight=True)
    return dict(words)


def make_wordcloud(words):
    wordcloud = WordCloud(
        font_path=str(FONT_PATH),
        background_color="white",
        mask=MASK,
        max_words=800,
        scale=2,
    )
    wordcloud.generate_from_frequencies(words)
    image_colors = ImageColorGenerator(MASK, default_color=(255, 255, 255))
    wordcloud.recolor(color_func=image_colors)
    pyplot.imshow(wordcloud.recolor(color_func=image_colors), interpolation="bilinear")
    pyplot.axis("off")
    image = wordcloud.to_image()
    imageio = BytesIO()
    image.save(imageio, format="JPEG", quality=98)
    return imageio.getvalue()
