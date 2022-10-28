import datetime

from peewee import (
    TextField,
    BooleanField,
    IntegerField,
    DateTimeField,
    BigIntegerField,
)

from app.util.dao import ORM


class DriftingBottle(ORM):
    member = BigIntegerField()
    group = BigIntegerField()
    text = TextField(null=True)
    image = TextField(null=True)
    fishing_times = IntegerField(default=0)
    send_date = DateTimeField(default=datetime.datetime.now)
    isdelete = BooleanField(default=False)

    class Meta:
        db_table = "plugin_drifting_bottle_list"


class BottleScore(ORM):
    member = BigIntegerField()
    bottle_id = IntegerField()
    socre = IntegerField()

    class Meta:
        db_table = "plugin_drifting_bottle_score"


class BottleDiscuss(ORM):
    member = BigIntegerField()
    bottle_id = IntegerField()
    discuss = TextField()
    discuss_time = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = "plugin_drifting_bottle_discuss"


class DiscussLike(ORM):
    member = BigIntegerField()
    discuss_id = IntegerField()
    like = BooleanField()
    like_time = DateTimeField(default=datetime.datetime.now)

    class Meta:
        db_table = "plugin_drifting_bottle_discuss_like"


DriftingBottle.create_table()
BottleScore.create_table()
BottleDiscuss.create_table()
DiscussLike.create_table()
