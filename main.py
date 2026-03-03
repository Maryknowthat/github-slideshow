#!/usr/bin/env python3
"""Generate iPhone lockscreen/homescreen wallpapers and UI previews from an input image."""

from __future__ import annotations

import argparse
import base64
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

from openai import OpenAI
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

TARGET_SIZE = (1290, 2796)  # iPhone 15 Pro Max portrait resolution


@dataclass
class StyleProfile:
    avg_saturation: float
    luminance_std: float
    color_mode: str
    palette_guidance: str
    mood_guidance: str


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if path and Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def analyze_image_style(image: Image.Image) -> StyleProfile:
    rgb = image.convert("RGB")
    hsv = rgb.convert("HSV")
    _, s, _ = hsv.split()
    sat_mean = ImageStat.Stat(s).mean[0] / 255.0

    gray = rgb.convert("L")
    luminance_std = ImageStat.Stat(gray).stddev[0] / 255.0

    if sat_mean >= 0.45:
        color_mode = "vibrant"
        palette_guidance = (
            "use energetic complementary colors, tasteful color contrast, richer saturation, and cinematic depth"
        )
        mood_guidance = "bold, immersive, high-energy but still premium"
    else:
        color_mode = "soft"
        palette_guidance = "use soft low-saturation tones, gentle contrast, airy gradients, and calm harmony"
        mood_guidance = "minimal, cozy, elegant, and serene"

    return StyleProfile(
        avg_saturation=sat_mean,
        luminance_std=luminance_std,
        color_mode=color_mode,
        palette_guidance=palette_guidance,
        mood_guidance=mood_guidance,
    )


def build_style_anchor(profile: StyleProfile) -> str:
    return (
        "Create an iPhone wallpaper series from the uploaded reference image. "
        "Preserve the source image's core visual DNA (subject cues, abstract motif language, and material mood) "
        "while redesigning it into a clean premium wallpaper aesthetic. "
        f"Color strategy: {profile.palette_guidance}. "
        f"Mood: {profile.mood_guidance}. "
        "Do not add text, logos, watermarks, frames, or device mockups. "
        "Deliver a photoreal/illustrative wallpaper-only image with polished lighting and coherent composition."
    )


def build_lockscreen_prompt(anchor: str) -> str:
    return (
        f"{anchor} "
        "Variant A for iOS lock screen: "
        "reserve clean readability zones for one date line near top and very large time digits below it in center-upper area. "
        "Avoid busy high-frequency textures in top 45% of frame and central time area. "
        "Keep main subject around mid-lower area, leaving middle open and legible. "
        "Notification area in lower-middle should remain moderately calm and not overly contrasty. "
        "Keep elegant depth and premium finish."
    )


def build_homescreen_prompt(anchor: str) -> str:
    return (
        f"{anchor} "
        "Variant B for iOS home screen: "
        "top half (app icon region) should be cleaner, lower detail, lower contrast, with broad smooth gradients. "
        "Main subject can sit lower and should not interfere with icon readability. "
        "Keep same series style and palette as lock screen but with distinctly different composition. "
        "Overall less clutter, softly layered, premium phone wallpaper look."
    )


def generate_wallpaper(image_path: str, prompt: str, size: Tuple[int, int]) -> Image.Image:
    size_str = f"{size[0]}x{size[1]}"
    client = OpenAI()
    with open(image_path, "rb") as image_file:
        response = client.images.edit(
            model="gpt-image-1",
            image=image_file,
            prompt=prompt,
            size=size_str,
        )
    b64_data = response.data[0].b64_json
    if not b64_data:
        raise ValueError("Images API returned empty image payload")
    image_bytes = base64.b64decode(b64_data)
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def choose_text_style(background: Image.Image, region: Tuple[int, int, int, int]) -> Tuple[Tuple[int, int, int], Tuple[int, int, int, int]]:
    crop = background.crop(region).convert("L")
    brightness = ImageStat.Stat(crop).mean[0]
    if brightness < 130:
        return (245, 245, 248), (0, 0, 0, 120)
    return (15, 18, 26), (255, 255, 255, 120)


def draw_text_with_shadow(draw: ImageDraw.ImageDraw, xy: Tuple[int, int], text: str, font: ImageFont.ImageFont,
                          fill: Tuple[int, int, int], shadow: Tuple[int, int, int, int]) -> None:
    sx, sy = xy
    shadow_rgb = shadow[:3]
    draw.text((sx + 2, sy + 2), text, font=font, fill=shadow_rgb)
    draw.text((sx, sy), text, font=font, fill=fill)


def create_lockscreen_preview(wallpaper: Image.Image, date_text: str, time_text: str) -> Image.Image:
    canvas = wallpaper.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    w, h = canvas.size

    date_font = load_font(int(h * 0.032), bold=False)
    time_font = load_font(int(h * 0.13), bold=True)

    date_region = (0, int(h * 0.11), w, int(h * 0.22))
    time_region = (0, int(h * 0.18), w, int(h * 0.42))

    date_color, date_shadow = choose_text_style(canvas, date_region)
    time_color, time_shadow = choose_text_style(canvas, time_region)

    date_bbox = draw.textbbox((0, 0), date_text, font=date_font)
    date_x = (w - (date_bbox[2] - date_bbox[0])) // 2
    date_y = int(h * 0.13)

    time_bbox = draw.textbbox((0, 0), time_text, font=time_font)
    time_x = (w - (time_bbox[2] - time_bbox[0])) // 2
    time_y = int(h * 0.19)

    draw_text_with_shadow(draw, (date_x, date_y), date_text, date_font, date_color, date_shadow)
    draw_text_with_shadow(draw, (time_x, time_y), time_text, time_font, time_color, time_shadow)

    return canvas.convert("RGB")


def create_homescreen_preview(wallpaper: Image.Image) -> Image.Image:
    canvas = wallpaper.convert("RGBA")
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = canvas.size

    cols, rows = 4, 6
    margin_x = int(w * 0.08)
    top = int(h * 0.14)
    bottom = int(h * 0.74)
    grid_w = w - margin_x * 2
    grid_h = bottom - top
    cell_w = grid_w / cols
    cell_h = grid_h / rows

    icon_size = int(min(cell_w, cell_h) * 0.62)
    radius = int(icon_size * 0.23)

    for r in range(rows):
        for c in range(cols):
            cx = int(margin_x + c * cell_w + (cell_w - icon_size) / 2)
            cy = int(top + r * cell_h + (cell_h - icon_size) / 2)
            fill = (255, 255, 255, 52) if (r + c) % 2 == 0 else (255, 255, 255, 36)
            outline = (255, 255, 255, 86)
            draw.rounded_rectangle([cx, cy, cx + icon_size, cy + icon_size], radius=radius, fill=fill, outline=outline, width=1)

    dock_h = int(h * 0.115)
    dock_margin = int(w * 0.06)
    dock_y1 = h - dock_h - int(h * 0.03)
    dock_y2 = h - int(h * 0.02)
    draw.rounded_rectangle(
        [dock_margin, dock_y1, w - dock_margin, dock_y2],
        radius=int(dock_h * 0.36),
        fill=(245, 245, 250, 72),
        outline=(255, 255, 255, 90),
        width=1,
    )

    dock_cols = 4
    dock_icon_size = int(dock_h * 0.52)
    dock_space = (w - dock_margin * 2) / dock_cols
    for i in range(dock_cols):
        x = int(dock_margin + i * dock_space + (dock_space - dock_icon_size) / 2)
        y = int(dock_y1 + (dock_h - dock_icon_size) / 2)
        draw.rounded_rectangle(
            [x, y, x + dock_icon_size, y + dock_icon_size],
            radius=int(dock_icon_size * 0.25),
            fill=(255, 255, 255, 98),
            outline=(255, 255, 255, 140),
            width=1,
        )

    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=0.35))
    return Image.alpha_composite(canvas, overlay).convert("RGB")


def save_image(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")


def process_one(input_path: Path, outdir: Path, date_text: str, time_text: str) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Input image not found: {input_path}")

    outdir.mkdir(parents=True, exist_ok=True)

    source_image = Image.open(input_path).convert("RGB")
    profile = analyze_image_style(source_image)
    anchor = build_style_anchor(profile)

    logging.info("Image style analysis | saturation=%.3f contrast=%.3f mode=%s", profile.avg_saturation, profile.luminance_std, profile.color_mode)

    lock_path = outdir / "lockscreen_wallpaper.png"
    home_path = outdir / "homescreen_wallpaper.png"
    lock_preview_path = outdir / "lockscreen_preview.png"
    home_preview_path = outdir / "homescreen_preview.png"

    lock_img = None
    home_img = None

    try:
        logging.info("Generating lockscreen wallpaper...")
        lock_img = generate_wallpaper(str(input_path), build_lockscreen_prompt(anchor), TARGET_SIZE)
        save_image(lock_img, lock_path)
        logging.info("Saved %s", lock_path)
    except Exception as exc:
        logging.exception("Failed lockscreen wallpaper generation: %s", exc)

    try:
        logging.info("Generating homescreen wallpaper...")
        home_img = generate_wallpaper(str(input_path), build_homescreen_prompt(anchor), TARGET_SIZE)
        save_image(home_img, home_path)
        logging.info("Saved %s", home_path)
    except Exception as exc:
        logging.exception("Failed homescreen wallpaper generation: %s", exc)

    if lock_img is not None:
        try:
            lock_preview = create_lockscreen_preview(lock_img, date_text, time_text)
            save_image(lock_preview, lock_preview_path)
            logging.info("Saved %s", lock_preview_path)
        except Exception as exc:
            logging.exception("Failed lockscreen preview composition: %s", exc)

    if home_img is not None:
        try:
            home_preview = create_homescreen_preview(home_img)
            save_image(home_preview, home_preview_path)
            logging.info("Saved %s", home_preview_path)
        except Exception as exc:
            logging.exception("Failed homescreen preview composition: %s", exc)

    logging.info("Done.")


def collect_images(root_dir: Path) -> Iterable[Path]:
    exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    for path in sorted(root_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in exts:
            yield path


def make_unique_subdir(base_outdir: Path, stem: str) -> Path:
    candidate = base_outdir / stem
    if not candidate.exists():
        return candidate

    index = 2
    while True:
        candidate = base_outdir / f"{stem}-{index}"
        if not candidate.exists():
            return candidate
        index += 1


def process(args: argparse.Namespace) -> None:
    base_outdir = Path(args.outdir)
    base_outdir.mkdir(parents=True, exist_ok=True)

    if args.input:
        process_one(Path(args.input), base_outdir, args.date, args.time)
        return

    input_dir = Path(args.input_dir)
    if not input_dir.exists() or not input_dir.is_dir():
        raise NotADirectoryError(f"Input directory not found: {input_dir}")

    images = list(collect_images(input_dir))
    if not images:
        logging.warning("No supported images found under %s", input_dir)
        return

    logging.info("Found %d images under %s", len(images), input_dir)
    for image_path in images:
        target_dir = make_unique_subdir(base_outdir, image_path.stem)
        logging.info("Processing %s -> %s", image_path, target_dir)
        try:
            process_one(image_path, target_dir, args.date, args.time)
        except Exception as exc:
            logging.exception("Failed processing %s: %s", image_path, exc)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repaint an input image into iPhone lock/home wallpapers and output UI previews.",
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", help="Path to one source image")
    source_group.add_argument("--input-dir", help="Path to source image directory (recursive)")
    parser.add_argument("--outdir", default="out", help="Output directory")
    parser.add_argument("--time", default="22:48", help="Time text for lockscreen preview")
    parser.add_argument("--date", default="3月1日 周日 · 农历正月十三", help="Date text for lockscreen preview")
    return parser.parse_args()


if __name__ == "__main__":
    configure_logging()
    process(parse_args())
