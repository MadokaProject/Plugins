import requests
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Plain
from loguru import logger

from app.plugin.base import Plugin, Scheduler, InitDB
from app.util.dao import MysqlDao
from app.util.tools import isstartswith

requests.packages.urllib3.disable_warnings()


class Module(Plugin):
    entry = ['.sspanel', '.机场签到']
    brief_help = '机场签到'
    full_help = {
        'qd': {
            '立即进行一次签到': '',
            '[host]': '签到地址',
            '[email]': '登录邮箱',
            '[password]': '登录密码'
        },
        'add': {
            '添加签到账号': '',
            '[host]': '签到地址',
            '[email]': '登录邮箱',
            '[password]': '登录密码'
        },
        'remove': {
            '删除签到账号': '',
            '[host]': '签到地址',
            '[email]': '登录邮箱'
        },
        'list': '列出您添加的签到账号',
        '============\n为保证账号安全, 该服务仅私发有效': ''
    }

    async def process(self):
        if not self.msg:
            await self.print_help()
            return
        try:
            if not hasattr(self, 'friend'):
                self.resp = MessageChain.create([
                    Plain('请私聊使用该命令!')
                ])
                return
            if isstartswith(self.msg[0], 'qd'):
                assert len(self.msg) == 4
                account = {
                    0: {
                        'web': self.msg[1],
                        'user': self.msg[2],
                        'pwd': self.msg[3]
                    }
                }
                msg = await Tasker(self.app).checkin(account)
                self.resp = MessageChain.create([
                    Plain('机场签到完成\r\n'),
                    Plain(msg)
                ])
            elif isstartswith(self.msg[0], 'add'):
                assert len(self.msg) == 4
                with MysqlDao() as db:
                    self.resp = MessageChain.create([
                        Plain('添加/修改成功！' if db.update(
                            'REPLACE INTO plugin_sspanel_account(qid, web, user, pwd) VALUES (%s, %s, %s, %s)',
                            [self.friend.id, self.msg[1], self.msg[2], self.msg[3]]
                        ) else '添加/修改失败！')
                    ])
            elif isstartswith(self.msg[0], 'remove'):
                assert len(self.msg) == 3
                with MysqlDao() as db:
                    self.resp = MessageChain.create([
                        Plain('删除成功！' if db.update(
                            'DELETE FROM plugin_sspanel_account WHERE qid=%s and web=%s and user=%s',
                            [self.friend.id, self.msg[1], self.msg[2]]
                        ) else '删除失败！')
                    ])
            elif isstartswith(self.msg[0], 'list'):
                with MysqlDao() as db:
                    res = db.query(
                        'SELECT web, user FROM plugin_sspanel_account WHERE qid=%s',
                        [self.friend.id]
                    )
                    self.resp = MessageChain.create([
                        Plain('\n'.join(f'{index}: {web}\t{user}' for index, (web, user) in enumerate(res)))
                    ])
            else:
                self.args_error()
                return
        except AssertionError as e:
            print(e)
            self.args_error()

        except Exception as e:
            logger.exception(e)
            self.unkown_error()


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
