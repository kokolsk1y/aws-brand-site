# -*- coding: utf-8 -*-
"""
АУРА-РАМКИ: ¾-ракурс («ракурс 3х4», index _1) — геройское фото.
Источник — уже вырезанные (без фона) ¾ рамок из папки на рабочем столе
(корень, не БЕЛЫЕ/ЧЁРНЫЕ): G50/G51/P50/PG51 (белые) + W30 (дерево).

Нормализация как у существующих рамок серии: длинная сторона = 0.918×1600,
центр квадрата 1600, натуральная ориентация (НЕ вращаем — фронтальные рамки
на сайте тоже в натуральной ориентации).

Вход:  <DESK>/*.png  (только рамки — в корне папки)
Выход: staging  _incoming_aura/hero34_out/<ART>_1.webp
       QC       _incoming_aura/hero34_out/_qc_frames.jpg  (все на сером фоне карточки)

Запуск: python scripts/build_aura_34_frames.py
"""
import os, glob
import numpy as np
import cv2
from PIL import Image, ImageDraw

import sys
sys.stdout.reconfigure(encoding='utf-8')

DESK = r'C:\Users\ikoko\OneDrive\Desktop\АУРА РАКУРС 3 НА 4 БЕЗ ФОНА'
OUT  = '_incoming_aura/hero34_out'
CANVAS = 1600
FILL = 0.918   # как у существующих рамок серии
CARD_BG = (229, 229, 228)  # #e5e5e4 — фон карточки товара
os.makedirs(OUT, exist_ok=True)

def center_square(rgba, fill=FILL):
    a = rgba[..., 3]
    ys, xs = np.where(a > 10)
    if len(ys) == 0:
        return None
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    crop = rgba[y0:y1+1, x0:x1+1]
    h, w = crop.shape[:2]
    scale = (fill * CANVAS) / max(h, w)
    nw, nh = max(1, int(round(w*scale))), max(1, int(round(h*scale)))
    crop = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((CANVAS, CANVAS, 4), np.uint8)
    ox, oy = (CANVAS - nw)//2, (CANVAS - nh)//2
    canvas[oy:oy+nh, ox:ox+nw] = crop
    return canvas

def on_bg(rgba, bg=CARD_BG):
    al = rgba[..., 3:4].astype(np.float32) / 255
    base = np.zeros_like(rgba[..., :3]); base[:] = bg
    return (rgba[..., :3]*al + base*(1-al)).astype(np.uint8)

def main():
    files = sorted(glob.glob(os.path.join(DESK, '*.png')))  # только корень = рамки
    print(f'рамок-источников: {len(files)}')
    made = []
    for f in files:
        art = os.path.splitext(os.path.basename(f))[0]
        im = np.array(Image.open(f).convert('RGBA'))
        sq = center_square(im)
        if sq is None:
            print('  ПУСТО:', art); continue
        Image.fromarray(sq, 'RGBA').save(os.path.join(OUT, f'{art}_1.webp'), 'WEBP', quality=92, method=6)
        made.append(art)
    print(f'сделано: {len(made)} -> {made}')

    # QC: все рамки на сером фоне карточки — видно, прозрачны ли проёмы
    cols = 5
    tiles = []
    row = []
    for art in made:
        sq = np.array(Image.open(os.path.join(OUT, f'{art}_1.webp')).convert('RGBA'))
        t = on_bg(cv2.resize(sq, (300, 300)))
        cap = np.full((22, 300, 3), 255, np.uint8)
        pim = Image.fromarray(cap); ImageDraw.Draw(pim).text((4, 5), art, fill=(0, 0, 0))
        row.append(np.vstack([np.array(pim), t]))
        if len(row) == cols:
            tiles.append(np.hstack(row)); row = []
    if row:
        while len(row) < cols:
            row.append(np.full_like(row[0], 255))
        tiles.append(np.hstack(row))
    if tiles:
        sheet = np.vstack(tiles)
        cv2.imencode('.jpg', cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))[1].tofile(os.path.join(OUT, '_qc_frames.jpg'))
        print('QC ->', os.path.join(OUT, '_qc_frames.jpg'))

if __name__ == '__main__':
    main()
