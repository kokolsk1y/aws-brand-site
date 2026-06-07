# -*- coding: utf-8 -*-
"""Надёжный вырез УНО ¾: alpha = силуэт И НЕ(фон). Фон = почти-белый плоский (студия).
Так ВСЕ сквозные белые дыры в монтажной рамке (замок/винты/клипсы) убираются
последовательно, а тёмный материал остаётся. Для светлых клавиш есть guard."""
import os, numpy as np, cv2
from PIL import Image
import sys; sys.path.insert(0, 'scripts')
from whitebg_cutout import _silhouette, _largest_cc
from scipy.ndimage import binary_fill_holes

def cut_uno2(bgr, spill_erode=1, bg_thr=245, bg_grad=8):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, 3); gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, 3)
    grad = cv2.GaussianBlur(np.sqrt(gx*gx + gy*gy), (0, 0), 1.0)

    fg = _silhouette(bgr, 28, 14, False).astype(np.uint8)
    solid = binary_fill_holes(fg).astype(np.uint8)        # сплошной контур товара

    bg_like = (gray >= bg_thr) & (grad <= bg_grad)         # студийный фон (вкл. сквозь дыры)
    alpha_mask = (solid == 1) & (~bg_like)                 # материал внутри контура
    # чистим: убрать «крошки», взять крупное тело, НО НЕ заливать дыры
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    am = cv2.morphologyEx(alpha_mask.astype(np.uint8), cv2.MORPH_OPEN, k)
    am = _largest_cc(am)
    # вернуть мелкие материи рядом (клеммы/винты) которые open мог срезать, но в пределах solid
    am = ((am == 1) | ((alpha_mask) & (cv2.dilate(am, k, iterations=2) == 1))).astype(np.uint8)

    info = {"coverage": round(100*am.mean(), 1)}
    if spill_erode > 0 and am.sum() > 0:
        am = cv2.erode(am, k, iterations=int(spill_erode))
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return np.dstack([rgb, (am*255).astype(np.uint8)]), info


if __name__ == "__main__":
    import zipfile, io, json
    from PIL import ImageDraw
    ROOT = "c:/Users/ikoko/Projects/aws-brand-site"
    mapping = json.load(open(os.path.join(ROOT, "_pipeline/_uno7/mapping.json"), encoding="utf-8"))
    def load(full):
        info = mapping[full]; z = zipfile.ZipFile(os.path.join(ROOT, info['zip']))
        return cv2.cvtColor(np.array(Image.open(io.BytesIO(z.read(info['name']))).convert('RGB')), cv2.COLOR_RGB2BGR)
    def redcheck(rgba, c=12):
        im = Image.fromarray(rgba, 'RGBA'); w, h = im.size
        arr = np.zeros((h, w, 3), np.uint8)
        for y in range(0, h, c):
            for x in range(0, w, c):
                arr[y:y+c, x:x+c] = (230, 120, 120) if ((x//c+y//c) % 2 == 0) else (130, 60, 60)
        bg = Image.fromarray(arr, 'RGB').convert('RGBA'); bg.alpha_composite(im); return bg.convert('RGB')
    tests = ['U2B-002-1 black', 'U1A-002-1 grey', 'U1A-002-1 dark grey',
             'U1A-002-1 silver', 'U1A-006 grey', 'U1A-011 silver']
    tiles = []
    for full in tests:
        bgr = load(full); rgba, inf = cut_uno2(bgr)
        im = redcheck(rgba); th = 300; im = im.resize((int(im.width*th/im.height), th))
        cap = Image.new('RGB', (im.width, th+18), (255, 255, 255)); cap.paste(im, (0, 18))
        ImageDraw.Draw(cap).text((3, 3), full + ' cov=' + str(inf['coverage']), fill=(0, 0, 0))
        tiles.append(cap); print(full, inf)
    W = sum(t.width for t in tiles) + 8*len(tiles); H = max(t.height for t in tiles)
    c = Image.new('RGB', (W, H), (255, 255, 255)); x = 0
    for t in tiles:
        c.paste(t, (x, 0)); x += t.width + 8
    c.save(os.path.join(ROOT, '_pipeline/_uno7/cut2_test.png')); print('saved')
