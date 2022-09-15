import json

from arclet.alconna import Alconna
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from loguru import logger

from app.core.commander import CommandDelegateManager
from app.util.network import general_request
from app.util.phrases import unknown_error

manager: CommandDelegateManager = CommandDelegateManager()


@manager.register(
    entry='来点丁真',
    brief_help='礼堂丁真',
    alc=Alconna(
        headers=manager.headers,
        command='来点丁真',
        help_text='礼堂丁真'
    )
)
async def ding():
    try:
        base_url = 'https://raw.fastgit.org/Brx86/DingZhen/main/src/'
        resp = json.loads(await general_request("https://api.ay1.us/randomdj?r=0"), encoding='utf-8')
        return MessageChain.create([Image(url=base_url + resp["url"].split('/')[-1])])
    except Exception as e:
        logger.error(e)
        return await unknown_error()