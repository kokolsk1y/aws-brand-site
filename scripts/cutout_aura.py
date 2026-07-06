# -*- coding: utf-8 -*-
"""
Серия АУРА (золото / серый): вырез фона у всех ракурсов + прозрачные webp.

Метод (как в проверенном DESIGN-пайплайне — угловые глянцевые фото на белом):
  - МЕХАНИЗМЫ (A-*): rembg isnet-general-use -> чистый силуэт,
    затем СПЛОШНАЯ заливка тела (largest CC + fill holes) — светлые
    (золото/серый) поверхности не сереют и не рвутся;
  - РАМКИ (B30/G50/G51/P50/PG51): rembg birefnet-general — держит
    сквозной проём (круг под механизм виден фоном) прозрачным, а чёрный
    суппорт-кроватку оставляет непрозрачной; берём крупнейший компонент;
  - чистка края: эрозия 1px (антиореол);
  - центрирование: обрезка по контуру -> длинная сторона = FILL*холст -> центр квадрата;
  - вход: _incoming_aura/{ЗОЛОТО,СЕРЫЙ}/**/ART_n.jpg (курированные);
  - выход: staging _incoming_aura/cutout_out/ART.webp (+ _2.._N), НЕ в public;
  - QC: per-article превью на тёмной шахматке в _incoming_aura/cutout_out/_qc/.

Запуск:
  python scripts/cutout_aura.py            # вся партия
  python scripts/cutout_aura.py A-001G G50-2GR B30-6G   # только указанные артикулы
"""
import sys, os, glob, re
import numpy as np
import cv2
from scipy.ndimage import binary_fill_holes, label, binary_dilation
from PIL import Image, ImageDraw
from rembg import remove, new_session
sys.path.insert(0, 'scripts')
from whitebg_cutout import cutout as whitebg_cutout

SRC_DIRS = ['_incoming_aura/ЗОЛОТО', '_incoming_aura/СЕРЫЙ']
OUT = '_incoming_aura/cutout_out'
QC = '_incoming_aura/cutout_out/_qc'
CANVAS = 1600
FILL = 0.918          # как у существующих АУРА (белый/чёрный) — совпадение размера в серии
os.makedirs(OUT, exist_ok=True)
os.makedirs(QC, exist_ok=True)

FRAME_PREFIXES = ('B30', 'G50', 'G51', 'P50', 'PG51')

SESS = new_session('isnet-general-use')       # механизмы
SESS_FRAME = new_session('birefnet-general')  # рамки (держит проёмы)

def is_frame(art):
    return art.split('-')[0] in FRAME_PREFIXES

def imread_u(p):
    return cv2.imdecode(np.fromfile(p, np.uint8), cv2.IMREAD_COLOR)

def rembg_rgba(bgr, sess):
    ok, buf = cv2.imencode('.png', bgr)
    out = remove(buf.tobytes(), session=sess)
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
    m = rgba[..., 3] > 50
    m = _largest_cc(m)
    m = binary_fill_holes(m)
    return m.astype(bool)

def punch_openings(S, bgr, min_area=0.004, compact_min=0.40):
    """По сплошному силуэту S выбивает сквозные проёмы рамки / монтажные слоты:
    яркий плоский фон, видимый сквозь отверстия — компактный и замкнутый
    материалом (не краевой надкус). Для 'пустых' рамок (B30) убирает белый
    в оконном проёме; тёмные кроватки (P50) не трогает (там не ярко).
    min_area/compact_min ослабляют для мелких вытянутых слотов суппорта."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, 3); gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, 3)
    grad = cv2.GaussianBlur(np.sqrt(gx*gx + gy*gy), (0, 0), 1.0)
    cand = (gray >= 242) & (grad <= 8) & S
    lab, n = label(cand)
    area_S = max(int(S.sum()), 1)
    out = S.copy()
    for i in range(1, n + 1):
        comp = lab == i
        a = int(comp.sum())
        if a < min_area * area_S:                                # мелочь/блик
            continue
        ys, xs = np.where(comp)                                   # компактность (проём — «пятно»)
        bb = (ys.max()-ys.min()+1) * (xs.max()-xs.min()+1)
        compact = a / max(bb, 1)
        if compact < compact_min:                                # тонкий блик/сливер — не проём
            continue
        enclosed = not (binary_dilation(comp, iterations=3) & (~S)).any()
        big = a > 0.03 * area_S and compact >= 0.5               # крупный центральный проём
        if not (enclosed or big):                                # иначе краевой надкус
            continue
        # РАСШИРЯЕМ дырку на 2px — съедаем белую антиалиас-кайму по краю проёма
        comp = cv2.dilate(comp.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2).astype(bool)
        out[comp & S] = False
    return out

def keep_bg_holes(S_raw, min_area=0.0006, compact_min=0.15, dil=2):
    """Механизмы: rembg сам помечает сквозные монтажные слоты суппорта как фон
    (дырки в S_raw) — даже затенённые на ¾-ракурсах. Заливаем ТЕЛО целиком
    (fill_holes: белые/светлые поверхности не дырявятся), затем возвращаем
    прозрачность в те дырки, что нашла rembg и которые крупнее спекла.
    Реальные дырки расширяем на dil px (съедаем белую антиалиас-кайму)."""
    S_fill = binary_fill_holes(S_raw)
    holes = S_fill & (~S_raw)
    lab, n = label(holes)
    area_S = max(int(S_fill.sum()), 1)
    out = S_fill.copy()
    for i in range(1, n + 1):
        comp = lab == i
        a = int(comp.sum())
        if a < min_area * area_S:                    # мелкий спекл rembg -> остаётся залитым
            continue
        ys, xs = np.where(comp)
        bb = (ys.max()-ys.min()+1) * (xs.max()-xs.min()+1)
        if a / max(bb, 1) < compact_min:             # тонкое кольцо-артефакт -> залито
            continue
        comp = cv2.dilate(comp.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=dil).astype(bool)
        out[comp & S_fill] = False
    return out

def punch_bg_holes(S_fill, bgr, lo=150, hi=210, sat_max=22, flat_grad=16,
                   min_core_px=25, min_area_px=45):
    """Пост-фильтр монтажных отверстий поверх ГОТОВОГО силуэта S_fill (механизмы).
    Студийный фон в слоте = ЯРКИЙ и НЕНАСЫЩЕННЫЙ. Кандидат — связная область
    (gray>=lo & sat<=sat_max) внутри силуэта, содержащая яркое плоское ядро
    (gray>=hi) и ЗАМКНУТАЯ материалом. Рост по нижнему порогу lo с sat-гейтом
    останавливается ровно на материале:
      • золотая клавиша — sat≈48 > sat_max -> стоп;
      • серая клавиша ≈150 / серый металл ≈130 -> у границы lo, тело не задето;
      • дилатации в товар НЕТ — только настоящие фон-пиксели.
    Так убираем и слот, и белую кайму, не откусывая край клавиши."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    sat = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[..., 1]
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, 3); gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, 3)
    grad = cv2.GaussianBlur(np.sqrt(gx*gx + gy*gy), (0, 0), 1.0)
    cand = (gray >= lo) & (sat <= sat_max) & S_fill
    lab, n = label(cand)
    punched = np.zeros_like(S_fill, bool)
    for i in range(1, n + 1):
        comp = lab == i
        if int(comp.sum()) < min_area_px:                       # спекл
            continue
        core = comp & (gray >= hi) & (grad <= flat_grad)         # плоское яркое ядро = настоящий фон
        if int(core.sum()) < min_core_px:                        # нет фон-ядра -> тёмная область товара
            continue
        if (binary_dilation(comp, iterations=2) & (~S_fill)).any():  # не замкнут материалом
            continue
        punched |= comp
    out = S_fill.copy()
    out[punched] = False
    return out

def punch_white_slots(S, bgr, bright=225, sat_max=20, flat_grad=14, min_area=60):
    """Консервативный добор остаточных монтажных слотов на birefnet-силуэте S.
    birefnet сам режет почти все слоты; изредка один остаётся включён в товар с
    белым фоном внутри. Выбиваем ТОЛЬКО чисто-белые плоские ненасыщенные области,
    ЗАМКНУТЫЕ материалом. Серый суппорт (~130) и клавиши (золото насыщ. / серый тёмный)
    не проходят порог. Рост 1px только в фон-пиксели — товар не задет."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    sat = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[..., 1]
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, 3); gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, 3)
    grad = cv2.GaussianBlur(np.sqrt(gx*gx + gy*gy), (0, 0), 1.0)
    white = (gray >= bright) & (sat <= sat_max) & (grad <= flat_grad) & S
    lab, n = label(white)
    punched = np.zeros_like(S, bool)
    for i in range(1, n + 1):
        comp = lab == i
        if int(comp.sum()) < min_area:
            continue
        if (binary_dilation(comp, iterations=2) & (~S)).any():   # не замкнут -> пропуск
            continue
        punched |= comp
    if punched.any():
        fringe = binary_dilation(punched, iterations=1) & (gray >= bright - 30) & (sat <= sat_max + 12) & S
        punched |= fringe
    out = S.copy()
    out[punched] = False
    return out

def to_rgba(rgb, mask):
    m = cv2.erode(mask.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)), 1)
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

def process_one(path, art):
    bgr = imread_u(path)
    if is_frame(art):
        # РАМКИ. birefnet «призрачит» большие плоские панели (стекло-фронт, тыл
        # многопостовых) и рвёт крупные фронты. whitebg держит сплошной материал
        # (стекло/алюминий/пластик — не белые). Объединяем материал, потом выбиваем
        # сквозные проёмы (яркий фон) + дилатация против каймы.
        B = _largest_cc(rembg_rgba(bgr, SESS_FRAME)[..., 3] > 128)
        # whitebg (заливка от белого фона) корректно отделяет рамку любого цвета,
        # включая near-white силвер (фильтр яркости выедал бы блики) — берём материал
        # прямо из W. Проёмы забиваются заливкой и выбиваются punch'ем.
        wr, _ = whitebg_cutout(bgr, white_tol=10, grad_tol=10, remove_openings=False, adaptive=True)
        W = wr[..., 3] > 128
        S = _largest_cc(B | W)                        # объединить материал (нет ghost/распада)
        S = binary_fill_holes(S)
        S = punch_openings(S, bgr)                    # выбить сквозные проёмы + съесть кайму
        rgba = to_rgba(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), S)
        return center_square(rgba)
    else:
        # МЕХАНИЗМЫ: birefnet сырой альфой уже даёт сплошной товар (клавиша/суппорт
        # непрозрачны) И прозрачные монтажные слоты — без заливок/порогов/выбиваний.
        # Берём крупнейший компонент (отсечь спекл) + срез каймы 1px в to_rgba. НЕ fill_holes!
        # МЕХАНИЗМЫ. База — birefnet (клавиша сплошная, слоты прозрачны, выключатели идеальны).
        # Плюс возврат СЕРОГО МЕТАЛЛА пластины из whitebg там, где birefnet его срезал/
        # призрачил (розетки): добавляем только тёмный+ненасыщенный металл, яркую клавишу
        # не трогаем -> без спекла. Остаточные белые слоты — точечно вручную.
        B = _largest_cc(rembg_rgba(bgr, SESS_FRAME)[..., 3] > 128)
        wr, _ = whitebg_cutout(bgr, white_tol=10, grad_tol=10, remove_openings=True, adaptive=True)
        W = wr[..., 3] > 128
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        sat = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[..., 1]
        grey_metal = (gray <= 195) & (sat <= 45)
        S = _largest_cc(B | (W & grey_metal))
        rgba = to_rgba(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), S)
        return center_square(rgba)

def collect():
    only = set(sys.argv[1:])
    tasks = {}  # art -> {angle: path}
    for d in SRC_DIRS:
        for f in glob.glob(d + '/**/*.jpg', recursive=True):
            m = re.match(r'(.+)_(\d+)\.jpg$', os.path.basename(f))
            if not m:
                continue
            art, ang = m.group(1), int(m.group(2))
            if only and art not in only:
                continue
            tasks.setdefault(art, {})[ang] = f
    return tasks

def qc_sheet(art, squares):
    # ряд превью всех ракурсов на тёмной шахматке, высота 300
    tiles = []
    for ang, sq in sorted(squares.items()):
        prev = cv2.resize(on_checker(sq, 14, True), (300, 300), interpolation=cv2.INTER_AREA)
        cap = np.full((20, 300, 3), 255, np.uint8)
        pim = Image.fromarray(cap); ImageDraw.Draw(pim).text((3, 3), f'{art}_{ang}', fill=(0, 0, 0))
        tiles.append(np.vstack([np.array(pim), prev]))
    sheet = np.hstack(tiles)
    cv2.imencode('.jpg', cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))[1].tofile(os.path.join(QC, f'{art}.jpg'))

def main():
    tasks = collect()
    print(f'артикулов: {len(tasks)}, фото: {sum(len(v) for v in tasks.values())}')
    for art in sorted(tasks):
        squares = {}
        for ang, path in sorted(tasks[art].items()):
            sq = process_one(path, art)
            if sq is None:
                print('  ПУСТО:', art, ang); continue
            name = f'{art}.webp' if ang == 1 else f'{art}_{ang}.webp'
            Image.fromarray(sq, 'RGBA').save(os.path.join(OUT, name), 'WEBP', quality=90, method=6)
            squares[ang] = sq
        if squares:
            qc_sheet(art, squares)
        print(f'  {art:10s} ракурсы {sorted(squares)}  ({"рамка" if is_frame(art) else "механизм"})')
    print('Готово ->', OUT)

if __name__ == '__main__':
    main()
