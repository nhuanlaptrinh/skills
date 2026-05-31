#!/usr/bin/env python
"""Compose a square Anh Lap Trinh post with Vietnamese text and logo."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLED_LOGO = ROOT / "assets" / "anh_lap_trinh_logo.png"
DEFAULT_EXTERNAL_LOGO = Path(r"D:\00.Demo\54.Demo3In1\logo3.png")
DEFAULT_BOLD_FONT = Path(r"C:\Windows\Fonts\arialbd.ttf")


def default_logo_path() -> Path:
    if DEFAULT_EXTERNAL_LOGO.exists():
        return DEFAULT_EXTERNAL_LOGO
    return DEFAULT_BUNDLED_LOGO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose square social image.")
    parser.add_argument("--input", required=True, help="Background image path")
    parser.add_argument("--output", required=True, help="Output image path")
    parser.add_argument("--headline", required=True, help="Main headline")
    parser.add_argument("--subheadline", default="", help="Short supporting line")
    parser.add_argument("--badge", default="", help="Small CTA/badge")
    parser.add_argument("--logo", default=str(default_logo_path()), help="Logo image path")
    parser.add_argument("--size", type=int, default=1080, help="Square output size")
    parser.add_argument("--logo-scale", type=float, default=0.18, help="Logo width relative to canvas")
    parser.add_argument("--theme", default="ai", choices=["ai", "course", "tool"], help="Color theme")
    return parser.parse_args()


def load_font(size: int) -> ImageFont.FreeTypeFont:
    if DEFAULT_BOLD_FONT.exists():
        return ImageFont.truetype(str(DEFAULT_BOLD_FONT), size)
    return ImageFont.load_default(size=size)


def fit_square(path: Path, size: int) -> Image.Image:
    image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return ImageOps.fit(image, (size, size), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)).convert("RGBA")


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        test = f"{current} {word}"
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def split_headline(headline: str) -> list[str]:
    words = headline.split()
    if len(words) <= 4:
        return [headline]
    midpoint = (len(words) + 1) // 2
    return [" ".join(words[:midpoint]), " ".join(words[midpoint:])]


def draw_shadow_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
) -> None:
    x, y = xy
    shadow = (0, 0, 0, 210)
    draw.text((x + 4, y + 5), text, font=font, fill=shadow, stroke_width=2, stroke_fill=shadow)
    draw.text((x, y), text, font=font, fill=fill, stroke_width=2, stroke_fill=(0, 0, 0, 95))


def theme_colors(theme: str) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    if theme == "course":
        return (255, 255, 255, 255), (255, 204, 51, 255)
    if theme == "tool":
        return (255, 255, 255, 255), (86, 220, 145, 255)
    return (255, 255, 255, 255), (180, 235, 80, 255)


def add_text(base: Image.Image, headline: str, subheadline: str, badge: str, theme: str) -> Image.Image:
    size = base.width
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle((0, 0, int(size * 0.68), int(size * 0.40)), fill=(2, 18, 38, 138))
    overlay = overlay.filter(ImageFilter.GaussianBlur(18))
    image = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(image)

    head_font = load_font(76)
    sub_font = load_font(36)
    badge_font = load_font(46)
    white, accent = theme_colors(theme)

    x = 56
    y = 55
    for index, line in enumerate(split_headline(headline.upper())):
        draw_shadow_text(draw, (x, y), line, head_font, white if index == 0 else accent)
        y += 84

    if subheadline:
        sub_lines = wrap_text(draw, subheadline, sub_font, int(size * 0.70))
        for line in sub_lines[:2]:
            bbox = draw.textbbox((0, 0), line, font=sub_font)
            line_w = bbox[2] - bbox[0]
            line_h = bbox[3] - bbox[1]
            box = (52, y + 28, 52 + line_w + 44, y + 28 + line_h + 34)
            draw.rounded_rectangle(box, radius=16, fill=(0, 102, 210, 228), outline=(122, 204, 255, 170), width=2)
            draw.text((76, y + 42), line, font=sub_font, fill=(255, 255, 255, 255))
            y += line_h + 52

    if badge:
        bbox = draw.textbbox((0, 0), badge, font=badge_font)
        badge_w = bbox[2] - bbox[0]
        badge_h = bbox[3] - bbox[1]
        box = (52, y + 18, 52 + badge_w + 54, y + 18 + badge_h + 32)
        draw.rounded_rectangle(box, radius=16, fill=(61, 165, 49, 235), outline=(190, 255, 120, 160), width=2)
        draw.text((79, y + 30), badge, font=badge_font, fill=(255, 255, 255, 255))

    return image


def add_logo(base: Image.Image, logo_path: Path, logo_scale: float) -> Image.Image:
    if not logo_path.exists():
        raise FileNotFoundError(f"Logo not found: {logo_path}")
    image = base.copy()
    draw = ImageDraw.Draw(image)
    logo = ImageOps.exif_transpose(Image.open(logo_path)).convert("RGBA")
    logo_w = int(image.width * logo_scale)
    logo_h = int(logo.height * logo_w / logo.width)
    logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
    margin = int(image.width * 0.035)
    pad = 8
    x = image.width - logo_w - margin
    y = image.height - logo_h - margin
    draw.rounded_rectangle((x - pad, y - pad, x + logo_w + pad, y + logo_h + pad), radius=6, fill=(255, 255, 255, 235))
    image.alpha_composite(logo, (x, y))
    return image


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    base = fit_square(input_path, args.size)
    result = add_text(base, args.headline, args.subheadline, args.badge, args.theme)
    result = add_logo(result, Path(args.logo), args.logo_scale)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.convert("RGB").save(output_path, quality=95)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
