from peewee import *

from app.util.dao import ORM


class PluginNeteaseAccount(ORM):
    phone = FixedCharField(max_length=11)
    """手机号"""
    pwd = FixedCharField(max_length=20)
    """密码"""
    qid = FixedCharField(max_length=12)
    """QQ号"""
    class Meta:
        table_name = 'plugin_netease_account'
        primary_key = False


PluginNeteaseAccount.create_table()
