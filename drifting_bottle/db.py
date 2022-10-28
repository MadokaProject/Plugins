import random

from typing import List
from decimal import ROUND_HALF_UP, Decimal

from graia.ariadne.model import Member

from app.util.dao import database

from .database.database import DriftingBottle, BottleScore, BottleDiscuss


def throw_bottle(sender: Member, text=None, image=None) -> int:
    bottle = DriftingBottle(member=sender.id, group=sender.group.id, text=text, image=image)
    bottle.save()
    return bottle.id


def get_bottle_by_id(bottle_id: int) -> list[DriftingBottle]:
    return DriftingBottle.select().where(DriftingBottle.id == bottle_id, DriftingBottle.isdelete == 0)


def count_bottle() -> int:
    return DriftingBottle.select(DriftingBottle.isdelete == 0).count()


def clear_bottle():
    DriftingBottle.delete().execute()


def delete_bottle_by_member(member: Member):
    DriftingBottle.update(isdelete=True).where(DriftingBottle.member == member.id).execute()


def delete_bottle(bottle_id: int):
    DriftingBottle.update(isdelete=True).where(DriftingBottle.id == bottle_id).execute()


# 漂流瓶评分系统

# 获取漂流瓶评分平均数，保留一位小数
def get_bottle_score_avg(bottle_id: int):
    bottle_score_count = BottleScore.select().where(BottleScore.bottle_id == bottle_id).count()
    if bottle_score_count == 0:
        return False
    socre = sum(i.socre for i in BottleScore.select(BottleScore.socre).where(BottleScore.bottle_id == bottle_id))

    return "%.1f" % (socre / bottle_score_count)


def add_bottle_score(bottle_id: int, member: Member, score: int):
    if 1 <= score <= 5:
        if BottleScore.select().where(BottleScore.bottle_id == bottle_id, BottleScore.member == member.id).exists():
            return False
        BottleScore.create(bottle_id=bottle_id, member=member.id, socre=score)
        return True


def get_bottle() -> dict:
    "随机捞三个瓶子，按权值分配"
    if DriftingBottle.select().count() == 0:
        return None
    bottles: List[DriftingBottle] = (
        DriftingBottle.select().where(DriftingBottle.isdelete == 0).order_by(database.random()).limit(3)
    )

    bottle_list = []
    for i, _ in enumerate(bottles):
        score = get_bottle_score_avg(bottles[i].id)
        bottle_list.extend(
            i
            for _ in range(
                int(Decimal(float(score) if score else 3.0).quantize(Decimal("1.0"), rounding=ROUND_HALF_UP))
            )
        )

    random.shuffle(bottle_list)
    bottle: DriftingBottle = bottles[random.choice(bottle_list)]

    DriftingBottle.update(fishing_times=DriftingBottle.fishing_times + 1).where(
        DriftingBottle.id == bottle.id
    ).execute()
    return {
        "id": bottle.id,
        "member": bottle.member,
        "group": bottle.group,
        "text": bottle.text,
        "image": bottle.image,
        "fishing_times": bottle.fishing_times,
        "send_date": bottle.send_date,
    }


# 漂流瓶评论系统

# 获取漂流瓶评论
def get_bottle_discuss(bottle_id: int):
    discuss_count = BottleDiscuss.select().where(BottleDiscuss.bottle_id == bottle_id).count()
    if discuss_count == 0:
        return None
    else:
        return BottleDiscuss.select().where(BottleDiscuss.bottle_id == bottle_id)


# 添加漂流瓶评论
def add_bottle_discuss(bottle_id: int, member: Member, discuss: str):
    if (
        BottleDiscuss.select().where(BottleDiscuss.bottle_id == bottle_id, BottleDiscuss.member == member.id).count()
        >= 3
    ):
        return False
    BottleDiscuss.create(bottle_id=bottle_id, member=member.id, discuss=discuss)
    return True


# 获取自己的所有漂流瓶
def get_my_bottles(member: Member) -> list[DriftingBottle]:
    return DriftingBottle.select().where(DriftingBottle.member == member.id, DriftingBottle.isdelete == 0)
