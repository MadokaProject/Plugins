from arclet.alconna import Alconna, Subcommand, Args, Arpamar
from loguru import logger

from app.core.commander import CommandDelegateManager
from app.util.network import general_request
from app.util.phrases import *

manager: CommandDelegateManager = CommandDelegateManager()


@manager.register(
    entry='site',
    brief_help="站点工具",
    alc=Alconna(
        headers=manager.headers,
        command='site',
        options=[
            Subcommand('ping', help_text='ping网站测速'),
            Subcommand('speed', help_text='网站测速'),
            Subcommand('dmreg', help_text='域名注册查询'),
            Subcommand('dmjc',help_text='域名拦截检测'),
            Subcommand('gab',help_text='公安备案查询')
        ],
        main_args=Args['site;O|H', str],
        help_text='站点工具'
    )
)
async def process(cmd: Arpamar, alc: Alconna):
    if not cmd.subcommands:
        return await print_help(alc.get_help())
    try:
        site = cmd.query('site')
        if cmd.find('ping'):
            api = 'http://api.api.kingapi.cloud/api/ping.php'
            result = await general_request(api, 'GET', params={'url': site})
            return MessageChain(result)
        elif cmd.find('speed'):
            api = 'http://api.api.kingapi.cloud/api/cs.php'
            result = await general_request(api, 'GET', params={'url': site})
            return MessageChain('\n'.join(i for i in result.split('\n')[2:-2]))
        elif cmd.find('dmreg'):
            api = 'http://api.api.kingapi.cloud/api/dmreg.php'
            result = await general_request(api, 'GET', params={'url':site})
            return MessageChain('\n'.join(i for i in result.split('\n')[2:-2]))
        elif cmd.find('dmjc'):
            api= 'http://api.api.kingapi.cloud/api/qmjc.php'
            result = await general_request(api,'GET', params={'url':site})
            return MessageChain(('\n'.join(i for i in result.split('\n')[2:-2])))
        elif cmd.find('gab'):
            api= 'http://api.api.kingapi.cloud/api/GongAnBeiAn.php'
            result = await general_request(api,'GET', 'JSON', params={'url':site})
            return MessageChain(result['msg'])
        else:
            return args_error()
    except Exception as e:
        logger.error(e)
        return unknown_error()
