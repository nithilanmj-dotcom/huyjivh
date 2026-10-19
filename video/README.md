# Project Alter Ego — video generation

Two videos, both generated **from code on this machine**: no GPU, no API key, no
paid service, no model weights.

| File | Format | Pipeline |
|---|---|---|
| `video/out/alter_ego_explainer.mp4` | 1920×1080 · 30 fps · 47.5 s | hand-drawn whiteboard (ink streaming) |
| `video/out/alter_ego_teaser.mp4` | 1080×1920 · 30 fps · 20.0 s | kinetic typography (vertical) |

Both use copy from `src/data.ts` → `FUTURE_SCENES` inside the app bundle.

---

## What actually runs here

This sandbox is **2 vCPU / 3.8 GB RAM / no GPU / no Chrome**, and it can only reach
GitHub, npm and PyPI — `huggingface.co` and `storage.googleapis.com` are blocked.
That single constraint decides everything below.

### Whiteboard / hand-drawn

| Repo | ★ | License | Verdict in this environment |
|---|---:|---|---|
| [geeklee/srt-whiteboard-animation](https://github.com/geeklee/srt-whiteboard-animation) | 4.6k | MIT | ✅ **Used.** Pure Python (OpenCV + PyAV). Vendored in `whiteboard/vendor/`. |
| [letuandat131/whiteboard-animation-vi](https://github.com/letuandat131/whiteboard-animation-vi) | 139 | CC0-1.0 | ❌ needs `torch` + `safetensors` weights |
| [yogendra-yatnalkar/storyboard-ai](https://github.com/yogendra-yatnalkar/storyboard-ai) | 175 | GPL-3.0 | ❌ calls an image API per scene |
| [NadirWeb-App/Inkplainer-OS](https://github.com/NadirWeb-App/Inkplainer-OS) | 43 | — | ❌ browser-only |

### Programmatic / typography

| Repo | ★ | License | Verdict |
|---|---:|---|---|
| [Zulko/moviepy](https://github.com/Zulko/moviepy) | 15.0k | MIT | ✅ **Used** for the teaser. |
| [ManimCommunity/manim](https://github.com/ManimCommunity/manim) | 41.7k | MIT | ❌ `pycairo` needs system cairo, no apt |
| [nexu-io/html-video](https://github.com/nexu-io/html-video) | 4.7k | Apache-2.0 | ❌ headless Chromium |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | 67.5k | Apache-2.0 | ❌ headless Chromium |
| [remotion-dev/remotion](https://github.com/remotion-dev/remotion) | 65.3k | Remotion License | ❌ downloads Chrome Headless Shell |
| [motion-canvas/motion-canvas](https://github.com/motion-canvas/motion-canvas) | 19.4k | MIT | ❌ renders through a browser |
| [latent-spaces/brag](https://github.com/latent-spaces/brag) | 16.9k | MIT | ❌ agent skill on top of Hyperframes |

### AI text-to-video (all GPU-bound)

| Repo | ★ | License | Verdict |
|---|---:|---|---|
| [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) | 69.9k | AGPL-3.0 | ❌ orchestrates paid Veo/Kling/fal keys |
| [Anil-matcha/Open-Generative-AI](https://github.com/Anil-matcha/Open-Generative-AI) | 30.9k | MIT | ❌ self-hosted UI, still calls paid APIs |
| [ATH-MaaS/Pixelle-Video](https://github.com/ATH-MaaS/Pixelle-Video) | 29.2k | Apache-2.0 | ❌ ComfyUI + HF weights |
| [Wan-Video/Wan2.1](https://github.com/Wan-Video/Wan2.1) | 17.2k | Apache-2.0 | ❌ 8–16 GB+ VRAM |
| [zai-org/CogVideo](https://github.com/zai-org/CogVideo) | 13.1k | Apache-2.0 | ❌ GPU + weights |
| [Lightricks/LTX-Video](https://github.com/Lightricks/LTX-Video) | 11.1k | Apache-2.0 | ❌ GPU + weights |
| [Tencent-Hunyuan/HunyuanVideo](https://github.com/Tencent-Hunyuan/HunyuanVideo) | 12.6k | — | ❌ ~45 GB VRAM |
| [KlingAIResearch/LivePortrait](https://github.com/KlingAIResearch/LivePortrait) | 19.3k | — | ❌ GPU |
| [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) | 139.5k | GPL-3.0 | ❌ engine only, needs GPU models |

**The honest read:** every *free* text-to-video diffusion model is free-as-in-license,
not free-as-in-runs-here — they need a CUDA GPU and multi-GB weights. On a 2-core CPU
box the free repos that genuinely produce an MP4 are the programmatic ones. For hand-drawn
specifically, only `srt-whiteboard-animation` works without a browser or a C toolchain.

If you *do* have a GPU, the best free text-to-video repos are **Wan 2.2**, **LTX-Video**
and **HunyuanVideo 1.5**, all Apache-2.0 and runnable via ComfyUI.

---

## The hand-drawn explainer

`whiteboard/` is a three-stage pipeline:

```
make_scenes.py        render.py                  vendor/
─────────────►  PNG + annotation.json  ──────►  stream_render.py  ──►  MP4
  draws the art        (regions + timings)        inks it in
```

1. **`doodle.py`** — a small sketch kit on Pillow. Every line is drawn twice with
   slow sine wobble (that is what makes it look hand-made), glyphs are placed one at
   a time with random rotation and baseline drift, shading is loose hatching.
   Drawn at 2× and downsampled.
2. **`make_scenes.py`** — composes five 1920×1080 frames and writes the region
   annotations: *coffee → no balance check → overheard praise → the notebook → end card*.
3. **`render.py`** — drives the vendored renderer. Each region is inked in sequence,
   the pen follows the actual stroke, then colour is wiped in. Renders two scenes at
   once (2 vCPUs), then muxes a marimba-and-pad score synthesized with numpy.

```bash
pip install -r video/whiteboard/requirements.txt

python video/whiteboard/make_scenes.py      # redraw the five frames (~3 s)
python video/whiteboard/render.py           # ~3 min -> video/out/alter_ego_explainer.mp4
python video/whiteboard/render.py --only s1-coffee     # one scene, for previews
python video/whiteboard/render.py --hand-height 240    # smaller pen hand
```

| Knob | Where |
|---|---|
| Scene copy / layout | `make_scenes.py` (`scene1()` … `scene5()`) |
| Ink / accents | `doodle.py` (`INK`, `RED`, `ORANGE`, `BLUE`, `PAPER`) |
| Reveal order + timing | the `build_annotation(...)` call in each scene |
| Pen hand size | `--hand-height` (Default 330px for 1080p) |
| Stroke style | `--ink-path skeleton` (tighter to line work) in `vendor/render_stream_whiteboard.py` |

Swap `drawing-hand.png` for a different pen, or pass `--bare-tip` for no hand at all.

## The vertical teaser

```bash
pip install -r video/requirements.txt
python video/generate_teaser.py            # ~85 s -> video/out/alter_ego_teaser.mp4
python video/generate_teaser.py --stills 2.6,7.0,18.8   # preview PNGs
```

Scene copy, timings and palette all live at the top of `generate_teaser.py`.

---

## Credits

- `whiteboard/vendor/` — [geeklee/srt-whiteboard-animation](https://github.com/geeklee/srt-whiteboard-animation), MIT (see `LICENSE-srt-whiteboard-animation`). Vendored unmodified apart from the driver in `render.py`.
- `whiteboard/fonts/` — Caveat and Patrick Hand, SIL Open Font License, fetched from npm (`@expo-google-fonts/*`).
- `whiteboard/vendor/drawing-hand.png` — from the MIT-licensed upstream repo.

Rendering is deterministic where it matters: grain and stroke jitter use fixed seeds.
