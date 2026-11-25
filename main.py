#!/usr/bin/env python3
"""Build the 25 November 2026 world-news image and place it for grading.

One self-contained program: it draws a 1024x1024 infographic with PIL
from six stories, each verified against reputable reporting dated
Wednesday 25 November 2026, checks the finished picture is a whole,
well-formed PNG inside the competition's limits, then writes it to
/output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png when that is set)
and keeps a copy as entry.png beside this file for review.

No network, no randomness, no timestamps, no state: two runs of this
script produce byte-identical output.
"""

import hashlib
import os
import struct
import sys
import zlib

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_BYTES = 1_048_576
MAX_SIDE = 1024
CHUNK = 1 << 16
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# ---- palette -------------------------------------------------------
INK_BG = (11, 20, 36)
INK_CARD = (22, 35, 58)
INK_EDGE = (42, 59, 87)
INK_RULE = (58, 82, 122)
INK_WHITE = (255, 255, 255)
INK_BODY = (214, 222, 235)
INK_MUTED = (148, 163, 184)
INK_AMBER = (232, 163, 61)

# ---- type ----------------------------------------------------------
DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def load_fonts():
    return {
        "title": ImageFont.truetype(DEJAVU_BOLD, 56),
        "sub": ImageFont.truetype(DEJAVU, 27),
        "tag": ImageFont.truetype(DEJAVU_BOLD, 20),
        "head": ImageFont.truetype(DEJAVU_BOLD, 30),
        "body": ImageFont.truetype(DEJAVU, 22),
        "foot": ImageFont.truetype(DEJAVU, 20),
    }


# ---- stories: (tag, accent, headline, detail, glyph) ---------------
STORIES = [
    (
        "UKRAINE WAR  \u2022  REFINERIES",
        (91, 141, 239),
        "Drones hit two Russian refineries",
        "Ukrainian drones strike the Syzran and Kuibyshev plants in "
        "Samara; Putin warns retaliation is \u201cinevitable\u201d.",
        "flame",
    ),
    (
        "NVIDIA  \u2022  TECH",
        (245, 166, 35),
        "Huang rally fades fast",
        "Nvidia shares fall about 6% as lawmakers question Trump\u2019s "
        "role in reinstating Huang; a pardon is floated.",
        "chip",
    ),
    (
        "YEMEN  \u2022  RED SEA",
        (232, 93, 93),
        "Houthis threaten Jeddah ports",
        "After coalition strikes on Hodeidah, the Houthis say Jeddah "
        "and all Saudi Red Sea ports will be targeted.",
        "anchor",
    ),
    (
        "SPACE  \u2022  SHENZHOU-24",
        (62, 207, 142),
        "Pakistan\u2019s first astronaut in orbit",
        "Zeeshan Ali lifts off on Shenzhou-24, the first foreigner to "
        "board China\u2019s Tiangong station.",
        "rocket",
    ),
    (
        "COLOMBIA  \u2022  CARTAGENA",
        (178, 132, 245),
        "Cartagena standoff ends",
        "All hostages freed without casualties after gunmen seize a "
        "supermarket in a botched robbery.",
        "store",
    ),
    (
        "INDONESIA  \u2022  RESCUE",
        (240, 200, 70),
        "Dozens trapped in a West Java mine",
        "Rescuers search for miners blocked in a 100-metre-deep mine "
        "since Monday after heavy rains cut off roads.",
        "helmet",
    ),
]

SOURCES_LINE = (
    "Sources: Reuters  \u2022  The Independent  \u2022  BBC  \u2022  "
    "WSJ  \u2022  NY Post  \u2022  TBS News"
)


def wrap_text(draw, text, font, max_width):
    """Greedy word wrap measured in pixels."""
    lines = []
    current = ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


# ---- glyphs, drawn in a 48x48 box ----------------------------------
def glyph_chip(d, x, y, c):
    d.rectangle([x + 10, y + 10, x + 38, y + 38], outline=c, width=4)
    d.rectangle([x + 20, y + 20, x + 28, y + 28], fill=c)
    for p in (16, 24, 32):
        d.line([x + p, y + 2, x + p, y + 10], fill=c, width=3)
        d.line([x + p, y + 38, x + p, y + 46], fill=c, width=3)
        d.line([x + 2, y + p, x + 10, y + p], fill=c, width=3)
        d.line([x + 38, y + p, x + 46, y + p], fill=c, width=3)


def glyph_flame(d, x, y, c):
    d.polygon(
        [(x + 24, y + 2), (x + 38, y + 20), (x + 44, y + 32),
         (x + 36, y + 46), (x + 12, y + 46), (x + 4, y + 32),
         (x + 10, y + 20)],
        outline=c, width=4,
    )
    d.polygon(
        [(x + 24, y + 22), (x + 32, y + 32), (x + 28, y + 42),
         (x + 18, y + 42), (x + 15, y + 32)],
        fill=c,
    )


def glyph_anchor(d, x, y, c):
    d.ellipse([x + 18, y + 2, x + 30, y + 14], outline=c, width=4)
    d.line([x + 24, y + 12, x + 24, y + 44], fill=c, width=4)
    d.line([x + 8, y + 20, x + 40, y + 20], fill=c, width=4)
    d.arc([x + 6, y + 26, x + 42, y + 48], 0, 180, fill=c, width=4)


def glyph_rocket(d, x, y, c):
    d.polygon(
        [(x + 24, y + 2), (x + 34, y + 22), (x + 30, y + 36),
         (x + 18, y + 36), (x + 14, y + 22)],
        outline=c, width=4,
    )
    d.ellipse([x + 20, y + 22, x + 28, y + 30], fill=c)
    d.polygon([(x + 14, y + 30), (x + 6, y + 44), (x + 16, y + 38)], fill=c)
    d.polygon([(x + 34, y + 30), (x + 42, y + 44), (x + 32, y + 38)], fill=c)
    d.polygon([(x + 20, y + 42), (x + 28, y + 42), (x + 24, y + 50)], fill=c)


def glyph_store(d, x, y, c):
    d.rectangle([x + 6, y + 20, x + 42, y + 46], outline=c, width=4)
    d.line([x + 2, y + 20, x + 46, y + 20], fill=c, width=4)
    for xx in (7, 17, 27, 37):
        d.rectangle([x + xx, y + 6, x + xx + 8, y + 20], outline=c, width=3)
    d.rectangle([x + 20, y + 32, x + 28, y + 46], fill=c)


def glyph_helmet(d, x, y, c):
    d.arc([x + 6, y + 10, x + 42, y + 44], 180, 360, fill=c, width=4)
    d.line([x + 4, y + 36, x + 44, y + 36], fill=c, width=4)
    d.line([x + 24, y + 8, x + 24, y + 20], fill=c, width=4)
    d.line([x + 14, y + 40, x + 14, y + 46], fill=c, width=3)
    d.line([x + 34, y + 40, x + 34, y + 46], fill=c, width=3)


GLYPHS = {
    "chip": glyph_chip,
    "flame": glyph_flame,
    "anchor": glyph_anchor,
    "rocket": glyph_rocket,
    "store": glyph_store,
    "helmet": glyph_helmet,
}


def draw_card(d, fonts, box, story):
    tag, accent, head, detail, glyph = story
    x, y, w, h = box
    d.rounded_rectangle(
        [x, y, x + w, y + h], radius=18,
        fill=INK_CARD, outline=INK_EDGE, width=2,
    )
    d.line([x + 4, y + 10, x + 4, y + h - 10], fill=accent, width=5)
    d.text((x + 22, y + 16), tag, font=fonts["tag"], fill=accent)
    GLYPHS[glyph](d, x + w - 66, y + 14, accent)
    pen = y + 52
    for line in wrap_text(d, head, fonts["head"], w - 44)[:2]:
        d.text((x + 22, pen), line, font=fonts["head"], fill=INK_WHITE)
        pen += 36
    pen += 6
    for line in wrap_text(d, detail, fonts["body"], w - 44)[:3]:
        d.text((x + 22, pen), line, font=fonts["body"], fill=INK_BODY)
        pen += 29


def render():
    """Draw the infographic and return its PNG bytes."""
    fonts = load_fonts()
    img = Image.new("RGB", (1024, 1024), INK_BG)
    d = ImageDraw.Draw(img)

    d.text((28, 22), "THE WORLD IN ONE DAY", font=fonts["title"], fill=INK_WHITE)
    d.text(
        (28, 92),
        "Wednesday, 25 November 2026  \u2022  Six stories that defined the day",
        font=fonts["sub"], fill=INK_AMBER,
    )
    d.line([28, 138, 996, 138], fill=INK_RULE, width=3)

    card_w, card_h, gap = 472, 252, 24
    origin_x, origin_y = 28, 158
    for i, story in enumerate(STORIES):
        col, row = i % 2, i // 2
        box = (
            origin_x + col * (card_w + gap),
            origin_y + row * (card_h + gap),
            card_w,
            card_h,
        )
        draw_card(d, fonts, box, story)

    foot_y = origin_y + 3 * card_h + 2 * gap + 14
    d.line([28, foot_y, 996, foot_y], fill=INK_RULE, width=2)
    d.text((28, foot_y + 12), SOURCES_LINE, font=fonts["foot"], fill=INK_MUTED)

    import io

    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


# ---- PNG validation -------------------------------------------------
def check_png(data):
    """Return an error string, or None when the bytes are a sound PNG."""
    if len(data) < 8 or data[:8] != PNG_MAGIC:
        return "not a PNG file"
    if len(data) > MAX_BYTES:
        return f"{len(data)} bytes, over the 1 MiB cap"
    width, height = struct.unpack(">II", data[16:24])
    if width != 1024 or height != 1024:
        return f"dimensions {width}x{height}, expected 1024x1024"
    pos = 8
    saw_iend = False
    while pos + 12 <= len(data):
        size, kind = struct.unpack(">I4s", data[pos:pos + 8])
        end = pos + 12 + size
        if end > len(data):
            return "truncated PNG chunk"
        stored, = struct.unpack(">I", data[end - 4:end])
        actual = zlib.crc32(data[pos + 4:end - 4]) & 0xFFFFFFFF
        if stored != actual:
            return f"bad CRC in {kind.decode('ascii', 'replace')} chunk"
        if kind == b"IEND":
            saw_iend = True
            if end != len(data):
                return "trailing bytes after IEND"
            break
        pos = end
    if not saw_iend:
        return "missing IEND chunk"
    return None


def write_file(path, data):
    written = 0
    with open(path, "wb") as handle:
        while written < len(data):
            written += handle.write(data[written:written + CHUNK])
    os.chmod(path, 0o644)


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    data = render()
    problem = check_png(data)
    if problem is not None:
        print(f"entry.png rejected: {problem}", file=sys.stderr)
        return 1
    digest = sha256_hex(data)

    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, "entry.png")
    write_file(target, data)
    with open(target, "rb") as handle:
        if sha256_hex(handle.read()) != digest:
            print("entry.png rejected: copy does not match", file=sys.stderr)
            return 1

    review = os.path.join(HERE, "entry.png")
    write_file(review, data)
    print(f"wrote {target} ({len(data)} bytes, sha256 {digest[:16]}...)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
