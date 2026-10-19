#!/usr/bin/env python3
"""
make_reel.py — a 64 second, 1080p "faceless format reel".

Six formats in one video, all generated on this 2-core box:
  01 data story  · animated bars + counters
  02 quote card  · kinetic type
  03 comparison  · split panels
  04 timeline    · moving marker
  05 countdown   · numbered list
  06 menu        · call to action

Every number on screen is measured from this project — nothing is invented.

Usage:
  python video/showcase/make_reel.py --stills 3,9,21,30,40,50,59
  python video/showcase/make_reel.py            # full render
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoClip

# --------------------------------------------------------------------------
W, H, FPS = 1920, 1080, 30
MARGIN = 110

CREAM = (242, 237, 227)
MUTED = (146, 141, 130)
DIM = (96, 92, 85)
RULE = (52, 51, 48)
RED = (194, 84, 72)
ORANGE = (214, 137, 72)
BLUE = (108, 134, 170)

FONT_DIRS = [
    Path(__file__).resolve().parent.parent / "whiteboard" / "fonts",
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/dejavu"),
]
FONTS = {
    "hand": "Caveat_700Bold.ttf",
    "note": "PatrickHand_400Regular.ttf",
    "serif": "DejaVuSerif.ttf",
    "serif-bold": "DejaVuSerif-Bold.ttf",
    "sans": "DejaVuSans.ttf",
    "sans-bold": "DejaVuSans-Bold.ttf",
    "mono": "DejaVuSansMono.ttf",
}

# chapter clock -------------------------------------------------------------
CH = [
    (0.0, 5.2, "hook"),
    (5.2, 16.4, "data"),
    (16.4, 24.4, "quote"),
    (24.4, 34.4, "compare"),
    (34.4, 44.8, "timeline"),
    (44.8, 54.0, "countdown"),
    (54.0, 64.0, "menu"),
]
TOTAL = CH[-1][1]

CHAPTER_LABELS = {
    "data": ("01", "DATA STORY"),
    "quote": ("02", "QUOTE CARD"),
    "compare": ("03", "COMPARISON"),
    "timeline": ("04", "TIMELINE"),
    "countdown": ("05", "COUNTDOWN"),
    "menu": ("06", "MENU"),
}


# --------------------------------------------------------------------------
# fonts + cached text images
# --------------------------------------------------------------------------
_fc: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    key = (name, size)
    if key not in _fc:
        fn = FONTS[name]
        for d in FONT_DIRS:
            p = d / fn
            if p.exists():
                _fc[key] = ImageFont.truetype(str(p), size)
                break
        else:
            raise FileNotFoundError(fn)
    return _fc[key]


_tc: dict[tuple, tuple[Image.Image, int]] = {}


def text_img(s: str, fname: str, size: int, color):
    key = (s, fname, size, color)
    if key in _tc:
        return _tc[key]
    f = font(fname, size)
    asc, desc = f.getmetrics()
    w = max(1, int(math.ceil(f.getlength(s)))) + 10
    h = asc + desc + 10
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((5, 5 + asc), s, font=f, fill=tuple(color) + (255,), anchor="ls")
    _tc[key] = (img, asc)
    return _tc[key]


_ac: dict[tuple, Image.Image] = {}


def at_alpha(img: Image.Image, a: float) -> Image.Image:
    q = round(max(0.0, min(1.0, a)) * 24) / 24
    if q >= 1.0:
        return img
    key = (id(img), q)
    if key not in _ac:
        im = img.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * q)))
        _ac[key] = im
    return _ac[key]


def put(base, s, x, baseline, fname="sans", size=30, color=MUTED, alpha=1.0, align="left"):
    if alpha <= 0.01:
        return 0.0
    img, asc = text_img(s, fname, size, color)
    if align == "center":
        x -= img.width / 2 - 5
    elif align == "right":
        x -= img.width - 10
    base.alpha_composite(at_alpha(img, alpha), (int(round(x - 5)), int(round(baseline - 5 - asc))))
    return img.width - 10


def width_of(s, fname, size):
    return font(fname, size).getlength(s)


def fit_size(s, fname, size, max_w, floor=14):
    while size > floor and width_of(s, fname, size) > max_w:
        size -= 2
    return size


def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ease_out(p):
    return 1.0 - (1.0 - clamp01(p)) ** 3


def ease_io(p):
    return 0.5 - 0.5 * math.cos(math.pi * clamp01(p))


def rect(base, x0, y0, x1, y1, color, alpha=1.0):
    w, h = int(round(x1 - x0)), int(round(y1 - y0))
    if w <= 0 or h <= 0 or alpha <= 0.01:
        return
    layer = Image.new("RGBA", (w, h), tuple(color) + (int(255 * min(alpha, 1.0)),))
    base.alpha_composite(layer, (int(round(x0)), int(round(y0))))


# --------------------------------------------------------------------------
# background + chrome
# --------------------------------------------------------------------------
LW, LH = 480, 270
_yy, _xx = np.mgrid[0:LH, 0:LW].astype(np.float32)
_nx = (_xx / LW - 0.5) * 2
_ny = (_yy / LH - 0.5) * 2
_VIG = np.clip(1.0 - 0.55 * np.clip(_nx ** 2 * 0.5 + _ny ** 2 * 0.85, 0, 1.8) ** 1.2,
               0.18, 1.0).astype(np.float32)
_rng = np.random.default_rng(4242)


def background(t, accent):
    c1x = LW * (0.26 + 0.06 * math.sin(0.13 * t))
    c1y = LH * (0.22 + 0.05 * math.cos(0.11 * t))
    g1 = np.exp(-(((_xx - c1x) ** 2 + (_yy - c1y) ** 2) / (2 * (LW * 0.55) ** 2))).astype(np.float32)
    c2x = LW * (0.82 - 0.05 * math.cos(0.09 * t))
    c2y = LH * (0.86 + 0.04 * math.sin(0.12 * t))
    g2 = np.exp(-(((_xx - c2x) ** 2 + (_yy - c2y) ** 2) / (2 * (LW * 0.48) ** 2))).astype(np.float32)

    base = np.array([9.0, 9.5, 11.5], dtype=np.float32)
    arr = base + g1[..., None] * np.array(accent, dtype=np.float32) * 0.30
    arr += g2[..., None] * np.array([16.0, 18.0, 26.0], dtype=np.float32)
    arr *= _VIG[..., None]
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    return img.convert("RGBA")


def grain():
    n = _rng.integers(-5, 6, size=(LH // 2, LW // 2), dtype=np.int16)
    up = Image.fromarray((n + 128).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    return (np.asarray(up, dtype=np.int16) - 128)[:, :, None]


def chrome(base, t, chapter_key):
    a = clamp01((t - 0.5) / 0.8) * (1 - clamp01((t - TOTAL + 0.7) / 0.6))
    put(base, "PROJECT ALTER EGO", MARGIN, 86, "sans", 20, MUTED, a)
    put(base, "FORMAT REEL", MARGIN + 258, 86, "sans", 20, DIM, a * 0.9)

    if chapter_key in CHAPTER_LABELS:
        num, name = CHAPTER_LABELS[chapter_key]
        put(base, f"{num} — {name}", W - MARGIN, 86, "sans", 20, MUTED, a, align="right")

    # progress
    rect(base, MARGIN, 1016, W - MARGIN, 1018, RULE, a)
    p = ease_out(clamp01(t / TOTAL))
    if p > 0:
        rect(base, MARGIN, 1016, MARGIN + (W - 2 * MARGIN) * p, 1018, CREAM, a * 0.75)


def accent_for(key):
    return {"data": (26, 22, 16), "quote": (18, 12, 12), "compare": (14, 16, 24),
            "timeline": (16, 18, 14), "countdown": (22, 17, 12),
            "menu": (18, 15, 14), "hook": (16, 14, 16)}.get(key, (18, 16, 16))


# --------------------------------------------------------------------------
# 00 — hook
# --------------------------------------------------------------------------
def ch_hook(base, lt):
    t0, t1 = 0.15, 0.55
    s1 = "Six formats."
    s2 = "Zero face."

    y = 512
    put(base, s1, W / 2, y, "serif-bold", 138, CREAM,
        ease_out(clamp01((lt - t0) / 0.7)), align="center")
    put(base, s2, W / 2, y + 168, "serif-bold", 138, MUTED,
        ease_out(clamp01((lt - t1) / 0.7)), align="center")

    a = clamp01((lt - 1.25) / 0.8)
    if a > 0:
        w = 92 * ease_io(a)
        rect(base, W / 2 - w, y + 232, W / 2 + w, y + 234, RED, a)
    put(base, "generated on a 2-core CPU  ·  no GPU  ·  no API key", W / 2, y + 300,
        "note", 34, DIM, clamp01((lt - 1.6) / 0.9), align="center")


# --------------------------------------------------------------------------
# 01 — data story: animated bars, counters (all values measured)
# --------------------------------------------------------------------------
BARS = [
    ("Vertical teaser", "20 s of video", 85, CREAM),
    ("Doodle explainer", "47.5 s of video", 183, CREAM),
]
MAXV = 183


def ch_data(base, lt):
    x0, y0 = MARGIN, 300
    put(base, "Render time, measured on this box", x0, y0 - 56, "sans", 24, MUTED,
        clamp01((lt - 0.1) / 0.6))
    put(base, "seconds of CPU to produce one finished video", x0, y0 - 16, "note", 32, DIM,
        clamp01((lt - 0.25) / 0.6))

    bar_x, bar_max = x0 + 430, 980
    for i, (label, sub, val, col) in enumerate(BARS):
        row_y = 400 + i * 168
        start = 0.55 + i * 0.42
        p = ease_out(clamp01((lt - start) / 1.25))
        a = clamp01((lt - start) / 0.5)

        put(base, label, x0, row_y, "sans-bold", 34, CREAM, a)
        put(base, sub, x0, row_y + 40, "sans", 22, DIM, a)

        w = (val / MAXV) * bar_max * p
        rect(base, bar_x, row_y - 34, bar_x + bar_max, row_y + 6, RULE, a * 0.55)
        if w > 1:
            rect(base, bar_x, row_y - 34, bar_x + w, row_y + 6, col, a * 0.92)
        counter = f"{int(round(val * ease_out(clamp01((lt - start) / 1.35))))} s"
        put(base, counter, bar_x + bar_max + 40, row_y, "sans-bold", 34, CREAM, a)

    # third row: the thing this box cannot do
    row_y = 400 + 2 * 168
    a3 = clamp01((lt - 1.95) / 0.6)
    put(base, "GPU video model", x0, row_y, "sans-bold", 34, DIM, a3)
    put(base, "Wan · LTX · Hunyuan", x0, row_y + 40, "sans", 22, RULE, a3)
    rect(base, bar_x, row_y - 34, bar_x + 250, row_y + 6, (30, 29, 27), a3 * 0.8)
    put(base, "no CUDA on this machine", bar_x + 274, row_y, "note", 30, DIM, a3)
    if a3 > 0.2:
        # one clean strike line that draws across the empty bar
        sp = ease_io(clamp01((lt - 2.25) / 0.65))
        if sp > 0:
            rect(base, bar_x - 14, row_y - 15, bar_x - 14 + 278 * sp, row_y - 12, RED, a3 * 0.9)

    put(base, "Total spend: $0.00", MARGIN, 960, "note", 36, RED, clamp01((lt - 2.8) / 0.7))


# --------------------------------------------------------------------------
# 02 — quote card
# --------------------------------------------------------------------------
def ch_quote(base, lt):
    lines = ["The face was", "never the point."]
    y = 470
    for i, line in enumerate(lines):
        size = fit_size(line, "serif-bold", 128, W - 2 * MARGIN)
        put(base, line, W / 2, y + i * 158, "serif-bold", size,
            CREAM if i == 0 else MUTED, ease_out(clamp01((lt - 0.3 - i * 0.35) / 0.8)),
            align="center")

    a = clamp01((lt - 1.25) / 0.8)
    if a > 0:
        w = 74 * ease_io(a)
        rect(base, W / 2 - w, y + 232, W / 2 + w, y + 234, RED, a)
    put(base, "what the viewer actually came for", W / 2, y + 300, "note", 34, DIM,
        clamp01((lt - 1.6) / 0.8), align="center")


# --------------------------------------------------------------------------
# 03 — comparison
# --------------------------------------------------------------------------
LEFT = ["Subscription", "Credit packs", "Watermark", "Render queue"]
RIGHT = ["$0, forever", "Unlimited", "No watermark", "~3 minutes, local"]
PADX = 90


def ch_compare(base, lt):
    top, bot = 312, 812
    mid = W / 2
    maxw = mid - 60 - MARGIN

    # panels slide in
    pl = ease_out(clamp01((lt - 0.2) / 0.75))
    pr = ease_out(clamp01((lt - 0.35) / 0.75))

    lh = maxw * pl
    rh = maxw * pr
    rect(base, mid - 60 - lh, top, mid - 60, bot, (22, 21, 20), pl * 0.75)
    rect(base, mid + 60, top, mid + 60 + rh, bot, (26, 27, 24), pr * 0.75)

    put(base, "CLOUD TOOL", mid - 60 - PADX, top + 70, "sans-bold", 30, DIM, pl, align="right")
    put(base, "THIS BOX", mid + 60 + PADX, top + 70, "sans-bold", 30, CREAM, pr)
    if pl > 0.3:
        rect(base, mid - 60 - lh + PADX, top + 96, mid - 60 - PADX, top + 98, RULE, pl * 0.7)
    if pr > 0.3:
        rect(base, mid + 60 + PADX, top + 96, mid + 60 + rh - PADX, top + 98, RULE, pr * 0.7)

    for i, (l, r) in enumerate(zip(LEFT, RIGHT)):
        y = top + 172 + i * 96
        al = clamp01((lt - 0.75 - i * 0.14) / 0.55)
        ar = clamp01((lt - 1.05 - i * 0.16) / 0.55)
        put(base, l, mid - 60 - PADX, y, "sans", 36, (132, 128, 120), al, align="right")
        put(base, r, mid + 60 + PADX, y, "sans-bold", 36, CREAM, ar)
        if ar > 0.3:
            put(base, "✓", mid + 60 + PADX + width_of(r, "sans-bold", 36) + 22, y,
                "sans-bold", 34, RED, ar * 0.9)

    # divider draws down
    p = ease_io(clamp01((lt - 0.45) / 0.9))
    if p > 0:
        rect(base, mid - 1, top, mid + 1, top + (bot - top) * p, RULE, 1.0)
    put(base, "same output, different bill", W / 2, 900, "note", 34, MUTED,
        clamp01((lt - 1.9) / 0.7), align="center")


# --------------------------------------------------------------------------
# 04 — timeline
# --------------------------------------------------------------------------
NODES = [("Script", "one paragraph"), ("Frames", "drawn in code"),
         ("Ink", "strokes animate"), ("Score", "synthesized"),
         ("MP4", "ready to post")]


def ch_timeline(base, lt):
    y = 560
    x0, x1 = MARGIN + 90, W - MARGIN - 90
    step = (x1 - x0) / (len(NODES) - 1)

    p = ease_io(clamp01((lt - 0.15) / 1.1))
    rect(base, x0, y - 1, x0 + (x1 - x0) * p, y + 1, RULE, 1.0)

    for i, (name, sub) in enumerate(NODES):
        cx = x0 + step * i
        a = clamp01((lt - 0.45 - i * 0.34) / 0.5)
        if a <= 0:
            continue
        r = 9 + 5 * (1 - ease_out(clamp01((lt - 0.45 - i * 0.34) / 0.45)))
        rect(base, cx - r, y - r, cx + r, y + r, CREAM if i < len(NODES) - 1 else RED, a)
        put(base, name, cx, y + 78, "sans-bold", 30, CREAM, a, align="center")
        put(base, sub, cx, y + 120, "note", 28, DIM, a, align="center")

    # travelling marker
    tp = clamp01((lt - 1.9) / 2.6)
    if tp > 0:
        mx = x0 + (x1 - x0) * ease_io(tp)
        rect(base, mx - 2, y - 34, mx + 2, y + 34, RED, 0.85)
        put(base, "you don't touch any of this", W / 2, 830, "note", 36, MUTED,
            clamp01((lt - 2.2) / 0.7), align="center")


# --------------------------------------------------------------------------
# 05 — countdown
# --------------------------------------------------------------------------
ITEMS = [
    ("05", "DATA STORIES", "charts that move"),
    ("04", "QUOTE CARDS", "one line, big type"),
    ("03", "COMPARISONS", "before / after"),
    ("02", "TIMELINES", "how it happened"),
    ("01", "DOODLE EXPLAINERS", "drawn by hand"),
]


def ch_countdown(base, lt):
    put(base, "Five you can post tonight", MARGIN, 250, "sans", 26, MUTED,
        clamp01((lt - 0.1) / 0.6))

    for i, (num, name, sub) in enumerate(ITEMS):
        start = 0.45 + i * 1.62
        a = clamp01((lt - start) / 0.5)
        if a <= 0:
            continue
        y = 372 + i * 126
        hi = i == len(ITEMS) - 1 and lt > start + 1.5
        col = CREAM if not hi else RED
        put(base, num, MARGIN, y, "sans-bold", 44, col, a * 0.9)
        put(base, name, MARGIN + 110, y, "sans-bold", 44, CREAM, a)
        put(base, sub, MARGIN + 110, y + 42, "sans", 24, DIM, a)
        # slide-in rule
        rw = 300 * ease_out(clamp01((lt - start) / 0.5))
        rect(base, W - MARGIN - rw, y - 12, W - MARGIN, y - 10, RULE, a * 0.8)


# --------------------------------------------------------------------------
# 06 — menu
# --------------------------------------------------------------------------
def ch_menu(base, lt):
    put(base, "Pick one.", W / 2, 392, "serif-bold", 116, CREAM,
        ease_out(clamp01((lt - 0.15) / 0.7)), align="center")
    put(base, "Give me a topic.", W / 2, 520, "serif-bold", 116, MUTED,
        ease_out(clamp01((lt - 0.42) / 0.7)), align="center")

    a = clamp01((lt - 0.95) / 0.8)
    if a > 0:
        w = 92 * ease_io(a)
        rect(base, W / 2 - w, 584, W / 2 + w, 586, RED, a)

    put(base, "doodle explainer  ·  data story  ·  quote card  ·  comparison  ·  timeline  ·  countdown",
        W / 2, 700, "note", 42, MUTED, clamp01((lt - 1.2) / 0.8), align="center")

    fa = clamp01((lt - 1.75) / 0.8)
    put(base, "1080p  ·  16:9 and 9:16  ·  ~3 minutes per render  ·  $0", W / 2, 800,
        "sans", 26, DIM, fa, align="center")
    put(base, "no GPU  ·  no API key  ·  no subscription", W / 2, 852,
        "sans", 26, DIM, fa * 0.85, align="center")


CH_FN = {"hook": ch_hook, "data": ch_data, "quote": ch_quote, "compare": ch_compare,
         "timeline": ch_timeline, "countdown": ch_countdown, "menu": ch_menu}


# --------------------------------------------------------------------------
def render_frame(t: float) -> np.ndarray:
    key = next((k for s, e, k in CH if s <= t < e), "menu")
    base = background(t, accent_for(key))

    start, end = next((s, e) for s, e, k in CH if k == key)
    CH_FN[key](base, t - start)

    # chapter-to-chapter dip so cuts feel authored
    for s, _, _ in CH[1:]:
        base = _fade(base, t, s)
    chrome(base, t, key)

    arr = np.asarray(base)[:, :, :3].astype(np.int16) + grain()
    fade = clamp01(t / 0.4) * clamp01((TOTAL - t) / 0.8)
    return np.clip(arr.astype(np.float32) * fade, 0, 255).astype(np.uint8)


def _fade(base, t, cut):
    """Brief dip to black around a chapter cut."""
    d = abs(t - cut)
    if d > 0.18:
        return base
    k = 1.0 - d / 0.18
    dark = Image.new("RGBA", base.size, (6, 6, 8, int(210 * k)))
    out = base.copy()
    out.alpha_composite(dark)
    return out


# --------------------------------------------------------------------------
# score: one soft pulse per chapter, pad underneath, tick on each cut
# --------------------------------------------------------------------------
SR = 44100


def score(duration: float) -> np.ndarray:
    n = int(duration * SR)
    t = np.arange(n) / SR
    L = np.zeros(n)
    R = np.zeros(n)

    for i, f0 in enumerate([110.0, 164.81, 220.0, 277.18]):
        for detune, pan in ((-0.1, 0.32), (0.1, 0.68)):
            lfo = 0.6 + 0.4 * np.sin(2 * np.pi * (0.027 + 0.007 * i) * t + i * 1.3)
            tone = np.sin(2 * np.pi * f0 * (1 + detune / 100) * t) + 0.16 * np.sin(2 * np.pi * 2 * f0 * t)
            amp = 0.026 * lfo
            L += amp * tone * math.cos(pan * math.pi / 2)
            R += amp * tone * math.sin(pan * math.pi / 2)

    # one soft hit + a short tick on every chapter cut
    for _, cut, _ in CH:
        if cut <= 0:
            continue
        start = int(cut * SR)
        seg = min(n - start, int(1.6 * SR))
        if seg <= 0:
            continue
        tt = np.arange(seg) / SR
        boom = 0.16 * np.sin(2 * np.pi * 52 * tt) * np.exp(-tt * 5.0)
        tick = 0.05 * np.sin(2 * np.pi * 1180 * tt) * np.exp(-tt * 90)
        L[start:start + seg] += boom + tick
        R[start:start + seg] += boom + tick

    mix = np.stack([L, R])
    mix /= max(1e-9, np.max(np.abs(mix)))
    mix = np.tanh(mix * 1.2) / math.tanh(1.2) * 0.7
    mix *= np.clip(t / 1.5, 0, 1) * np.clip((duration - t) / 2.5, 0, 1)
    return mix


def write_wav(path: Path, stereo: np.ndarray):
    data = (np.clip(stereo.T, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="video/out/faceless-format-reel.mp4")
    ap.add_argument("--stills", default="")
    ap.add_argument("--silent", action="store_true")
    ap.add_argument("--no-audio", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.stills:
        d = out.parent / "stills"
        d.mkdir(exist_ok=True)
        for s in [x.strip() for x in args.stills.split(",") if x.strip()]:
            Image.fromarray(render_frame(float(s))).save(d / f"reel_{float(s):05.2f}.png")
            print(f"  still @ {s}s")
        return

    print(f"rendering {TOTAL:.0f}s @ {W}x{H} {FPS}fps ({int(TOTAL * FPS)} frames)")
    silent = out.with_name("_silent.mp4")
    clip = VideoClip(render_frame, duration=TOTAL).with_fps(FPS)
    clip.write_videofile(str(silent), codec="libx264", audio=False, preset="medium",
                         ffmpeg_params=["-crf", "19", "-pix_fmt", "yuv420p"], logger=None)

    if args.no_audio:
        shutil.move(str(silent), str(out))
        print(f"done -> {out}  ({out.stat().st_size / 1e6:.1f} MB)")
        return

    wav = out.with_name("_score.wav")
    write_wav(wav, score(TOTAL))
    ff = shutil.which("ffmpeg")
    if not ff:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wav),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(out)], check=True)
    silent.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    print(f"done -> {out}  ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
