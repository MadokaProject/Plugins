import asyncio
import re
from typing import Union

from loguru import logger

from app.util.alconna import Args, Arpamar, Commander
from app.util.graia import Source, Group, Friend, message
from app.util.tools import to_thread

command = Commander("calc", "计算器", Args["formula;S", str], help_text="四则计算器")


@command.no_match()
async def calculator_main(sender: Union[Friend, Group], source: Source, cmd: Arpamar):
    if not (formula := cmd.query("formula")):
        return
    expression = rep_str("".join(formula))
    if len(expression) > 800:
        return message("字符数过多").quote(source).target(sender).send()
    try:
        answer = await asyncio.wait_for(to_thread(arithmetic, expression), timeout=15)
    except ZeroDivisionError:
        return message("0 不可作为除数").quote(source).target(sender).send()
    except asyncio.TimeoutError:
        return message("计算超时").quote(source).target(sender).send()
    except Exception as e:
        logger.error(e)
        return message("出现未知错误，终止计算").quote(source).target(sender).send()

    return message(answer).quote(source).target(sender).send()


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
        content = re.sub(
            r"-?\d+\.?\d*[-+]-?\d+\.?\d*", add_sub_content, content, count=1
        )

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
    content = (
        -float(content[1]) + float(content[3])
        if content[0] == ""
        else float(content[0]) - float(content[1])
    )

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
