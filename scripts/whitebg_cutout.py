# -*- coding: utf-8 -*-
"""
ПРЕМИАЛЬНОЕ удаление ровного белого студийного фона у жёстких изделий
(выключатели, розетки, рамки = скруглённые прямоугольники).

Идея: фон НЕ удаляем по цвету (светлый товар != фон по нейросети), а
1) находим точный силуэт по связности: фон = почти-белое И плоское, связное с краем кадра;
   кромка товара даёт всплеск градиента -> барьер -> заливка не течёт в белую клавишу;
2) аппроксимируем силуэт скруглённым прямоугольником (товары прямоугольные) и
   отрисовываем ЧИСТУЮ маску с суперсэмплингом 4x -> идеально прямые стороны + ровный AA-край;
3) сжимаем маску на ~2px внутрь -> срезаем загрязнённый белым ободок -> НЕТ ореола.

cutout(bgr) -> (rgba_uint8, info). Переиспользуется свотчами и каталогом.
Запуск как скрипт: тест на трудных образцах -> монтаж + диаг-кропы в _pipeline/_cutout_test/.
"""
import glob
from pathlib import Path
import numpy as np
import cv2
from scipy.ndimage import binary_fill_holes, label, binary_closing

ROOT = Path("c:/Users/ikoko/Projects/aws-brand-site")
SS = 4            # суперсэмплинг для AA
ERODE_PX = 2.0    # сжатие внутрь (срез ореола), в пикселях исходника

def packaging_score(bgr):
    """Доля ярких пикселей с заметным градиентом — высокая у товара В УПАКОВКЕ
    (текст/складки прозрачного пакета на белом). У чистых студийных фото ~низкая."""
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, 3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, 3)
    grad = np.sqrt(gx * gx + gy * gy)
    bright = g > 200
    if bright.sum() < 100:
        return 0.0
    return float(100 * ((grad > 30) & bright).sum() / bright.sum())

def is_packaging(bgr, thr=9.0):
    return packaging_score(bgr) >= thr

def _largest_cc(mask):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if n <= 1:
        return mask
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return (lab == idx).astype(np.uint8)

def _silhouette(bgr, white_tol=28, grad_tol=14, remove_openings=False):
    """Точная бинарная маска товара (0/1)."""
    H, W = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = cv2.GaussianBlur(np.sqrt(gx * gx + gy * gy), (0, 0), 1.0)

    floodable = (gray >= 255 - white_tol) & (grad <= grad_tol)
    bf = floodable.copy()                       # «бело-плоское» (фон-подобное) — для проёмов
    barrier = binary_closing(~floodable, structure=np.ones((3, 3)), iterations=1)
    floodable = ~barrier
    floodable[gray < 255 - white_tol] = False

    lab, n = label(floodable)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    border.discard(0)
    bg = np.isin(lab, list(border)) if border else np.zeros_like(floodable)

    fg = (~bg).astype(np.uint8)
    fg = binary_fill_holes(fg).astype(np.uint8)     # сплошной товар (дырки = часть товара)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, k)
    fg = _largest_cc(fg)
    fg = binary_fill_holes(fg).astype(np.uint8)

    # --- удаление ПРОЁМОВ: ТОЛЬКО для рамок (remove_openings=True).
    #     У не-рамок (диммеры, выключатели) внутренние светлые области НЕ трогаем. ---
    if not remove_openings:
        return fg
    from scipy.ndimage import binary_dilation
    solid = binary_fill_holes(fg).astype(np.uint8)
    solid_area = max(int(solid.sum()), 1)
    material = (solid == 1) & (~bf)              # непрозрачный материал (тёмное/серое/текстура)
    inner = bf & (solid == 1) & (bg == 0)        # светлые «фон-подобные» регионы внутри силуэта
    il, ino = label(inner)
    for i in range(1, ino + 1):
        comp = il == i
        a = int(comp.sum())
        if a < 60 or a > 0.55 * solid_area:      # мелочь / крупное белое тело товара -> не проём
            continue
        ring = binary_dilation(comp, iterations=6) & (~comp) & (solid == 1)
        if ring.sum() > 0 and material[ring].mean() > 0.45:  # окружён материалом -> это проём
            fg[comp] = 0
    return fg

def cutout(bgr, white_tol=28, grad_tol=14, spill_erode=1, remove_openings=False, adaptive=True):
    """Убирает белый фон, СОХРАНЯЯ реальный контур изделия 1:1.
    Без скруглений/оболочек/перерисовки формы. spill_erode=1 убирает 1px
    белого ободка по краю (антиореол); 0 — вообще не трогать край.
    remove_openings=True — для РАМОК: делает прозрачными внутренние проёмы.
    adaptive=True — для БЕЛОГО-НА-БЕЛОМ (белые рамки/товары): если при обычном допуске
    покрытие подозрительно мало (заливка съела светлый товар) — повторяем с низким
    допуском (убираем только чисто-белое) и берём вариант с большим сохранением.
    """
    H, W = bgr.shape[:2]
    fg = _silhouette(bgr, white_tol, grad_tol, remove_openings)  # точный силуэт = настоящая форма
    if adaptive and fg.mean() < 0.45:
        fg_lo = _silhouette(bgr, 8, 8, remove_openings)
        if fg_lo.mean() > 1.4 * max(fg.mean(), 1e-6):
            fg = fg_lo
    info = {"coverage": round(100 * fg.mean(), 1), "mode": "silhouette"}
    if spill_erode > 0 and fg.sum() > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fg = cv2.erode(fg, k, iterations=int(spill_erode))   # срез загрязнённого белым ободка
    alpha = (fg * 255).astype(np.uint8)                       # чёткая альфа, край = настоящая кромка
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return np.dstack([rgb, alpha]), info

# ---------- тест/диагностика ----------
def _on_checker(rgba, cell, dark):
    H, W = rgba.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    chk = (((xx // cell) + (yy // cell)) % 2)
    base = np.where(chk[..., None] == 0, 235 if not dark else 90, 200 if not dark else 30).astype(np.uint8).repeat(3, 2)
    a = rgba[..., 3:4].astype(np.float32) / 255
    return (rgba[..., :3] * a + base * (1 - a)).astype(np.uint8)

def _imread_u(p):
    return cv2.imdecode(np.fromfile(p, np.uint8), cv2.IMREAD_COLOR)

if __name__ == "__main__":
    SRC = ROOT / "_pipeline" / "одноклавишные-в-сборе"
    OUT = ROOT / "_pipeline" / "_cutout_test"; OUT.mkdir(parents=True, exist_ok=True)
    tests = [("U1A-001-1 silver.jpg", "СЕРЕБРО"), ("*B30-1G [!R]*", "ЗОЛОТО B30"),
             ("*A-001W*P50-1W*", "БЕЛЫЙ Аура P50"), ("U2B-001-1 black.jpg", "ЧЁРНЫЙ"),
             ("A-D001W.jpg", "ДИЗАЙН белый")]
    tiles = []
    for pat, label_ in tests:
        hits = sorted(glob.glob(str(SRC / pat)))
        if not hits:
            print("нет:", pat); continue
        bgr = _imread_u(hits[0]); rgba, info = cutout(bgr)
        print("%-16s cov=%-5s mode=%s" % (label_, info["coverage"], info["mode"]))
        cv2.imencode(".png", cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))[1].tofile(str(OUT / (label_ + ".png")))
        def fit(img, h=400):
            s = h / img.shape[0]; return cv2.resize(img, (int(img.shape[1] * s), h))
        orig = fit(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        light = fit(_on_checker(rgba, 20, False)); dark = fit(_on_checker(rgba, 20, True))
        g = np.full((orig.shape[0], 8, 3), 255, np.uint8)
        tiles.append(np.hstack([orig, g, light, g, dark]))
        # диаг-кроп угла на тёмном
        a = rgba[..., 3]; ys, xs = np.where(a > 10); y0, x0 = ys.min(), xs.min()
        crop = rgba[max(0,y0-12):y0+168, max(0,x0-12):x0+168]
        cc = _on_checker(crop, 10, True)
        cc = cv2.resize(cc, (cc.shape[1]*3, cc.shape[0]*3), interpolation=cv2.INTER_NEAREST)
        cv2.imencode(".png", cv2.cvtColor(cc, cv2.COLOR_RGB2BGR))[1].tofile(str(OUT / ("_угол-" + label_ + ".png")))
    if tiles:
        wmax = max(t.shape[1] for t in tiles)
        tiles = [cv2.copyMakeBorder(t, 6, 6, 0, wmax - t.shape[1], cv2.BORDER_CONSTANT, value=(255,255,255)) for t in tiles]
        cv2.imencode(".png", cv2.cvtColor(np.vstack(tiles), cv2.COLOR_RGB2BGR))[1].tofile(str(OUT / "_МОНТАЖ.png"))
        print("\nМонтаж:", OUT / "_МОНТАЖ.png")
