#!/usr/bin/env python3
"""
Project Alter Ego — 20 second vertical teaser, generated entirely from code.

Why this stack (all free / open source, CPU only):
  moviepy  (MIT)      -> clip assembly + H.264 encode (bundled ffmpeg)
  pillow   (MIT-CMU)  -> typography, compositing
  numpy    (BSD)      -> gradients, film grain, soundtrack synthesis

Nothing here needs a GPU, an API key, a browser, or an internet connection
at render time.

Usage
-----
  python video/generate_teaser.py                    # full render -> video/out
  python video/generate_teaser.py --stills 2.0,6.5   # preview PNG frames
  python video/generate_teaser.py --no-audio         # silent render

Copy is adapted from src/data.ts (FUTURE_SCENES) inside the app bundle.
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoClip

# --------------------------------------------------------------------------
# Canvas
# --------------------------------------------------------------------------
W, H = 1080, 1920
FPS = 30
DURATION = 20.0
MARGIN = 72

# Palette — matches the app: near-black, warm white, one muted grey ramp.
INK = (243, 240, 233)
MUTED = (128, 125, 117)
DIM = (78, 76, 70)
RULE = (46, 45, 41)

# Scene clock (seconds)
T1, T2, T3, T4, T5, TEND = 0.0, 4.2, 8.6, 13.2, 16.9, 20.0
SCENES = [(T1, T2, "01"), (T2, T3, "02"), (T3, T4, "03"), (T4, T5, "04"), (T5, TEND, "05")]

# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------
FONT_FILES = {
    "serif": "DejaVuSerif.ttf",
    "serif-bold": "DejaVuSerif-Bold.ttf",
    "sans": "DejaVuSans.ttf",
    "sans-bold": "DejaVuSans-Bold.ttf",
    "mono": "DejaVuSansMono.ttf",
    "mono-bold": "DejaVuSansMono-Bold.ttf",
}
FONT_DIRS = [
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/dejavu"),
    Path("/Library/Fonts"),
    Path.home() / "Library/Fonts",
    Path("C:/Windows/Fonts"),
]


def font_file(kind: str) -> str:
    name = FONT_FILES[kind]
    for d in FONT_DIRS:
        p = d / name
        if p.exists():
            return str(p)
    raise FileNotFoundError(
        f"{name} not found. Install the DejaVu fonts or edit FONT_DIRS/PATHS."
    )


_fonts: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def get_font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    key = (kind, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(font_file(kind), size)
    return _fonts[key]


# --------------------------------------------------------------------------
# Sprites (cached glyph runs, baseline aligned)
# --------------------------------------------------------------------------
class Sprite:
    __slots__ = ("img", "x_off", "y_off", "advance", "alpha_cache")

    def __init__(self, img, x_off, y_off, advance):
        self.img = img
        self.x_off = x_off
        self.y_off = y_off
        self.advance = advance
        self.alpha_cache: dict[float, Image.Image] = {}

    def at_alpha(self, a: float) -> Image.Image:
        q = round(a * 32) / 32
        if q >= 1.0:
            return self.img
        if q not in self.alpha_cache:
            im = self.img.copy()
            im.putalpha(im.getchannel("A").point(lambda v: int(v * q)))
            self.alpha_cache[q] = im
        return self.alpha_cache[q]


_sprites: dict[tuple, Sprite] = {}


def sprite(text: str, kind: str, size: int, color, tracking: float = 0.0) -> Sprite:
    key = (text, kind, size, color, tracking)
    if key in _sprites:
        return _sprites[key]

    f = get_font(kind, size)
    ascent, descent = f.getmetrics()
    pad = 8

    if tracking:
        widths = [f.getlength(ch) for ch in text]
        total = sum(widths) + tracking * max(0, len(text) - 1)
    else:
        widths = [f.getlength(text)]
        total = widths[0]

    img = Image.new("RGBA", (max(1, int(math.ceil(total)) + 2 * pad), ascent + descent + 2 * pad),
                    (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    baseline = pad + ascent

    if tracking:
        x = pad
        for ch, wd in zip(text, widths):
            d.text((x, baseline), ch, font=f, fill=color, anchor="ls")
            x += wd + tracking
    else:
        d.text((pad, baseline), text, font=f, fill=color, anchor="ls")

    bbox = img.getbbox()
    if bbox is None:
        sp = Sprite(Image.new("RGBA", (1, 1)), 0, 0, total)
    else:
        sp = Sprite(img.crop(bbox), bbox[0] - pad, bbox[1] - baseline, total)

    _sprites[key] = sp
    return sp


def blit(base: Image.Image, sp: Sprite, x: float, baseline: float, alpha: float = 1.0):
    if alpha <= 0.01:
        return
    base.alpha_composite(sp.at_alpha(min(alpha, 1.0)),
                         (int(round(x + sp.x_off)), int(round(baseline + sp.y_off))))


# --------------------------------------------------------------------------
# Small drawing helpers
# --------------------------------------------------------------------------
def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ease_out(p: float) -> float:
    return 1.0 - (1.0 - p) ** 3


def ease_in_out(p: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * clamp01(p))


def text_width(words, kind: str, size: int) -> float:
    f = get_font(kind, size)
    return sum(f.getlength(w) for w in words) + f.getlength(" ") * (len(words) - 1)


def fit(words, kind: str, size: int, max_w: float = W - 2 * MARGIN) -> int:
    while size > 16 and text_width(words, kind, size) > max_w:
        size -= 2
    return size


def draw_line(base, t, t0, words, kind, size, baseline, color,
              stagger=0.06, dur=0.5, rise=18.0, align="center", x=None,
              alpha=1.0, fade_start=None, fade_dur=0.5):
    """Word-by-word reveal. Layout is computed once so words never reflow."""
    if t < t0:
        return
    f = get_font(kind, size)
    space = f.getlength(" ")
    total = text_width(words, kind, size)

    if align == "center":
        cursor = (W - total) / 2.0
    elif align == "right":
        cursor = (x if x is not None else W - MARGIN) - total
    else:
        cursor = x if x is not None else MARGIN

    for i, word in enumerate(words):
        p = clamp01((t - (t0 + i * stagger)) / dur)
        advance = f.getlength(word)
        if p > 0:
            e = ease_out(p)
            a = alpha * e
            if fade_start is not None:
                a *= 1.0 - clamp01((t - fade_start) / fade_dur)
            blit(base, sprite(word, kind, size, color), cursor, baseline + rise * (1.0 - e), a)
        cursor += advance + space


def draw_tracked(base, text, x, baseline, size=18, color=MUTED, tracking=5,
                 alpha=1.0, align="left"):
    if alpha <= 0.01:
        return
    sp = sprite(text, "mono", size, color, tracking=tracking)
    if align == "center":
        x -= sp.advance / 2.0
    elif align == "right":
        x -= sp.advance
    blit(base, sp, x, baseline, alpha)


def rect(base, x0, y0, x1, y1, color, alpha=1.0):
    w, h = int(round(x1 - x0)), int(round(y1 - y0))
    if w <= 0 or h <= 0 or alpha <= 0.01:
        return
    layer = Image.new("RGBA", (w, h), tuple(color) + (int(255 * alpha),))
    base.alpha_composite(layer, (int(round(x0)), int(round(y0))))


def ring(base, cx, cy, r, color, alpha=1.0, width=2):
    if alpha <= 0.01 or r <= 1:
        return
    size = int(2 * r + 8)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse((4, 4, size - 4, size - 4), outline=tuple(color) + (int(255 * alpha),), width=width)
    base.alpha_composite(layer, (int(cx - size / 2), int(cy - size / 2)))


# --------------------------------------------------------------------------
# Background — low-res drifting gradient, upscaled (cheap + buttery smooth)
# --------------------------------------------------------------------------
LW, LH = 270, 480
_yy, _xx = np.mgrid[0:LH, 0:LW].astype(np.float32)

_nx = (_xx / LW - 0.5) * 2.0
_ny = (_yy / LH - 0.5) * 2.0
_VIGNETTE = np.clip(1.0 - 0.46 * np.clip(_nx ** 2 * 0.55 + _ny ** 2 * 0.95, 0, 1.7) ** 1.15,
                    0.20, 1.0).astype(np.float32)


def background(t: float) -> Image.Image:
    c1x = LW * (0.30 + 0.24 * math.sin(0.19 * t))
    c1y = LH * (0.28 + 0.10 * math.cos(0.15 * t + 0.6))
    c2x = LW * (0.74 + 0.16 * math.cos(0.12 * t + 1.1))
    c2y = LH * (0.76 + 0.12 * math.sin(0.10 * t))

    s1, s2 = LW * 0.52, LW * 0.60
    g1 = np.exp(-((( _xx - c1x) ** 2 + (_yy - c1y) ** 2) / (2 * s1 * s1))).astype(np.float32)
    g2 = np.exp(-((( _xx - c2x) ** 2 + (_yy - c2y) ** 2) / (2 * s2 * s2))).astype(np.float32)

    flicker = 1.0 + 0.030 * math.sin(t * 6.7) + 0.018 * math.sin(t * 2.1 + 1.3)

    r = 5.0 + 26.0 * g1 + 9.0 * g2
    g = 6.0 + 18.0 * g1 + 12.0 * g2
    b = 9.0 + 11.0 * g1 + 26.0 * g2

    arr = np.stack([r, g, b], axis=-1) * _VIGNETTE[..., None] * flicker
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    return img.convert("RGBA")


_rng = np.random.default_rng(20260609)


def grain() -> np.ndarray:
    n = _rng.integers(-4, 5, size=(LH // 2, LW // 2), dtype=np.int16)
    up = Image.fromarray((n + 128).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    return (np.asarray(up, dtype=np.int16) - 128)[:, :, None]


# --------------------------------------------------------------------------
# Scenes
# --------------------------------------------------------------------------
def scene_one(base, t):
    lt = t - T1
    a_in = clamp01((lt - 0.35) / 0.7)
    draw_tracked(base, "TUESDAY — 8:32 AM", W / 2, 700, 22, MUTED, 5, a_in, align="center")

    draw_line(base, lt, 0.95, ["You", "buy", "coffee."], "serif-bold",
              fit(["You", "buy", "coffee."], "serif-bold", 104), 890, INK,
              stagger=0.09, rise=22)

    size2 = fit(["No", "hesitation."], "serif", 56)
    draw_line(base, lt, 1.95, ["No", "hesitation."], "serif", size2, 1022, MUTED, stagger=0.07)
    size3 = fit(["No", "checking", "your", "account", "first."], "serif", 56)
    draw_line(base, lt, 2.9, ["No", "checking", "your", "account", "first."], "serif",
              size3, 1136, MUTED, stagger=0.06)


def scene_two(base, t):
    lt = t - T2
    a_in = clamp01((lt - 0.25) / 0.7)
    draw_tracked(base, "HALFWAY THROUGH THE WALK", W / 2, 690, 20, MUTED, 6, a_in, align="center")

    size1 = fit(["It", "hits", "you."], "serif-bold", 96)
    draw_line(base, lt, 0.55, ["It", "hits", "you."], "serif-bold", size1, 850, INK,
              stagger=0.10, rise=20)

    # a quiet rule that draws itself between the two statements
    p = clamp01((lt - 1.15) / 0.9)
    if p > 0:
        w = 132 * ease_in_out(p)
        rect(base, W / 2 - w, 936, W / 2 + w, 938, RULE, 1.0)

    size2 = fit(["things", "changed."], "serif-bold", 120)
    draw_line(base, lt, 1.85, ["things", "changed."], "serif-bold", size2, 1105, INK,
              stagger=0.16, rise=28)


def scene_three(base, t):
    lt = t - T3
    a_in = clamp01((lt - 0.25) / 0.7)
    draw_tracked(base, "SATURDAY — 10:14 PM", W / 2, 650, 22, MUTED, 5, a_in, align="center")

    s1 = fit(["“Wait…"], "serif", 86)
    draw_line(base, lt, 0.55, ["“Wait…"], "serif", s1, 828, INK, stagger=0.0, rise=18)
    s2 = fit(["he", "actually", "made", "this?”"], "serif", 86)
    draw_line(base, lt, 0.95, ["he", "actually", "made", "this?”"], "serif", s2, 930, INK,
              stagger=0.08, rise=18)

    p = clamp01((lt - 1.75) / 0.9)
    if p > 0:
        w = 96 * ease_in_out(p)
        rect(base, W / 2 - w, 1012, W / 2 + w, 1014, RULE, 1.0)

    draw_line(base, lt, 2.15, ["You", "pretend", "not", "to", "hear."], "mono",
              fit(["You", "pretend", "not", "to", "hear."], "mono", 30), 1108, MUTED,
              stagger=0.06, rise=12)
    s3 = fit(["But", "you", "do."], "serif-bold", 72)
    draw_line(base, lt, 3.05, ["But", "you", "do."], "serif-bold", s3, 1206, INK,
              stagger=0.12, rise=20)


def scene_four(base, t):
    lt = t - T4
    a_in = clamp01((lt - 0.25) / 0.7)
    draw_tracked(base, "THURSDAY — 11:42 PM", W / 2, 656, 22, MUTED, 5, a_in, align="center")

    s1 = fit(["You", "find", "the", "dusty", "notebook"], "serif", 60)
    draw_line(base, lt, 0.5, ["You", "find", "the", "dusty", "notebook"], "serif", s1,
              812, MUTED, stagger=0.06, rise=14)
    s2 = fit(["where", "you", "wrote", "the", "original", "idea."], "serif", 60)
    draw_line(base, lt, 0.95, ["where", "you", "wrote", "the", "original", "idea."], "serif",
              s2, 896, MUTED, stagger=0.05, rise=14)

    size = fit(["You", "didn't", "quit."], "serif-bold", 114)
    draw_line(base, lt, 1.75, ["You", "didn't", "quit."], "serif-bold", size, 1090, INK,
              stagger=0.16, rise=28)


def scene_five(base, t):
    lt = t - T5
    a_in = clamp01((lt - 0.15) / 0.8)

    # monogram
    r = 58 + 34 * ease_out(clamp01((lt - 0.1) / 0.95))
    ring(base, W / 2, 772, r, DIM, alpha=a_in * 0.95, width=2)
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        cx, cy = W / 2 + dx * (r + 16), 772 + dy * (r + 16)
        rect(base, cx - 1, cy - 1, cx + 1, cy + 1, DIM, a_in * 0.9)

    blit(base, sprite("AE", "serif-bold", 76, INK), W / 2 - get_font("serif-bold", 76).getlength("AE") / 2,
         772 + 26, a_in)

    # wordmark
    draw_tracked(base, "ALTER EGO", W / 2, 1018, 58, INK, 16,
                 clamp01((lt - 0.55) / 0.8), align="center")
    draw_tracked(base, "YOUR FUTURE SELF, CHECKING IN.", W / 2, 1092, 21, MUTED, 5,
                 clamp01((lt - 0.9) / 0.8), align="center")

    # footer
    a_foot = clamp01((lt - 1.25) / 0.8)
    rect(base, MARGIN, 1712, MARGIN + (W - 2 * MARGIN) * ease_in_out(a_foot), 1714, RULE, a_foot)
    draw_tracked(base, "MVP PROTOTYPE — 2026", W / 2, 1772, 18, MUTED, 5, a_foot, align="center")


SCENE_FN = [scene_one, scene_two, scene_three, scene_four, scene_five]


# --------------------------------------------------------------------------
# Persistent chrome
# --------------------------------------------------------------------------
def overlays(base, t):
    ls, le, idx = next(((s, e, i) for s, e, i in SCENES if s <= t < e), (T5, TEND, "05"))
    a = clamp01((t - 0.45) / 0.9) * (1.0 - clamp01((t - 16.45) / 0.45))
    draw_tracked(base, "PROJECT ALTER EGO", MARGIN, 104, 17, MUTED, 5, a)
    if idx != "05":
        draw_tracked(base, f"{idx} / 04", W - MARGIN, 104, 17, MUTED, 4, a, align="right")
        p = clamp01((t - ls) / 0.85)
        rect(base, MARGIN, 1806, MARGIN + (W - 2 * MARGIN) * ease_out(p), 1808, RULE, a)


# --------------------------------------------------------------------------
# Frame renderer
# --------------------------------------------------------------------------
def render_frame(t: float) -> np.ndarray:
    base = background(t)

    for (start, end, _), fn in zip(SCENES, SCENE_FN):
        if start <= t < end:
            fn(base, t)
            break
    overlays(base, t)

    arr = np.asarray(base)[:, :, :3].astype(np.int16) + grain()

    fade = clamp01(t / 0.35) * clamp01((DURATION - t) / 0.75)
    arr = arr.astype(np.float32) * fade

    return np.clip(arr, 0, 255).astype(np.uint8)


# --------------------------------------------------------------------------
# Soundtrack — a slow Am pad, a noise bed, and one sub hit per scene
# --------------------------------------------------------------------------
SR = 44100


def make_score() -> np.ndarray:
    n = int(DURATION * SR)
    t = np.arange(n, dtype=np.float64) / SR
    L = np.zeros(n, dtype=np.float64)
    R = np.zeros(n, dtype=np.float64)

    # sustained pad (A minor add9, spread across the stereo field)
    for i, f0 in enumerate([110.0, 164.81, 220.0, 261.63, 329.63]):
        for detune, pan in ((-0.16, 0.28), (0.16, 0.72)):
            freq = f0 * (1.0 + detune / 100.0)
            lfo = 0.55 + 0.45 * np.sin(2 * np.pi * (0.043 + 0.011 * i) * t + i * 1.7)
            tone = (np.sin(2 * np.pi * freq * t + 0.15 * np.sin(2 * np.pi * 0.07 * t))
                    + 0.22 * np.sin(2 * np.pi * 2 * freq * t)
                    + 0.06 * np.sin(2 * np.pi * 3 * freq * t))
            amp = 0.052 * lfo * (1.0 if i == 0 else 0.8)
            L += amp * tone * math.cos(pan * math.pi / 2)
            R += amp * tone * math.sin(pan * math.pi / 2)

    # air / tape bed, band-limited noise via FFT
    rng = np.random.default_rng(11)
    nz = rng.standard_normal(n)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    bed = np.fft.irfft(np.fft.rfft(nz) / (1.0 + (freqs / 480.0) ** 4), n)
    bed /= max(1e-9, np.max(np.abs(bed)))
    swell = 0.020 * bed * np.clip((t - 2.2) / 6.0, 0, 1) * np.clip((DURATION - 1.2 - t) / 4.0, 0, 1)
    L += swell
    R += np.roll(swell, 313)

    # sub hit on every scene cut
    for hit in (0.10, T2, T3, T4, T5):
        tt = t - hit
        env = np.where(tt >= 0, np.exp(-np.clip(tt, 0, None) * 3.1), 0.0)
        boom = 0.30 * np.sin(2 * np.pi * 44 * tt + 0.4 * np.sin(2 * np.pi * 5 * tt)) * env
        L += boom
        R += boom

    mix = np.stack([L, R])
    mix /= max(1e-9, np.max(np.abs(mix)))
    mix = np.tanh(mix * 1.25) / math.tanh(1.25) * 0.82
    mix *= np.clip(t / 1.8, 0, 1) * np.clip((DURATION - t) / 2.6, 0, 1)
    return mix


def write_wav(path: Path, stereo: np.ndarray):
    data = (np.clip(stereo.T, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def render_stills(stamps, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    for s in stamps:
        Image.fromarray(render_frame(float(s))).save(out_dir / f"still_{float(s):05.2f}.png")
        print(f"  still @ {s}s")


def main():
    ap = argparse.ArgumentParser(description="Generate the Project Alter Ego teaser.")
    ap.add_argument("--out", default="video/out/alter_ego_teaser.mp4")
    ap.add_argument("--stills", default="", help="comma separated timestamps -> PNG only")
    ap.add_argument("--no-audio", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.stills:
        render_stills([s.strip() for s in args.stills.split(",") if s.strip()], out.parent / "stills")
        return

    silent = out.with_name("_silent.mp4")
    print(f"rendering {DURATION:.0f}s @ {W}x{H}, {FPS}fps ({int(DURATION * FPS)} frames)")

    clip = VideoClip(render_frame, duration=DURATION).with_fps(FPS)
    clip.write_videofile(str(silent), codec="libx264", audio=False,
                         preset="medium", ffmpeg_params=["-crf", "19", "-pix_fmt", "yuv420p"],
                         logger=None)
    print(f"  video  -> {silent}")

    if args.no_audio:
        shutil.move(str(silent), str(out))
        print(f"done -> {out}")
        return

    wav = out.with_name("_score.wav")
    write_wav(wav, make_score())
    print(f"  score  -> {wav}")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            sys.exit("ffmpeg not found. `pip install imageio-ffmpeg` or install ffmpeg.")

    subprocess.run([ffmpeg, "-y", "-loglevel", "error",
                    "-i", str(silent), "-i", str(wav),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", str(out)], check=True)

    silent.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    print(f"done -> {out}  ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
