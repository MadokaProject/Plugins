import requests
from loguru import logger
from peewee import fn

from app.core.app import AppCore
from app.util.alconna import Args, Subcommand, Arpamar, Commander
from app.util.graia import (
    Ariadne,
    Friend,
    FriendMessage,
    GraiaScheduler,
    timers,
    message,
)
from app.util.phrases import *
from .database.database import PluginSspanelAccount as DBSspanel

requests.packages.urllib3.disable_warnings()

core: AppCore = AppCore()
app: Ariadne = core.get_app()
sche: GraiaScheduler = core.get_scheduler()


command = Commander(
    "sspanel",
    "机场签到",
    Subcommand(
        "qd",
        help_text="立即进行一次签到",
        args=Args["host", "url"]["email", "email"]["password", str],
    ),
    Subcommand(
        "add",
        help_text="添加/修改签到账号",
        args=Args["host", "url"]["email", "email"]["password", str],
    ),
    Subcommand(
        "remove", help_text="删除签到账号", args=Args["host", "url"]["email", "email"]
    ),
    Subcommand("list", help_text="列出你添加的签到账号"),
    help_text="机场签到: 为保证账号安全, 该服务仅私发有效",
)


@command.parse("qd", events=[FriendMessage])
async def qd_sspanel(sender: Friend, cmd: Arpamar):
    account = {
        0: {
            "web": cmd.query("host"),
            "user": cmd.query("email"),
            "pwd": cmd.query("password"),
        }
    }
    msg = await checkin(account)
    message([Plain("机场签到完成\r\n"), Plain(msg)]).target(sender).send()


@command.parse("add", events=[FriendMessage])
async def add_sspanel(sender: Friend, cmd: Arpamar):
    DBSspanel.replace(
        qid=sender.id,
        web=cmd.query("host"),
        user=cmd.query("email"),
        pwd=cmd.query("password"),
    ).execute()
    message("添加/修改成功！").target(sender).send()


@command.parse("remove", events=[FriendMessage])
async def remove_sspanel(sender: Friend, cmd: Arpamar):
    DBSspanel.delete().where(
        DBSspanel.qid == sender.id,
        DBSspanel.web == cmd.query("host"),
        DBSspanel.user == cmd.query("email"),
    ).execute()
    message("删除成功！").target(sender).send()


@command.parse("list", events=[FriendMessage])
async def list_sspanel(sender: Friend):
    message(
        "\n".join(
            f"{index}: {res.web}\t{res.user}"
            for index, res in enumerate(
                DBSspanel.select().where(DBSspanel.qid == sender.id)
            )
        )
    ).target(sender).send()


@sche.schedule(timers.crontabify("0 8 * * * 0"))
async def tasker():
    for res in DBSspanel.select(
        DBSspanel.qid,
        fn.GROUP_CONCAT(DBSspanel.web, "||").alias("group_web"),
        fn.GROUP_CONCAT(DBSspanel.user, "||").alias("group_user"),
        fn.GROUP_CONCAT(DBSspanel.pwd, "||").alias("group_pwd"),
    ).group_by(DBSspanel.qid):
        accounts = {
            index: {"web": web, "user": user, "pwd": pwd}
            for index, (web, user, pwd) in enumerate(
                zip(
                    res.group_web.replace("||,", "||").strip("||").split("||"),
                    res.group_user.replace("||,", "||").strip("||").split("||"),
                    res.group_pwd.replace("||,", "||").strip("||").split("||"),
                )
            )
        }
        msg = await checkin(accounts)
        await message_send(msg, int(res.qid))


async def checkin(account):
    msgall = ""
    for i in account.keys():

        email = account[i]["user"].split("@")
        email = f"{email[0]}%40{email[1]}"
        password = account[i]["pwd"]

        session = requests.session()

        try:
            # 以下except都是用来捕获当requests请求出现异常时，
            # 通过捕获然后等待网络情况的变化，以此来保护程序的不间断运行
            session.get(account[i]["web"], verify=False)

        except requests.exceptions.ConnectionError:
            msg = account[i]["web"] + "\n\n" + "网络不通"
            msgall = msgall + account[i]["web"] + "\n\n" + msg + "\n\n"
            logger.warning(msg)
            continue
        except requests.exceptions.ChunkedEncodingError:
            msg = account[i]["web"] + "\n\n" + "分块编码错误"
            msgall = msgall + account[i]["web"] + "\n\n" + msg + "\n\n"
            logger.warning(msg)
            continue
        except Exception as e:
            msg = account[i]["web"] + "\n\n" + "未知错误"
            msgall = msgall + account[i]["web"] + "\n\n" + msg + "\n\n"
            logger.warning(msg)
            logger.exception(e)
            continue

        login_url = account[i]["web"] + "/auth/login"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

        post_data = f"email={email}&passwd={password}&code="
        post_data = post_data.encode()
        session.post(login_url, post_data, headers=headers, verify=False)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
            "Referer": account[i]["web"] + "/user",
        }

        response = session.post(
            account[i]["web"] + "/user/checkin", headers=headers, verify=False
        )
        msg = (response.json()).get("msg")

        msgall = msgall + account[i]["web"] + "\n\n" + msg + "\n\n"

        info_url = account[i]["web"] + "/user"
        session.get(info_url, verify=False)

    return msgall


async def message_send(msg, qid):
    """签到消息推送"""
    message([Plain("机场签到完成\r\n"), Plain(msg)]).target(qid).send()
