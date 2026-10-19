#!/usr/bin/env python3
"""
make_scenes.py — draws the five hand-sketched frames for the Alter Ego
explainer and writes the annotation JSON that the whiteboard renderer consumes.

Output (all 1920x1080, warm paper):
  video/whiteboard/scenes/s1-coffee.png     + .annotation.json
  ... s5-endcard

Run:  python video/whiteboard/make_scenes.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from doodle import (BLUE, GREEN, INK, INK_FAINT, INK_SOFT, ORANGE, PAPER, RED, Sheet,
                    arrow, cross_out, cup, notebook, person, sparkle, speech_bubble,
                    underline)

W, H = 1920, 1080
OUT = Path(__file__).resolve().parent / "scenes"
OUT.mkdir(exist_ok=True)


# --------------------------------------------------------------------------
# Annotation helpers
# --------------------------------------------------------------------------
def region(x, y, w, h):
    return {"x": int(x), "y": int(y), "width": int(w), "height": int(h)}


def build_annotation(scene_id, story, items, tail_ms=900, gap_ms=140):
    """items: list of (label, role, region, duration_ms, subtitle)"""
    elements, t = [], gap_ms
    for i, (label, role, reg, dur, sub) in enumerate(items, start=1):
        elements.append({
            "id": f"e{i}",
            "label": label,
            "sequence": i,
            "narrativeRole": role,
            "subtitle": sub,
            "type": "structure",
            "region": reg,
            "reveal": {
                "direction": "top_to_bottom",
                "startMs": t,
                "durationMs": dur,
                "maskPaddingPx": 24,
                "protectedRegions": [],
            },
            "handPath": {
                "start": [reg["x"] + reg["width"] // 2, reg["y"] + 10],
                "end": [reg["x"] + reg["width"] // 2, reg["y"] + reg["height"] - 10],
                "easing": "easeInOut",
            },
        })
        t += dur + gap_ms

    return {
        "sceneId": scene_id,
        "canvas": {"width": W, "height": H},
        "storyBasis": story,
        "sceneDurationMs": t + tail_ms,
        "elements": elements,
    }


def write(name, sheet, annotation):
    png = OUT / f"{name}.png"
    sheet.save(png)
    json.dump(annotation, open(OUT / f"{name}.annotation.json", "w"),
              ensure_ascii=False, indent=2)
    print(f"  {name:<14} {annotation['sceneDurationMs']/1000:5.1f}s  "
          f"{len(annotation['elements'])} regions")


# --------------------------------------------------------------------------
# Scene 1 — You buy coffee
# --------------------------------------------------------------------------
def scene1():
    s = Sheet(W, H, seed=11)

    hand = person(s, cx=430, feet=880, height=600, arm="hold", accent=BLUE)
    cup(s, cx=hand[0] + 6, base_y=hand[1] + 52, width=112)

    s.text("You buy coffee.", (955, 520), size=124, color=INK)
    s.text("No hesitation.", (958, 668), size=104, color=INK_SOFT)
    underline(s, 958, 1467, 712, color=RED, width=5.0)

    ann = build_annotation(
        "s1-coffee",
        "Tuesday morning: buying coffee without hesitating.",
        [
            ("figure", "主角出场", region(320, 250, 300, 660), 2500,
             "You buy coffee."),
            ("cup", "咖啡杯", region(510, 470, 150, 210), 2100, "You buy coffee."),
            ("line-1", "字幕一", region(930, 430, 720, 120), 1800, "You buy coffee."),
            ("line-2", "字幕二", region(930, 580, 640, 140), 1700, "No hesitation."),
        ],
    )
    write("s1-coffee", s, ann)


# --------------------------------------------------------------------------
# Scene 2 — No checking your account first
# --------------------------------------------------------------------------
def scene2():
    s = Sheet(W, H, seed=23)

    # phone
    s.rounded_rect(430, 210, 760, 800, r=42, width=4.0, rough=1.0)
    s.rounded_rect(462, 262, 728, 700, r=14, width=2.4, color=INK_SOFT, rough=0.8)
    s.stroke([(570, 236), (620, 236)], width=3.0, color=INK_SOFT)

    # balance row
    s.rounded_rect(492, 300, 698, 372, r=10, width=2.4, color=INK_SOFT, rough=0.9)
    s.stroke([(516, 336), (596, 336)], width=3.0, color=INK_FAINT, rough=0.8)
    s.stroke([(516, 356), (656, 356)], width=3.6, color=INK_SOFT, rough=0.8)

    # a rising chart that we then refuse to look at
    s.stroke([(496, 646), (556, 596), (600, 620), (652, 536), (700, 512)],
             width=3.6, color=GREEN, rough=1.0)
    s.stroke([(496, 660), (700, 660)], width=2.2, color=INK_FAINT, rough=0.8)
    for x, y in ((556, 596), (652, 536)):
        s.dot((x, y), r=3.4, color=GREEN)

    # lock
    s.rounded_rect(566, 420, 656, 500, r=12, width=3.0, color=INK_SOFT, rough=0.9)
    s.ellipse((611, 420), 24, 26, start=math.pi, end=2 * math.pi,
              width=3.2, color=INK_SOFT, rough=0.9)
    s.dot((611, 462), r=4.0, color=INK_SOFT)

    cross_out(s, (596, 505), r=150, color=RED, width=6.0)

    s.text("No checking", (1010, 520), size=118, color=INK)
    s.text("your account first.", (1013, 650), size=96, color=INK_SOFT)

    ann = build_annotation(
        "s2-balance",
        "No checking the balance before buying.",
        [
            ("phone", "手机外壳", region(400, 180, 400, 650), 2400, "No checking your account first."),
            ("statement", "账户余额", region(470, 280, 260, 420), 2000, "No checking your account first."),
            ("cross", "红叉否定", region(430, 340, 340, 340), 1400, "No checking your account first."),
            ("line-1", "字幕一", region(980, 430, 720, 120), 1700, "No checking"),
            ("line-2", "字幕二", region(980, 570, 800, 120), 1800, "your account first."),
        ],
    )
    write("s2-balance", s, ann)


# --------------------------------------------------------------------------
# Scene 3 — Wait… he actually made this?
# --------------------------------------------------------------------------
def scene3():
    s = Sheet(W, H, seed=37)

    person(s, cx=370, feet=880, height=580, arm="point", accent=ORANGE)
    person(s, cx=1350, feet=880, height=600, arm="down", accent=BLUE)

    # framed piece of work hanging on the wall — reads instantly as "the work"
    fx0, fy0, fx1, fy1 = 800, 380, 1120, 690
    s.stroke([(fx0, fy0), (fx1, fy0), (fx1, fy1), (fx0, fy1), (fx0, fy0)],
             width=4.0, rough=0.7, smooth=False)
    s.stroke([(fx0 + 22, fy0 + 22), (fx1 - 22, fy0 + 22), (fx1 - 22, fy1 - 22),
              (fx0 + 22, fy1 - 22), (fx0 + 22, fy0 + 22)],
             width=2.0, color=INK_FAINT, rough=0.6, smooth=False)
    # nail + wire
    s.dot((960, 352), r=5.0, color=INK_SOFT)
    s.stroke([(880, fy0 - 2), (960, 356), (1040, fy0 - 2)], width=2.0, color=INK_SOFT, rough=0.6)
    # the sketch inside: a rising line and a little spark
    s.stroke([(838, 620), (884, 566), (918, 588), (972, 512), (1074, 470)],
             width=3.6, color=GREEN, rough=0.9)
    s.stroke([(838, 642), (1082, 642)], width=2.0, color=INK_FAINT, rough=0.6, smooth=False)
    sparkle(s, (1060, 448), r=18, color=ORANGE)

    speech_bubble(s, 1576, 268, 380, 190, tail_to=(1446, 452), accent=RED)
    for k in (-1, 1):
        bx = 1576 + k * 60
        s.stroke([(bx, 212), (bx, 322)], width=6.0, color=INK, rough=1.1)
        s.dot((bx, 350), r=6.0, color=INK)
    sparkle(s, (1712, 184), r=13, color=ORANGE)
    sparkle(s, (1444, 180), r=9, color=ORANGE)

    s.text_center("“Wait… he actually", 960, 936, size=86, color=INK)
    s.text_center("made this?”", 960, 1022, size=86, color=INK)

    ann = build_annotation(
        "s3-overheard",
        "A stranger notices someone's work and is surprised it is real.",
        [
            ("listener", "旁听者", region(280, 300, 300, 620), 2300, "“Wait…"),
            ("frame", "挂在墙上的作品", region(780, 340, 370, 380), 2400, "he actually"),
            ("speaker", "说话的人", region(1250, 300, 320, 620), 2200, "made this?”"),
            ("bubble", "感叹气泡", region(1350, 180, 440, 320), 1500, "“Wait… he actually made this?”"),
            ("caption", "字幕", region(470, 860, 980, 210), 1900, "“Wait… he actually made this?”"),
        ],
    )
    write("s3-overheard", s, ann)


# --------------------------------------------------------------------------
# Scene 4 — You didn't quit
# --------------------------------------------------------------------------
def scene4():
    s = Sheet(W, H, seed=53)

    notebook(s, cx=760, cy=548, w=640, accent=BLUE)
    # loose idea bursts
    sparkle(s, (1160, 380), r=20, color=ORANGE)
    sparkle(s, (1236, 470), r=12, color=ORANGE)
    sparkle(s, (1150, 546), r=15, color=RED)
    arrow(s, (1100, 452), (1160, 430), color=INK_FAINT, width=2.6, head=14)

    s.text("You didn't quit.", (1150, 690), size=116, color=INK)
    underline(s, 1154, 1744, 734, color=RED, width=5.0)

    ann = build_annotation(
        "s4-notebook",
        "Finding the original notebook: the idea survived.",
        [
            ("notebook", "旧笔记本", region(430, 330, 660, 440), 2600, "You didn't quit."),
            ("spark", "灵光", region(1100, 340, 190, 250), 1400, "You didn't quit."),
            ("line", "字幕", region(1120, 600, 720, 160), 1900, "You didn't quit."),
        ],
    )
    write("s4-notebook", s, ann)


# --------------------------------------------------------------------------
# Scene 5 — end card
# --------------------------------------------------------------------------
def scene5():
    s = Sheet(W, H, seed=71)

    # monogram
    s.circle((960, 360), 112, width=4.2, rough=0.9, color=INK)
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        cx, cy = 960 + dx * 132, 360 + dy * 132
        s.stroke([(cx - 7, cy), (cx + 7, cy)], width=3.0, color=INK_FAINT)
        s.stroke([(cx, cy - 7), (cx, cy + 7)], width=3.0, color=INK_FAINT)
    s.text_center("AE", 960, 392, size=104, color=INK)

    s.text_center("ALTER EGO", 960, 700, size=168, color=INK)
    underline(s, 612, 1312, 748, color=RED, width=6.0, dip=14)
    s.text_center("your future self, checking in.", 960, 850, size=72,
                  color=INK_SOFT, font="note")

    ann = build_annotation(
        "s5-endcard",
        "Brand end card.",
        [
            ("mark", "字母组合", region(800, 210, 320, 300), 1900, "ALTER EGO"),
            ("wordmark", "品牌字", region(600, 570, 720, 190), 2300, "ALTER EGO"),
            ("tagline", "标语", region(660, 790, 620, 110), 1700, "your future self, checking in."),
        ],
    )
    write("s5-endcard", s, ann)


if __name__ == "__main__":
    print(f"drawing frames -> {OUT}")
    scene1()
    scene2()
    scene3()
    scene4()
    scene5()
