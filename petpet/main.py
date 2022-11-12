from io import BytesIO
from pathlib import Path

from PIL import Image as IMG, ImageOps

from app.util.alconna import Args, Arpamar, Commander
from app.util.graia import At, Group, GroupMessage, message
from app.util.network import general_request
from app.util.phrases import *

FRAMES_PATH = Path(__file__).parent.joinpath("PetPetFrames")

command = Commander("pet", "摸摸", Args["qq", At])


@command.no_match(events=[GroupMessage])
async def petpet(sender: Group, cmd: Arpamar):
    message(Image(data_bytes=await pet(cmd.query("qq").target))).target(sender).send()


frame_spec = [
    (27, 31, 86, 90),
    (22, 36, 91, 90),
    (18, 41, 95, 90),
    (22, 41, 91, 91),
    (27, 28, 86, 91),
]

squish_factor = [
    (0, 0, 0, 0),
    (-7, 22, 8, 0),
    (-8, 30, 9, 6),
    (-3, 21, 5, 9),
    (0, 0, 0, 0),
]

squish_translation_factor = [0, 20, 34, 21, 0]

frames = tuple(FRAMES_PATH.joinpath(f"frame{i}.png") for i in range(5))


# 生成函数（非数学意味）
async def make_frame(avatar, i, squish=0, flip=False):
    # 读入位置
    spec = list(frame_spec[i])
    # 将位置添加偏移量
    for j, s in enumerate(spec):
        spec[j] = int(s + squish_factor[i][j] * squish)
    # 读取手
    hand = IMG.open(frames[i])
    # 反转
    if flip:
        avatar = ImageOps.mirror(avatar)
    # 将头像放缩成所需大小
    avatar = avatar.resize(
        (int((spec[2] - spec[0]) * 1.2), int((spec[3] - spec[1]) * 1.2)), IMG.ANTIALIAS
    ).quantize()
    # 并贴到空图像上
    gif_frame = IMG.new("RGB", (112, 112), (255, 255, 255))
    gif_frame.paste(avatar, (spec[0], spec[1]))
    # 将手覆盖（包括偏移量）
    gif_frame.paste(hand, (0, int(squish * squish_translation_factor[i])), hand)
    # 返回
    return gif_frame


async def pet(member_id, flip=False, squish=0) -> bytes:
    url = f"http://q1.qlogo.cn/g?b=qq&nk={str(member_id)}&s=640"
    gif_frames = []
    resp = await general_request(url, _type="bytes")
    avatar = IMG.open(BytesIO(resp))

    # 生成每一帧
    for i in range(5):
        gif_frames.append(await make_frame(avatar, i, squish=squish, flip=flip))
    # 输出

    image = BytesIO()
    gif_frames[0].save(
        image,
        format="GIF",
        append_images=gif_frames[1:],
        save_all=True,
        duration=60,
        loop=0,
        optimize=False,
    )
    return image.getvalue()
