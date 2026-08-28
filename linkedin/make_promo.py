"""8-second EDA Studio LinkedIn promo with original music."""
from __future__ import annotations

import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
SYMBOL = ROOT / "frontend" / "src" / "assets" / "symbol.png"
FONTS = Path(r"C:\Windows\Fonts")

DURATION = 8.0
FPS = 30
SR = 44100
NAVY = (10, 18, 32)
INK = (18, 35, 58)
TEAL = (91, 168, 160)
CREAM = (243, 238, 228)
MUTED = (201, 194, 180)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def fade(t: float, start: float, end: float, fade_in: float = 0.35, fade_out: float = 0.4) -> float:
    if t < start or t > end:
        return 0.0
    a = ease((t - start) / fade_in) if t < start + fade_in else 1.0
    b = ease((end - t) / fade_out) if t > end - fade_out else 1.0
    return a * b


def rounded_rect(draw: ImageDraw.ImageDraw, box, radius: int, fill) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def make_music(path: Path) -> None:
    n = int(SR * DURATION)
    t = np.arange(n) / SR
    pad = np.zeros(n, dtype=np.float64)
    for f, amp in ((130.81, 0.10), (196.00, 0.08), (261.63, 0.07), (329.63, 0.05)):
        pad += amp * np.sin(2 * math.pi * f * t) * np.exp(-0.04 * t)
    notes = [261.63, 329.63, 392.00, 523.25, 392.00, 329.63, 440.00, 523.25]
    pluck = np.zeros(n, dtype=np.float64)
    for i, f in enumerate(notes):
        start = int(0.22 * SR + i * 0.88 * SR)
        length = int(0.9 * SR)
        if start >= n:
            break
        end = min(n, start + length)
        tt = np.arange(end - start) / SR
        env = np.exp(-3.2 * tt) * (1 - np.exp(-40 * tt))
        pluck[start:end] += 0.16 * np.sin(2 * math.pi * f * tt) * env
        pluck[start:end] += 0.04 * np.sin(2 * math.pi * f * 2 * tt) * env
    audio = pad + pluck
    fade_in = np.linspace(0, 1, int(0.25 * SR))
    fade_out = np.linspace(1, 0, int(0.9 * SR))
    audio[: len(fade_in)] *= fade_in
    audio[-len(fade_out) :] *= fade_out
    peak = np.max(np.abs(audio)) or 1.0
    pcm = (audio / peak * 0.72 * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def draw_bg(w: int, h: int, t: float) -> Image.Image:
    img = Image.new("RGB", (w, h), NAVY)
    glow = Image.new("RGB", (w, h), NAVY)
    g = ImageDraw.Draw(glow)
    cx, cy = w // 2, int(h * 0.42)
    pulse = 0.55 + 0.12 * math.sin(t * 1.6)
    for i, r in enumerate((int(min(w, h) * 0.55), int(min(w, h) * 0.32), int(min(w, h) * 0.16))):
        a = int(18 * pulse / (i + 1))
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(overlay).ellipse((cx - r, cy - r, cx + r, cy + r), fill=(91, 168, 160, a))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    return img


def paste_center(base: Image.Image, layer: Image.Image, y: int, alpha: float) -> None:
    if alpha <= 0:
        return
    x = (base.width - layer.width) // 2
    if layer.mode != "RGBA":
        layer = layer.convert("RGBA")
    a = layer.split()[-1].point(lambda p: int(p * alpha))
    layer.putalpha(a)
    base.paste(layer, (x, y), layer)


def text_layer(text: str, fnt: ImageFont.FreeTypeFont, fill, w: int) -> Image.Image:
    tmp = Image.new("RGBA", (w, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    bbox = d.textbbox((0, 0), text, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    img = Image.new("RGBA", (tw + 8, th + 8), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((4 - bbox[0], 4 - bbox[1]), text, font=fnt, fill=fill)
    return img


def compose_frame(w: int, h: int, t: float, logo: Image.Image, story: bool) -> Image.Image:
    frame = draw_bg(w, h, t).convert("RGBA")
    draw = ImageDraw.Draw(frame)

    kicker_f = font("segoeuib.ttf", 28 if story else 26)
    title_f = font("georgiab.ttf", 54 if story else 48)
    sub_f = font("segoeui.ttf", 30 if story else 28)
    url_f = font("segoeui.ttf", 24 if story else 22)

    logo_a = fade(t, 0.15, 8.0, 0.5, 0.35)
    scale = 0.88 + 0.10 * ease(t / DURATION)
    lw = int(logo.width * scale)
    logo_r = logo.resize((lw, lw), Image.Resampling.LANCZOS)
    logo_y = int(h * (0.22 if story else 0.16))
    paste_center(frame, logo_r, logo_y, logo_a)

    kicker = text_layer("EDA STUDIO", kicker_f, TEAL, w)
    title1 = text_layer("Magic of", title_f, CREAM, w)
    title2 = text_layer("Exploratory Data Analysis", title_f, CREAM, w)
    tag = text_layer("CSV in.  Quality.  Insights out.", sub_f, MUTED, w)
    url = text_layer("eda-ai-five.vercel.app", url_f, TEAL, w)

    k_a = fade(t, 0.4, 3.4, 0.3, 0.35)
    t_a = fade(t, 2.2, 8.0, 0.4, 0.4)
    u_a = fade(t, 4.6, 8.0, 0.4, 0.45)

    ky = logo_y - 48
    paste_center(frame, kicker, ky, k_a)

    ty = logo_y + logo_r.height + (36 if story else 28)
    paste_center(frame, title1, ty, t_a)
    paste_center(frame, title2, ty + title1.height + 4, t_a)

    line_y = ty + title1.height + title2.height + 22
    if t_a > 0.05:
        lw_line = int(180 * t_a)
        cx = w // 2
        draw.rectangle((cx - lw_line, line_y, cx + lw_line, line_y + 3), fill=(*TEAL, int(220 * t_a)))

    paste_center(frame, tag, line_y + 22, u_a)
    paste_center(frame, url, line_y + 22 + tag.height + 10, u_a)

    bar = Image.new("RGBA", (w, 6), (*TEAL, 180))
    frame.paste(bar, (0, 0), bar)
    frame.paste(bar, (0, h - 6), bar)
    return frame.convert("RGB")


def encode(frames_dir: Path, wav: Path, mp4: Path, w: int, h: int) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(frames_dir / "%04d.png"),
        "-i",
        str(wav),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(mp4),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-2000:])


def render(name: str, w: int, h: int, story: bool, logo: Image.Image, wav: Path) -> Path:
    frames = OUT / f"_frames_{name}"
    frames.mkdir(parents=True, exist_ok=True)
    n = int(DURATION * FPS)
    for i in range(n):
        t = i / FPS
        compose_frame(w, h, t, logo, story).save(frames / f"{i:04d}.png")
    mp4 = OUT / f"EDA_Studio_{name}.mp4"
    encode(frames, wav, mp4, w, h)
    for png in frames.glob("*.png"):
        png.unlink()
    frames.rmdir()
    return mp4


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    logo = Image.open(SYMBOL).convert("RGBA")
    wav = OUT / "bed.wav"
    make_music(wav)
    square = render("square_8s", 1080, 1080, False, logo, wav)
    story = render("story_8s", 1080, 1920, True, logo, wav)
    wav.unlink(missing_ok=True)
    print(square)
    print(story)


if __name__ == "__main__":
    main()
