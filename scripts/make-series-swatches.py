# -*- coding: utf-8 -*-
"""
Прозрачные свотчи серий 800x800 из фото в сборе (_pipeline/одноклавишные-в-сборе).
Фон убирается через whitebg_cutout.cutout() — классический CV по связности (см. модуль).
Выход: public/img/series/<series>-1kl-<color>.webp
Существующие *-1kl-w/b.webp (Аура/УНО) НЕ трогаем — генерим только новые цвета + Дизайн.
"""
import glob
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
from whitebg_cutout import cutout

ROOT = Path("c:/Users/ikoko/Projects/aws-brand-site")
SRC  = ROOT / "_pipeline" / "одноклавишные-в-сборе"
DST  = ROOT / "public" / "img" / "series"
CANVAS, FILL = 800, 0.82

JOBS = [
    ("U1A-001-1 grey.jpg",        "uno-1kl-grey.webp"),
    ("U1A-001-1 dark grey.jpg",   "uno-1kl-dark_grey.webp"),
    ("U1A-001-1 silver.jpg",      "uno-1kl-silver.webp"),
    ("U2B-001-1 matte black.jpg", "uno-1kl-matte_black.webp"),
    ("*B30-1GR*",                 "aura-1kl-grey.webp"),   # серый, рамка B30 алюминий
    ("*B30-1G [!R]*",             "aura-1kl-gold.webp"),   # золото B30 (не GR)
    ("A-D001W.jpg",               "design-1kl-w.webp"),
    ("A-D001B.jpg",               "design-1kl-b.webp"),
    ("A-D001GR.jpg",              "design-1kl-grey.webp"),
]

def imread_u(path):
    return cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)

def main():
    DST.mkdir(parents=True, exist_ok=True)
    ok = 0
    for pat, dst in JOBS:
        hits = sorted(glob.glob(str(SRC / pat)))
        if not hits:
            print("  ПРОПУСК (нет источника):", pat); continue
        rgba, info = cutout(imread_u(hits[0]))
        if info["coverage"] < 15:
            print("  ⚠ ПОДОЗРИТЕЛЬНО (%s%%) — на ручную проверку: %s" % (info["coverage"], dst)); continue
        im = Image.fromarray(rgba, "RGBA")
        im = im.crop(im.getchannel("A").getbbox())
        bw, bh = im.size; sc = (CANVAS * FILL) / max(bw, bh)
        im = im.resize((max(1, round(bw*sc)), max(1, round(bh*sc))), Image.LANCZOS)
        cv = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
        cv.paste(im, ((CANVAS-im.width)//2, (CANVAS-im.height)//2), im)
        cv.save(DST / dst, "WEBP", quality=90, method=6)
        print("  OK -> %-26s (cov %s%%)" % (dst, info["coverage"])); ok += 1
    print("\nГотово: %d/%d свотчей" % (ok, len(JOBS)))

if __name__ == "__main__":
    main()
