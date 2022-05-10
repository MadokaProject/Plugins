import asyncio
from typing import List, Dict

from arclet.alconna import Alconna, Subcommand, Args, Arpamar
from graia.ariadne.event.message import FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain, Image
from graia.ariadne.model import Friend
from graia.broadcast.interrupt.waiter import Waiter
from loguru import logger
from prettytable import PrettyTable

from app.core.commander import CommandDelegateManager
from app.plugin.base import Plugin, Scheduler, InitDB
from app.util.dao import MysqlDao
from app.util.text2image import create_image
from .chaoxing_res.sign import AutoSign


class Module(Plugin):
    entry = 'xxt'
    brief_help = '学习通'
    manager: CommandDelegateManager = CommandDelegateManager.get_instance()

    @manager.register(Alconna(
        headers=manager.headers,
        command=entry,
        options=[
            Subcommand('签到', help_text='立即进行一次签到操作'),
            Subcommand('自动签到', args=Args['status': ['0', '1']], help_text='开关自动签到'),
            Subcommand('配置', help_text='配置学习通账号信息')
        ],
        help_text='学习通签到工具'
    ))
    async def process(self, command: Arpamar, alc: Alconna):
        if not command.subcommands:
            return await self.print_help(alc.get_help())
        try:
            user = getattr(self, 'friend', None) or getattr(self, 'member', None)
            if command.find('签到'):
                """签到一次"""
                info = await get_config(user.id)
                if not info:
                    return MessageChain.create([Plain('你还未配置账号信息，请私聊我进行配置')])
                auto_sign = AutoSign(username=info[0],
                                     password=info[1],
                                     latitude=info[2],
                                     longitude=info[3],
                                     clientip=info[4],
                                     address=info[5])
                results: List[List[Dict]] = await auto_sign.start_sign_task()
                await auto_sign.close_session()
                return MessageChain.create([
                    Image(data_bytes=await create_image(
                        (await send_message(results)).get_string())) if results else Plain('暂无签到任务')
                ])
            elif command.find('自动签到'):
                """自动签到开关"""
                if not await get_config(user.id):
                    return MessageChain.create([Plain('你还未配置账号信息，请私聊我进行配置')])
                with MysqlDao() as db:
                    db.update('UPDATE chaoxing_sign SET auto_sign=%s WHERE qid=%s', [command.query('status'), user.id])
                return MessageChain.create([Plain('开启成功' if int(self.msg[1]) else '关闭成功')])
            elif command.find('配置'):
                """配置账号信息"""

                @Waiter.create_using_function([FriendMessage])
                async def waiter(waiter_friend: Friend, waiter_message: MessageChain):
                    if waiter_friend.id == self.friend.id:
                        waiter_saying = waiter_message.asDisplay()
                        if waiter_saying == '取消':
                            await self.app.sendFriendMessage(waiter_friend, MessageChain.create([Plain('取消配置!')]))
                            return False
                        return waiter_saying

                @Waiter.create_using_function([FriendMessage])
                async def answer_waiter(waiter_friend: Friend, waiter_message: MessageChain):
                    if waiter_friend.id == self.friend.id:
                        waiter_saying = waiter_message.asDisplay()
                        if waiter_saying == '是':
                            return True
                        elif waiter_saying == '否':
                            return False
                        else:
                            await self.app.sendFriendMessage(waiter_friend, MessageChain.create([Plain('请回答：是 / 否')]))

                if not hasattr(self, 'friend'):
                    return MessageChain.create([Plain('请私聊我配置账号信息')])
                if await get_config(user.id):
                    await self.app.sendFriendMessage(self.friend, MessageChain.create([Plain('你已经配置了账号信息，是否重新配置？')]))
                    if not await asyncio.wait_for(self.inc.wait(answer_waiter), timeout=15):
                        return
                await self.app.sendFriendMessage(self.friend, MessageChain.create([Plain('开始配置，若想中途退出配置请发送：取消')]))
                await asyncio.sleep(1)
                await self.app.sendFriendMessage(self.friend, MessageChain.create([Plain('请输入用户名（手机号）')]))
                if username := await asyncio.wait_for(self.inc.wait(waiter), timeout=60):
                    await self.app.sendFriendMessage(self.friend, MessageChain.create([Plain('请输入密码')]))
                    if password := await asyncio.wait_for(self.inc.wait(waiter), timeout=60):
                        await self.app.sendFriendMessage(self.friend, MessageChain.create([Plain('请输入定位纬度')]))
                        if latitude := await asyncio.wait_for(self.inc.wait(waiter), timeout=60):
                            await self.app.sendFriendMessage(self.friend, MessageChain.create([Plain('请输入定位经度')]))
                            if longitude := await asyncio.wait_for(self.inc.wait(waiter), timeout=60):
                                await self.app.sendFriendMessage(self.friend, MessageChain.create([Plain('请输入你的IP地址')]))
                                if clientip := await asyncio.wait_for(self.inc.wait(waiter), timeout=60):
                                    await self.app.sendFriendMessage(self.friend,
                                                                     MessageChain.create([Plain('请输入定位地址名')]))
                                    if address := await asyncio.wait_for(self.inc.wait(waiter), timeout=60):
                                        await self.app.sendFriendMessage(self.friend, MessageChain.create([
                                            Plain('配置完成，请检查你的配置信息\r\n'),
                                            Plain(f'用户名：{username}\r\n密码：{password}\r\n纬度：{latitude}\r\n'),
                                            Plain(f'经度：{longitude}\r\nIP地址：{clientip}\r\n地址名：{address}\r\n'),
                                            Plain('是否保存？')
                                        ]))
                                        if await asyncio.wait_for(self.inc.wait(answer_waiter), timeout=30):
                                            with MysqlDao() as db:
                                                db.update(
                                                    'REPLACE INTO chaoxing_sign(qid, username, password, latitude, longitude, clientip, address) '
                                                    'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                                                    [self.friend.id, username, password, latitude, longitude, clientip,
                                                     address]
                                                )
                                            return MessageChain.create([Plain('配置成功！')])
            else:
                return self.args_error()
        except asyncio.TimeoutError:
            return MessageChain.create([Plain('回答超时')])
        except Exception as e:
            logger.exception(e)
            return self.unkown_error()


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


class Tasker(Scheduler):
    cron = '* 8-17 * * * 10'

    async def process(self):
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
                await self.app.sendFriendMessage(int(user[0]), MessageChain.create([
                    Image(data_bytes=await create_image((await send_message(result)).get_string()))
                ]))


class DB(InitDB):
    async def process(self):
        with MysqlDao() as _db:
            _db.update(
                "create table if not exists chaoxing_sign( \
                    qid char(12) not null comment 'QQ', \
                    username char(11) not null comment '手机号', \
                    password varchar(256) not null comment '密码', \
                    latitude varchar(256) null default '-2' comment '纬度', \
                    longitude varchar(256) null default '-1' comment '经度', \
                    clientip varchar(20) not null comment 'IP地址', \
                    address varchar(256) null default '中国' comment '地址名', \
                    expiration_time datetime null comment '到期时间', \
                    auto_sign int null default 0 comment '自动签到状态', \
                    primary key (qid))"
            )
