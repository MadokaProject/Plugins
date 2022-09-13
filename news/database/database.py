from peewee import *

from app.util.dao import ORM


class News(ORM):
    uid = FixedCharField(max_length=12)
    model = FixedCharField(max_length=6)
    status = BooleanField(default=True)
    
    class Meta:
        table_name = 'plugin_news'
        primary_key = CompositeKey('uid', 'model')
        
        
News.create_table()
