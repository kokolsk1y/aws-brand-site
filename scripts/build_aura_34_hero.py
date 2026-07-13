# -*- coding: utf-8 -*-
"""
АУРА: ¾-ракурс («ракурс 3х4», index _1) — геройское фото для всех цветов.

Источник — уже вырезанные (без фона) ¾ из проекта infografika:
  <INF>/<ART>/<ART> 1 без фона_nobg.png
Проблема источника: объект занимает ~0.70 холста (portrait 750×1000), а фото
на сайте — 0.918 (золото/серый) и 0.942 (чёрный/белый). Поэтому НОРМАЛИЗУЕМ:
обрезка по контуру → длинная сторона = FILL_цвета × 1600 → центр квадрата 1600.

Вход:  артикулы, у которых уже есть фото в public/img/products (все цвета AURA A-*)
Выход: staging  _incoming_aura/hero34_out/<ART>_1.webp   (НЕ в public)
       size-QC   _incoming_aura/hero34_out/_qc_size.jpg   (¾ рядом с лицом-эталоном)

Запуск: python scripts/build_aura_34_hero.py
"""
import os, re, sys
import numpy as np
import cv2
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

SITE = 'public/img/products'
INF  = r'C:\Users\ikoko\Projects\infografika\assets\aura'
OUT  = '_incoming_aura/hero34_out'
CANVAS = 1600
os.makedirs(OUT, exist_ok=True)

# FILL по цвету — совпадает с существующими фото серии на сайте.
FILL_GOLD_GREY = 0.918   # золото/серый: как _2.._5 (пайплайн cutout_aura.py)
FILL_BLACK_WHITE = 0.942 # чёрный/белый: как существующее лицо (A-001B.webp)

def color_fill(art):
    if art.endswith('GR') or art.endswith('G'):
        return FILL_GOLD_GREY
    return FILL_BLACK_WHITE  # B / W

def inf_hero_path(art):
    return os.path.join(INF, art, f'{art} 1 без фона_nobg.png')

def load_rgba(path):
    im = Image.open(path).convert('RGBA')
    return np.array(im)  # HxWx4 RGBA

def center_square(rgba, fill):
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

def on_bg(rgba, bg=(229, 229, 228)):
    """Композит на серый фон карточки сайта (#e5e5e4)."""
    al = rgba[..., 3:4].astype(np.float32) / 255
    base = np.zeros_like(rgba[..., :3]); base[:] = bg
    return (rgba[..., :3]*al + base*(1-al)).astype(np.uint8)

def site_articles():
    arts = set()
    for f in os.listdir(SITE):
        m = re.match(r'(A-\d+[A-Z]*?)(_\d+)?\.(webp|png|jpg|jpeg)$', f, re.I)
        if m:
            arts.add(m.group(1))
    return sorted(arts)

def site_face(art):
    """Эталон-лицо для size-QC: main-файл (Ч/Б) или _2 (З/С)."""
    for cand in [f'{art}.webp', f'{art}.png', f'{art}_2.webp', f'{art}_2.png']:
        p = os.path.join(SITE, cand)
        if os.path.exists(p):
            return p
    return None

def main():
    arts = site_articles()
    print(f'AURA-артикулов на сайте: {len(arts)}')
    made, missing = [], []
    for art in arts:
        src = inf_hero_path(art)
        if not os.path.exists(src):
            missing.append(art); continue
        sq = center_square(load_rgba(src), color_fill(art))
        if sq is None:
            missing.append(art); continue
        Image.fromarray(sq, 'RGBA').save(os.path.join(OUT, f'{art}_1.webp'), 'WEBP', quality=92, method=6)
        made.append(art)
    print(f'сделано: {len(made)} | без источника: {len(missing)} -> {missing}')

    # size-QC: по одному артикулу на цвет — ¾ рядом с лицом, оба на сером фоне.
    samples = ['A-001B', 'A-001W', 'A-001G', 'A-001GR', 'A-009GR', 'A-013G']
    tiles = []
    for art in samples:
        newp = os.path.join(OUT, f'{art}_1.webp')
        facep = site_face(art)
        if not os.path.exists(newp) or not facep:
            continue
        new = on_bg(cv2.resize(np.array(Image.open(newp).convert('RGBA')), (400, 400)))
        face = np.array(Image.open(facep).convert('RGBA'))
        face = on_bg(cv2.resize(face, (400, 400)))
        lab = np.full((26, 800, 3), 255, np.uint8)
        from PIL import ImageDraw
        pim = Image.fromarray(lab); ImageDraw.Draw(pim).text((4, 6), f'{art}:  NEW 3/4  |  site face', fill=(0, 0, 0))
        pair = np.hstack([new, face])
        # разделитель
        pair[:, 399:401] = (200, 60, 60)
        tiles.append(np.vstack([np.array(pim), pair]))
    if tiles:
        sheet = np.vstack(tiles)
        cv2.imencode('.jpg', cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))[1].tofile(os.path.join(OUT, '_qc_size.jpg'))
        print('size-QC ->', os.path.join(OUT, '_qc_size.jpg'))

if __name__ == '__main__':
    main()
