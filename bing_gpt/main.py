from typing import Union

from arclet.alconna import AllParam
from EdgeGPT import Chatbot, ConversationStyle
from loguru import logger

from app.util.alconna import Args, Arpamar, Commander, Option
from app.util.graia import (
    DefaultFunctionWaiter,
    Friend,
    FriendMessage,
    GroupMessage,
    Source,
    Group,
    Member,
    MessageChain,
    message,
)
from app.util.phrases import unknown_error
from app.util.tools import extension_data_path


cookie_path = extension_data_path("bing_gpt", "cookies.json")
cookie_path.parent.mkdir(parents=True, exist_ok=True)
if not cookie_path.exists():
    logger.warning(f"未找到 cookies.json 文件，无法使用该插件。请按照教程将 cookies.json 文件放至 {cookie_path.parent}，随后重载该插件")
else:
    global_bot = Chatbot(cookiePath=str(cookie_path))
session_pools: dict[int, Chatbot] = {}


command = Commander(
    "bing-chat",
    "Bing 聊天",
    Option("--keep|-k", help_text="保持对话"),
    Args["msg;O", AllParam],
    help_text="与 Bing AI 聊天",
)


def parse_bot_msg(msg: dict):
    if msg["contentOrigin"] == "TurnLimiter":
        return "Unfortunately, we need to move on! Send “重置对话” to chat more."
    try:
        readmore = msg["adaptiveCards"][0]["body"][1]["text"] if len(msg["adaptiveCards"][0]["body"]) >= 2 else ""
        tips = " | ".join(i["text"] for i in msg["suggestedResponses"]) if msg["suggestedResponses"] else ""
        return (f"{msg['text']}\n", "-------------------------\n", f"{readmore}\n\n", f"{tips}")
    except KeyError:
        return msg["text"]


async def connect_chat(target: Union[Friend, Member], sender: Union[Friend, Group], quote_source: Source):
    async def keep_chat(user: Union[Friend, Member], origin: Union[Friend, Group], msg: MessageChain, source: Source):
        if user.id == target.id and origin.id == sender.id and msg.safe_display.startswith("#"):
            return msg.safe_display[1:], source

    try:
        if target.id in session_pools:
            bot = session_pools[target.id]
            message("检测到您有一个会话正在进行，请结束之前的对话。").target(sender).quote(quote_source).send()
            return
        elif len(session_pools) >= 5:
            message("当前会话过多，请稍后再试。").target(sender).quote(quote_source).send()
            return
        else:
            bot = Chatbot(cookiePath=cookie_path)
            session_pools[target.id] = bot
        message("正在保持与你的对话，请以“#”开头与我聊天，需要结束对话请发送：#结束对话。\n重置对话请发送: #重置对话。").target(sender).quote(quote_source).send()
        while True:
            msg: Union[MessageChain, tuple] = await DefaultFunctionWaiter(keep_chat, [FriendMessage, GroupMessage]).wait(
                180, "TimeoutError"
            )
            if msg == "TimeoutError":
                message("等待超时，结束对话").target(sender).send()
                break
            elif msg[0] == "重置对话":
                await bot.reset()
                message("明白了，我已经抹去了过去，专注于现在。我们现在应该探索什么?").target(sender).quote(msg[1]).send()
            else:
                bot_response = await bot.ask(prompt=msg[0], conversation_style=ConversationStyle.creative)
                bot_msg = bot_response["item"]["messages"][1]
                message(parse_bot_msg(bot_msg)).target(sender).quote(msg[1]).send()
                if msg[0] == "结束对话":
                    break
    except Exception as e:
        unknown_error(sender)
        logger.error(e)
    finally:
        await bot.close()
        if target.id in session_pools:
            del session_pools[target.id]


@command.no_match(friend_limit=3)
async def chat(target: Union[Friend, Member], sender: Union[Friend, Group], source: Source, cmd: Arpamar):
    if cmd.find("keep"):
        await connect_chat(target, sender, source)
    elif cmd.find("msg"):
        await global_bot.reset()
        bot_response = await global_bot.ask(
            prompt=" ".join(cmd.query("msg")), conversation_style=ConversationStyle.creative
        )
        bot_msg = bot_response["item"]["messages"][1]
        message(parse_bot_msg(bot_msg)).target(sender).quote(source).send()
    else:
        message("请输入要发送的消息").target(sender).send()
