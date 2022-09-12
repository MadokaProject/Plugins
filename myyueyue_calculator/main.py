import asyncio
import re
from typing import Union

from arclet.alconna import Alconna, Args, Arpamar
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Source
from graia.ariadne.model import Group, Friend
from loguru import logger

from app.core.commander import CommandDelegateManager
from app.util.send_message import safeSendMessage
from app.util.tools import to_thread

manager: CommandDelegateManager = CommandDelegateManager()


@manager.register(
    entry='calc',
    brief_help='计算器',
    alc=Alconna(
        headers=manager.headers,
        command='calc',
        main_args=Args['formula;S', str],
        help_text='四则计算器'
    )
)
async def calculator_main(sender: Union[Friend, Group], source: Source, cmd: Arpamar):
    if formula := cmd.query('formula'):
        expression = rep_str(''.join(i for i in formula))
        print(expression)
        if len(expression) > 800:
            return await safeSendMessage(
                sender, MessageChain.create("字符数过多"), quote=source
            )
        try:
            answer = await asyncio.wait_for(
                to_thread(arithmetic, expression), timeout=15
            )
        except ZeroDivisionError:
            return await safeSendMessage(
                sender, MessageChain.create("0 不可作为除数"), quote=source
            )
        except asyncio.TimeoutError:
            return await safeSendMessage(
                sender, MessageChain.create("计算超时"), quote=source
            )
        except Exception as e:
            logger.error(e)
            return await safeSendMessage(
                sender, MessageChain.create("出现未知错误，终止计算"), quote=source
            )

        return await safeSendMessage(sender, MessageChain.create(answer), quote=source)


def rep_str(say: str):
    rep_list = [
        [[" "], ""],
        [["加", "＋"], "+"],
        [["减", "－"], "-"],
        [["乘", "x", "X", "×"], "*"],
        [["除", "÷", "∣"], "/"],
        [["（"], "("],
        [["）"], ")"],
    ]
    for rp in rep_list:
        for old_str in rp[0]:
            say = say.replace(old_str, rp[1])
    return say


def arithmetic(expression="1+1"):
    if content := re.search(r"\(([-+*/]*\d+\.?\d*)+\)", expression):
        content = content.group()
        content = content[1:-1]
        replace_content = next_arithmetic(content)
        expression = re.sub(
            r"\(([-+*/]*\d+\.?\d*)+\)", replace_content, expression, count=1
        )
    else:
        return next_arithmetic(expression)
    return arithmetic(expression)


def next_arithmetic(content):
    while True:
        if next_content_mul_div := re.search(r"\d+\.?\d*[*/][-+]?\d+\.?\d*", content):
            next_content_mul_div = next_content_mul_div.group()
            mul_div_content = mul_div(next_content_mul_div)
            content = re.sub(
                r"\d+\.?\d*[*/][-+]?\d+\.?\d*", str(mul_div_content), content, count=1
            )
            continue
        next_content_add_sub = re.search(r"-?\d+\.?\d*[-+][-+]?\d+\.?\d*", content)
        if not next_content_add_sub:
            break
        next_content_add_sub = next_content_add_sub.group()
        add_sub_content = add_sub(next_content_add_sub)
        add_sub_content = str(add_sub_content)
        content = re.sub(r"-?\d+\.?\d*[-+]-?\d+\.?\d*", add_sub_content, content, count=1)

    return content


def add_sub(content):
    if "+" in content:
        content = content.split("+")
        content = float(content[0]) + float(content[1])
        return content
    elif "-" in content:
        return _reduce(content)


def _reduce(content):
    content = content.split("-")
    if content[0] == "-" and content[2] == "-":
        content = -float(content[1]) - float(content[-1])
        return content
    if content[0] == "-":
        content = -float(content[1]) - float(content[-1])
        return content
    if content[1] == "-" and content[2] == "-":
        content = -float(content[0]) + float(content[-1])
        return content
    if content[1] == "":
        content = float(content[0]) - float(content[2])
        return content
    if content[0] == "" and content[2] != "":
        content = -float(content[1]) - float(content[2])
        return content
    content = -float(content[1]) + float(content[3]) if content[0] == "" else float(content[0]) - float(content[1])

    return content


def mul_div(content):
    if "*" in content:
        content = content.split("*")
        content = float(content[0]) * float(content[1])
        return content
    elif "/" in content:
        content = content.split("/")
        content = float(content[0]) / float(content[1])
        return content
