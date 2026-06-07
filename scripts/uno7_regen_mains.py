# -*- coding: utf-8 -*-
"""Перегенерация ¾-главных УНО по финальной схеме и обновление ТОЛЬКО главных фото в public.
  -022 (двойные розетки) -> плоский cutout; остальные -> cut_uno2 (надёжный, убирает заглушки).
Сдвиг ракурсов уже применён ранее — здесь только перезапись главного {артикул}.webp + sync dist."""
import zipfile, os, json, io, re, shutil
import numpy as np, cv2
from PIL import Image
import sys; sys.path.insert(0, 'scripts')
from whitebg_cutout import cutout
from uno7_cut2 import cut_uno2

ROOT = "c:/Users/ikoko/Projects/aws-brand-site"
PROD = os.path.join(ROOT, "public/img/products")
DIST = os.path.join(ROOT, "dist/img/products")
CUTS = os.path.join(ROOT, "_pipeline/_uno7/cuts")
mapping = json.load(open(os.path.join(ROOT, "_pipeline/_uno7/mapping.json"), encoding="utf-8"))

cache = {}; updated = 0; skipped = []
for full, info in sorted(mapping.items()):
    if '-022 ' in full:                           # ДВОЙНЫЕ РОЗЕТКИ — не трогаем (владелец: они ок)
        skipped.append(full); continue
    z = zipfile.ZipFile(os.path.join(ROOT, info['zip']))
    key = (info['zip'], info['name'])
    if key not in cache:
        bgr = cv2.cvtColor(np.array(Image.open(io.BytesIO(z.read(info['name']))).convert('RGB')), cv2.COLOR_RGB2BGR)
        rgba, _ = cut_uno2(bgr)                    # надёжный bg-hole: убирает заглушки, клавиши/углубления целы
        cache[key] = rgba
    Image.fromarray(cache[key], 'RGBA').save(os.path.join(CUTS, full + '.webp'), 'WEBP', quality=90, method=6)
    shutil.copyfile(os.path.join(CUTS, full + '.webp'), os.path.join(PROD, full + '.webp'))   # перезапись ТОЛЬКО главного
    if os.path.isdir(DIST):
        shutil.copyfile(os.path.join(PROD, full + '.webp'), os.path.join(DIST, full + '.webp'))
    updated += 1
print("glavnyh obnovleno:", updated, "(cut_uno2); NE tronuto dvoynyh -022:", len(skipped), skipped)
print("dist sync:", os.path.isdir(DIST))
