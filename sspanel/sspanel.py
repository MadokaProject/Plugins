import requests
from arclet.alconna import Alconna, Args, Subcommand, Arpamar, AnyUrl, Email
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from loguru import logger

from app.core.command_manager import CommandManager
from app.plugin.base import Plugin, Scheduler, InitDB
from app.util.dao import MysqlDao

requests.packages.urllib3.disable_warnings()


class Module(Plugin):
    entry = 'sspanel'
    brief_help = '机场签到'
    manager: CommandManager = CommandManager.get_command_instance()

    @manager(Alconna(
        headers=manager.headers,
        command=entry,
        options=[
            Subcommand('qd', help_text='立即进行一次签到', args=Args['host': AnyUrl, 'email' :Email, 'password': str]),
            Subcommand('add', help_text='添加/修改签到账号', args=Args['host': AnyUrl, 'email' :Email, 'password': str]),
            Subcommand('remove', help_text='删除签到账号', args=Args['host': AnyUrl, 'email' :Email]),
            Subcommand('list', help_text='列出你添加的签到账号')
        ],
        help_text='机场签到: 为保证账号安全, 该服务仅私发有效'
    ))
    async def process(self, command: Arpamar, alc: Alconna):
        subcommand = command.subcommands
        other_args = command.other_args
        if not subcommand:
            return await self.print_help(alc.get_help())
        try:
            if not hasattr(self, 'friend'):
                return MessageChain.create([Plain('请私聊使用该命令!')])
            if subcommand.__contains__('qd'):
                account = {0: {
                    'web': other_args['host'],
                    'user': other_args['email'],
                    'pwd': other_args['password']
                }}
                msg = await Tasker(self.app).checkin(account)
                return MessageChain.create([
                    Plain('机场签到完成\r\n'),
                    Plain(msg)
                ])
            elif subcommand.__contains__('add'):
                with MysqlDao() as db:
                    return MessageChain.create([
                        Plain('添加/修改成功！' if db.update(
                            'REPLACE INTO plugin_sspanel_account(qid, web, user, pwd) VALUES (%s, %s, %s, %s)',
                            [self.friend.id, other_args['host'], other_args['email'], other_args['password']]
                        ) else '添加/修改失败！')
                    ])
            elif subcommand.__contains__('remove'):
                with MysqlDao() as db:
                    return MessageChain.create([
                        Plain('删除成功！' if db.update(
                            'DELETE FROM plugin_sspanel_account WHERE qid=%s and web=%s and user=%s',
                            [self.friend.id, other_args['host'], other_args['email']]
                        ) else '删除失败！')
                    ])
            elif subcommand.__contains__('list'):
                with MysqlDao() as db:
                    res = db.query(
                        'SELECT web, user FROM plugin_sspanel_account WHERE qid=%s',
                        [self.friend.id]
                    )
                    return MessageChain.create([
                        Plain('\n'.join(f'{index}: {web}\t{user}' for index, (web, user) in enumerate(res)))
                    ])
            return self.args_error()
        except Exception as e:
            logger.exception(e)
            return self.unkown_error()


class Tasker(Scheduler):
    cron = '0 8 * * * 0'

    async def process(self):
        with MysqlDao() as _db:
            accounts = _db.query(
                'SELECT qid, web, user, pwd FROM Plugin_Sspanel_Account'
            )
            if accounts:
                for index, (qid, web, user, pwd) in enumerate(accounts):
                    account = {}
                    account.update({
                        index: {
                            'web': web,
                            'user': user,
                            'pwd': pwd
                        }
                    })
                    msg = await self.checkin(account)
                    await self.message_send(msg, int(qid))

    async def checkin(self, account):
        msgall = ''
        for i in range(len(account.keys())):

            email = account[i]['user'].split('@')
            email = email[0] + '%40' + email[1]
            password = account[i]['pwd']

            session = requests.session()

            try:
                # 以下except都是用来捕获当requests请求出现异常时，
                # 通过捕获然后等待网络情况的变化，以此来保护程序的不间断运行
                session.get(account[i]['web'], verify=False)

            except requests.exceptions.ConnectionError:
                msg = account[i]['web'] + '\n\n' + '网络不通'
                msgall = msgall + account[i]['web'] + '\n\n' + msg + '\n\n'
                print(msg)
                continue
            except requests.exceptions.ChunkedEncodingError:
                msg = account[i]['web'] + '\n\n' + '分块编码错误'
                msgall = msgall + account[i]['web'] + '\n\n' + msg + '\n\n'
                print(msg)
                continue
            except:
                msg = account[i]['web'] + '\n\n' + '未知错误'
                msgall = msgall + account[i]['web'] + '\n\n' + msg + '\n\n'
                print(msg)
                continue

            login_url = account[i]['web'] + '/auth/login'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            }

            post_data = 'email=' + email + '&passwd=' + password + '&code='
            post_data = post_data.encode()
            response = session.post(login_url, post_data, headers=headers, verify=False)

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
                'Referer': account[i]['web'] + '/user'
            }

            response = session.post(account[i]['web'] + '/user/checkin', headers=headers, verify=False)
            msg = (response.json()).get('msg')

            msgall = msgall + account[i]['web'] + '\n\n' + msg + '\n\n'
            print(msg)

            info_url = account[i]['web'] + '/user'
            response = session.get(info_url, verify=False)

        return msgall

    async def message_send(self, msg, qid):
        """签到消息推送"""
        await self.app.sendFriendMessage(qid, MessageChain.create([
            Plain('机场签到完成\r\n'),
            Plain(msg)
        ]))


class DB(InitDB):

    async def process(self):
        with MysqlDao() as __db:
            __db.update(
                "create table if not exists Plugin_Sspanel_Account( \
                    qid char(10) not null comment 'QQ号', \
                    web varchar(50) not null comment '签到地址', \
                    user varchar(50) not null comment '登陆邮箱', \
                    pwd varchar(50) not null comment '登陆密码', \
                    primary key(qid, web, user))"
            )
