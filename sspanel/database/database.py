from peewee import *

from app.util.dao import ORM


class PluginSspanelAccount(ORM):
    pwd = CharField()
    """登录密码"""
    qid = FixedCharField(max_length=10)
    """QQ号"""
    user = CharField()
    """登录邮箱"""
    web = CharField()
    """登录网址"""

    class Meta:
        table_name = 'plugin_sspanel_account'
        indexes = (
            (('qid', 'web', 'user'), True),
        )
        primary_key = CompositeKey('qid', 'user', 'web')


PluginSspanelAccount.create_table()
