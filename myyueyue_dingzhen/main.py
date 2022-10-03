import json
from typing import Union

from app.util.alconna import Commander
from app.util.graia import Friend, Group, Image, message
from app.util.network import general_request

command = Commander("来点丁真", "礼堂丁真", command="来点丁真")


@command.no_match()
async def ding(sender: Union[Friend, Group]):
    base_url = "https://raw.fastgit.org/Brx86/DingZhen/main/src/"
    resp = json.loads(
        await general_request("https://api.ay1.us/randomdj?r=0"), encoding="utf-8"
    )
    message(Image(url=base_url + resp["url"].split("/")[-1])).target(sender).send()
