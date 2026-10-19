"""
doodle.py — a tiny "hand-drawn" vector-ish drawing kit on top of Pillow.

Everything is drawn on a 2x supersampled RGBA sheet and downsampled on save,
so strokes are smooth without any anti-alias trickery.

The look is deliberately naive: every line is drawn twice with a slow random
wobble, glyphs are placed one at a time with a little rotation and baseline
drift, and shading is done with loose hatching. That is what separates a
"doodle explainer" frame from clean vector art.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------------------------------
# Palette (warm paper, graphite ink, three muted accents)
# --------------------------------------------------------------------------
PAPER = (245, 235, 215)
INK = (58, 55, 50)
INK_SOFT = (104, 100, 91)
INK_FAINT = (150, 145, 133)
RED = (194, 84, 72)
ORANGE = (214, 137, 72)
BLUE = (84, 120, 162)
GREEN = (108, 138, 104)

FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONTS = {
    "hand": "Caveat_700Bold.ttf",
    "note": "PatrickHand_400Regular.ttf",
}

_SS = 2  # supersample factor
_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def _font(name: str, px: int) -> ImageFont.FreeTypeFont:
    key = (name, px)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(str(FONT_DIR / FONTS[name]), px)
    return _font_cache[key]


def mix(c1, c2, t: float):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3))


def _dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def catmull(points, steps: int = 14):
    """Smooth a control polygon into a dense polyline."""
    if len(points) < 3:
        return [tuple(p) for p in points]
    pts = [points[0]] + [tuple(p) for p in points] + [points[-1]]
    out = []
    for i in range(len(pts) - 3):
        p0, p1, p2, p3 = pts[i], pts[i + 1], pts[i + 2], pts[i + 3]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append((
                0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
            ))
    out.append(tuple(points[-1]))
    return out


def wobble(points, amp: float, rng: random.Random):
    """Displace a polyline along its normal with slow, layered sine noise."""
    n = len(points)
    if n < 2 or amp <= 0:
        return list(points)

    length = sum(_dist(points[i], points[i + 1]) for i in range(n - 1)) or 1.0
    waves = [(rng.uniform(0, math.tau), rng.uniform(0.6, 2.2), rng.uniform(0.5, 1.5))
             for _ in range(3)]

    out, walked = [], 0.0
    for i, (x, y) in enumerate(points):
        if i:
            walked += _dist(points[i - 1], points[i])
        if i < n - 1:
            tx, ty = points[i + 1][0] - x, points[i + 1][1] - y
        else:
            tx, ty = x - points[i - 1][0], y - points[i - 1][1]
        ln = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / ln, tx / ln
        u = walked / length
        d = sum(math.sin(math.tau * u * w[1] + w[0]) * w[2] for w in waves) / 2.6
        out.append((x + nx * amp * d, y + ny * amp * d))
    return out


class Sheet:
    """A drawing surface. Coordinates are in final-image pixels."""

    def __init__(self, w: int, h: int, paper=PAPER, seed: int = 7):
        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w * _SS, h * _SS), tuple(paper) + (255,))
        self.d = ImageDraw.Draw(self.img)
        self.rng = random.Random(seed)

    # ---------------------------------------------------------------- strokes
    def stroke(self, pts, width=3.0, color=INK, rough=1.0, passes=2, smooth=True):
        if len(pts) < 2:
            return
        base = catmull(pts) if smooth and len(pts) > 2 else [tuple(p) for p in pts]
        for k in range(passes):
            amp = rough * (0.85 if k == 0 else 1.7)
            path = [(x * _SS, y * _SS) for x, y in wobble(base, amp, self.rng)]
            w = max(1, int(round(width * _SS * (1.0 if k == 0 else 0.7))))
            c = color if k == 0 else mix(color, PAPER, 0.30)
            self.d.line(path, fill=c + (255,), width=w, joint="curve")
            if k == 0:  # round caps
                r = w / 2.0
                for px, py in (path[0], path[-1]):
                    self.d.ellipse([px - r, py - r, px + r, py + r], fill=c + (255,))

    def line(self, a, b, **kw):
        self.stroke([a, b], smooth=False, **kw)

    def circle(self, c, r, **kw):
        self.ellipse(c, r, r, **kw)

    def ellipse(self, c, rx, ry, ry2=None, start=0.0, end=math.tau, **kw):
        if ry2 is not None:  # allow (cx, cy), rx, ry, rot-ish call style
            end = ry2
        n = max(24, int((abs(end - start) / math.tau) * 64))
        pts = []
        for i in range(n + 1):
            a = start + (end - start) * i / n
            pts.append((c[0] + math.cos(a) * rx, c[1] + math.sin(a) * ry))
        kw.setdefault("smooth", False)
        self.stroke(pts, **kw)

    def rounded_rect(self, x0, y0, x1, y1, r=18, **kw):
        pts = []
        for cx, cy, a0 in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0.0),
                           (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
            for i in range(9):
                a = a0 + (math.pi / 2) * i / 8
                pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        pts.append(pts[0])
        kw.setdefault("smooth", False)
        self.stroke(pts, **kw)

    def hatch(self, poly, spacing=16.0, angle=55.0, width=1.8, color=INK_FAINT, rough=0.7):
        """Loose parallel hatching clipped to a polygon."""
        mask = Image.new("L", self.img.size, 0)
        ImageDraw.Draw(mask).polygon([(x * _SS, y * _SS) for x, y in poly], fill=255)

        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        a = math.radians(angle)
        dx, dy = math.cos(a), math.sin(a)
        nx, ny = -dy, dx

        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        span = max(max(xs) - min(xs), max(ys) - min(ys)) + spacing * 2
        steps = int(span / spacing) + 2

        for i in range(-steps, steps + 1):
            ox, oy = cx + nx * i * spacing, cy + ny * i * spacing
            p0 = ((ox - dx * span) * _SS, (oy - dy * span) * _SS)
            p1 = ((ox + dx * span) * _SS, (oy + dy * span) * _SS)
            ld.line([p0, p1], fill=tuple(color) + (255,), width=max(1, int(width * _SS)))

        self.img.paste(layer, (0, 0), Image.composite(layer, Image.new("RGBA", layer.size), mask))
        self.d = ImageDraw.Draw(self.img)

    def fill(self, poly, color, alpha=255):
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).polygon([(x * _SS, y * _SS) for x, y in poly],
                                      fill=tuple(color) + (alpha,))
        self.img.alpha_composite(layer)
        self.d = ImageDraw.Draw(self.img)

    def dot(self, c, r=3.0, color=INK):
        r *= _SS
        self.d.ellipse([c[0] * _SS - r, c[1] * _SS - r, c[0] * _SS + r, c[1] * _SS + r],
                       fill=tuple(color) + (255,))

    # ------------------------------------------------------------------ text
    def text(self, s, xy, size=72, color=INK, font="hand", jitter=1.0, rot=1.4,
             spacing=0.0, alpha=255):
        """Hand-lettered text: per-glyph rotation + baseline drift."""
        f = _font(font, int(size * _SS))
        asc, desc = f.getmetrics()
        x, y = xy

        for i, ch in enumerate(s):
            adv = f.getlength(ch) / _SS
            if ch == " ":
                x += adv
                continue

            pad = int(size * 0.4 * _SS)
            tw = int(adv) + 2 * pad
            th = asc + desc + 2 * pad
            tile = Image.new("RGBA", (max(tw, 2), max(th, 2)), (0, 0, 0, 0))
            ImageDraw.Draw(tile).text((pad, pad + asc), ch, font=f,
                                      fill=tuple(color) + (alpha,), anchor="ls")
            ang = self.rng.uniform(-rot, rot) if jitter else 0.0
            if ang:
                tile = tile.rotate(ang, resample=Image.BICUBIC)
            drift = self.rng.uniform(-1.6, 1.6) * (size / 90.0) * jitter
            bob = math.sin(i * 0.9) * 1.1 * jitter
            # tile baseline sits at (pad + asc); shift up by asc so it lands on y
            self.img.alpha_composite(
                tile, (int(x * _SS - pad), int((y + drift + bob) * _SS - pad - asc)))
            x += adv + spacing * size

        self.d = ImageDraw.Draw(self.img)
        return x

    def text_width(self, s, size, font="hand", spacing=0.0):
        f = _font(font, int(size * _SS))
        return sum(f.getlength(c) / _SS for c in s) + spacing * size * max(0, len(s) - 1)

    def text_center(self, s, cx, y, size, **kw):
        self.text(s, (cx - self.text_width(s, size, kw.get("font", "hand"),
                                           kw.get("spacing", 0.0)) / 2, y), size, **kw)

    # ------------------------------------------------------------------ save
    def save(self, path):
        out = self.img.convert("RGB").resize((self.w, self.h), Image.LANCZOS)
        out.save(path, quality=95)
        return path


# --------------------------------------------------------------------------
# Reusable doodle objects
# --------------------------------------------------------------------------
def steam(s: Sheet, x, y, height=110, spread=34, color=ORANGE, width=3.4):
    s.stroke([(x, y), (x - spread, y - height * 0.35), (x + spread * 0.6, y - height * 0.65),
              (x - spread * 0.4, y - height)], width=width, color=color, rough=1.2)
    s.stroke([(x + spread * 1.5, y - 6), (x + spread * 0.7, y - height * 0.4),
              (x + spread * 1.6, y - height * 0.75)], width=width * 0.8,
             color=mix(color, PAPER, 0.25), rough=1.2)


def cup(s: Sheet, cx, base_y, width=150, accent=ORANGE, steam_on=True):
    """A takeaway coffee cup: tapered body, lid, sleeve band, steam."""
    h = width * 1.12
    top_y = base_y - h
    ht, hb = width * 0.5, width * 0.37

    def half_at(u):  # u: 0 at rim, 1 at base
        return ht + (hb - ht) * u

    s.stroke([(cx - ht, top_y), (cx - hb, base_y), (cx + hb, base_y),
              (cx + ht, top_y)], width=3.6, rough=1.0)
    s.ellipse((cx, top_y), ht, ht * 0.24, width=3.2, rough=0.9)
    s.ellipse((cx, base_y), hb, hb * 0.22, width=3.0, rough=0.9)

    # sleeve: two horizontals clamped to the taper, plus a soft tint
    u0, u1 = 0.34, 0.56
    y0, y1 = top_y + h * u0, top_y + h * u1
    w0, w1 = half_at(u0) + 5, half_at(u1) + 5
    s.stroke([(cx - w0, y0), (cx + w0, y0)], width=2.6, color=INK_SOFT, rough=0.9)
    s.stroke([(cx - w1, y1), (cx + w1, y1)], width=2.6, color=INK_SOFT, rough=0.9)
    s.fill([(cx - w0, y0), (cx + w0, y0), (cx + w1, y1), (cx - w1, y1)], accent, alpha=58)

    # lid
    lid_h = h * 0.13
    s.stroke([(cx - ht - 8, top_y - 2), (cx - ht - 5, top_y - lid_h),
              (cx + ht + 5, top_y - lid_h), (cx + ht + 8, top_y - 2)],
             width=3.0, rough=0.9)
    s.stroke([(cx - ht - 5, top_y - lid_h), (cx + ht + 5, top_y - lid_h)], width=3.2, rough=0.8)
    s.stroke([(cx - 12, top_y - lid_h - 9), (cx + 12, top_y - lid_h - 9)], width=2.8, rough=0.8)

    if steam_on:
        steam(s, cx - 4, top_y - lid_h - 22, height=h * 0.62, spread=20)
    return top_y


def notebook(s: Sheet, cx, cy, w=460, accent=BLUE):
    """Open notebook, straight-on: two pages, spine, ruled lines, pencil."""
    h = w * 0.66
    left, right = cx - w / 2, cx + w / 2
    top, bot = cy - h / 2, cy + h / 2
    mid = cx

    # page block outline — square corners (no smoothing, or it reads as a leaf)
    outline = [(left, top + 10), (mid - 10, top), (mid, top + 14), (mid + 10, top),
               (right, top + 10), (right, bot - 10), (mid + 10, bot), (mid, bot - 14),
               (mid - 10, bot), (left, bot - 10), (left, top + 10)]
    s.stroke(outline, width=3.8, rough=0.7, smooth=False)
    # page stack thickness along the bottom
    s.stroke([(left, bot - 10), (left + 4, bot + 6), (mid, bot + 2), (right - 4, bot + 6),
              (right, bot - 10)], width=2.4, color=INK_SOFT, rough=0.6, smooth=False)
    # spine
    s.stroke([(mid, top + 14), (mid, bot - 14)], width=3.2, color=INK_SOFT, rough=0.5, smooth=False)

    # ruled lines, full page width
    for i in range(4):
        y = top + 56 + i * 36
        s.stroke([(left + 30, y), (mid - 26, y)], width=1.9, color=INK_FAINT, rough=0.5, smooth=False)
        s.stroke([(mid + 26, y), (right - 30, y)], width=1.9, color=INK_FAINT, rough=0.5, smooth=False)

    # lightbulb doodle on the right page
    bx, by, br = mid + w * 0.19, cy + h * 0.03, w * 0.075
    s.circle((bx, by), br, width=3.0, color=INK_SOFT, rough=0.8)
    s.stroke([(bx - br * 0.42, by + br * 1.06), (bx + br * 0.42, by + br * 1.06)],
             width=2.6, color=INK_SOFT, smooth=False)
    s.stroke([(bx - br * 0.30, by + br * 1.34), (bx + br * 0.30, by + br * 1.34)],
             width=2.2, color=INK_SOFT, smooth=False)
    for a in (-0.85, 0.0, 0.85):
        s.stroke([(bx + math.sin(a) * br * 1.45, by - math.cos(a) * br * 1.45),
                  (bx + math.sin(a) * br * 1.85, by - math.cos(a) * br * 1.85)],
                 width=2.2, color=ORANGE, rough=0.4, smooth=False)

    # pencil lying on the left page
    px, py = left + w * 0.10, cy + h * 0.22
    s.stroke([(px, py + 26), (px + w * 0.26, py - 14)], width=3.0, rough=0.6, smooth=False)
    s.stroke([(px, py + 40), (px + w * 0.26, py)], width=3.0, rough=0.6, smooth=False)
    s.stroke([(px + w * 0.26, py - 14), (px + w * 0.32, py - 6), (px + w * 0.26, py)],
             width=2.4, color=accent, rough=0.5, smooth=False)


def person(s: Sheet, cx, feet, height=560, arm="down", accent=None, colour=INK):
    """A faceless doodle figure. arm in {down, hold, point, up}; returns the hand point."""
    r = height * 0.095
    head_cy = feet - height + r * 1.12
    neck_y = head_cy + r * 1.00
    sh_y = neck_y + height * 0.045
    hip_y = feet - height * 0.40
    sw = height * 0.125

    # head — no face, by design
    s.ellipse((cx, head_cy), r * 0.95, r, width=3.6, color=colour, rough=0.9)
    # a single soft hair arc
    s.stroke([(cx - r * 0.80, head_cy - r * 0.30), (cx - r * 0.45, head_cy - r * 1.02),
              (cx + r * 0.10, head_cy - r * 1.10), (cx + r * 0.62, head_cy - r * 0.92),
              (cx + r * 0.86, head_cy - r * 0.22)], width=2.8, color=colour, rough=1.0)

    # neck
    s.stroke([(cx - r * 0.28, neck_y - 8), (cx - r * 0.28, sh_y)], width=3.0, color=colour)
    s.stroke([(cx + r * 0.28, neck_y - 8), (cx + r * 0.28, sh_y)], width=3.0, color=colour)

    # coat: one closed polygon, filled then stroked, so the tint always fits
    sh_l, sh_r = cx - sw, cx + sw
    hip_l, hip_r = cx - sw * 0.90, cx + sw * 0.90
    coat = [(sh_l, sh_y + 6), (sh_l + sw * 0.42, sh_y - height * 0.012),
            (cx, sh_y - height * 0.026), (sh_r - sw * 0.42, sh_y - height * 0.012),
            (sh_r, sh_y + 6), (hip_r, hip_y), (hip_l, hip_y)]
    if accent:
        s.fill(coat, accent, alpha=44)
    s.stroke(coat + [coat[0]], width=3.6, color=colour, rough=0.9, smooth=False)

    # legs
    for side in (-1, 1):
        hip_x = cx + side * sw * 0.40
        foot_x = cx + side * sw * 0.52
        s.stroke([(hip_x, hip_y - 2), (foot_x, feet - 16), (foot_x, feet)],
                 width=3.2, color=colour, rough=0.9)
        s.stroke([(foot_x - 17, feet + 2), (foot_x + 19, feet + 2)], width=3.0,
                 color=colour, rough=0.8)

    # arms
    hand = None
    if arm == "hold":
        s.stroke([(sh_l, sh_y + 10), (sh_l - height * 0.045, hip_y - height * 0.07),
                  (sh_l + sw * 0.42, hip_y + height * 0.01)], width=3.2, color=colour, rough=0.9)
        hand = (sh_r + height * 0.105, sh_y + height * 0.235)
        s.stroke([(sh_r, sh_y + 10), (sh_r + height * 0.075, sh_y + height * 0.115), hand],
                 width=3.2, color=colour, rough=0.9)
    elif arm == "point":
        s.stroke([(sh_l, sh_y + 10), (sh_l - height * 0.04, hip_y - height * 0.06),
                  (sh_l + sw * 0.40, hip_y + height * 0.01)], width=3.2, color=colour, rough=0.9)
        hand = (sh_r + height * 0.20, sh_y + height * 0.015)
        s.stroke([(sh_r, sh_y + 10), (sh_r + height * 0.10, sh_y + height * 0.03), hand],
                 width=3.2, color=colour, rough=0.9)
    elif arm == "up":
        s.stroke([(sh_l, sh_y + 10), (sh_l - height * 0.05, hip_y - height * 0.05),
                  (sh_l + sw * 0.40, hip_y + height * 0.01)], width=3.2, color=colour, rough=0.9)
        hand = (sh_r + height * 0.075, sh_y - height * 0.20)
        s.stroke([(sh_r, sh_y + 10), (sh_r + height * 0.075, sh_y - height * 0.09), hand],
                 width=3.2, color=colour, rough=0.9)
    else:
        for side in (-1, 1):
            shx = cx + side * sw
            s.stroke([(shx, sh_y + 10), (shx + side * height * 0.045, hip_y - height * 0.06),
                      (shx + side * sw * 0.28, hip_y + height * 0.02)],
                     width=3.2, color=colour, rough=0.9)
    return hand


def speech_bubble(s: Sheet, cx, cy, w, h, tail_to, accent=RED):
    r = min(w, h) * 0.28
    s.rounded_rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, r=r, width=3.4, rough=1.0)
    tx, ty = tail_to
    s.stroke([(cx - w * 0.16, cy + h / 2 - 4), (tx + (cx - tx) * 0.15, ty),
              (cx + w * 0.04, cy + h / 2 - 6)], width=3.2, rough=0.9)
    return (cx, cy)


def arrow(s: Sheet, a, b, color=INK, width=3.2, head=18):
    s.stroke([a, b], width=width, color=color, rough=0.9, smooth=False)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for sgn in (-1, 1):
        s.stroke([(b[0] - head * math.cos(ang + sgn * 0.5), b[1] - head * math.sin(ang + sgn * 0.5)), b],
                 width=width, color=color, rough=0.7, smooth=False)


def cross_out(s: Sheet, c, r=46, color=RED, width=5.0):
    s.stroke([(c[0] - r, c[1] - r), (c[0] + r, c[1] + r)], width=width, color=color, rough=1.2)
    s.stroke([(c[0] + r, c[1] - r), (c[0] - r, c[1] + r)], width=width, color=color, rough=1.2)


def underline(s: Sheet, x0, x1, y, color=RED, width=4.6, dip=10):
    mid = (x0 + x1) / 2
    s.stroke([(x0, y), (mid, y + dip), (x1, y - dip * 0.4)], width=width, color=color, rough=1.4)


def sparkle(s: Sheet, c, r=10, color=ORANGE, width=2.4):
    """A 4-point hand-drawn twinkle with a rotating tilt."""
    tilt = s.rng.uniform(-0.45, 0.45)
    for k in range(4):
        a = tilt + k * math.pi / 2
        pts = []
        for j in range(5):
            f = 0.18 + 0.82 * j / 4
            pts.append((c[0] + math.cos(a) * r * f, c[1] + math.sin(a) * r * f))
        s.stroke(pts, width=width * (1.0 - 0.25 * (k % 2)), color=color, rough=0.4, smooth=False)

