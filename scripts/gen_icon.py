"""生成 RedVideo 应用图标（ICO，含多尺寸）。"""
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import os, struct, io

SIZES = [16, 24, 32, 48, 64, 128, 256]
OUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.ico")


def _draw(size: int) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cy = size // 2
    r = size * 0.42

    # 暗色圆形背景，带轻微径向渐变
    bg_r = int(size * 0.44)
    for i in range(bg_r, int(bg_r * 0.6), -1):
        t = (bg_r - i) / (bg_r * 0.4)
        gray = int(26 + t * 30)
        d.ellipse(
            [cx - i, cy - i, cx + i, cy + i],
            fill=(gray, gray, gray + 4, 255),
        )

    # 红色播放三角
    tri_r = int(size * 0.2)
    angle = 0.35  # 略微偏右让视觉居中
    p1 = (cx + int(tri_r * 1.15), cy)
    p2 = (cx - int(tri_r * 0.5), cy - int(tri_r * 0.9))
    p3 = (cx - int(tri_r * 0.5), cy + int(tri_r * 0.9))
    d.polygon([p1, p2, p3], fill=(255, 50, 50, 255))

    # 高光（左上白色半透明小圆）
    hl_r = int(size * 0.15)
    d.ellipse(
        [cx - bg_r + 2, cy - bg_r + 2, cx - bg_r + 2 + hl_r, cy - bg_r + 2 + hl_r],
        fill=(255, 255, 255, 40),
    )

    return im


def _to_ico(images: list[Image.Image]) -> bytes:
    """多张 PNG → ICO 格式字节。"""
    png_data = []
    for im in images:
        buf = io.BytesIO()
        im.save(buf, "PNG")
        png_data.append(buf.getvalue())

    # ICO header
    count = len(png_data)
    header = struct.pack("<HHH", 0, 1, count)

    # Directory entries + PNG data, offsets after header + dir entries
    dir_offset = 6 + count * 16
    entries = b""
    data = b""
    offset = dir_offset
    for i, im in enumerate(images):
        w = im.width
        h = im.height
        bpp = 32
        sz = len(png_data[i])
        entries += struct.pack(
            "<BBBBHHII",
            w if w < 256 else 0,
            h if h < 256 else 0,
            0,  # color palette
            0,  # reserved
            1,  # color planes
            bpp,
            sz,
            offset,
        )
        data += png_data[i]
        offset += sz

    return header + entries + data


def main():
    imgs = [_draw(s) for s in SIZES]
    ico = _to_ico(imgs)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(ico)
    print(f"ICO generated: {OUT} ({len(imgs)} sizes)")


if __name__ == "__main__":
    main()
