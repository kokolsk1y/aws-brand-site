# -*- coding: utf-8 -*-
"""Хирургический cutout для УНО ¾: фон 255 убираем, силуэт 1:1, и прорезаем ТОЛЬКО
сквозные дыры (монтажные слоты), где сквозь товар виден чисто-белый фон (==255, плоский).
Серые углубления розетки (пластик, не 255) НЕ трогаем."""
import os, numpy as np, cv2
from PIL import Image
import sys; sys.path.insert(0, 'scripts')
from whitebg_cutout import _silhouette
from scipy.ndimage import label, binary_fill_holes

def cut_uno(bgr, spill_erode=1, punch=True):
    from scipy.ndimage import binary_dilation
    H, W = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, 3); gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, 3)
    grad = cv2.GaussianBlur(np.sqrt(gx*gx + gy*gy), (0, 0), 1.0)

    fg = _silhouette(bgr, white_tol=28, grad_tol=14, remove_openings=False).astype(np.uint8)
    solid = binary_fill_holes(fg).astype(np.uint8)   # товар сплошной
    solid_area = max(int(solid.sum()), 1)

    info = {"coverage": round(100*solid.mean(), 1), "punched": 0}
    if punch:
        # ЧИСТО-ФОНОВЫЕ пиксели = студийный фон 255, идеально плоский (НЕ серый пластик розетки)
        pure_bg = (gray >= 252) & (grad <= 3)
        # внешний фон = pure_bg, связанный с краем кадра
        lab0, n0 = label(pure_bg)
        border = set(np.unique(np.concatenate([lab0[0], lab0[-1], lab0[:, 0], lab0[:, -1]]))); border.discard(0)
        outer = np.isin(lab0, list(border)) if border else np.zeros_like(pure_bg)
        # материал товара = внутри силуэта и НЕ чисто-фон
        material = (solid == 1) & (~pure_bg)
        # кандидаты в сквозные слоты: чисто-фон ВНУТРИ силуэта, не внешний фон
        inner = pure_bg & (solid == 1) & (~outer)
        il, ino = label(inner)
        punched = np.zeros_like(solid)
        for i in range(1, ino+1):
            comp = il == i
            a = int(comp.sum())
            if a < 50 or a > 0.40*solid_area:        # мелочь / слишком крупное -> не слот
                continue
            ring = binary_dilation(comp, iterations=6) & (~comp) & (solid == 1)
            if ring.sum() > 0 and material[ring].mean() > 0.6:   # окружён материалом -> сквозной слот
                punched[comp] = 1
        solid = (solid & (~punched.astype(bool))).astype(np.uint8)
        info["punched"] = int(punched.sum())

    if spill_erode > 0 and solid.sum() > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        solid = cv2.erode(solid, k, iterations=int(spill_erode))
    alpha = (solid*255).astype(np.uint8)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return np.dstack([rgb, alpha]), info


if __name__ == "__main__":
    import zipfile, io
    ROOT = "c:/Users/ikoko/Projects/aws-brand-site"
    from PIL import ImageDraw
    def get(zp, frag):
        z = zipfile.ZipFile(os.path.join(ROOT, zp))
        for n in z.namelist():
            if frag in n and n.lower().endswith(('.jpg', '.jpeg', '.png')):
                return cv2.cvtColor(np.array(Image.open(io.BytesIO(z.read(n))).convert('RGB')), cv2.COLOR_RGB2BGR)
    def checker(rgba, c=16):
        im = Image.fromarray(rgba, 'RGBA'); w, h = im.size
        arr = np.zeros((h, w, 3), np.uint8)
        for y in range(0, h, c):
            for x in range(0, w, c):
                arr[y:y+c, x:x+c] = (215, 215, 215) if ((x//c+y//c) % 2 == 0) else (95, 95, 95)
        bg = Image.fromarray(arr, 'RGB').convert('RGBA'); bg.alpha_composite(im); return bg.convert('RGB')
    tests = [('silver.zip', 'U1A-003 silver', 'switch U1A-003'),
             ('grey.zip', 'U1A-022 grey', 'socket U1A-022'),
             ('silver.zip', 'U1A-011 silver', 'socket2 U1A-011')]
    tiles = []
    for zp, frag, tag in tests:
        bgr = get(zp, frag)
        rgba, inf = cut_uno(bgr)
        print(tag, inf)
        im = checker(rgba); th = 360; im = im.resize((int(im.width*th/im.height), th))
        d = ImageDraw.Draw(im);
        cap = Image.new('RGB', (im.width, th+20), (255, 255, 255)); cap.paste(im, (0, 20))
        ImageDraw.Draw(cap).text((3, 4), tag, fill=(0, 0, 0)); tiles.append(cap)
    W = sum(t.width for t in tiles)+16; H = max(t.height for t in tiles)
    c = Image.new('RGB', (W, H), (255, 255, 255)); x = 0
    for t in tiles:
        c.paste(t, (x, 0)); x += t.width+8
    c.save(os.path.join(ROOT, '_pipeline/_uno7/surgical_test.png')); print('saved')
