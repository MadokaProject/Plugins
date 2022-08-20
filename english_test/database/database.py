from peewee import *

from app.util.dao import ORM


class WordDict(ORM):
    book_id = CharField(column_name='bookId')
    pos = CharField()
    tran = CharField()
    word = CharField()

    class Meta:
        table_name = 'word_dict'
        primary_key = CompositeKey('word', 'pos')


WordDict.create_table()
