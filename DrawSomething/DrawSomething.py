import asyncio
import secrets
import time

from arclet.alconna import Alconna, Subcommand, Arpamar
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.exception import UnknownTarget
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Source, Plain, At
from graia.ariadne.model import Group, Member
from graia.broadcast.interrupt.waiter import Waiter
from loguru import logger

from app.core.commander import CommandDelegateManager
from app.core.config import Config
from app.core.settings import *
from app.entities.game import BotGame
from app.plugin.base import Plugin

WORD = {
    "word": [
        "安全帽",
        "台灯",
        "苍蝇",
        "飞机",
        "铃铛",
        "手机",
        "龟",
        "镰刀",
        "包子",
        "张三",
        "钙质化",
        "股市",
        "粉笔擦",
        "蝌蚪",
        "哪吒",
        "牛头人",
        "清华大学",
        "热狗",
        "鹰角",
        "叔叔",
        "猛男",
        "合成玉",
        "丝瓜",
        "水管",
        "扑克牌",
        "华为",
        "鸭子",
        "乌鸦",
        "兔子",
        "洗衣机",
        "足球",
        "安卓",
        "苹果",
        "电脑",
        "手表",
        "鼠标",
        "内裤",
        "A",
        "AK47",
        "农夫山泉",
        "鸡腿",
        "火山",
        "美国",
        "日本",
        "黑板",
        "老虎",
        "猫",
        "空调",
        "刻晴",
        "猴子",
        "蝴蝶",
        "鱿鱼",
        "耳机",
        "键盘",
        "瓶盖",
        "玻璃",
        "牛奶",
        "水桶",
        "毛巾",
        "肥皂",
        "灯泡",
        "羽毛",
        "避孕套",
        "可乐",
        "刺猬",
        "粉笔",
        "铅笔",
        "充电器",
        "樱桃",
        "眼睛",
        "眼镜",
        "石头",
        "黄昏",
        "艾雅法拉",
        "落井下石",
        "腾讯",
        "送分题",
        "火腿",
        "鸡翅",
        "路灯",
        "路由器",
        "输入法",
        "台风",
        "电风扇",
        "荷叶",
        "海猫",
        "寻仇者",
        "垃圾",
        "水井",
        "音响",
        "电视机",
        "菊花",
        "喇叭",
        "猪八戒",
        "孙悟空",
        "僵尸",
        "首都",
        "粉丝",
        "口香糖",
        "汽车",
        "卡车",
        "摩托车",
        "自行车",
        "白骨精",
        "中国银行",
        "人民币",
        "支付宝",
        "Madoka",
        "管理员",
        "电池",
        "西瓜",
        "奖券",
        "唱片",
        "水龙头",
        "火车",
        "轮胎",
        "红绿灯",
        "斑马线",
        "复读机",
        "汤圆",
        "月亮",
        "太阳",
        "大象",
        "水泥",
        "鲨鱼",
        "海绵宝宝",
        "派大星",
        "章鱼哥",
        "核桃",
        "大脑",
        "绯红之王",
        "拖鞋",
        "砖头",
        "医院",
        "公交车",
        "马路",
        "头发",
        "小米",
        "黄焖鸡",
        "热干面",
        "同性恋",
        "烤鸭",
        "篮球",
        "发动机",
        "奥运会",
        "垃圾桶",
        "源氏",
        "半藏",
        "泥岩",
        "面包",
        "萝莉",
        "蝴蝶结",
        "爱情",
        "飞机杯",
        "派蒙",
        "丘丘人",
        "乒乓球",
        "空白",
        "你画我猜",
        "字典",
        "栅栏",
        "云",
        "屎",
        "望远镜",
        "章鱼",
        "对牛弹琴",
        "喜羊羊",
        "奥特曼",
        "镜子",
        "洛天依",
        "王",
        "网络",
        "萝卜",
        "南瓜",
        "火箭",
        "陀螺",
        "屎壳郎",
        "Steam",
        "吴京",
        "秒表",
        "圣遗物",
        "理智",
        "高压电",
        "冰箱",
        "海豚",
        "冰淇淋",
        "猫娘",
        "童话",
        "金字塔",
        "食人花",
        "沙漠",
        "手榴弹",
        "口罩",
        "菠萝派",
        "史莱姆",
        "狗屎",
        "大腿",
        "丝袜",
        "大海",
        "斯卡蒂",
        "塔露拉",
        "卫生纸",
        "五年中考",
        "阿米娅",
        "芙兰朵露",
        "相机",
        "天堂",
        "玉米",
        "水",
        "睡觉",
        "暗杀",
        "钢铁侠",
        "气球",
        "南极",
        "汉堡包",
        "火鸡",
        "色图",
        "望梅止渴",
        "声东击西",
        "披风",
        "魔芋",
        "立交桥",
        "熊掌",
        "指南针",
        "回形针",
        "图钉",
        "时间",
        "帕拉斯",
        "芒果",
        "无人机",
        "击剑",
        "氢气",
        "煤炭",
        "抽象",
        "火焰",
        "太空站",
        "提莫",
        "狗妈",
        "书包",
        "危机合约",
        "浮士德",
        "脚",
        "电锯",
        "斧头",
        "旗帜",
        "黄金",
        "树",
        "大拇指",
        "恋童癖",
        "异客",
        "李白",
        "洞庭湖",
        "弹簧",
        "螺丝",
        "螺母",
        "俄罗斯",
        "椰子",
        "火龙果",
        "轨道",
        "地图",
        "箭",
        "弓",
        "法老王",
        "门",
        "桌子",
        "脑啡肽",
        "卡费",
        "咖啡",
        "老婆",
        "粉",
        "光",
        "跑",
        "跳",
        "冰壶",
        "烧烤",
        "柠檬",
        "棒棒糖",
        "碎冰冰",
        "菠萝",
        "二次元",
        "哆啦A梦",
        "沥青",
        "和尚",
        "寺庙",
        "成功人士",
        "马化腾",
        "数学题",
        "科学",
        "原子",
        "吉他",
        "钢琴",
        "城墙",
        "城门",
        "鼓",
        "法西斯",
        "充电宝",
        "尖嘴钳",
        "优酸乳",
        "厨房",
        "狼牙棒",
        "烈焰人",
        "苦力怕",
        "蜘蛛",
        "老鼠",
        "羊",
        "史蒂夫",
        "木头",
        "狼",
        "海带",
        "伞兵",
        "核弹",
        "意识",
        "C4",
        "毒气",
        "摸鱼",
        "磁铁",
        "鬼",
        "屁股",
        "信",
        "马桶",
        "水壶",
        "奖杯",
        "脸",
        "罗翔",
        "台湾",
        "照片",
        "自己",
        "关羽",
        "二氧化碳",
        "灭火器",
        "地铁",
        "齿轮",
        "扳手",
        "麦克风",
        "WIFI",
        "雨",
        "星星",
        "白羊座",
        "金牛座",
        "狮子座",
        "真银斩",
        "限定寻访",
        "任天堂",
        "锤子",
        "风",
        "PPT",
        "力量",
        "打电话",
        "肚子",
        "雪人",
        "雪花",
        "武松打虎",
        "红包",
        "周杰伦",
        "巫师",
        "武士",
        "武士刀",
        "跆拳道",
        "爱国者",
        "王羲之",
        "成龙",
        "霜星",
        "硬币",
        "爷爷",
        "花生",
        "龙门币",
        "火车票",
        "银行卡",
        "身份证",
        "法术",
        "羽毛球",
        "穷",
        "祈祷",
        "菩萨",
        "光头",
        "佛祖",
        "药丸",
        "天使",
        "左轮",
        "子弹",
        "潜艇",
        "小麦",
        "圣域",
        "鸟笼",
        "弑君者",
        "击飞",
        "成吉思汗",
        "源石",
        "明日方舟",
        "歪比巴卜",
        "盒子",
        "福瑞",
        "城堡",
        "盾牌",
        "嘴巴",
        "方块",
        "投资",
        "骰子",
        "邮票",
        "坟墓",
        "令牌",
        "牛排",
        "电话卡",
        "健康码",
        "肯德基",
        "草",
        "卢本伟",
        "斗地主",
        "嘉然",
        "钱包",
        "医疗兵",
        "监狱",
        "军队",
        "细菌",
        "京东",
        "收音机",
        "一块钱",
        "体温计",
        "VCD",
        "发电机",
        "非酋",
        "欧皇",
        "风神瞳",
        "厕所",
        "魔法",
        "快递",
        "血压",
        "伊芙利特",
        "水月",
        "囚犯",
        "法国",
        "洒水车",
        "网易云",
        "米哈游",
        "广告",
        "西游记",
        "萨卡兹",
        "奶嘴",
        "钢管舞",
        "拐棍",
        "威龙",
        "伊桑",
        "触手",
        "爬",
        "枪",
        "杀虫剂",
        "三叉戟",
        "明信片",
        "碗",
        "圣诞节",
        "盾构机",
        "悬崖",
        "烟雾弹",
        "微博",
        "网吧",
        "唯",
        "植树",
        "分支",
        "日历",
        "试卷",
        "二维码",
        "生日",
        "暑假",
        "书架",
        "哑巴",
        "自忍",
        "拉普兰德",
        "源石冰晶",
        "地雷",
        "七天神像",
        "蝙蝠",
        "动物园",
        "天空之琴",
        "五菱宏光",
        "特朗普",
        "自言自语",
        "独一无二",
        "百里挑一",
        "归心似箭",
        "未雨绸缪",
        "世外桃源",
        "武汉",
        "花木兰",
        "陈奕迅",
        "梅菲斯特",
        "莱茵生命",
        "过载",
        "航海",
        "科目一",
        "抑郁",
        "奥运五环",
        "音乐",
        "恐龙",
        "蜈蚣",
        "蔡徐坤",
        "吴亦凡",
        "蒙德城",
        "猪",
        "牛",
        "马",
        "薯条",
        "突袭",
        "艾滋病",
        "打气筒",
        "眼罩",
        "口球",
        "直升机",
        "哥斯拉",
        "传送带",
        "三体",
        "百慕大三角",
        "古筝",
        "骨折",
        "妹妹",
        "佩奇",
        "唢呐",
        "字字字字",
        "字",
        "字字",
        "字字字",
        "吃豆人",
        "活字印刷",
        "火药",
        "洗衣粉",
        "玉兔",
        "舔狗",
        "煤气罐",
        "刺客",
        "火葬场",
        "火花",
        "变色龙",
        "蟒蛇",
        "脑瘫",
        "轮椅",
        "交易",
        "微积分",
        "抗日战争",
        "毕加索",
        "被子",
        "床",
        "杯子",
        "铃兰",
        "圣经",
        "三字经",
        "鸡蛋",
        "西红柿",
        "土豆",
        "女朋友",
        "答案",
        "蔡英文",
        "富士山",
        "指头",
        "猫尾巴",
        "隐身",
        "井底之蛙",
        "坐井观天",
        "银行",
        "保安",
        "奥迪",
        "莲花",
        "耐克",
        "迫击炮",
        "格陵兰岛",
        "葫芦娃",
        "好莱坞",
        "火蓝之心",
        "骨头",
        "双节棍",
        "课桌",
        "蟑螂",
        "末影龙",
        "中二病",
        "传火",
        "高坚果",
        "金针菇",
        "地狱",
        "工业",
        "资本家",
        "梯子",
        "吹风机",
        "双鱼座",
        "冬灵血巫",
        "铅封行动",
        "停车场",
        "朝夕相处",
        "博士",
        "沃伦姆德",
        "刘德华",
        "骡",
        "生不逢时",
        "警察",
        "裁判",
        "闪光弹",
        "刷怪笼",
        "七夕",
        "世界",
        "饭圈",
        "哔咔",
        "核电站",
        "海盗",
        "肝",
        "垃圾袋",
        "刑法",
        "饮料",
        "蜜雪冰城",
        "张飞",
        "热水器",
        "麻将",
        "汤姆",
        "杰瑞",
        "臭豆腐",
        "鸡毛掸子",
        "水表",
        "指甲钳",
        "数字",
        "梳子",
        "电钻",
        "犀牛",
        "长颈鹿",
        "蛇",
        "狮子",
        "鳄鱼",
        "书",
        "电影",
        "匕首",
        "坦克",
        "航母",
        "手枪",
        "金箍棒",
        "雷",
        "蚂蚱",
        "萤火虫",
        "胃",
        "花好月圆",
        "仪表盘",
        "手机壳",
        "程序员",
        "医生",
        "老师",
        "举重",
        "笛子",
        "不倒翁",
        "魔方",
        "风筝",
        "拼图",
        "沙漏",
        "鱼钩",
        "扫帚",
        "秤",
        "发箍",
        "辣椒",
        "木耳",
        "少林寺",
        "黑洞",
        "罗德岛",
        "船",
        "战狼",
        "周恩来",
        "蒋介石",
        "红海行动",
        "花果山",
        "五花肉",
        "蟠桃园",
        "白龙马",
        "达芬奇",
        "爱因斯坦",
        "新宝岛",
        "洗洁精",
        "刘华强",
        "母鸡",
        "果汁",
        "开国大典",
        "绝影",
        "QQ飞车",
        "深海",
        "蓝图",
        "双面胶",
        "墓碑",
        "老鼠夹",
        "雅典娜",
        "口红",
        "圣骑士",
        "战争",
        "瘟疫",
        "飞机场",
        "小黄人",
        "狙击手",
        "电鳗",
        "彩虹",
        "安瓿",
        "芭蕉扇",
        "清明节",
        "毛笔",
        "钢笔",
        "闪现",
        "蕾米莉亚",
        "P90",
        "凤凰",
        "龙",
        "搜狗",
        "百度",
        "乔治",
        "芭芭拉",
        "苏轼",
        "白面鸮",
        "美团外卖",
        "长安",
        "槐花",
        "字母",
        "蒙古上单",
        "河豚",
        "梨",
        "香蕉",
        "飞",
        "有机化学",
        "马鞍",
        "泥土",
        "氯化氢",
        "吉吉国王",
        "熊大",
        "光头强",
        "地平线",
        "魑魅魍魉",
        "甘雨"
    ]
}


class Module(Plugin):
    entry = 'ds'
    brief_help = '你画我猜'
    manager: CommandDelegateManager = CommandDelegateManager.get_instance()

    @manager.register(Alconna(
        headers=manager.headers,
        command=entry,
        options=[
            Subcommand('start', help_text='开始一局你画我猜游戏'),
            Subcommand('status', help_text='查看你画我猜状态')
        ],
        help_text='你画我猜'
    ))
    async def process(self, command: Arpamar, alc: Alconna):
        if not command.subcommands:
            return await self.print_help(alc.get_help())
        try:
            config = Config()
            if command.has('start'):
                # 判断用户是否正在游戏中
                if self.member.id in MEMBER_RUNING_LIST:
                    return
                else:
                    MEMBER_RUNING_LIST.append(self.member.id)

                # 判断私信是否可用
                try:
                    await self.app.sendFriendMessage(self.member.id, MessageChain.create([
                        Plain(f"本消息仅用于测试私信是否可用，无需回复\n{time.time()}")
                    ]))
                except:
                    await self.app.sendGroupMessage(self.group, MessageChain.create([
                        Plain(f"由于你未添加好友，暂时无法发起你画我猜，请自行添加 {config.BOT_NAME} 好友，用于发送题目")
                    ]))
                    MEMBER_RUNING_LIST.remove(self.member.id)
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

                # 等待答案中断
                @Waiter.create_using_function([GroupMessage])
                async def start_game(submit_answer_group: Group, submit_answer_member: Member,
                                     submit_answer_message: MessageChain, submit_answer_source: Source):
                    group_id = GROUP_GAME_PROCESS[self.group.id]
                    owner = group_id["owner"]
                    question = group_id["question"].upper()
                    question_len = len(question)
                    saying = submit_answer_message.asDisplay().upper()
                    saying_len = len(saying)

                    if all([submit_answer_member.id == owner, saying in ["终止", "取消", "结束"]]):
                        return False

                    if all([submit_answer_group.id == self.group.id, submit_answer_member.id != owner,
                            saying_len == question_len]):
                        if submit_answer_member.id not in group_id["player"]:
                            GROUP_GAME_PROCESS[self.group.id]["player"][submit_answer_member.id] = 1
                        if group_id["player"][submit_answer_member.id] < 9:
                            talk_num = group_id["player"][submit_answer_member.id] + 1
                            GROUP_GAME_PROCESS[self.group.id]["player"][submit_answer_member.id] = talk_num
                            if saying == question:
                                return [submit_answer_member, submit_answer_source]
                        elif group_id["player"][submit_answer_member.id] == 9:
                            await self.app.sendGroupMessage(self.group, MessageChain.create([
                                At(submit_answer_member.id),
                                Plain("你的本回合答题机会已用尽")
                            ]), quote=submit_answer_source)

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
                            Plain(f"是否确认在本群开启一场你画我猜？这将消耗你 4 点{config.COIN_NAME}")
                        ]), quote=self.source)
                    except UnknownTarget:
                        await self.app.sendGroupMessage(self.group, MessageChain.create([
                            At(self.member.id),
                            Plain(f" 是否确认在本群开启一场你画我猜？这将消耗你 4 点{config.COIN_NAME}")
                        ]))
                    try:
                        # 新游戏创建完成，进入等待玩家阶段
                        if await asyncio.wait_for(self.inc.wait(confirm), timeout=15):
                            question = secrets.choice(WORD["word"])
                            GROUP_GAME_PROCESS[self.group.id] = {
                                "question": question,
                                "owner": self.member.id,
                                "player": {}
                            }
                            if await BotGame(str(self.member.id)).get_coins() < 4:
                                GROUP_RUNING_LIST.remove(self.group.id)
                                del GROUP_GAME_PROCESS[self.group.id]
                                await self.app.sendGroupMessage(self.group, MessageChain.create([
                                    At(self.member.id),
                                    Plain(f" 你的{config.COIN_NAME}不足，无法开始游戏")]))
                                return
                            else:
                                await BotGame(str(self.member.id)).update_coin(-4)
                                question_len = len(question)
                                await self.app.sendGroupMessage(self.group, MessageChain.create([
                                    Plain(f"本次题目为 {question_len} 个字，请等待 "),
                                    At(self.member.id),
                                    Plain(" 在群中绘图"),
                                    Plain("\n创建者发送 <取消/终止/结束> 可结束本次游戏"),
                                    Plain("\n每人每回合只有 8 次答题机会，请勿刷屏请勿抢答。")
                                ]), quote=self.source)
                                await asyncio.sleep(1)
                                await self.app.sendFriendMessage(self.member.id, MessageChain.create([
                                    Plain(f"本次的题目为：{question}，请在一分钟内\n在群中\n在群中\n在群中\n发送涂鸦或其他形式等来表示该主题")
                                ]))

                            try:
                                result = await asyncio.wait_for(self.inc.wait(start_game), timeout=180)
                                if result:
                                    owner = str(GROUP_GAME_PROCESS[self.group.id]["owner"])
                                    await BotGame(owner).update_coin(2)
                                    await BotGame(str(result[0].id)).update_coin(1)
                                    GROUP_RUNING_LIST.remove(self.group.id)
                                    del GROUP_GAME_PROCESS[self.group.id]
                                    await self.app.sendGroupMessage(self.group.id, MessageChain.create([
                                        Plain("恭喜 "),
                                        At(result[0].id),
                                        Plain(f" 成功猜出本次答案，你和创建者分别获得 1 点和 2 点{config.COIN_NAME}，本次游戏结束")
                                    ]), quote=result[1])
                                else:
                                    owner = str(GROUP_GAME_PROCESS[self.group.id]["owner"])
                                    await BotGame(owner).update_coin(1)
                                    GROUP_RUNING_LIST.remove(self.group.id)
                                    del GROUP_GAME_PROCESS[self.group.id]
                                    await self.app.sendGroupMessage(self.group, MessageChain.create([
                                        Plain(f"本次你画我猜已终止，将返还创建者 1 点{config.COIN_NAME}")
                                    ]))
                            except asyncio.TimeoutError:
                                owner = str(GROUP_GAME_PROCESS[self.group.id]["owner"])
                                question = GROUP_GAME_PROCESS[self.group.id]["question"]
                                await BotGame(owner).update_coin(1)
                                GROUP_RUNING_LIST.remove(self.group.id)
                                del GROUP_GAME_PROCESS[self.group.id]
                                await self.app.sendGroupMessage(self.group, MessageChain.create([
                                    Plain(f"由于长时间没有人回答出正确答案，将返还创建者 1 点{config.COIN_NAME}，本次你画我猜已结束"),
                                    Plain(f"\n本次的答案为：{question}")
                                ]))

                        # 终止创建流程
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
            elif command.has('status'):
                if self.friend.id == int(config.MASTER_QQ):
                    runlist_len = len(GROUP_RUNING_LIST)
                    runlist_str = "\n".join(map(lambda x: str(x), GROUP_RUNING_LIST))
                    if runlist_len > 0:
                        await self.app.sendFriendMessage(config.MASTER_QQ, MessageChain.create([
                            Plain(f"当前共有 {runlist_len} 个群正在玩你画我猜"),
                            Plain(f"\n{runlist_str}")
                        ]))
                    else:
                        await self.app.sendFriendMessage(config.MASTER_QQ, MessageChain.create([
                            Plain(f"当前没有正在运行你画我猜的群")
                        ]))
            return self.args_error()
        except Exception as e:
            logger.exception(e)
            return self.unkown_error()
