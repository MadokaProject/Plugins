import asyncio
import random
import time
from collections import Counter

from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.exception import UnknownTarget
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Source, Plain, At
from graia.ariadne.model import Friend, Group, Member, MemberPerm
from graia.broadcast.interrupt.waiter import Waiter
from loguru import logger

from app.core.config import Config
from app.core.settings import *
from app.entities.user import *
from app.plugin.base import Plugin
from app.util.tools import isstartswith

positions_info = {'wolf': '狼人', 'vil': '村民', 'prophet': '预言家', 'guard': '守卫', 'witch': '女巫', 'hunter': '猎人'}


class WereWolfGame(Plugin):
    entry = ['.wolf', '.狼人杀']
    brief_help = '\r\n[√]\t狼人杀：wolf'
    full_help = \
        '.狼人杀/.wolf 创建/create\t创建狼人杀游戏\r\n' \
        '.狼人杀/.wolf 加入/join\t加入狼人杀游戏\r\n' \
        '.狼人杀/.wolf 退出/exit\t退出狼人杀游戏\r\n' \
        '.狼人杀/.wolf 结束/stop\t强制结束狼人杀游戏(管理员)'

    async def judge_playing(self):
        """判断用户是否正在游戏中"""
        if self.member.id in MEMBER_RUNING_LIST:
            return True
        else:
            MEMBER_RUNING_LIST.append(self.member.id)

    async def private_letter(self):
        """判断私信是否可用"""
        try:
            await self.app.sendFriendMessage(self.member.id, MessageChain.create([
                Plain(f"本消息仅用于测试私信是否可用，无需回复\n{time.time()}")
            ]))
        except:
            config = Config()
            await self.app.sendGroupMessage(self.group, MessageChain.create([
                Plain(f"由于你未添加好友，暂时无法发起|加入狼人杀，请自行添加 {config.BOT_NAME} 好友，用于发送身份牌及发言投票")
            ]))
            MEMBER_RUNING_LIST.remove(self.member.id)
            return True

    async def initialize_game(self):
        """初始化游戏
        wolf: 狼人
        vil: 村民
        prophet: 预言家
        guard: 守卫
        witch: 女巫
        hunter: 猎人
        """
        num = len(GROUP_GAME_PROCESS[self.group.id]['player'])
        all_positions = {
            6: ['wolf', 'wolf', 'vil', 'vil', 'prophet', 'guard'],
            7: ['wolf', 'wolf', 'vil', 'vil', 'vil', 'prophet', 'guard'],
            8: ['wolf', 'wolf', 'wolf', 'vil', 'vil', 'vil', 'prophet', 'witch'],
            9: ['wolf', 'wolf', 'wolf', 'vil', 'vil', 'vil', 'prophet', 'witch', 'hunter']
        }
        positions = all_positions[num]
        random.shuffle(positions)

        def add_user_position(player, **kwargs):
            """添加玩家职业"""
            GROUP_GAME_PROCESS[self.group.id]['position'].update(
                {player: {k: v for k, v in kwargs.items()}})

        for i in range(num):
            ability = None
            if positions[i] == 'witch':
                ability = ['antidote', 'poison']
            elif positions[i] in ['prophet', 'hunter']:
                ability = []
            add_user_position(GROUP_GAME_PROCESS[self.group.id]['player'][i], position=positions[i], survive=1,
                              ability=ability)

    async def process(self):
        if not self.msg:
            self.print_help()
            return
        try:
            if not hasattr(self, 'group'):
                self.resp = MessageChain.create([
                    Plain('独乐乐不如众乐乐，请在群聊内使用该命令跟大家一起玩吧!')
                ])
                return
            if isstartswith(self.msg[0], ['创建', 'create']):
                """创建狼人杀游戏房间"""
                # 检查机器人是否为管理
                if self.group.accountPerm == MemberPerm.Member:
                    await self.app.sendGroupMessage(self.group.id, MessageChain.create([
                        Plain('由于机器人非管理员，暂时无法发起狼人杀游戏，请联系群主将机器人设为管理，用于法官调度'),
                    ]))
                    return
                # 判断用户是否正在游戏中
                if await self.judge_playing():
                    return
                # 判断私信是否可用
                if await self.private_letter():
                    return

                # 请求确认中断
                @Waiter.create_using_function([GroupMessage])
                async def confirm(confirm_group: Group, confirm_member: Member, confirm_message: MessageChain,
                                  confirm_source: Source):
                    if all([confirm_group.id == self.group.id,
                            confirm_member.id == self.member.id]):
                        saying = confirm_message.asDisplay()
                        if saying == "是":
                            return True
                        elif saying == "否":
                            return False
                        else:
                            await self.app.sendGroupMessage(self.group, MessageChain.create([
                                At(confirm_member.id),
                                Plain("请发送是或否来进行确认")
                            ]), quote=confirm_source)

                # 等待开始游戏
                @Waiter.create_using_function([GroupMessage])
                async def wait_start(wait_start_group: Group, wait_start_member: Member,
                                     wait_start_message: MessageChain,
                                     wait_start_source: Source):
                    if all([wait_start_group.id == self.group.id,
                            wait_start_member.id == self.member.id]):
                        saying = wait_start_message.asDisplay()
                        if saying == "开始游戏":
                            if len(GROUP_GAME_PROCESS[self.group.id]['player']) < 5:  # 玩家少于6人不能开始(房主最后加入玩家列表)
                                await self.app.sendGroupMessage(self.group, MessageChain.create([
                                    At(wait_start_member.id),
                                    Plain("游戏玩家必须6人以上才能开始")
                                ]), quote=wait_start_source)
                            else:
                                return True
                        elif saying == "解散游戏":
                            return False

                # 如果当前群有一个正在进行中的游戏
                if self.group.id in GROUP_RUNING_LIST:
                    if self.group.id not in GROUP_GAME_PROCESS:
                        await self.app.sendGroupMessage(self.group, MessageChain.create([
                            At(self.member.id),
                            Plain(" 本群正在请求确认开启一场游戏，请稍候")
                        ]), quote=self.source)
                    else:
                        owner = GROUP_GAME_PROCESS[self.group.id]["owner"]
                        owner_name = (await self.app.getMember(self.group, owner)).name
                        await self.app.sendGroupMessage(self.group, MessageChain.create([
                            At(self.member.id),
                            Plain(" 本群存在一场已经开始的游戏，请等待当前游戏结束"),
                            Plain(f"\n发起者：{str(owner)} | {owner_name}")
                        ]), quote=self.source)
                # 新游戏创建流程
                else:
                    GROUP_RUNING_LIST.append(self.group.id)
                    try:
                        await self.app.sendGroupMessage(self.group, MessageChain.create([
                            Plain("是否确认在本群开启一场狼人杀？")
                        ]), quote=self.source)
                    except UnknownTarget:
                        await self.app.sendGroupMessage(self.group, MessageChain.create([
                            At(self.member.id),
                            Plain(" 是否确认在本群开启一场狼人杀？")
                        ]))
                    try:
                        # 新游戏创建完成，进入等待玩家阶段
                        if await asyncio.wait_for(self.inc.wait(confirm), timeout=15):
                            GROUP_GAME_PROCESS[self.group.id] = {
                                "owner": self.member.id,
                                "player": [],  # 加入的游戏玩家
                                "position": {}  # 职位等信息（开始游戏后生成）
                            }
                            if BotUser(str(self.member.id)).get_points() < 4:
                                GROUP_RUNING_LIST.remove(self.group.id)
                                del GROUP_GAME_PROCESS[self.group.id]
                                await self.app.sendGroupMessage(self.group, MessageChain.create([
                                    At(self.member.id),
                                    Plain(" 你的积分不足，无法开始游戏")]))
                                # 将用户移除正在游戏中
                                MEMBER_RUNING_LIST.remove(self.member.id)
                                return
                            else:
                                # BotUser(str(self.member.id)).update_point(-4)
                                await self.app.sendGroupMessage(self.group, MessageChain.create([
                                    Plain("狼人杀游戏已创建，请等待群员加入游戏\r\n开始游戏请发送开始游戏\r\n解散游戏请发送解散游戏"),
                                ]), quote=self.source)
                            while True:
                                counts = [1, 2, 3, 4, 5, 6]
                                for count in counts:
                                    try:
                                        result = await asyncio.wait_for(self.inc.wait(wait_start), timeout=30)
                                        if result:
                                            # 开始游戏流程
                                            GROUP_GAME_PROCESS[self.group.id]['player'].append(
                                                self.member.id)  # 将房主加入游戏玩家
                                            # 初始化游戏
                                            await self.initialize_game()
                                            # 游戏过程
                                            await self.app.sendGroupMessage(self.group, MessageChain.create([
                                                Plain(f'当前为{len(GROUP_GAME_PROCESS[self.group.id]["player"])}人\r\n'),
                                                Plain(
                                                    f'{"屠边" if len(GROUP_GAME_PROCESS[self.group.id]["player"]) == 9 else "屠城"}局')
                                            ]))
                                            await self.app.sendGroupMessage(self.group, MessageChain.create(
                                                [Plain('游戏将在5秒后开始，请在私聊消息中查看自己的身份牌')]))
                                            # 开始游戏，全群禁言
                                            await self.app.muteAll(self.group.id)
                                            for index, __player in enumerate(
                                                    GROUP_GAME_PROCESS[self.group.id]['player']):
                                                await self.app.sendFriendMessage(__player, MessageChain.create([
                                                    Plain('游戏即将开始\r\n'),
                                                    Plain(f'你的序号是: {index + 1}号\r\n'),
                                                    Plain(
                                                        f'你的身份是: {positions_info[GROUP_GAME_PROCESS[self.group.id]["position"][__player]["position"]]}'),
                                                    Plain('\r\n请准备')
                                                ]))
                                            await asyncio.sleep(5)
                                            await self.start_game()
                                            members = await self.app.getMemberList(self.group.id)
                                            group_user = {item.id: item.name for item in members}  # 群组所有人QQ号: 昵称
                                            await self.app.sendGroupMessage(self.group, MessageChain.create([
                                                Plain('身份公布\r\n'),
                                                Plain('\r\n'.join(
                                                    f'{index + 1}:\t{group_user[__player]}\t{positions_info[GROUP_GAME_PROCESS[self.group.id]["position"][__player]["position"]]}'
                                                    for index, __player in GROUP_GAME_PROCESS[self.group.id]['player']))
                                            ]))
                                            # 结束游戏，全群解除禁言
                                            await self.app.unmuteAll(self.group.id)
                                            # 将用户移除正在游戏中
                                            MEMBER_RUNING_LIST.remove(self.member.id)
                                            for __player in GROUP_GAME_PROCESS[self.group.id]['player']:
                                                MEMBER_RUNING_LIST.remove(__player)
                                            GROUP_RUNING_LIST.remove(self.group.id)
                                            del GROUP_GAME_PROCESS[self.group.id]
                                            return
                                        else:
                                            # 将用户移除正在游戏中
                                            MEMBER_RUNING_LIST.remove(self.member.id)
                                            for __player in GROUP_GAME_PROCESS[self.group.id]['player']:
                                                MEMBER_RUNING_LIST.remove(__player)
                                            GROUP_RUNING_LIST.remove(self.group.id)
                                            del GROUP_GAME_PROCESS[self.group.id]
                                            await self.app.sendGroupMessage(self.group, MessageChain.create([
                                                Plain("本次狼人杀游戏房间已解散")
                                            ]))
                                            return
                                    except asyncio.TimeoutError:
                                        async def print_player(__time):
                                            """输出当前房间内玩家"""
                                            members = await self.app.getMemberList(self.group.id)
                                            group_user = {item.id: item.name for item in members}
                                            num = len(GROUP_GAME_PROCESS[self.group.id]['player'])
                                            await self.app.sendGroupMessage(self.group, MessageChain.create([
                                                Plain(f"当前房间内有 {num + 1} / 9 人\r\n"),
                                                Plain(f"昵称: {group_user[self.member.id]}\r\n"),
                                                Plain('\r\n'.join(f'昵称: {group_user[number]}' for number in
                                                                  GROUP_GAME_PROCESS[self.group.id]['player'])),
                                                Plain(f'\r\n请在{180 - __time}秒内加入房间')
                                            ]))

                                        if count in [1, 2, 3, 4, 5]:
                                            await print_player(30 * count)
                                        elif count == 6:
                                            # 将用户移除正在游戏中
                                            MEMBER_RUNING_LIST.remove(self.member.id)
                                            for __player in GROUP_GAME_PROCESS[self.group.id]['player']:
                                                MEMBER_RUNING_LIST.remove(__player)
                                            GROUP_RUNING_LIST.remove(self.group.id)
                                            del GROUP_GAME_PROCESS[self.group.id]
                                            await self.app.sendGroupMessage(self.group, MessageChain.create([
                                                Plain('由于长时间未开始游戏，房间已自动解散')
                                            ]))
                                            return
                        else:
                            GROUP_RUNING_LIST.remove(self.group.id)
                            await self.app.sendGroupMessage(self.group, MessageChain.create([
                                Plain("已取消")
                            ]))
                    # 如果 15 秒内无响应
                    except asyncio.TimeoutError:
                        GROUP_RUNING_LIST.remove(self.group.id)
                        await self.app.sendGroupMessage(self.group, MessageChain.create([
                            Plain("确认超时")
                        ]))

                # 将用户移除正在游戏中
                MEMBER_RUNING_LIST.remove(self.member.id)
            elif isstartswith(self.msg[0], ['加入', 'join']):
                """加入狼人杀游戏房间"""
                # 检查有无狼人杀房间
                if self.group.id not in GROUP_RUNING_LIST:
                    await self.app.sendGroupMessage(self.group, MessageChain.create([
                        At(self.member.id),
                        Plain('当前暂无狼人杀房间，你可发送.wolf create创建一局狼人杀游戏')
                    ]))
                    return
                # 检查是否在房间中
                if self.member.id in GROUP_GAME_PROCESS[self.group.id]['player']:
                    await self.app.sendGroupMessage(self.group, MessageChain.create([
                        At(self.member.id),
                        Plain('你当前已在房间中，请勿重复加入！')
                    ]))
                    return
                # 判断房间人数是否已满
                if len(GROUP_GAME_PROCESS[self.group.id]['player']) >= 8:
                    await self.app.sendGroupMessage(self.group, MessageChain.create([
                        At(self.member.id),
                        Plain('当前房间人数已满，无法加入！')
                    ]))
                    return
                # 判断用户是否正在游戏中
                if await self.judge_playing():
                    return
                # 判断私信是否可用
                if await self.private_letter():
                    return
                # 加入房间
                GROUP_GAME_PROCESS[self.group.id]['player'].append(self.member.id)
                await self.app.sendGroupMessage(self.group, MessageChain.create([
                    At(self.member.id),
                    Plain('加入成功')
                ]))
            elif isstartswith(self.msg[0], ['退出', 'exit']):
                """退出狼人杀房间"""
                # 判断有无狼人杀房间
                if self.group.id not in GROUP_RUNING_LIST:
                    await self.app.sendGroupMessage(self.group, MessageChain.create([
                        At(self.member.id),
                        Plain('当前暂无狼人杀房间，你可发送.wolf create创建一局狼人杀游戏')
                    ]))
                    return
                # 检查是否在房间中
                if self.member.id not in GROUP_GAME_PROCESS[self.group.id]['player']:
                    await self.app.sendGroupMessage(self.group, MessageChain.create([
                        At(self.member.id),
                        Plain('你当前不在任何房间中！')
                    ]))
                # 退出房间
                GROUP_GAME_PROCESS[self.group.id]['player'].remove(self.member.id)
                MEMBER_RUNING_LIST.remove(self.member.id)
                await self.app.sendGroupMessage(self.group, MessageChain.create([
                    At(self.member.id),
                    Plain('退出成功')
                ]))
            elif isstartswith(self.msg[0], ['结束', 'stop']):
                if self.group.id not in GROUP_RUNING_LIST:  # 检查该群是否在游戏中
                    await self.app.sendGroupMessage(self.group, MessageChain.create([Plain('该群不在游戏中，无法使用该命令！')]))
                    return
                if self.member.permission == MemberPerm.Member and self.member.id != GROUP_GAME_PROCESS[self.group.id][
                    'owner']:
                    await self.app.sendGroupMessage(self.group, MessageChain.create([
                        Plain('你无权限操作此命令，该命令仅管理员或房间创建者可以执行')
                    ]))
                    return
                # kill 所有狼人，播报等待当前流程结束
                group_id = GROUP_GAME_PROCESS[self.group.id]
                for player in group_id['player']:
                    if group_id['position'][player]['position'] == 'wolf':
                        group_id['position'][player]['survive'] = 0
                await self.app.sendGroupMessage(self.group, MessageChain.create([Plain('已执行强制结束游戏，请等待当前流程结束')]))
            else:
                self.args_error()
                return
        except AssertionError as e:
            print(e)
            self.args_error()
        except Exception as e:
            logger.exception(e)
            self.unkown_error()

    async def start_game(self):
        days = 1  # 初始化天数
        now_speak = None  # 白天正在发言的玩家
        player_votes = {}  # 白天放逐投票
        player_votes_result = None  # 白天放逐投票结果
        survive_info = {1: '存活', 0: '死亡'}
        wolfs = []  # 狼人
        prophet = None  # 预言家
        guard = None  # 守卫
        witch = None  # 女巫
        witch_kill = None  # 女巫的击杀
        hunter = None  # 猎人
        hunter_kill = None  # 猎人的击杀
        player_number = {k + 1: v for k, v in enumerate(GROUP_GAME_PROCESS[self.group.id]['player'])}  # 玩家序号: QQ号
        members = await self.app.getMemberList(self.group.id)
        group_user = {item.id: item.name for item in members}  # 群组所有人QQ号: 昵称
        player_state = '\r\n'.join(  # 玩家存活状态
            f'{index + 1}: {group_user[player]}\t({survive_info[GROUP_GAME_PROCESS[self.group.id]["position"][player]["survive"]]})'
            for index, player in enumerate(GROUP_GAME_PROCESS[self.group.id]['player']))
        for k, v in GROUP_GAME_PROCESS[self.group.id]['position'].items():
            if v['position'] == 'wolf':
                wolfs.append(k)
            elif v['position'] == 'prophet':
                prophet = k
            elif v['position'] == 'guard':
                guard = k
            elif v['position'] == 'witch':
                witch = k
            elif v['position'] == 'hunter':
                hunter = k

        # 白天顺序发言
        @Waiter.create_using_function([FriendMessage])
        async def player_speaking(submit_answer_friend: Friend, submit_answer_message: MessageChain):
            saying = submit_answer_message.asDisplay().upper()
            saying_len = len(saying)
            if submit_answer_friend.id == now_speak:
                # 转发消息至群组
                await self.app.sendGroupMessage(self.group, MessageChain.create([
                    Plain(f'{list(player_number.values()).index(now_speak)}号{group_user[now_speak]}说:\r\n{saying}')
                ]))
                if saying == '过':
                    return

        # 白天放逐投票阶段
        @Waiter.create_using_function([FriendMessage])
        async def wait_player_vote(submit_answer_friend: Friend, submit_answer_message: MessageChain):
            group_id = GROUP_GAME_PROCESS[self.group.id]
            saying = submit_answer_message.asDisplay().upper()
            saying_len = len(saying)
            if all([submit_answer_friend.id in player_number.values(),
                    group_id['position'][submit_answer_friend.id]['survive'] == 1]):  # 在玩家列表并且存活
                try:
                    if saying == '弃票':
                        player_votes[submit_answer_friend.id] = None
                        await self.app.sendFriendMessage(submit_answer_friend.id,
                                                         MessageChain.create([Plain('你选择了弃票')]))
                    elif all([saying_len == 1, int(saying[0]) in range(1, len(group_id['player']) + 1)]):
                        if group_id['position'][player_number[int(saying[0])]]['survive'] == 0:  # 判断被投票玩家是否死亡
                            await self.app.sendFriendMessage(submit_answer_friend.id, MessageChain.create([
                                Plain('该玩家已死亡，请勿鞭尸')
                            ]))
                        else:
                            player_votes[submit_answer_friend.id] = int(saying[0])
                            await self.app.sendFriendMessage(submit_answer_friend.id, MessageChain.create([
                                Plain(f'投票成功，当前投票：{saying[0]}号')
                            ]))
                except:
                    await self.app.sendFriendMessage(submit_answer_friend.id,
                                                     MessageChain.create([Plain('请发送玩家序号进行投票，弃票请发送 ‘弃票’')]))

        # 等待狼人发言|投票
        @Waiter.create_using_function([FriendMessage])
        async def wait_wolf_vote(submit_answer_friend: Friend, submit_answer_message: MessageChain):
            group_id = GROUP_GAME_PROCESS[self.group.id]
            saying = submit_answer_message.asDisplay().upper()
            saying_len = len(saying)
            # 未死亡的狼人可发言，已死亡的狼人仍可看见
            if all([submit_answer_friend.id in wolfs, group_id['position'][submit_answer_friend.id]['survive'] == 1]):
                # 转发消息至其他狼
                for wolf in wolfs:
                    if wolf is not submit_answer_friend.id:
                        await self.app.sendFriendMessage(wolf, MessageChain.create([
                            Plain(f'{group_user[submit_answer_friend.id]}说: {saying}')
                        ]))
                # 投票
                try:
                    if all([saying[0] == '刀', saying_len == 2,
                            int(saying[1]) in range(1, len(group_id['player']) + 1)]):
                        if group_id['position'][player_number[int(saying[1])]]['survive'] == 0:
                            await self.app.sendFriendMessage(submit_answer_friend.id, MessageChain.create([
                                Plain('该玩家已死亡，请勿鞭尸')
                            ]))
                        else:
                            GROUP_GAME_PROCESS[self.group.id]['position'][submit_answer_friend.id]['ability'] = int(
                                saying[1])
                            await self.app.sendFriendMessage(submit_answer_friend.id, MessageChain.create([
                                Plain(f'你选择了{int(saying[1])}号')
                            ]))
                except:
                    pass

        # 等待预言家查验
        @Waiter.create_using_function([FriendMessage])
        async def wait_prophet_vote(submit_answer_friend: Friend, submit_answer_message: MessageChain):
            group_id = GROUP_GAME_PROCESS[self.group.id]
            saying = submit_answer_message.asDisplay().upper()
            saying_len = len(saying)
            if all([submit_answer_friend.id == prophet, group_id['position'][prophet]['survive'] == 1]):
                try:
                    if all([saying[0] == '查', saying_len == 2, int(saying[1]) in range(1, len(group_id['player']) + 1),
                            player_number[int(saying[1])] != prophet]):
                        if group_id['position'][player_number[int(saying[1])]]['survive'] == 0:
                            await self.app.sendFriendMessage(prophet, MessageChain.create([Plain('该玩家已死亡，你无法查验')]))
                        elif int(saying[1]) in group_id['position'][submit_answer_friend.id]['ability']:
                            await self.app.sendFriendMessage(prophet, MessageChain.create([
                                Plain('该玩家你已查验，请选择其他玩家')
                            ]))
                        else:
                            position = '好人' if group_id['position'][player_number[int(saying[1])]][
                                                   'position'] != 'wolf' else '狼人'
                            await self.app.sendFriendMessage(prophet, MessageChain.create([
                                Plain(f'你选择了查验{saying[1]}号，他的身份是:{position}')
                            ]))
                            group_id['position'][submit_answer_friend.id]['ability'].append(
                                int(saying[1]))  # 将该玩家加入已查验名单
                            return
                    else:
                        await self.app.sendFriendMessage(prophet, MessageChain.create([
                            Plain('请发送 ‘查x’ 查验对应玩家，你不能查验自己')
                        ]))
                except:
                    await self.app.sendFriendMessage(prophet, MessageChain.create([
                        Plain('请发送 ‘查x’ 查验对应玩家，你不能查验自己')
                    ]))

        # 等待守卫选择
        @Waiter.create_using_function([FriendMessage])
        async def wait_guard_vote(submit_answer_friend: Friend, submit_answer_message: MessageChain):
            group_id = GROUP_GAME_PROCESS[self.group.id]
            saying = submit_answer_message.asDisplay().upper()
            saying_len = len(saying)
            if all([submit_answer_friend.id == guard, group_id['position'][guard]['survive'] == 1]):
                if saying[0] == '守' and saying_len == 2 and int(saying[1]) in range(1, len(group_id['player']) + 1) and \
                        group_id['position'][guard]['ability'] != int(saying[1]):
                    # if all([saying[0] == '守', saying_len == 2, int(saying[1]) in range(1, 10),
                    #         group_id['position'][guard]['ability'] != int(saying[1])]):
                    if group_id['position'][player_number[int(saying[1])]]['survive'] == 0:  # 验证玩家是否死亡
                        await self.app.sendFriendMessage(guard, MessageChain.create([Plain('该玩家已死亡，你无法守卫')]))
                    else:
                        await self.app.sendFriendMessage(guard, MessageChain.create([
                            Plain(f'你选择了守卫{saying[1]}号')
                        ]))
                        group_id['position'][guard]['ability'] = int(saying[1])
                        return int(saying[1])
                else:
                    await self.app.sendFriendMessage(guard, MessageChain.create([
                        Plain('请发送 ‘守x’ 守卫对应玩家，你不能连续俩晚守卫同一个人')
                    ]))

        # 等待女巫选择
        @Waiter.create_using_function([FriendMessage])
        async def wait_witch_vote(submit_answer_friend: Friend, submit_answer_message: MessageChain):
            group_id = GROUP_GAME_PROCESS[self.group.id]
            saying = submit_answer_message.asDisplay().upper()
            if all([submit_answer_friend.id == witch, group_id['position'][witch]['survive'] == 1]):
                if saying == '是':
                    return True
                elif saying == '否':
                    return False
                else:
                    await self.app.sendFriendMessage(witch, MessageChain.create([
                        Plain('请发送是或否来进行确认')
                    ]))

        # 等待女巫选择毒药使用玩家
        @Waiter.create_using_function([FriendMessage])
        async def wait_witch_poison(submit_answer_friend: Friend, submit_answer_message: MessageChain):
            group_id = GROUP_GAME_PROCESS[self.group.id]
            saying = submit_answer_message.asDisplay().upper()
            saying_len = len(saying)
            if submit_answer_friend.id == witch:
                try:
                    if all([saying[0] == '毒', saying_len == 2,
                            int(saying[1]) in range(1, len(group_id['player']) + 1)]):
                        if group_id['position'][player_number[int(saying[1])]]['survive'] == 0:  # 若对应玩家死亡
                            await self.app.sendFriendMessage(witch, MessageChain.create([Plain('该玩家已死亡，请勿鞭尸')]))
                        else:
                            await self.app.sendFriendMessage(witch, MessageChain.create([
                                Plain(f'你选择了毒{saying[1]}号')
                            ]))
                            return int(saying[1])
                    else:
                        await self.app.sendFriendMessage(witch, MessageChain.create([
                            Plain('请发送 ‘毒x’ 对对应玩家使用毒药')
                        ]))
                except:
                    await self.app.sendFriendMessage(witch, MessageChain.create([
                        Plain('请发送 ‘毒x’ 对对应玩家使用毒药')
                    ]))

        # 等待猎人选择
        @Waiter.create_using_function([FriendMessage])
        async def wait_hunter_vote(submit_answer_friend: Friend, submit_answer_message: MessageChain):
            saying = submit_answer_message.asDisplay().upper()
            if submit_answer_friend.id == hunter:
                if saying == '是':
                    return True
                elif saying == '否':
                    return False
                else:
                    await self.app.sendFriendMessage(hunter, MessageChain.create([
                        Plain('请发送是或否来进行确认')
                    ]))

        # 等待猎人开枪
        @Waiter.create_using_function([FriendMessage])
        async def wait_hunter_poison(submit_answer_friend: Friend, submit_answer_message: MessageChain):
            group_id = GROUP_GAME_PROCESS[self.group.id]
            saying = submit_answer_message.asDisplay().upper()
            saying_len = len(saying)
            if submit_answer_friend.id == hunter:
                try:
                    if all([saying[0] == '杀', saying_len == 2,
                            int(saying[1]) in range(1, len(group_id['player']) + 1)]):
                        if group_id['position'][player_number[int(saying[1])]]['survive'] == 0:  # 若对应玩家死亡
                            await self.app.sendFriendMessage(hunter, MessageChain.create([Plain('该玩家已死亡，请勿鞭尸')]))
                        else:
                            await self.app.sendFriendMessage(hunter, MessageChain.create([
                                Plain(f'你选择了猎杀{saying[1]}号')
                            ]))
                            return int(saying[1])
                    else:
                        await self.app.sendFriendMessage(hunter, MessageChain.create([
                            Plain('请发送 ‘杀x’ 猎杀对应玩家')
                        ]))
                except:
                    await self.app.sendFriendMessage(hunter, MessageChain.create([
                        Plain('请发送 ‘杀x’ 猎杀对应玩家')
                    ]))

        async def voting_machines(votes):
            """投票器"""
            votes = [v for v in votes if v is not None]  # 将空值删除
            votes = Counter(votes)
            votes = {k: v for k, v in sorted(votes.items(), key=lambda x: x[1], reverse=True)}
            votes_len = len(votes.keys())
            if votes_len == 0:
                return False
            else:
                return [k for k, v in votes.items() if v == list(votes.values())[0]]

        async def wolf_behavior():
            """狼人行为"""
            for wolf in wolfs:
                GROUP_GAME_PROCESS[self.group.id]['position'][wolf]['ability'] = None  # 清楚狼人的选择
                await self.app.sendFriendMessage(wolf, MessageChain.create([
                    Plain('你的队友是:\r\n'),
                    Plain('\r\n'.join(f'{group_user[w]}' for w in wolfs))
                ]))
                await self.app.sendFriendMessage(wolf, MessageChain.create([
                    Plain('请在60秒内投票决定今晚要刀的玩家\r\n'),
                    Plain(player_state),
                    Plain('\r\n发送 ‘刀x’ 可投票，你们现在可以进行交流')
                ]))
            for i in range(60):
                try:
                    await asyncio.wait_for(self.inc.wait(wait_wolf_vote), timeout=1)
                except asyncio.TimeoutError:
                    if i in [30, 45, 55]:
                        for wolf in wolfs:
                            await self.app.sendFriendMessage(wolf, MessageChain.create([
                                Plain(f'还有{60 - i}秒发言投票时间')
                            ]))
            # 最终投票计算
            wolf_votes = [GROUP_GAME_PROCESS[self.group.id]['position'][wolf]['ability'] for wolf in wolfs]
            result = await voting_machines(wolf_votes)
            if result and len(result) == 1:
                for wolf in wolfs:
                    await self.app.sendFriendMessage(wolf, MessageChain.create([Plain(f'今晚你们选择了刀{result[0]}号玩家')]))
                return result[0]
            else:
                for wolf in wolfs:
                    await self.app.sendFriendMessage(wolf, MessageChain.create([Plain('今晚你们没有行动')]))
                return None

        async def prophet_behavior():
            """预言家行为"""
            if GROUP_GAME_PROCESS[self.group.id]['position'][prophet]['survive'] == 0:
                await self.app.sendFriendMessage(prophet, MessageChain.create([Plain('你已经死亡，无法查验玩家')]))
                await asyncio.sleep(30)
                return None
            await self.app.sendFriendMessage(prophet, MessageChain.create([
                Plain('请在30秒内选择你要查验的玩家'),
                Plain(player_state),
                Plain('\r\n发送 ‘查x’ 查验对应玩家')
            ]))
            try:
                await asyncio.wait_for(self.inc.wait(wait_prophet_vote), timeout=30)
            except asyncio.TimeoutError:
                await self.app.sendFriendMessage(prophet, MessageChain.create([Plain('选择结束')]))

        async def guard_behavior():
            """守卫行为"""
            if GROUP_GAME_PROCESS[self.group.id]['position'][guard]['survive'] == 0:
                await self.app.sendFriendMessage(guard, MessageChain.create([Plain('你已经死亡，无法守卫玩家')]))
                await asyncio.sleep(30)
                return None
            await self.app.sendFriendMessage(guard, MessageChain.create([
                Plain('请在30秒内选择你要守卫的玩家'),
                Plain(player_state),
                Plain('\r\n发送 ‘守x’ 守卫对应玩家')
            ]))
            try:
                result1 = await asyncio.wait_for(self.inc.wait(wait_guard_vote), timeout=30)
                if result1:
                    return result1
                else:
                    return None
            except asyncio.TimeoutError:
                await self.app.sendFriendMessage(guard, MessageChain.create([Plain('选择结束')]))
            return None

        async def witch_behavior(will_kills):
            """女巫行为"""
            res = [False, False]
            if GROUP_GAME_PROCESS[self.group.id]['position'][witch]['survive'] == 0:
                await self.app.sendFriendMessage(witch, MessageChain.create([Plain('你已经死亡，无法进行操作')]))
                await asyncio.sleep(30)
                return res
            if 'antidote' in GROUP_GAME_PROCESS[self.group.id]['position'][witch]['ability']:  # 若女巫有解药
                await self.app.sendFriendMessage(witch, MessageChain.create([
                    Plain(
                        f'昨晚{will_kills[0]}号{group_user[player_number[will_kills[0]]]}玩家死亡，要使用解药吗？\r\n回答 ‘是’ ‘否’' if
                        will_kills[0] else '昨晚没有玩家死亡')
                ]))
                if will_kills[0]:
                    try:
                        if await asyncio.wait_for(self.inc.wait(wait_witch_vote), timeout=30):
                            GROUP_GAME_PROCESS[self.group.id]['position'][witch]['ability'].remove('antidote')
                            res[0] = True
                            return res
                    except asyncio.TimeoutError:
                        await self.app.sendFriendMessage(witch, MessageChain.create([Plain('选择结束')]))
            else:
                await asyncio.sleep(1)
                await self.app.sendFriendMessage(witch, MessageChain.create([Plain('你没有解药了')]))
            await self.app.sendFriendMessage(witch, MessageChain.create([
                Plain('要使用毒药吗？\r\n'),
                Plain('回答 ‘是’ ‘否’')
            ]))
            if 'poison' in GROUP_GAME_PROCESS[self.group.id]['position'][witch]['ability']:  # 检查有无毒药
                try:
                    if await asyncio.wait_for(self.inc.wait(wait_witch_vote), timeout=30):  # 选择是否使用毒药
                        await self.app.sendFriendMessage(witch, MessageChain.create([
                            Plain('选择要使用的玩家\r\n'),
                            Plain(player_state),
                            Plain('\r\n请发送 ‘毒x’ 对对应玩家使用毒药')
                        ]))
                        result = await asyncio.wait_for(self.inc.wait(wait_witch_poison), timeout=30)  # 选择使用玩家
                        if result:
                            GROUP_GAME_PROCESS[self.group.id]['position'][witch]['ability'].remove('poison')  # 移除毒药
                            res[1] = result
                            return res
                except asyncio.TimeoutError:
                    await self.app.sendFriendMessage(witch, MessageChain.create([Plain('选择结束')]))
            else:
                await asyncio.sleep(1)
                await self.app.sendFriendMessage(witch, MessageChain.create([Plain('你没有毒药了')]))
            return res

        async def hunter_behavior():
            """猎人行为"""
            await self.app.sendFriendMessage(hunter, MessageChain.create([Plain('你已死亡，是否发动技能？\r\n回答 ‘是’ ‘否’')]))
            try:
                if await asyncio.wait_for(self.inc.wait(wait_hunter_vote), timeout=30):  # 是否发动技能
                    await self.app.sendGroupMessage(self.group, MessageChain.create([Plain('等待猎人发动技能')]))  # 确认发动技能后公布消息
                    await self.app.sendFriendMessage(hunter, MessageChain.create([
                        Plain('请选择要猎杀的对象\r\n'),
                        Plain(player_state),
                        Plain('\r\n请发送 ‘杀x’ 猎杀对应玩家')
                    ]))
                    result = await asyncio.wait_for(self.inc.wait(wait_hunter_poison), timeout=30)  # 选择猎杀玩家
                    if result:
                        GROUP_GAME_PROCESS[self.group.id]['position'][hunter]['ability'] = player_number[result]
                        return result
                    else:
                        return None
            except asyncio.TimeoutError:
                await self.app.sendFriendMessage(hunter, MessageChain.create([Plain('选择结束')]))
            return None

        async def game_over() -> bool:
            """游戏结束验证流程"""
            # 判断双方存活状态
            player_number = {k + 1: v for k, v in enumerate(GROUP_GAME_PROCESS[self.group.id]['player'])}  # 重置玩家序号
            wolf_player = [player for player in player_number.values() if
                           GROUP_GAME_PROCESS[self.group.id]['position'][player]['survive'] == 1 and
                           GROUP_GAME_PROCESS[self.group.id]['position'][player]['position'] == 'wolf']
            if len(player_number) in [6, 7, 8]:  # 屠城局
                people = [player for player in player_number.values() if
                          GROUP_GAME_PROCESS[self.group.id]['position'][player]['survive'] == 1 and
                          GROUP_GAME_PROCESS[self.group.id]['position'][player]['position'] in ['vil', 'prophet',
                                                                                                'guard', 'witch']]
                if (not wolf_player and not people) or not people:  # 若没有好人或双方都死亡
                    await self.app.sendGroupMessage(self.group, MessageChain.create([Plain('游戏结束，狼人胜利')]))
                    return True
                if not wolf_player:
                    await self.app.sendGroupMessage(self.group, MessageChain.create([Plain('游戏结束，好人胜利')]))
                    return True
            else:  # 屠边局
                priest = [player for player in player_number.values() if
                          GROUP_GAME_PROCESS[self.group.id]['position'][player]['survive'] == 1 and
                          GROUP_GAME_PROCESS[self.group.id]['position'][player]['position'] in ['prophet', 'hunter',
                                                                                                'witch']]
                vils = [player for player in player_number.values() if
                        GROUP_GAME_PROCESS[self.group.id]['position'][player]['survive'] == 1 and
                        GROUP_GAME_PROCESS[self.group.id]['position'][player]['position'] == 'vil']
                if (not wolf_player and not priest or vils) or not priest or not vils:
                    await self.app.sendGroupMessage(self.group, MessageChain.create([Plain('游戏结束，狼人胜利')]))
                    return True
                if not wolf_player:
                    await self.app.sendGroupMessage(self.group, MessageChain.create([Plain('游戏结束，好人胜利')]))
                    return True
            return False

        while True:
            await self.app.sendGroupMessage(self.group, MessageChain.create([
                Plain('玩家信息\r\n'),
                Plain(player_state)
            ]))
            await asyncio.sleep(5)
            first_speak_player = 1  # 初始化白天首位发言玩家序号
            await self.app.sendGroupMessage(self.group, MessageChain.create([Plain('天黑请闭眼，狼人请睁眼')]))
            await self.app.sendGroupMessage(self.group, MessageChain.create([Plain('请选择今晚你们要刀的对象')]))
            will_kill = [await wolf_behavior() or None]  # 狼人将要刀的玩家，为空则为空刀，询问女巫 or 守卫
            await self.app.sendGroupMessage(self.group, MessageChain.create([Plain('等待预言家操作')]))
            await prophet_behavior()  # 预言家查验
            if len(player_number) in [6, 7]:
                await self.app.sendGroupMessage(self.group, MessageChain.create([Plain('等待守卫操作')]))
                guard_player = await guard_behavior()  # 守卫选择的玩家
                if not guard_player:
                    GROUP_GAME_PROCESS[self.group.id]['position'][guard]['ability'] = None  # 守卫没有选择，将守卫玩家清除
                if will_kill[0] == guard_player:
                    will_kill[0] = None
            else:
                await self.app.sendGroupMessage(self.group, MessageChain.create([Plain('等待女巫操作')]))
                result = await witch_behavior(will_kill)
                if result[0]:
                    will_kill[0] = None
                if result[1]:
                    witch_kill = result[1]
                    will_kill.append(result[1])
                if will_kill[0] and player_number[int(will_kill[0])] == hunter and (
                        not witch_kill or player_number[int(witch_kill)] != hunter):  # 猎人不是女巫毒的
                    hunter_kill = await hunter_behavior()  # 等待猎人选择
                    will_kill.append(hunter_kill or None)
            kill = [int(i) for i in will_kill if i is not None]  # 序号
            if kill:
                for __kill in kill:
                    GROUP_GAME_PROCESS[self.group.id]['position'][player_number[__kill]]['survive'] = 0  # 记录夜晚死亡的玩家
                first_speak_player = sorted(kill, reverse=True)[0] + 1
                await self.app.sendGroupMessage(self.group, MessageChain.create([
                    Plain(f'（第{days}天）天亮了，昨晚'),
                    Plain(', '.join(f'{k}号: {group_user[player_number[k]]}' for k in kill)),
                    Plain(f'死亡')
                ]))
                player_state = '\r\n'.join(  # 重新生成玩家存活状态
                    f'{index + 1}: {group_user[player]}\t({survive_info[GROUP_GAME_PROCESS[self.group.id]["position"][player]["survive"]]})'
                    for index, player in enumerate(GROUP_GAME_PROCESS[self.group.id]['player']))
                if days == 1:
                    for __kill in kill:
                        now_speak = player_number[__kill]
                        await self.app.sendGroupMessage(self.group, MessageChain.create([
                            At(now_speak),
                            Plain(f'请{__kill}号{group_user[now_speak]}发表遗言')
                        ]))
                        await self.app.sendFriendMessage(now_speak, MessageChain.create([
                            Plain('玩家信息\r\n'),
                            Plain(player_state),
                            Plain('\r\n请发表遗言')
                        ]))
                        try:
                            await asyncio.wait_for(self.inc.wait(player_speaking), timeout=60)
                        except asyncio.TimeoutError:
                            await self.app.sendFriendMessage(now_speak, MessageChain.create([Plain('发言结束')]))
                elif hunter_kill and hunter_kill != witch_kill:  # 若猎人开枪并且对象不是女巫击杀的对象
                    now_speak = player_number[int(hunter_kill)]
                    await self.app.sendGroupMessage(self.group, MessageChain.create([
                        At(now_speak),
                        Plain(f'请{hunter_kill}号{group_user[now_speak]}发表遗言')
                    ]))
                    await self.app.sendFriendMessage(now_speak, MessageChain.create([
                        Plain('玩家信息\r\n'),
                        Plain(player_state),
                        Plain('\r\n请发表遗言')
                    ]))
                    try:
                        await asyncio.wait_for(self.inc.wait(player_speaking), timeout=60)
                    except asyncio.TimeoutError:
                        await self.app.sendFriendMessage(now_speak, MessageChain.create([Plain('发言结束')]))
                if game_over():  # 检查游戏是否结束
                    return
            else:
                await self.app.sendGroupMessage(self.group, MessageChain.create([
                    Plain(f'（第{days}天）天亮了，昨晚是平安夜')
                ]))
            # 生成发言顺序表(将死亡玩家排除)
            speak_player = [i for i in range(first_speak_player, len(player_number) + 1) if
                            GROUP_GAME_PROCESS[self.group.id]['position'][player_number[i]]['survive'] == 1]
            __speak_player = [i for i in range(1, first_speak_player - 1) if
                              GROUP_GAME_PROCESS[self.group.id]['position'][player_number[i]]['survive'] == 1]
            speak_player += __speak_player  # 序号
            for speak in speak_player:
                now_speak = player_number[speak]  # 序号转换玩家QQ
                if GROUP_GAME_PROCESS[self.group.id]['position'][now_speak]['survive'] == 0:
                    # 该玩家已死亡跳过发言
                    continue
                await self.app.sendGroupMessage(self.group, MessageChain.create([
                    At(now_speak),
                    Plain(f'下面由{speak}号: {group_user[now_speak]}发言\r\n请私聊我进行发言，时间:60秒')
                ]))
                await self.app.sendFriendMessage(now_speak, MessageChain.create([
                    Plain('玩家信息\r\n'),
                    Plain(player_state),
                    Plain('\r\n请发言讨论')
                ]))
                try:
                    await asyncio.wait_for(self.inc.wait(player_speaking), timeout=60)
                except asyncio.TimeoutError:
                    await self.app.sendFriendMessage(now_speak, MessageChain.create([Plain('发言结束')]))
            player_state = '\r\n'.join(  # 重新生成玩家存活状态
                f'{index + 1}: {group_user[player]}\t({survive_info[GROUP_GAME_PROCESS[self.group.id]["position"][player]["survive"]]})'
                for index, player in enumerate(GROUP_GAME_PROCESS[self.group.id]['player']))
            await self.app.sendGroupMessage(self.group, MessageChain.create([
                Plain('进入投票阶段\r\n'),
                Plain(player_state),
                Plain('\r\n请在30秒内投票'),
                Plain('\r\n私聊我发送序号即可投票，弃票请发送 ‘弃票’。可重复进行投票选择')
            ]))
            try:
                player_votes.clear()  # 清空玩家投票信息
                player_votes_result = None  # 清空放逐玩家结果
                await asyncio.wait_for(self.inc.wait(wait_player_vote), timeout=30)  # 已处理死亡玩家不发言
            except asyncio.TimeoutError:
                # 投票完成，统计投票
                player_votes_result = await voting_machines(player_votes.values())  # 序号
                if player_votes_result:
                    await self.app.sendGroupMessage(self.group, MessageChain.create([
                        Plain('投票结果\r\n'),
                        Plain('\r\n'.join(
                            f'{group_user[__vote_user]}  →  {__vote}' for __vote_user, __vote in player_votes.items())),
                        Plain('\r\n未显示玩家即为弃票或已死亡')
                    ]))
                    if len(player_votes_result) == 1:
                        await self.app.sendGroupMessage(self.group, MessageChain.create([
                            Plain(f'{player_votes_result[0]}: {group_user[player_number[player_votes_result[0]]]}被放逐了')
                        ]))
                        GROUP_GAME_PROCESS[self.group.id]['position'][player_number[player_votes_result[0]]][
                            'survive'] = 0  # 记录玩家死亡
                    else:
                        await self.app.sendGroupMessage(self.group, MessageChain.create([
                            Plain('\r\n'.join(
                                f'{player_votes_result[i]}: {group_user[player_number[player_votes_result[i]]]}' for i
                                in range(len(player_votes_result)))),
                            Plain('\r\n上述玩家票数一致，将进行一次辩论')
                        ]))
                        for speak in player_votes_result:
                            now_speak = player_number[speak]
                            await self.app.sendGroupMessage(self.group, MessageChain.create([
                                At(now_speak),
                                Plain(f'下面由{speak}号: {group_user[now_speak]}发言\r\n请私聊我进行发言，时间:60秒')
                            ]))
                            await self.app.sendFriendMessage(now_speak, MessageChain.create([
                                Plain('玩家信息\r\n'),
                                Plain(player_state),
                                Plain('\r\n请发言讨论')
                            ]))
                            try:
                                await asyncio.wait_for(self.inc.wait(player_speaking), timeout=60)
                            except asyncio.TimeoutError:
                                await self.app.sendFriendMessage(now_speak, MessageChain.create([Plain('发言结束')]))
                        await self.app.sendGroupMessage(self.group, MessageChain.create([
                            Plain('进入投票阶段，请针对辩论玩家进行投票\r\n'),
                            Plain('\r\n'.join(f'{i}: {group_user[player_number[i]]}' for i in player_votes_result)),
                            Plain('\r\n请在30秒内投票'),
                            Plain('\r\n私聊我发送序号即可投票，弃票请发送 ‘弃票’。可重复进行投票选择')
                        ]))
                        player_number = {k: v for k, v in player_number.items() if
                                         k not in player_votes_result}  # 辩论玩家不能投票
                        try:
                            player_votes.clear()  # 清空玩家投票信息
                            player_votes_result = None  # 清空放逐玩家结果
                            await asyncio.wait_for(self.inc.wait(wait_player_vote), timeout=30)
                        except asyncio.TimeoutError:
                            # 投票完成，统计投票
                            player_votes_result = await voting_machines(player_votes.values())  # 序号
                            if player_votes_result:
                                await self.app.sendGroupMessage(self.group, MessageChain.create([
                                    Plain('投票结果(辩论玩家不参与投票)\r\n'),
                                    Plain('\r\n'.join(
                                        f'{group_user[__vote_user]}  →  {__vote}' for __vote_user, __vote in
                                        player_votes.items())),
                                    Plain('\r\n未显示玩家即为弃票或已死亡')
                                ]))
                                if len(player_votes_result) == 1:
                                    await self.app.sendGroupMessage(self.group, MessageChain.create([
                                        Plain(
                                            f'{player_votes_result[0]}: {group_user[player_number[player_votes_result[0]]]}被放逐了')
                                    ]))
                                    GROUP_GAME_PROCESS[self.group.id]['position'][
                                        player_number[player_votes_result[0]]][
                                        'survive'] = 0  # 记录玩家死亡
                                else:
                                    await self.app.sendGroupMessage(self.group, MessageChain.create([
                                        Plain('没有玩家被放逐')
                                    ]))
                            else:
                                await self.app.sendGroupMessage(self.group, MessageChain.create([
                                    Plain('所有玩家都弃票了，没有玩家被放逐')
                                ]))
                else:
                    await self.app.sendGroupMessage(self.group, MessageChain.create([
                        Plain('所有玩家都弃票了，没有玩家被放逐')
                    ]))
                if all([player_votes_result, len(player_votes_result) == 1,
                        player_votes_result[0] == hunter]):  # 若猎人被放逐
                    hunter_kill = await hunter_behavior()  # 等待猎人选择
                    if hunter_kill:
                        GROUP_GAME_PROCESS[self.group.id]['position'][player_number[int(hunter_kill)]][
                            'survive'] = 0  # 记录死亡的玩家
                        now_speak = player_number[int(hunter_kill)]
                        await self.app.sendGroupMessage(self.group, MessageChain.create([
                            At(now_speak),
                            Plain(f'请{group_user[now_speak]}发表遗言')
                        ]))
                        await self.app.sendFriendMessage(now_speak, MessageChain.create([
                            Plain('玩家信息\r\n'),
                            Plain(player_state),
                            Plain('\r\n请发表遗言')
                        ]))
                        try:
                            await asyncio.wait_for(self.inc.wait(player_speaking), timeout=60)
                        except asyncio.TimeoutError:
                            await self.app.sendFriendMessage(now_speak, MessageChain.create([Plain('发言结束')]))
            await asyncio.sleep(2)
            # 判断双方存活状态
            if game_over():
                return
            days += 1  # 天数+1
            hunter_kill = None  # 重置猎人击杀信息
            witch_kill = None  # 重置女巫击杀信息
            player_number = {k + 1: v for k, v in enumerate(GROUP_GAME_PROCESS[self.group.id]['player'])}  # 重置玩家序号
            player_state = '\r\n'.join(  # 更新玩家存活状态
                f'{index + 1}: {group_user[player]}\t({survive_info[GROUP_GAME_PROCESS[self.group.id]["position"][player]["survive"]]})'
                for index, player in enumerate(GROUP_GAME_PROCESS[self.group.id]['player']))
