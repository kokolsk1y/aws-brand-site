# -*- coding: utf-8 -*-
"""
ШАГ 0 конструктора: из 28 combo-фото (выключатель уже В РАМКЕ, 1 пост) в
_pipeline/одноклавишные-в-сборе/ делает чистые webp для конструктора:

  вырез белого фона (whitebg_cutout, remove_openings=False — сборка = единый силуэт)
  -> обрезка по альфа-bbox -> паддинг в квадрат -> ресайз 1000x1000 -> webp

Раскладка (схема для генератора constructor-data.json):
  АУРА:        public/img/constructor/aura/<color>-<material>.webp
  УНО/ДИЗАЙН:  public/img/constructor/<series>/<color>.webp   (один материал)

color:    white | black | grey | gold | dark_grey | silver | matte_black
material: plain(P50) | glossy(PG51) | glass(G50) | glass_relief(G51) | aluminum(B30)

Запуск:  python scripts/build_constructor_combos.py
Локально, без деплоя/пуша. Идемпотентно (перезапись).
"""
import re, glob
from pathlib import Path
import numpy as np
import cv2
from whitebg_cutout import cutout, _imread_u

ROOT = Path("c:/Users/ikoko/Projects/aws-brand-site")
SRC = ROOT / "_pipeline" / "одноклавишные-в-сборе"
OUT = ROOT / "public" / "img" / "constructor"
SIZE = 1000          # финальный квадрат

# Внешний контур рамки вписываем в ОДИН И ТОТ ЖЕ квадрат у всех combo, чтобы при
# переключении края рамки точно совпадали (пользователь оценивает разницу по краям).
# FILL = доля холста под рамку; лёгкое анизотропное подтягивание (w и h независимо)
# выправляет перекос от угла съёмки (~3%, незаметно).
FILL = 0.90

AURA_COLOR = {"W": "white", "G": "gold", "GR": "grey", "B": "black"}
FRAME_MAT = {"P50": "plain", "PG51": "glossy", "G50": "glass",
             "G51": "glass_relief", "B30": "aluminum"}
UNO_COLOR = {"white": "white", "grey": "grey", "silver": "silver",
             "dark grey": "dark_grey", "black": "black", "matte black": "matte_black"}
DESIGN_COLOR = {"W": "white", "B": "black", "GR": "grey"}


def classify(fname):
    """-> (series, color, material|None) либо None если файл пропускаем."""
    base = fname
    if "(2)" in base:                      # дубль серой P50 — пропускаем
        return None
    # АУРА: содержит выключатель A-001X и артикул рамки
    if "A-001" in base and re.search(r"(P50|PG51|G50|G51|B30)-1", base):
        mc = re.search(r"A-001(GR|G|W|B)\b", base)
        mf = re.search(r"(P50|PG51|G50|G51|B30)-1(?:GR|G|W|B)", base)
        if mc and mf:
            return ("aura", AURA_COLOR[mc.group(1)], FRAME_MAT[mf.group(1)])
    # ДИЗАЙН: A-D001X.jpg
    md = re.match(r"A-D001(W|B|GR)\.jpg$", base, re.I)
    if md:
        return ("design", DESIGN_COLOR[md.group(1).upper()], None)
    # УНО: U1A-001-1 <color> / U2B-001-1 <color>
    mu = re.match(r"U(?:1A|2B)-001-1 (.+)\.jpg$", base, re.I)
    if mu:
        cw = mu.group(1).strip().lower()
        if cw in UNO_COLOR:
            return ("uno", UNO_COLOR[cw], None)
    return None


def correct_soft(rgba):
    """Мягкая коррекция combo: приглушает ТОЛЬКО выбитые блики (L>245) внутри
    растушёванной маски. Цвет/насыщенность и фактуру вне маски не трогает —
    золото/стекло/софт-тач сохраняются. Вход/выход RGBA (альфа без изменений)."""
    rgb = rgba[..., :3].copy()
    a = rgba[..., 3]
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    L = lab[..., 0]
    m = np.clip((L - 245.0) / 10.0, 0, 1)          # 0 при L=245, 1 при L=255
    m = cv2.GaussianBlur(m, (0, 0), 3.0)           # мягкие края маски
    knee = 245.0
    over = np.clip(L - knee, 0, None)
    Lc = knee + over * 0.7                          # лёгкий soft-knee
    L2 = L * (1 - m) + Lc * m
    Lm = cv2.medianBlur(L2.astype(np.uint8), 3).astype(np.float32)
    L3 = L2 * (1 - m) + Lm * m                       # подавление смаза только в маске
    lab[..., 0] = L3
    out = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2RGB)
    return np.dstack([out, a])


def defringe(rgba, band=2, sigma=6.0):
    """Убирает белый ореол по кромке, НЕ трогая альфу (края остаются ровно на
    месте, чёткие). Тонкий ободок (band px) перекрашивается в цвет товара,
    взятый из глубины нормализованным размытием по внутренности (прозрачный
    фон в источник не попадает)."""
    a = rgba[..., 3]
    rgb = rgba[..., :3].astype(np.float32)
    M = (a > 128).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    inner = cv2.erode(M, k, iterations=band)        # чистая внутренность без ободка
    rim = ((M > 0) & (inner == 0))                   # ободок шириной band px
    innerf = inner.astype(np.float32)
    w = cv2.GaussianBlur(innerf, (0, 0), sigma)
    num = cv2.GaussianBlur(rgb * innerf[..., None], (0, 0), sigma)
    avg = num / np.maximum(w[..., None], 1e-6)       # средний цвет товара из глубины
    out = rgb.copy()
    out[rim] = avg[rim]                               # перекрашиваем только ободок
    res = rgba.copy()
    res[..., :3] = np.clip(out, 0, 255).astype(np.uint8)
    return res


def square_pad(rgba):
    a = rgba[..., 3]
    ys, xs = np.where(a > 8)
    if len(xs) == 0:
        return cv2.resize(rgba, (SIZE, SIZE))
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    crop = rgba[y0:y1 + 1, x0:x1 + 1]
    # Вписываем внешний контур в фиксированный квадрат target×target по центру холста.
    # Анизотропный ресайз (w и h → target) делает края рамки одинаковыми у ВСЕХ combo.
    target = int(round(SIZE * FILL))
    fitted = cv2.resize(crop, (target, target), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((SIZE, SIZE, 4), np.uint8)
    off = (SIZE - target) // 2
    canvas[off:off + target, off:off + target] = fitted
    return canvas


def main():
    files = sorted(glob.glob(str(SRC / "*.jpg")))
    done, skipped = [], []
    for f in files:
        name = Path(f).name
        cls = classify(name)
        if not cls:
            skipped.append(name); continue
        series, color, material = cls
        bgr = _imread_u(f)
        rgba, info = cutout(bgr)                 # remove_openings=False (сборка = единый силуэт)
        rgba = correct_soft(rgba)                # мягкое приглушение выбитых бликов
        out_img = square_pad(rgba)
        out_img = defringe(out_img)              # убрать белый ореол по кромке
        stem = f"{color}-{material}" if material else color
        dst = OUT / series
        dst.mkdir(parents=True, exist_ok=True)
        out_path = dst / f"{stem}.webp"
        bgra = cv2.cvtColor(out_img, cv2.COLOR_RGBA2BGRA)
        ok, buf = cv2.imencode(".webp", bgra, [cv2.IMWRITE_WEBP_QUALITY, 90])
        buf.tofile(str(out_path))
        done.append((series, stem, info["coverage"]))

    print(f"=== Готово: {len(done)} webp, пропущено {len(skipped)} ===")
    from collections import defaultdict
    by = defaultdict(list)
    for s, stem, cov in done:
        by[s].append(f"{stem}({cov})")
    for s in sorted(by):
        print(f"  {s}: {len(by[s])}")
        for x in sorted(by[s]):
            print("      ", x)
    if skipped:
        print("  пропущены:", skipped)


if __name__ == "__main__":
    main()
