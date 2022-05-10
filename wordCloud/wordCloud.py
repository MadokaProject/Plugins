import re
from io import BytesIO
from pathlib import Path

import jieba.analyse
import numpy
from arclet.alconna import Alconna, Subcommand, Arpamar
from PIL import Image as IMG
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain, Image
from loguru import logger
from matplotlib import pyplot
from wordcloud import WordCloud, ImageColorGenerator

from app.core.commander import CommandDelegateManager
from app.plugin.base import Plugin
from app.util.dao import MysqlDao
from app.util.sendMessage import safeSendGroupMessage
from app.util.tools import to_thread

BASEPATH = Path(__file__).parent
MASK = numpy.array(IMG.open(BASEPATH.joinpath("./wordCloud_res/wordcloud.jpg")))
FONT_PATH = Path("./app/resource/font").joinpath("sarasa-mono-sc-regular.ttf")
STOPWORDS = BASEPATH.joinpath("stopwords")

RUNNING = 0
RUNNING_LIST = []


class Module(Plugin):
    entry = '词云'
    brief_help = '词云'
    manager: CommandDelegateManager = CommandDelegateManager.get_instance()

    @manager.register(Alconna(
        headers=manager.headers,
        command=entry,
        options=[
            Subcommand('个人', help_text='查看个人词云'),
            Subcommand('本群', help_text='查看本群词云')
        ],
        help_text='词云'
    ))
    async def process(self, command: Arpamar, alc: Alconna):
        global RUNNING, RUNNING_LIST
        if not command.subcommands:
            return await self.print_help(alc.get_help())
        try:
            if not hasattr(self, 'group'):
                return MessageChain.create([Plain('请在群组使用该命令！')])
            if RUNNING < 5:
                RUNNING += 1
                RUNNING_LIST.append(self.member.id)
                with MysqlDao() as db:
                    if command.find('个人'):
                        talk_list = db.query(
                            'SELECT content FROM msg WHERE uid=%s and qid=%s and DATE_SUB(CURDATE(), INTERVAL 7 DAY) <= datetime',
                            [self.group.id, self.member.id]
                        )
                    else:
                        talk_list = db.query(
                            'SELECT content FROM msg WHERE uid=%s and DATE_SUB(CURDATE(), INTERVAL 7 DAY) <= datetime',
                            [self.group.id]
                        )
                    talk_list = [re.sub(r'[0-9]+', '', talk[0]).strip('@') for talk in talk_list if
                                 talk[0] not in ['[图片]']]
                if len(talk_list) < 10:
                    await safeSendGroupMessage(self.group, MessageChain.create([Plain("当前样本量较少，无法制作")]))
                    RUNNING -= 1
                    RUNNING_LIST.remove(self.member.id)
                    return
                await safeSendGroupMessage(self.group, MessageChain.create(
                    [At(self.member.id), Plain(f" 正在制作词云，一周内共 {len(talk_list)} 条记录")]
                ))
                words = await get_frequencies(talk_list)
                image = await to_thread(make_wordcloud, words)
                await safeSendGroupMessage(self.group, MessageChain.create([
                    At(self.member.id), Plain(f" 已成功制作{self.msg[0]}词云"), Image(data_bytes=image)]
                ))
                RUNNING -= 1
                RUNNING_LIST.remove(self.member.id)
            else:
                await safeSendGroupMessage(self.group, MessageChain.create([Plain("词云生成进程正忙，请稍后")]))
        except Exception as e:
            logger.exception(e)
            return self.unkown_error()


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
