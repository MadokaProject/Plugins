import asyncio
from typing import List, Dict, Union

from arclet.alconna import Alconna, Subcommand, Args, Arpamar
from graia.ariadne import Ariadne
from graia.ariadne.event.message import FriendMessage
from graia.ariadne.model import Friend, Member, Group
from graia.ariadne.util.interrupt import FunctionWaiter
from graia.scheduler import GraiaScheduler, timers
from loguru import logger
from prettytable import PrettyTable

from app.core.app import AppCore
from app.core.commander import CommandDelegateManager
from app.util.dao import MysqlDao
from app.util.phrases import *
from app.util.text2image import create_image
from .sign import AutoSign

core: AppCore = AppCore()
app: Ariadne = core.get_app()
sche: GraiaScheduler = core.get_scheduler()
manager: CommandDelegateManager = CommandDelegateManager()


@manager.register(
    entry='xxt',
    brief_help='学习通',
    alc=Alconna(
        headers=manager.headers,
        command='xxt',
        options=[
            Subcommand('签到', help_text='立即进行一次签到操作'),
            Subcommand('自动签到', args=Args['status', [0, 1]], help_text='开关自动签到'),
            Subcommand('配置', help_text='配置学习通账号信息')
        ],
        help_text='学习通签到工具'
    ))
async def process(target: Union[Friend, Member], sender: Union[Friend, Group], command: Arpamar, alc: Alconna):
    if not command.subcommands:
        return await print_help(alc.get_help())
    try:
        if command.find('签到'):
            """签到一次"""
            info = await get_config(target.id)
            if not info:
                return MessageChain([Plain('你还未配置账号信息，请私聊我进行配置')])
            auto_sign = AutoSign(username=info[0],
                                 password=info[1],
                                 latitude=info[2],
                                 longitude=info[3],
                                 clientip=info[4],
                                 address=info[5])
            results: List[List[Dict]] = await auto_sign.start_sign_task()
            await auto_sign.close_session()
            return MessageChain([
                Image(data_bytes=await create_image(
                    (await send_message(results)).get_string())) if results else Plain('暂无签到任务')
            ])
        elif command.find('自动签到'):
            """自动签到开关"""
            if not await get_config(target.id):
                return MessageChain([Plain('你还未配置账号信息，请私聊我进行配置')])
            with MysqlDao() as db:
                db.update('UPDATE chaoxing_sign SET auto_sign=%s WHERE qid=%s', [command.query('status'), target.id])
            return MessageChain([Plain('开启成功' if command.query('status') else '关闭成功')])
        elif command.find('配置'):
            """配置账号信息"""

            async def waiter(waiter_friend: Friend, waiter_message: MessageChain):
                if waiter_friend.id == target.id:
                    waiter_saying = waiter_message.display
                    if waiter_saying == '取消':
                        await app.send_friend_message(waiter_friend, MessageChain([Plain('取消配置!')]))
                        return False
                    return waiter_saying

            async def answer_waiter(waiter_friend: Friend, waiter_message: MessageChain):
                if waiter_friend.id == target.id:
                    waiter_saying = waiter_message.display
                    if waiter_saying == '是':
                        return True
                    elif waiter_saying == '否':
                        return False
                    else:
                        await app.send_friend_message(waiter_friend, MessageChain([Plain('请回答：是 / 否')]))

            if isinstance(sender, Group):
                return MessageChain([Plain('请私聊我配置账号信息')])
            if await get_config(target.id):
                await app.send_friend_message(sender, MessageChain([Plain('你已经配置了账号信息，是否重新配置？')]))
                if not await FunctionWaiter(answer_waiter, [FriendMessage]).wait(15):
                    return
            await app.send_friend_message(sender, MessageChain([Plain('开始配置，若想中途退出配置请发送：取消')]))
            await app.send_friend_message(sender, MessageChain([Plain('请输入用户名（手机号）')]))
            if username := await FunctionWaiter(waiter, [FriendMessage]).wait(60):
                await app.send_friend_message(sender, MessageChain([Plain('请输入密码')]))
                if password := await FunctionWaiter(waiter, [FriendMessage]).wait(60):
                    await app.send_friend_message(sender, MessageChain([Plain('请输入定位纬度')]))
                    if latitude := await FunctionWaiter(waiter, [FriendMessage]).wait(60):
                        await app.send_friend_message(sender, MessageChain([Plain('请输入定位经度')]))
                        if longitude := await FunctionWaiter(waiter, [FriendMessage]).wait(60):
                            await app.send_friend_message(sender, MessageChain([Plain('请输入你的IP地址')]))
                            if clientip := await FunctionWaiter(waiter, [FriendMessage]).wait(60):
                                await app.send_friend_message(sender, MessageChain([Plain('请输入定位地址名')]))
                                if address := await FunctionWaiter(waiter, [FriendMessage]).wait(60):
                                    await app.send_friend_message(sender, MessageChain([
                                        Plain('配置完成，请检查你的配置信息\r\n'),
                                        Plain(f'用户名：{username}\r\n密码：{password}\r\n纬度：{latitude}\r\n'),
                                        Plain(f'经度：{longitude}\r\nIP地址：{clientip}\r\n地址名：{address}\r\n'),
                                        Plain('是否保存？')
                                    ]))
                                    if await FunctionWaiter(answer_waiter, [FriendMessage]).wait(30):
                                        with MysqlDao() as db:
                                            db.update(
                                                'REPLACE INTO chaoxing_sign(qid, username, password, latitude, longitude, clientip, address) '
                                                'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                                                [target.id, username, password, latitude, longitude, clientip,
                                                 address]
                                            )
                                        return MessageChain([Plain('配置成功！')])
        else:
            return args_error()
    except asyncio.TimeoutError:
        return MessageChain([Plain('回答超时')])
    except Exception as e:
        logger.exception(e)
        return unknown_error()


async def get_config(user_id) -> list:
    with MysqlDao() as db:
        res = db.query(
            'SELECT username, password, latitude, longitude, clientip, address FROM chaoxing_sign WHERE qid=%s',
            [user_id]
        )
        return res[0] if res else None


async def gen_run(info: dict) -> List[List[Dict]]:
    auto_sign = AutoSign(username=info['username'],
                         password=info['password'],
                         latitude=info['latitude'],
                         longitude=info['longitude'],
                         clientip=info['clientip'],
                         address=info.get('address', None))
    result: List[List[Dict]] = await auto_sign.start_sign_task()
    await auto_sign.close_session()
    return result


async def send_message(datas):
    msg = PrettyTable()
    msg.field_names = ['课程名', '签到时间', '签到状态']
    for data in datas:
        if data:
            msg.add_row([data['name'], data['date'], data['status']])
    msg.align = 'r'
    return msg


@sche.schedule(timers.crontabify('* 8-17 * * * 10'))
@logger.catch()
async def tasker():
    logger.info('chaoxing tasker is running ...')
    with MysqlDao() as db:
        info = db.query('SELECT * FROM chaoxing_sign WHERE expiration_time>=CURDATE() and auto_sign=1')
    for user in info:
        if result := await gen_run({
            "username": user[1],
            "password": user[2],
            "latitude": user[3],
            "longitude": user[4],
            "clientip": user[5],
            "address": user[6]
        }):
            await app.send_friend_message(int(user[0]), MessageChain([
                Image(data_bytes=await create_image((await send_message(result)).get_string()))
            ]))
