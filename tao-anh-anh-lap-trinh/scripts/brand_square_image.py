#!/usr/bin/env python
"""Make a square Anh Lap Trinh image and overlay the bundled brand image."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOGO = ROOT / "assets" / "anh_lap_trinh_logo.png"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Square image + logo overlay.")
    parser.add_argument("--input", required=True, help="Input image path")
    parser.add_argument("--output", required=True, help="Output image path")
    parser.add_argument("--logo", default=str(DEFAULT_LOGO), help="Logo/brand image path")
    parser.add_argument("--size", type=int, default=1080, help="Square output size in px")
    parser.add_argument("--logo-scale", type=float, default=0.18, help="Logo width relative to canvas")
    parser.add_argument("--margin-scale", type=float, default=0.035, help="Margin relative to canvas")
    return parser.parse_args()


def fit_square(image: Image.Image, size: int) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    return ImageOps.fit(image, (size, size), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def overlay_logo(base: Image.Image, logo_path: Path, logo_scale: float, margin_scale: float) -> Image.Image:
    if not logo_path.exists():
        raise FileNotFoundError(f"Logo not found: {logo_path}")

    canvas = base.convert("RGBA")
    logo = ImageOps.exif_transpose(Image.open(logo_path)).convert("RGBA")

    target_w = max(80, int(canvas.width * logo_scale))
    target_h = max(1, int(logo.height * (target_w / logo.width)))
    logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)

    margin = int(canvas.width * margin_scale)
    x = canvas.width - logo.width - margin
    y = canvas.height - logo.height - margin

    canvas.alpha_composite(logo, (x, y))
    return canvas.convert("RGB")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    logo_path = Path(args.logo)

    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    base = fit_square(Image.open(input_path), args.size)
    result = overlay_logo(base, logo_path, args.logo_scale, args.margin_scale)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, quality=95)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
