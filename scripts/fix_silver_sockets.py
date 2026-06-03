# -*- coding: utf-8 -*-
"""
Точечная пере-резка двух серебряных розеток с битыми пикселями:
  U1A-022 silver  (Розетка 2-я с/з с шторками серебро)
  U1A-011 silver  (Розетка 1-я с/з с шторками с USB и TYPE C серебро)

Задача (по словам владельца): товар НЕ имеет сквозных отверстий — нужно
найти ВНЕШНЮЮ границу товара и убрать всё вокруг. Внутреннее заполнено сплошняком.

Почему не birefnet: на светлых ЛИЦЕВЫХ ракурсах нейросеть «съедает» серебряную
рамку (принимает за фон), оставляя только тёмный механизм. Поэтому используем
классический контурный метод whitebg_cutout._silhouette (flood-fill от краёв кадра
по «бело-плоскому» фону, кромка товара = градиент-барьер), затем заполняем ВСЕ
внутренние области (отверстий нет) и НЕ вызываем punch_openings_safe.

Режимы:
  (без аргумента)  — собрать варианты A/B/C в _pipeline/_silver_fix + QA-листы
  --deploy METHOD  — заменить файлы в public методом A|B|C
"""
import sys, json
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
from scipy.ndimage import binary_fill_holes, label

ROOT = Path("c:/Users/ikoko/Projects/aws-brand-site")
sys.path.insert(0, str(ROOT / "scripts"))
from whitebg_cutout import _silhouette, _largest_cc

SILVER_DIR = ROOT / "scripts/audit/photos_from_supplier/unpacked/УНО серебро/серебро"
STAGE = ROOT / "_pipeline/_silver_fix"
STAGE.mkdir(parents=True, exist_ok=True)
PUB = ROOT / "public/img/products"

TARGETS = {
    "U1A-022 silver": {1: "U1A-022_1.jpg", 2: "U1A-022_2.jpg",
                       3: "U1A-022_3.jpg", 4: "U1A-022_4.jpg"},
    "U1A-011 silver": {1: "U1A-011_1 серебро.jpg", 2: "U1A-011_2 серебро.jpg",
                       3: "U1A-011_3 серебро.jpg", 4: "U1A-011_4 серебро.jpg"},
}


def view_suffix(v):
    return "" if v == 1 else f"_{v}"


def load_bgr(src):
    bgr = cv2.imdecode(np.fromfile(str(src), np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        return None
    if max(bgr.shape[:2]) > 2000:
        s = 2000 / max(bgr.shape[:2])
        bgr = cv2.resize(bgr, (int(bgr.shape[1] * s), int(bgr.shape[0] * s)),
                         interpolation=cv2.INTER_AREA)
    return bgr


def silhouette_solid(bgr, white_tol, grad_tol, spill_erode=1):
    """Внешний контур товара, ВСЁ внутри залито сплошняком (отверстий нет)."""
    fg = _silhouette(bgr, white_tol=white_tol, grad_tol=grad_tol, remove_openings=False)
    fg = binary_fill_holes(fg).astype(np.uint8)   # заполнить любые внутренние дыры
    fg = _largest_cc(fg)
    fg = binary_fill_holes(fg).astype(np.uint8)
    if spill_erode > 0 and fg.sum() > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fg = cv2.erode(fg, k, iterations=int(spill_erode))
    alpha = (fg * 255).astype(np.uint8)
    rgba = np.dstack([cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), alpha])
    return rgba, round(100 * fg.mean(), 1)


# Три варианта параметров для светлого-на-белом
METHODS = {
    "A": dict(white_tol=28, grad_tol=14, spill_erode=1),   # дефолт
    "B": dict(white_tol=16, grad_tol=10, spill_erode=1),   # строже к фону (не затекать в товар)
    "C": dict(white_tol=10, grad_tol=8,  spill_erode=0),   # только чисто-белый фон, без среза
}


def checker(rgba, cell=18):
    H, W = rgba.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    chk = (((xx // cell) + (yy // cell)) % 2)
    base = np.where(chk[..., None] == 0, 230, 195).astype(np.float32).repeat(3, 2)
    a = (rgba[..., 3:4].astype(np.float32) / 255)
    return (rgba[..., :3].astype(np.float32) * a + base * (1 - a)).astype(np.uint8)


def fit(img, h=280):
    s = h / img.shape[0]
    return cv2.resize(img, (int(img.shape[1] * s), h))


def build():
    """Собрать все 3 метода × все ракурсы, сохранить webp по методам + QA-листы."""
    for article, views in TARGETS.items():
        print(f"\n=== {article} ===")
        rows = []
        for view_n, fname in views.items():
            src = SILVER_DIR / fname
            bgr = load_bgr(src)
            if bgr is None:
                print(f"  ⚠ не читается: {fname}"); continue
            orig = fit(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            tiles = [orig]
            covs = []
            for mkey, params in METHODS.items():
                rgba, cov = silhouette_solid(bgr, **params)
                covs.append(f"{mkey}={cov}%")
                # сохранить webp в подпапку метода
                mdir = STAGE / mkey
                mdir.mkdir(exist_ok=True)
                out_name = f"{article}{view_suffix(view_n)}.webp"
                Image.fromarray(rgba, "RGBA").save(str(mdir / out_name), "WEBP",
                                                   quality=90, method=6)
                tiles.append(fit(checker(rgba)))
            g = np.full((280, 6, 3), 255, np.uint8)
            row = []
            for i, t in enumerate(tiles):
                row.append(t)
                if i < len(tiles) - 1:
                    row.append(g)
            row = np.hstack(row)
            cv2.putText(row, f"v{view_n}  orig | A | B | C   {'  '.join(covs)}",
                        (4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 100, 0), 2)
            rows.append(row)
            print(f"  ракурс {view_n}: {'  '.join(covs)}")
        if rows:
            wmax = max(r.shape[1] for r in rows)
            rows = [cv2.copyMakeBorder(r, 4, 4, 0, wmax - r.shape[1],
                    cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]
            qa = STAGE / f"_QA_{article}.png"
            cv2.imencode(".png", cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR))[1].tofile(str(qa))
            print(f"  QA: {qa}")
    print(f"\nГотово. Сравни _QA_*.png, затем: python scripts/fix_silver_sockets.py --deploy A|B|C")


def deploy(method):
    import shutil
    mdir = STAGE / method
    files = list(mdir.glob("*.webp"))
    if not files:
        print(f"Нет файлов метода {method}. Сначала запусти без аргумента."); return
    for f in files:
        shutil.copy2(str(f), str(PUB / f.name))
        print(f"  {f.name}")
    print(f"Deploy метода {method}: {len(files)} файлов.")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--deploy":
        deploy(sys.argv[2].upper())
    else:
        build()
