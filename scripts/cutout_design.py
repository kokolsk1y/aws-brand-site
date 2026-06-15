# -*- coding: utf-8 -*-
"""
Серия ДИЗАЙН: вырез фона (rembg) + вырез проёмов у рамок + центрирование
в квадрат -> прозрачные webp в public/img/products/ (перезапись).

Метод:
  - rembg isnet-general-use -> чистый внешний силуэт (глянец/углы/тени);
  - РАМКИ (PD80*): дополнительно вырезаем проёмы = ультра-плоский яркий фон,
    видимый сквозь отверстия (детект по gray>=248 & низкий градиент);
  - чистка края: порог альфы + эрозия 1px (антиореол);
  - центрирование: обрезка по контуру -> длинная сторона = FILL*холст -> центр квадрата.
"""
import sys, glob, io, os
from pathlib import Path
import numpy as np
import cv2
from scipy.ndimage import label, binary_fill_holes, binary_dilation
from PIL import Image
from rembg import remove, new_session

sys.path.insert(0, 'scripts')
from place_design_photos import MAP  # article -> stem

RAW = 'incoming/design_raw'
OUT = 'public/img/products'
QC = 'incoming/design_crops/qc'
CANVAS = 1600
FILL = 0.86          # длинная сторона товара = доля холста
os.makedirs(QC, exist_ok=True)

SESS = new_session('isnet-general-use')        # механизмы
SESS_FRAME = new_session('birefnet-general')    # рамки (держит сквозные проёмы)

def imread_u(p):
    return cv2.imdecode(np.fromfile(p, np.uint8), cv2.IMREAD_COLOR)

def rembg_rgba(bgr, sess=None):
    ok, buf = cv2.imencode('.png', bgr)
    out = remove(buf.tobytes(), session=sess or SESS)
    a = cv2.imdecode(np.frombuffer(out, np.uint8), cv2.IMREAD_UNCHANGED)
    if a.shape[2] == 4:
        return np.dstack([cv2.cvtColor(a[..., :3], cv2.COLOR_BGR2RGB), a[..., 3]])
    return np.dstack([cv2.cvtColor(a, cv2.COLOR_BGR2RGB), np.full(a.shape[:2], 255, np.uint8)])

def _largest_cc(mask):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if n <= 1:
        return mask.astype(bool)
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return lab == idx

def solid_silhouette(rgba):
    """Сплошной непрозрачный силуэт товара: убирает полупрозрачность/дыры
    внутри (от rembg) -> белая поверхность НЕ сереет, тело не рвётся."""
    m = rgba[..., 3] > 50
    m = _largest_cc(m)
    m = binary_fill_holes(m)
    return m.astype(bool)

def punch_openings(S, bgr):
    """По сплошному силуэту S выбивает ТОЛЬКО проёмы рамки:
    яркий плоский фон, видимый сквозь отверстия — компактный и замкнутый."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, 3); gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, 3)
    grad = cv2.GaussianBlur(np.sqrt(gx*gx + gy*gy), (0, 0), 1.0)
    cand = (gray >= 244) & (grad <= 7) & S
    lab, n = label(cand)
    area_S = max(int(S.sum()), 1)
    out = S.copy()
    for i in range(1, n + 1):
        comp = lab == i
        a = int(comp.sum())
        if a < 0.006 * area_S:                       # мелочь
            continue
        if (binary_dilation(comp, iterations=8) & (~S)).any():   # не замкнут материалом -> краевой надкус
            continue
        ys, xs = np.where(comp)                       # компактность (проём — «пятно», а не сливер)
        bb = (ys.max()-ys.min()+1) * (xs.max()-xs.min()+1)
        if a / max(bb, 1) < 0.45:
            continue
        comp = cv2.erode(comp.astype(np.uint8), np.ones((3, 3), np.uint8), 1).astype(bool)
        out[comp] = False
    return out

def to_rgba(rgb, mask):
    m = cv2.erode(mask.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), 1)  # антиореол 1px
    return np.dstack([rgb, (m * 255).astype(np.uint8)])

def center_square(rgba):
    a = rgba[..., 3]
    ys, xs = np.where(a > 10)
    if len(ys) == 0:
        return None
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    crop = rgba[y0:y1+1, x0:x1+1]
    h, w = crop.shape[:2]
    scale = (FILL * CANVAS) / max(h, w)
    nw, nh = max(1, int(round(w*scale))), max(1, int(round(h*scale)))
    crop = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((CANVAS, CANVAS, 4), np.uint8)
    ox, oy = (CANVAS - nw)//2, (CANVAS - nh)//2
    canvas[oy:oy+nh, ox:ox+nw] = crop
    return canvas

def on_checker(rgba, cell=22, dark=True):
    H, W = rgba.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    chk = (((xx//cell)+(yy//cell)) % 2)
    base = np.where(chk[..., None] == 0, 90 if dark else 235, 30 if dark else 200).astype(np.uint8).repeat(3, 2)
    al = rgba[..., 3:4].astype(np.float32)/255
    return (rgba[..., :3]*al + base*(1-al)).astype(np.uint8)

def resolve(stem):
    hits = [h for h in glob.glob(f'{RAW}/IMG_{stem}.*')
            if os.path.splitext(os.path.basename(h))[0] == f'IMG_{stem}']
    return hits[0] if hits else None

def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None   # подстрока-фильтр артикула
    done = 0
    for art, stem in MAP.items():
        if only and only not in art:
            continue
        src = resolve(stem)
        if not src:
            print('НЕТ ИСХ:', art, stem); continue
        bgr = imread_u(src)
        if art.startswith('PD80'):
            # РАМКИ: birefnet сам держит проёмы. Берём силуэт с дырами, чистим спеклы
            # (только крупнейший компонент тела), проёмы-дыры сохраняются.
            rgba = rembg_rgba(bgr, SESS_FRAME)
            S = _largest_cc(rgba[..., 3] > 128)
        else:
            # МЕХАНИЗМЫ: isnet + сплошная заливка тела (без серости/полупрозрачности)
            rgba = rembg_rgba(bgr)
            S = solid_silhouette(rgba)
        rgba = to_rgba(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), S)
        sq = center_square(rgba)
        if sq is None:
            print('ПУСТО:', art); continue
        # webp с альфой
        Image.fromarray(sq, 'RGBA').save(f'{OUT}/{art}.webp', 'WEBP', quality=90, method=6)
        # qc-превью на тёмной шахматке
        prev = cv2.resize(on_checker(sq, 16, True), (360, 360), interpolation=cv2.INTER_AREA)
        cv2.imencode('.jpg', cv2.cvtColor(prev, cv2.COLOR_RGB2BGR))[1].tofile(f'{QC}/{art}.jpg')
        done += 1
        print(f'  {art:10s} <- IMG_{stem}')
    print('Готово:', done)

if __name__ == '__main__':
    main()
