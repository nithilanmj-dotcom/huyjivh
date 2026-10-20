#!/usr/bin/env python3
"""
render.py — drives the vendored whiteboard renderer over the five drawn scenes.

Adds three things the upstream CLI does not do:
  * a smaller drawing hand (493px is tuned for stock art; our line work is finer)
  * two scenes rendered at a time, so both vCPUs are used
  * a synthesized music bed, muxed at the end

Usage:
  python video/whiteboard/render.py                    # full render -> video/out/
  python video/whiteboard/render.py --hand-height 340
  python video/whiteboard/render.py --only s1-coffee   # single scene, for previews
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import shutil
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor"))
sys.path.insert(0, str(HERE))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import stream_render as sr  # noqa: E402
from render_stream_whiteboard import RegionStreamRenderer  # noqa: E402

SCENES = ["s1-coffee", "s2-balance", "s3-overheard", "s4-notebook", "s5-endcard"]
OUT_DIR = HERE.parent / "out"
BUILD = OUT_DIR / "build"


def ffmpeg_bin() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def make_cfg(fps: int, hand_height: int) -> sr.Config:
    cfg = sr.Config(fps=fps, cap_long_edge=1920, ink_path_mode="grid",
                    color_fill="contour-wipe", pause_mode="light")
    return dataclasses.replace(cfg, target_hand_height=hand_height)


def render_scene(name: str, fps: int, hand_height: int) -> Path:
    png = HERE / "scenes" / f"{name}.png"
    ann_path = HERE / "scenes" / f"{name}.annotation.json"
    out = BUILD / f"{name}.mp4"

    annotation = json.loads(ann_path.read_text())
    image = sr._imread_any(str(png))
    if image is None:
        raise RuntimeError(f"cannot read {png}")

    cfg = make_cfg(fps, hand_height)
    renderer = RegionStreamRenderer(image, annotation, cfg,
                                    HERE / "vendor" / "drawing-hand.png", False)
    raw = BUILD / f"{name}_raw.mp4"
    renderer.render_to(raw, annotation["sceneDurationMs"])
    sr.transcode_h264(raw, out)
    raw.unlink(missing_ok=True)
    print(f"  [ok] {name:<14} {renderer.out_w}x{renderer.out_h} "
          f"{annotation['sceneDurationMs'] / 1000:.1f}s")
    return out


# --------------------------------------------------------------------------
# Music: marimba-ish plucks over a warm pad, tuned to A minor pentatonic
# --------------------------------------------------------------------------
SR = 44100


def music(duration: float) -> np.ndarray:
    n = int(duration * SR)
    t = np.arange(n) / SR
    L = np.zeros(n)
    R = np.zeros(n)

    # pad (A2, E3, A3, C4)
    for i, f0 in enumerate([110.0, 164.81, 220.0, 261.63]):
        for detune, pan in ((-0.12, 0.3), (0.12, 0.7)):
            lfo = 0.6 + 0.4 * np.sin(2 * np.pi * (0.031 + 0.008 * i) * t + i)
            tone = np.sin(2 * np.pi * f0 * (1 + detune / 100) * t) + 0.18 * np.sin(2 * np.pi * 2 * f0 * t)
            amp = 0.030 * lfo
            L += amp * tone * math.cos(pan * math.pi / 2)
            R += amp * tone * math.sin(pan * math.pi / 2)

    # marimba plucks on a pentatonic ladder
    rng = np.random.default_rng(5)
    notes = [440.0, 523.25, 587.33, 659.25, 783.99]
    step, when = 0.62, 1.5
    while when < duration - 1.2:
        idx = int(rng.integers(0, len(notes)))
        f = notes[idx] * (0.5 if rng.random() < 0.22 else 1.0)
        start = int(when * SR)
        seg = min(n - start, int(2.4 * SR))
        if seg > 0:
            tt = np.arange(seg) / SR
            env = np.exp(-tt * 3.4) * (1 - np.exp(-tt * 90))
            body = (np.sin(2 * np.pi * f * tt) + 0.36 * np.sin(2 * np.pi * 2 * f * tt)
                    + 0.14 * np.sin(2 * np.pi * 3.02 * f * tt))
            pan = 0.34 + 0.32 * rng.random()
            L[start:start + seg] += 0.105 * body * env * math.cos(pan * math.pi / 2)
            R[start:start + seg] += 0.105 * body * env * math.sin(pan * math.pi / 2)
        when += step * (1.0 if rng.random() < 0.7 else 1.5)

    # paper room tone
    freqs = np.fft.rfftfreq(n, 1 / SR)
    nz = rng.standard_normal(n)
    room = np.fft.irfft(np.fft.rfft(nz) / (1.0 + (freqs / 900.0) ** 3), n)
    room /= max(1e-9, np.max(np.abs(room)))
    L += 0.014 * room
    R += 0.014 * np.roll(room, 297)

    mix = np.stack([L, R])
    mix /= max(1e-9, np.max(np.abs(mix)))
    mix = np.tanh(mix * 1.15) / math.tanh(1.15) * 0.72
    mix *= np.clip(t / 2.5, 0, 1) * np.clip((duration - t) / 3.0, 0, 1)
    return mix


def write_wav(path: Path, stereo: np.ndarray):
    data = (np.clip(stereo.T, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--hand-height", type=int, default=330)
    ap.add_argument("--only", default="", help="comma separated scene ids")
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--out", default=str(OUT_DIR / "alter_ego_explainer.mp4"))
    args = ap.parse_args()

    cv2.setNumThreads(1)
    BUILD.mkdir(parents=True, exist_ok=True)

    wanted = [s.strip() for s in args.only.split(",") if s.strip()] or SCENES
    print(f"rendering {len(wanted)} scene(s) at {args.fps}fps, hand={args.hand_height}px")

    import multiprocessing as mp
    jobs = [(n, args.fps, args.hand_height) for n in wanted]
    if len(jobs) == 1:
        paths = [render_scene(*jobs[0])]
    else:
        with mp.Pool(processes=2) as pool:   # both vCPUs busy
            paths = pool.starmap(render_scene, jobs)

    if len(paths) == 1:
        single = Path(args.out).with_suffix(".mp4")
        shutil.copy(paths[0], single)
        print(f"done -> {single}")
        return 0

    concat_list = BUILD / "concat.txt"
    concat_list.write_text("".join(f"file '{p.resolve()}'\n" for p in paths))
    ff = ffmpeg_bin()
    silent = BUILD / "_silent.mp4"
    subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(concat_list), "-c", "copy", str(silent)], check=True)

    total = 0.0
    for p in paths:
        ann = json.loads((HERE / "scenes" / f"{p.stem}.annotation.json").read_text())
        total += ann["sceneDurationMs"] / 1000.0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.no_audio:
        shutil.move(str(silent), str(out))
    else:
        wav = BUILD / "_music.wav"
        write_wav(wav, music(total))
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(wav),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", "-movflags", "+faststart", str(out)], check=True)
        wav.unlink(missing_ok=True)

    silent.unlink(missing_ok=True)
    print(f"done -> {out}  ({out.stat().st_size / 1e6:.1f} MB, {total:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
