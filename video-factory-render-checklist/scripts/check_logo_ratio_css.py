#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path('/root/Apps/video_factory/10.Nha_May_San_Xuat_Video')
FILES = [
    ROOT / 'styles.css',
    ROOT / 'templates/03_audio_motion_graphics_720x1280/styles.css.template',
]

def extract_brand_img_blocks(css: str):
    return re.findall(r'\.brand\s+img\s*\{[^}]*\}', css)

def main() -> int:
    ok = True
    for path in FILES:
        if not path.exists():
            print(f'WARN missing {path}')
            continue
        css = path.read_text(encoding='utf-8')
        blocks = extract_brand_img_blocks(css)
        if not blocks:
            print(f'FAIL {path}: missing .brand img rule')
            ok = False
            continue
        for block in blocks:
            compact = re.sub(r'\s+', '', block.lower())
            has_width_auto = 'width:auto' in compact
            has_height = re.search(r'height:[0-9.]+(px|rem|em|%)', compact) is not None
            has_contain = 'object-fit:contain' in compact
            equal_square = re.search(r'width:([0-9.]+)px;?height:\1px', compact) or re.search(r'height:([0-9.]+)px;?width:\1px', compact)
            if equal_square or not (has_width_auto and has_height and has_contain):
                print(f'FAIL {path}: logo rule must use width:auto + fixed height + object-fit:contain; got {block}')
                ok = False
            else:
                print(f'OK {path}: {block}')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
