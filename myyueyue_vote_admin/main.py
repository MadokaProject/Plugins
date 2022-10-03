import asyncio
import contextlib
import random
from typing import Union, Dict, Tuple

from app.core.config import Config
from app.util.alconna import Args, Subcommand, Option, Arpamar, Commander
from app.util.graia import (
    Ariadne,
    GroupMessage,
    MessageChain,
    At,
    Plain,
    Source,
    Group,
    Member,
    MemberPerm,
    FunctionWaiter,
    message,
)
from app.util.control import Permission
from app.util.online_config import save_config, get_config
from app.util.phrases import not_admin, args_error, exec_permission_error


command = Commander(
    "vote",
    "投票管理",
    Args["member;O", [At, int]]["time;O", int, 5],
    Subcommand("mute", help_text="投票禁言"),
    Subcommand("kick", help_text="投票踢出"),
    Subcommand("user", help_text="投票成员管理(仅管理可用)"),
    Option("--add", help_text="添加"),
    Option("--delete", help_text="删除"),
    Option("--list", help_text="列出"),
    Option("--config", help_text="设置投票通过比例", args=Args["proportion;O", float]),
)


@command.parse("user", events=[GroupMessage], permission=Permission.GROUP_ADMIN)
async def user_vote(sender: Group, cmd: Arpamar):
    vote_admin_users = (await get_config("myyueyue_vote", sender)).get("user", [])
    if cmd.find("list"):
        return (
            message([Plain("可投票成员: \n"), Plain("\n".join(f"{i}" for i in vote_admin_users))])
            .target(sender)
            .send()
        )
    if not (member := cmd.query("member")):
        return message("缺少 member 参数").target(sender).send()
    if isinstance(member, At):
        member = member.target
    if cmd.find("add"):
        if member in vote_admin_users:
            return message("该用户已存在").target(sender).send()
        vote_admin_users.append(member)
        await save_config(
            "myyueyue_vote", sender, {"user": vote_admin_users}, model="add"
        )
        return message("添加用户成功").target(sender).send()
    elif cmd.find("delete"):
        if member not in vote_admin_users:
            return message("该用户不存在").target(sender).send()
        vote_admin_users.remove(member)
        await save_config(
            "myyueyue_vote", sender, {"user": vote_admin_users}, model="add"
        )
        return message("删除用户成功").target(sender).send()
    else:
        return args_error(sender)


@command.parse("config", events=[GroupMessage], permission=Permission.GROUP_ADMIN)
async def config_vote(sender: Group, cmd: Arpamar):
    if cmd.find("list"):
        return (
            message(
                [
                    Plain("配置信息:\n"),
                    Plain(
                        "\n".join(
                            f"{k}: {v}"
                            for k, v in (
                                await get_config("myyueyue_vote", sender)
                            ).items()
                            if k != "user"
                        )
                    ),
                ]
            )
            .target(sender)
            .send()
        )
    if cmd.find("mute"):
        _type = "mute"
    elif cmd.find("kick"):
        _type = "kick"
    else:
        return message("缺少 mute 或 kick 参数").target(sender).send()
    proportion = cmd.query("proportion")
    if 0 < proportion <= 1:
        await save_config("myyueyue_vote", sender, {_type: proportion}, model="add")
        return message("设置成功！").target(sender).send()
    else:
        return message("比例应在 0-1 之间").target(sender).send()


@command.no_match(events=[GroupMessage])
async def start_vote(app: Ariadne, target: Member, sender: Group, cmd: Arpamar):
    vote_config = await get_config("myyueyue_vote", sender)
    vote_admin_users = vote_config.get("user", [])
    vote_mark = random.randint(1, 99999999)
    vote_result: Dict[int, bool] = {}

    async def voter(
        vote_member: Member,
        vote_group: Group,
        vote_message: MessageChain,
        vote_source: Source,
    ):
        """投票器"""
        vote_message = vote_message.display.replace("：", ":").replace(" ", "")
        if all([sender.id == vote_group.id, vote_member.id in vote_admin_users]):
            if vote_message == f"同意:{vote_mark}":
                vote_result[vote_member.id] = True
                message("你投了同意票").target(vote_group).quote(vote_source).send()
            elif vote_message == f"反对:{vote_mark}":
                vote_result[vote_member.id] = False
                message("你投了反对票").target(vote_group).quote(vote_source).send()
            if len(vote_result) == len(vote_admin_users):
                return True

    async def vote(vote_user: int, _type: str) -> Tuple[float, bool]:
        """投票

        :param vote_user: 投票目标
        :param _type: 投票类型
        """
        with contextlib.suppress(asyncio.TimeoutError):
            message(
                [
                    Plain("投票发起成功，请拥有投票权限者在90秒内投票！（重复投票可覆盖）\n"),
                    Plain("投票目标: "),
                    At(vote_user),
                    Plain(f"\n标识号: {vote_mark}\n"),
                    Plain(f"请输入: 同意:{vote_mark} | 反对:{vote_mark}"),
                ]
            ).target(sender).send()
            await FunctionWaiter(voter, [GroupMessage]).wait(90)
        _proportion = len([i for i in vote_result.values() if i]) / len(vote_result)
        if _type not in vote_config:
            vote_config[_type] = 0.7
        if _proportion > vote_config[_type]:
            vote_ret = _proportion, True
        else:
            vote_ret = _proportion, False
        message(
            [Plain(f"投票结果: {vote_ret[1]}\n"), Plain(f"同意比例: {vote_ret[0]:.2%}")]
        ).target(sender).send()
        return vote_ret

    if target.id not in vote_admin_users:
        return not_admin(sender)

    if not cmd.find("member"):
        return message("缺少 member 参数").target(sender).send()

    user: Union[At, int] = cmd.query("member")
    if isinstance(user, At):
        user: int = user.target
    if sender.account_perm == MemberPerm.Member:
        return exec_permission_error(sender)
    if user == app.account:
        return message("怎么会有笨蛋想要对我投票").target(sender).send()
    if user == Config().MASTER_QQ:
        await app.mute_member(sender, target, 30)
        return message("你又在调皮了").target(sender).send()
    if (
        user in vote_admin_users
        or (await app.get_member(sender, user)).permission != MemberPerm.Member
    ):
        return message("不能对拥有投票权限或管理员权限的成员进行投票").target(sender).send()

    if cmd.find("mute"):
        ret = await vote(user, "mute")
        if ret[1]:
            await app.mute_member(sender, user, cmd.query("time") * 60)
    elif cmd.find("kick"):
        ret = await vote(user, "kick")
        if ret[1]:
            await app.kick_member(sender, user, cmd.query("time") * 60)
    else:
        return args_error(sender)
