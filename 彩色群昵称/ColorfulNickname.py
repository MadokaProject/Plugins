import random

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Image, At
from graia.ariadne.model import MemberInfo
from loguru import logger
from prettytable import PrettyTable

from app.core.config import Config
from app.plugin.base import Plugin
from app.util.text2image import create_image
from app.util.tools import isstartswith

color_code = {
    '黑色': '<&ÿĀĀĀ>',
    '红色': '<&ÿÿ5@>',
    '粉色': '<&ÿÿ]>',
    '紫色': '<&ÿÒUÐ>',
    '蓝色': '<&ÿÇý>',
    '绿色': '<&ÿÄW>',
    '黄色': '<&ÿÿÏP>',
    '初春': '<%ĀĀÐ>',
    '冬梅': '<%ĀĀÑ>',
    '高级灰': '<%ĀĀÒ>',
    '黄昏': '<%ĀĀÓ>',
    '科技感': '<%ĀĀÔ>',
    '马卡龙': '<%ĀĀÕ>',
    '霓虹闪烁': '<%ĀĀÖ>',
    '日出': '<%ĀĀ×>',
    '盛夏': '<%ĀĀØ>',
    '糖果冰纷': '<%ĀĀÙ>',
    '晚秋': '<%ĀĀÚ>',
    '夜空': '<%ĀĀÛ>',
    '粉黛': '<%ĀĀÜ>',
    '朝夕': '<%ĀĀÝ>',
    '潮流': '%ĀĀÞ>'
}


def generate_color_code(index: int = None) -> str:
    if index:
        return {i + 1: code for i, code in enumerate(color_code.values())}[index]
    else:
        return random.choice(list(color_code.values()))


class ColorFulNickName(Plugin):
    entry = ['.colorname', '.彩色昵称']
    brief_help = '\r\n[√]\t彩色群昵称：colorname'
    full_help = \
        '.彩色昵称/.colorname 查看/list\t查看支持的彩色昵称列表\r\n' \
        '.彩色昵称/.colorname 更换/change [id]\t选择一种颜色更换群昵称\r\n' \
        '.彩色昵称/.colorname 随机/random\t随机更换一种颜色'

    async def process(self):
        if not self.msg:
            self.print_help()
            return
        try:
            if not hasattr(self, 'group'):
                self.resp = MessageChain.create([Plain('请在群里中使用该命令！')])
                return
            if isstartswith(self.msg[0], ['查看', 'list']):
                msg = PrettyTable()
                msg.field_names = ['序号', '颜色名']
                for index, item in enumerate(color_code.keys()):
                    msg.add_row([index + 1, item])
                msg.align = 'r'
                msg.align['颜色名'] = 'l'
                self.resp = MessageChain.create([
                    Image(data_bytes=(await create_image(msg.get_string())).getvalue()),
                    Image(url='https://wxsnote.cn/wp-content/uploads/2021/08/1630250432-321.png')
                ])
            elif isstartswith(self.msg[0], ['更换', 'change', '随机', 'random']):
                if self.msg[0] in ['更换', 'change']:
                    assert len(self.msg) == 2 and self.msg[1].isdigit()
                self.resp = MessageChain.create([
                    At(self.member.id),
                    Plain(' 请将该代码复制粘贴至你的群昵称前面后保存: \r\n' + f"{generate_color_code(int(self.msg[1]) if self.msg[0] in ['更换', 'change'] else None)}")
                ])
            else:
                self.args_error()
                return
        except PermissionError as e:
            print(e)
            self.exec_permission_error()
        except AssertionError as e:
            print(e)
            self.args_error()
        except Exception as e:
            logger.exception(e)
            self.unkown_error()
