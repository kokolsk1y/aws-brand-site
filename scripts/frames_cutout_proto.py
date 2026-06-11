# -*- coding: utf-8 -*-
"""Прототип выреза ¾-рамок тем же методом, что и сайт (whitebg_cutout.py).
Крупные композиты на шахматном фоне (свет+тьма) по каждому товару отдельно —
для визуального контроля повреждений кромки/защёлок/проёмов. В public/ не пишет."""
import os, sys
import numpy as np
import cv2
from PIL import Image

ROOT = "c:/Users/ikoko/Projects/aws-brand-site"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from whitebg_cutout import cutout

OUT = os.path.join(ROOT, "scripts", "cache", "frame_check")
os.makedirs(OUT, exist_ok=True)

TESTS = [
    ("U1A-028 white.webp", "028_white"),
    ("U1A-030 white.webp", "030_white"),
    ("U1A-030 grey.jpeg",  "030_grey"),
]

def imread_u(p):
    return cv2.imdecode(np.fromfile(p, np.uint8), cv2.IMREAD_COLOR)

def checker_pair(rgba, cell=22):
    """Возвращает композит: слева светлая шахматка, справа тёмная."""
    h, w = rgba.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    chk = ((xx // cell) + (yy // cell)) % 2
    a = rgba[..., 3:4].astype(np.float32) / 255
    rgb = rgba[..., :3].astype(np.float32)
    light = np.where(chk[..., None] == 0, 215, 165).astype(np.uint8).repeat(3, 2)
    dark = np.where(chk[..., None] == 0, 70, 30).astype(np.uint8).repeat(3, 2)
    cl = (rgb * a + light * (1 - a)).astype(np.uint8)
    cd = (rgb * a + dark * (1 - a)).astype(np.uint8)
    gap = np.full((h, 6, 3), 255, np.uint8)
    return np.hstack([cl, gap, cd])

for fn, tag in TESTS:
    bgr = imread_u(os.path.join(ROOT, fn))
    rgba, info = cutout(bgr, remove_openings=True, adaptive=True)
    print(f"{tag:12} {info}")
    comp = checker_pair(rgba)
    Image.fromarray(comp).save(os.path.join(OUT, f"_CHK_{tag}.png"))
    # отдельно RGBA-результат (как пойдёт на сайт)
    Image.fromarray(rgba, "RGBA").save(os.path.join(OUT, f"_RGBA_{tag}.png"))
print("готово ->", OUT)
