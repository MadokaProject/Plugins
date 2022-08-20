from peewee import *

from app.util.dao import ORM


class ChaoxingSign(ORM):
    address = CharField(default='中国', null=True)
    """地址名称"""
    auto_sign = IntegerField(default=0, null=True)
    """自动签到状态"""
    clientip = CharField()
    """IP 地址"""
    expiration_time = DateTimeField(null=True)
    """到期时间"""
    latitude = CharField(default='-2', null=True)
    """纬度"""
    longitude = CharField(default='-1', null=True)
    """经度"""
    password = CharField()
    """密码"""
    qid = FixedCharField(max_length=12, primary_key=True)
    """QQ"""
    username = FixedCharField(max_length=11)
    """手机号"""

    class Meta:
        table_name = 'chaoxing_sign'


ChaoxingSign.create_table()
