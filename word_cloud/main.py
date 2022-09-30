import re
import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

import jieba.analyse
import numpy
from PIL import Image as IMG
from loguru import logger
from matplotlib import pyplot
from wordcloud import WordCloud, ImageColorGenerator

from app.plugin.basic.__01_sys.database.database import Msg as DBMsg
from app.util.alconna import Subcommand, Arpamar, Commander
from app.util.graia import (
    At,
    Member,
    MessageChain,
    Group,
    GroupMessage,
    message,
)
from app.util.control import Permission
from app.util.phrases import *
from app.util.tools import to_thread

BASEPATH = Path(__file__).parent
MASK = numpy.array(IMG.open(BASEPATH.joinpath("wordcloud.jpg")))
FONT_PATH = Path("./app/resource/font").joinpath("sarasa-mono-sc-regular.ttf")
STOPWORDS = BASEPATH.joinpath("stopwords")

RUNNING = 0
RUNNING_LIST = []


command = Commander(
    "词云",
    "词云",
    Subcommand("个人", help_text="查看个人词云"),
    Subcommand("本群", help_text="查看本群词云"),
)


@command.parse("个人", events=[GroupMessage])
async def my_word_cloud(target: Member, sender: Group):
    global RUNNING, RUNNING_LIST
    if RUNNING < 5:
        RUNNING += 1
        RUNNING_LIST.append(target.id)
        talk_list = DBMsg.select(DBMsg.content).where(
            DBMsg.uid == sender.id,
            DBMsg.qid == target.id,
            DBMsg.datetime >= datetime.datetime.now() - datetime.timedelta(days=7),
        )
        if image := await make_word_cloud(target, sender, talk_list):
            message(
                [
                    At(target.id),
                    Plain(f" 已成功制作{'个人' if command.find('个人') else '本群'}词云"),
                    Image(data_bytes=image),
                ]
            ).target(sender).send()
            RUNNING -= 1
            RUNNING_LIST.remove(target.id)
    else:
        message("词云生成进程正忙，请稍后").target(sender).send()


@command.parse("本群", events=[GroupMessage], permission=Permission.GROUP_ADMIN)
async def group_word_cloud(target: Member, sender: Group):
    global RUNNING, RUNNING_LIST
    if RUNNING < 5:
        RUNNING += 1
        RUNNING_LIST.append(target.id)
        talk_list = DBMsg.select(DBMsg.content).where(
            DBMsg.uid == sender.id,
            DBMsg.datetime >= datetime.datetime.now() - datetime.timedelta(days=7),
        )
        if image := await make_word_cloud(target, sender, talk_list):
            message(
                [
                    At(target.id),
                    Plain(f" 已成功制作{'个人' if command.find('个人') else '本群'}词云"),
                    Image(data_bytes=image),
                ]
            ).target(sender).send()
            RUNNING -= 1
            RUNNING_LIST.remove(target.id)
    else:
        message("词云生成进程正忙，请稍后").target(sender).send()


async def make_word_cloud(
    target: Member, sender: Group, talk_list: list
) -> Optional[bytes]:
    talk_list = [
        re.sub(r"[0-9]+", "", talk).strip("@")
        for talk in (
            MessageChain.from_persistent_string(msg.content).display
            for msg in talk_list
        )
        if talk not in ["[图片]"] or talk[0] not in ".,;!?。，；！？/\\"
    ]
    if len(talk_list) < 10:
        message("当前样本量较少，无法制作").target(sender).send()
        RUNNING -= 1
        RUNNING_LIST.remove(target.id)
        return
    message(f" 正在制作词云，一周内共 {len(talk_list)} 条记录").at(target).target(sender).send()
    words = await get_frequencies(talk_list)
    image: bytes = await to_thread(make_wordcloud, words)
    return image


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
