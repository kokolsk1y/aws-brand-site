# -*- coding: utf-8 -*-
"""
Новые студийные фото «выключатель 1-кл. + рамка» (сплошной фон под цвет продукта)
-> прозрачный центрированный квадрат webp.

Метод:
  - rembg birefnet-general -> силуэт рамки (держит контур на низком контрасте);
  - largest connected component + fill holes (передняя плоскость 1-кл. сплошная);
  - антиореол: эрозия 1px;
  - нормализация масштаба: crop по контуру -> длинная сторона = FILL*холст -> центр;
  - вывод: master 1000 (constructor) + 800 (series) + QC-композиты (шахматка/градиент).

Запуск:
  python scripts/frames_with_bg_cutout.py            # все по MAP
  python scripts/frames_with_bg_cutout.py gold white # фильтр-подстроки по ключу
"""
import sys, os
import numpy as np
import cv2
from scipy.ndimage import binary_fill_holes
from PIL import Image

SRC = 'incoming/frames_with_bg'           # сюда положены img_*.jpg
QC  = 'incoming/frames_with_bg/qc'
CANVAS = 1000
FILL_CON = 0.94       # конструктор: крупно (нет ховер-зума) — длинная сторона = доля холста
FILL_SER = 0.86       # превью серий: поля как у ДИЗАЙН (на ховере не упирается в края)
TOL  = 30              # порог цветового расстояния «похоже на фон» (RGB евклид)
os.makedirs(QC, exist_ok=True)

# ключ -> (исходный файл, цель series, цель constructor|None)
MAP = {
    # УНО
    'uno-white':       ('img_2.jpg',  'uno-1kl-w',           'uno/white'),
    'uno-black':       ('img_11.jpg', 'uno-1kl-b',           'uno/black'),
    'uno-grey':        ('img_7.jpg',  'uno-1kl-grey',        'uno/grey'),
    'uno-dark_grey':   ('img_8.jpg',  'uno-1kl-dark_grey',   'uno/dark_grey'),
    'uno-silver':      ('img_4.jpg',  'uno-1kl-silver',      'uno/silver'),
    'uno-matte_black': ('img_12.jpg', 'uno-1kl-matte_black', 'uno/matte_black'),
    # АУРА (только превью серий; конструктор-материалы не трогаем)
    'aura-white':      ('img_0.jpg',  'aura-1kl-w',          None),
    'aura-black':      ('img_9.jpg',  'aura-1kl-b',          None),
    'aura-grey':       ('img_5.jpg',  'aura-1kl-grey',       None),
    'aura-gold':       ('img_3.jpg',  'aura-1kl-gold',       None),
}


def imread_u(p):
    return cv2.imdecode(np.fromfile(p, np.uint8), cv2.IMREAD_COLOR)


def largest_cc(mask):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if n <= 1:
        return mask.astype(bool)
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return lab == idx


def border_bg(bgr, frac=0.02):
    """Цвет фона = медиана узкой рамки по периметру кадра."""
    h, w = bgr.shape[:2]
    b = max(2, int(min(h, w) * frac))
    ring = np.concatenate([
        bgr[:b].reshape(-1, 3), bgr[-b:].reshape(-1, 3),
        bgr[:, :b].reshape(-1, 3), bgr[:, -b:].reshape(-1, 3),
    ])
    return np.median(ring, 0)


def silhouette(bgr, tol=TOL):
    """Силуэт товара = всё, что flood от краёв (по «похоже на фон») НЕ достал.

    Обобщение метода инфографики на ЛЮБОЙ цвет фона: ключ по цветовому
    расстоянию до угла, а не по яркости. Контактная тень вокруг рамки
    отделяет фон от лицевой панели (того же цвета) → flood не протекает.
    """
    bg = border_bg(bgr)
    diff = np.sqrt(((bgr.astype(np.float32) - bg) ** 2).sum(2))
    bgsim = (diff < tol).astype(np.uint8)            # похоже на фон
    n, lab = cv2.connectedComponents(bgsim, 8)        # компоненты «фоновых» пикселей
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    border.discard(0)
    ext = np.isin(lab, list(border)) & (bgsim > 0)    # внешний фон = касается края
    prod = ~ext
    prod = binary_fill_holes(prod)                    # лицевая панель того же цвета — замыкаем
    prod = largest_cc(prod)
    prod = binary_fill_holes(prod)
    return prod.astype(bool), bg


def to_rgba(rgb, mask):
    m = cv2.erode(mask.astype(np.uint8),
                  cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), 1)  # антиореол 1px
    return np.dstack([rgb, (m * 255).astype(np.uint8)])


def center_square(rgba, canvas=CANVAS, fill=FILL_CON):
    a = rgba[..., 3]
    ys, xs = np.where(a > 10)
    if len(ys) == 0:
        return None
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    crop = rgba[y0:y1+1, x0:x1+1]
    h, w = crop.shape[:2]
    scale = (fill * canvas) / max(h, w)
    nw, nh = max(1, int(round(w*scale))), max(1, int(round(h*scale)))
    crop = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_AREA)
    out = np.zeros((canvas, canvas, 4), np.uint8)
    ox, oy = (canvas - nw)//2, (canvas - nh)//2
    out[oy:oy+nh, ox:ox+nw] = crop
    return out


def on_bg(rgba, kind):
    H, W = rgba.shape[:2]
    if kind == 'checker':
        cell = 24
        yy, xx = np.mgrid[0:H, 0:W]
        chk = (((xx//cell)+(yy//cell)) % 2)
        base = np.where(chk[..., None] == 0, 120, 60).astype(np.uint8).repeat(3, 2)
    elif kind == 'grad':  # имитация радиального фона конструктора
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        cx, cy = W*0.5, H*0.45
        r = np.sqrt((xx-cx)**2 + (yy-cy)**2) / (0.75*max(W, H))
        r = np.clip(r, 0, 1)
        base = (255*(1-r) + 188*r)[..., None].repeat(3, 2).astype(np.uint8)
    else:  # 'light' карточка серии
        base = np.full((H, W, 3), 245, np.uint8)
    al = rgba[..., 3:4].astype(np.float32)/255
    return (rgba[..., :3]*al + base*(1-al)).astype(np.uint8)


def main():
    args = sys.argv[1:]
    dry = '--dry' in args
    flt = [a for a in args if not a.startswith('--')]
    OUT_SER = 'public/img/series'
    OUT_CON = 'public/img/constructor'
    done = 0
    for key, (fn, ser, con) in MAP.items():
        if flt and not any(f in key for f in flt):
            continue
        src = os.path.join(SRC, fn)
        if not os.path.exists(src):
            print('НЕТ ИСХ:', key, src); continue
        bgr = imread_u(src)
        S, bg = silhouette(bgr)
        cov = S.mean()
        rgba = to_rgba(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), S)
        sq_con = center_square(rgba, fill=FILL_CON)   # конструктор крупно
        sq_ser = center_square(rgba, fill=FILL_SER)   # превью серий с полями
        if sq_con is None:
            print('ПУСТО:', key); continue
        if not dry:
            ser800 = cv2.resize(sq_ser, (800, 800), interpolation=cv2.INTER_AREA)
            Image.fromarray(ser800, 'RGBA').save(f'{OUT_SER}/{ser}.webp', 'WEBP', quality=92, method=6)
            if con:
                Image.fromarray(sq_con, 'RGBA').save(f'{OUT_CON}/{con}.webp', 'WEBP', quality=92, method=6)
        # QC: три фона рядом (checker / градиент конструктора / светлая карточка) — превью серий
        tiles = [on_bg(sq_ser, k) for k in ('checker', 'grad', 'light')]
        strip = cv2.resize(np.hstack(tiles), (360*3, 360), interpolation=cv2.INTER_AREA)
        cv2.imencode('.jpg', cv2.cvtColor(strip, cv2.COLOR_RGB2BGR))[1].tofile(f'{QC}/{key}.jpg')
        done += 1
        tag = 'DRY ' if dry else ''
        print(f'  {tag}{key:16s} cov={cov:5.1%} bg={bg.astype(int)[::-1]}  <- {fn}')
    print('Готово:', done)


if __name__ == '__main__':
    main()
