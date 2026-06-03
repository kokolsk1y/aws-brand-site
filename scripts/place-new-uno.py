# -*- coding: utf-8 -*-
"""
Раскладка новых каталожных фото УНО (_pipeline/уно-доп-ракурсы) в public/img/products:
убрать белый фон (whitebg_cutout), ВЫКИНУТЬ упаковку (визуально подтверждённый список),
рамкам сделать прозрачные проёмы, переименовать в конвенцию сайта:
"{article}.webp" + "{article}_2.webp", ... (article включает цвет).
Сначала удаляет ранее разложенные файлы этих артикулов (чистый перезапуск).
"""
import glob, re
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
from whitebg_cutout import cutout

ROOT = Path("c:/Users/ikoko/Projects/aws-brand-site")
SRC = ROOT / "_pipeline" / "уно-доп-ракурсы"
PROD = ROOT / "public" / "img" / "products"

# (префикс файла-источника, целевой артикул, это_рамка?)
GROUPS = [
    ("U1A-016-2 dark grey", "U1A-016-2 dark grey", False),  # RJ45 розетка
    ("U1A-029-2",           "U1A-029-2 white",     True),   # рамка 2-я
    ("U1A-031-2",           "U1A-031-2 white",     True),   # рамка 3-я
    ("U2B-007",             "U2B-007 black",       False),  # выключатель звонка
    ("U2B-029-2",           "U2B-029-2 black",     True),   # рамка 2-я
    ("U2B-031-2",           "U2B-031-2 black",     True),   # рамка 3-я
]
# упаковка (товар в пакете) — подтверждено визуально, не выгружать
PACKAGING = {
    "U1A-016-2 dark grey-5", "U1A-016-2 dark grey-6", "U2B-007-4",
    "U1A-029-2-2", "U1A-031-2-3", "U2B-029-2-3", "U2B-031-2-3",
}

def angle_of(stem, prefix):
    rest = stem[len(prefix):].strip()
    m = re.match(r"-?(\d+)$", rest)
    return int(m.group(1)) if m else 0

def to_bgr(path):
    return cv2.cvtColor(np.array(Image.open(path).convert("RGB")), cv2.COLOR_RGB2BGR)

def main():
    # чистый перезапуск: удалить ранее разложенные файлы этих артикулов
    for _, article, _ in GROUPS:
        for old in glob.glob(str(PROD / (article + ".webp"))) + glob.glob(str(PROD / (article + "_*.webp"))):
            Path(old).unlink()
    total = 0
    for prefix, article, is_frame in GROUPS:
        files = []
        for f in glob.glob(str(SRC / (prefix + "*.jpg"))):
            stem = Path(f).stem
            if stem != prefix and not re.fullmatch(re.escape(prefix) + r"-\d+", stem):
                continue
            if stem in PACKAGING:
                print("  упаковка, пропуск:", stem); continue
            files.append((angle_of(stem, prefix), f))
        files.sort(key=lambda x: x[0])
        for idx, (a, f) in enumerate(files):
            name = f"{article}.webp" if idx == 0 else f"{article}_{idx + 1}.webp"
            rgba, info = cutout(to_bgr(f), remove_openings=is_frame)
            Image.fromarray(rgba, "RGBA").save(PROD / name, "WEBP", quality=90, method=6)
            print("  %-26s <- %-28s cov=%s%% %s" % (name, Path(f).name, info["coverage"], "рамка" if is_frame else ""))
            total += 1
    print("\nРазложено новых УНО (без упаковки):", total)

if __name__ == "__main__":
    main()
