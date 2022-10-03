from typing import Union

from app.util.alconna import Subcommand, Args, Arpamar, Commander
from app.util.graia import Friend, Group, message
from app.util.network import general_request
from app.util.phrases import *

command = Commander(
    "site",
    "站点工具",
    Args["site;O|H", str],
    Subcommand("ping", help_text="ping网站测速"),
    Subcommand("speed", help_text="网站测速"),
    Subcommand("dmreg", help_text="域名注册查询"),
    Subcommand("dmjc", help_text="域名拦截检测"),
    Subcommand("gab", help_text="公安备案查询"),
)


@command.parse("ping")
async def ping_site_tools(sender: Union[Friend, Group], cmd: Arpamar):
    api = "http://api.api.kingapi.cloud/api/ping.php"
    result = await general_request(api, "GET", params={"url": cmd.query("site")})
    message(result).target(sender).send()


@command.parse("speed")
async def speed_site_tools(sender: Union[Friend, Group], cmd: Arpamar):
    api = "http://api.api.kingapi.cloud/api/cs.php"
    result = await general_request(api, "GET", params={"url": cmd.query("site")})
    message("\n".join(result.split("\n")[2:-2])).target(sender).send()


@command.parse("dmreg")
async def dmreg_site_tools(sender: Union[Friend, Group], cmd: Arpamar):
    api = "http://api.api.kingapi.cloud/api/dmreg.php"
    result = await general_request(api, "GET", params={"url": cmd.query("site")})
    message("\n".join(result.split("\n")[2:-2])).target(sender).send()


@command.parse("dmjc")
async def dmjc_site_tools(sender: Union[Friend, Group], cmd: Arpamar):
    api = "http://api.api.kingapi.cloud/api/qmjc.php"
    result = await general_request(api, "GET", params={"url": cmd.query("site")})
    message("\n".join(result.split("\n")[2:-2])).target(sender).send()


@command.parse("gab")
async def gab_site_tools(sender: Union[Friend, Group], cmd: Arpamar):
    api = "http://api.api.kingapi.cloud/api/GongAnBeiAn.php"
    result = await general_request(
        api, "GET", "JSON", params={"url": cmd.query("site")}
    )
    message(result["msg"]).target(sender).send()
