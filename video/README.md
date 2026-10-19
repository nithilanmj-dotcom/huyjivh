# Project Alter Ego — video generation

A 20-second vertical teaser for this app, **generated entirely from code** on this
machine: no GPU, no API key, no paid service, no model downloads.

```
video/out/alter_ego_teaser.mp4   1080x1920 · 30 fps · 20.0 s · H.264 + AAC stereo
```

Copy is lifted from `src/data.ts` → `FUTURE_SCENES` inside the app bundle, so the
teaser says exactly what the product says.

---

## What actually runs here

This sandbox is **2 vCPU / 3.8 GB RAM / no GPU / no Chrome**, and it can only reach
GitHub, npm and PyPI — `huggingface.co` and `storage.googleapis.com` are blocked.
That single constraint decides everything below.

| Repo | ★ | License | Verdict in this environment |
|---|---:|---|---|
| [Zulko/moviepy](https://github.com/Zulko/moviepy) | 15.0k | MIT | ✅ **Used.** Pure Python + bundled ffmpeg. Rendered this video. |
| [ManimCommunity/manim](https://github.com/ManimCommunity/manim) | 41.7k | MIT | ❌ `pycairo`/`manimpango` compile against system cairo, no apt here |
| [nexu-io/html-video](https://github.com/nexu-io/html-video) | 4.7k | Apache-2.0 | ❌ needs headless Chromium (download host blocked) |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | 67.5k | Apache-2.0 | ❌ headless Chromium |
| [remotion-dev/remotion](https://github.com/remotion-dev/remotion) | 65.3k | Remotion License | ❌ downloads Chrome Headless Shell |
| [motion-canvas/motion-canvas](https://github.com/motion-canvas/motion-canvas) | 19.4k | MIT | ❌ renders through a browser |
| [latent-spaces/brag](https://github.com/latent-spaces/brag) | 16.9k | MIT | ❌ agent skill on top of Hyperframes |
| [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) | 69.9k | AGPL-3.0 | ❌ orchestrates paid Veo/Kling/fal keys + Remotion |
| [ATH-MaaS/Pixelle-Video](https://github.com/ATH-MaaS/Pixelle-Video) | 29.2k | Apache-2.0 | ❌ ComfyUI + model weights from Hugging Face |
| [Wan-Video/Wan2.1](https://github.com/Wan-Video/Wan2.1) | 17.2k | Apache-2.0 | ❌ 8–16 GB+ VRAM, weights on Hugging Face |
| [zai-org/CogVideo](https://github.com/zai-org/CogVideo) | 13.1k | Apache-2.0 | ❌ GPU + weights |
| [Lightricks/LTX-Video](https://github.com/Lightricks/LTX-Video) | 11.1k | Apache-2.0 | ❌ GPU + weights |
| [Tencent-Hunyuan/HunyuanVideo](https://github.com/Tencent-Hunyuan/HunyuanVideo) | 12.6k | — | ❌ ~45 GB VRAM |
| [KlingAIResearch/LivePortrait](https://github.com/KlingAIResearch/LivePortrait) | 19.3k | — | ❌ GPU |
| [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) | 139.5k | GPL-3.0 | ❌ engine only, needs GPU models |
| [Anil-matcha/Open-Generative-AI](https://github.com/Anil-matcha/Open-Generative-AI) | 30.9k | MIT | ❌ self-hosted UI that still calls paid APIs |

**The honest read:** every *free* text-to-video diffusion model (Wan, CogVideo, LTX,
Hunyuan) is free-as-in-license, not free-as-in-runs-here — they need a CUDA GPU and
multi-GB weights. On a 2-core CPU box, the free repos that genuinely produce an MP4
are the **programmatic** ones (MoviePy / Manim / Remotion), and of those only MoviePy
works without a browser or C toolchain.

If you *do* have a GPU, the best free text-to-video repos are **Wan 2.2**, **LTX-Video**
and **HunyuanVideo 1.5** — all Apache-2.0 and all runnable via ComfyUI.

---

## Render it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r video/requirements.txt

python video/generate_teaser.py                 # ~85 s -> video/out/alter_ego_teaser.mp4
python video/generate_teaser.py --no-audio      # silent cut
python video/generate_teaser.py --stills 2.6,7.0,18.8   # preview PNGs
```

`ffmpeg` is taken from `imageio-ffmpeg` if it is not already on `PATH`. No network
access is required at render time.

## Where to change things

| What | Where |
|---|---|
| Scene copy | `scene_one()` … `scene_five()` in `generate_teaser.py` |
| Scene timing | `T1 … T5`, `SCENES` at the top |
| Palette | `INK`, `MUTED`, `DIM`, `RULE` |
| Music | `make_score()` — one A-minor pad + a sub hit per cut |
| Size | `W, H`, `FPS` (layout is tuned for 9:16) |

Rendering is deterministic: the grain and noise seeds are fixed, so a re-render
produces the same file.
