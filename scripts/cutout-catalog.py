# -*- coding: utf-8 -*-
"""
Удаление белого фона у каталожных фото public/img/products через whitebg_cutout.cutout().
Режимы:
  sample           — проба на разнотипных товарах -> контактный лист (ничего не меняет)
  all   [--apply]  — обработать ВСЕ бело-фоновые в staging _pipeline/_catalog_cutout/;
                     с --apply заменить на месте те, что прошли QA (исходники в git).
QA-гейт: площадь товара 12..98% и не «схлопнулось» — иначе файл во flagged (не заменяется).
"""
import glob, sys, json, re
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
from whitebg_cutout import cutout, packaging_score

ROOT = Path("c:/Users/ikoko/Projects/aws-brand-site")
PROD = ROOT / "public" / "img" / "products"
STAGE = ROOT / "_pipeline" / "_catalog_cutout"
TEST = ROOT / "_pipeline" / "_cutout_test"

def _frame_articles():
    # рамка = товар, имя которого начинается с «Рамка» (надёжнее группы frames,
    # где попадаются заглушки/прочее). Только у рамок вырезаем внутренние проёмы.
    d = json.load(open(ROOT / "src/data/series.json", encoding="utf-8"))
    s = set()
    for sk in d:
        for grp, items in d[sk]["groups"].items():
            for p in items:
                if str(p.get("name", "")).strip().lower().startswith("рамка"):
                    a = str(p.get("article", "")).strip()
                    if a:
                        s.add(a)
    return s
FRAMES = _frame_articles()

def is_frame(path):
    art = re.sub(r"_\d+$", "", Path(path).stem)   # убрать суффикс ракурса
    return art in FRAMES

def load_rgba(path):
    im = Image.open(path).convert("RGBA")
    return np.array(im)

def is_white_bg(path):
    try:
        a = load_rgba(path)
    except Exception:
        return False
    alpha, rgb = a[..., 3], a[..., :3]
    if alpha.min() < 240:
        return False  # уже есть прозрачность
    c = np.concatenate([rgb[:8, :8].reshape(-1, 3), rgb[:8, -8:].reshape(-1, 3),
                        rgb[-8:, :8].reshape(-1, 3), rgb[-8:, -8:].reshape(-1, 3)])
    return c.min() >= 235

def white_bg_files():
    fs = sorted(glob.glob(str(PROD / "*.webp"))) + sorted(glob.glob(str(PROD / "*.png")))
    return [f for f in fs if is_white_bg(f)]

def to_bgr(path):
    rgba = load_rgba(path)
    return cv2.cvtColor(rgba[..., :3], cv2.COLOR_RGB2BGR)

def qa_ok(info):
    return 12.0 <= info["coverage"] <= 98.0

def on_checker(rgba, cell=14, dark=False):
    H, W = rgba.shape[:2]; yy, xx = np.mgrid[0:H, 0:W]; chk = (((xx // cell) + (yy // cell)) % 2)
    base = np.where(chk[..., None] == 0, 210 if not dark else 80, 150 if not dark else 25).astype(np.uint8).repeat(3, 2)
    al = rgba[..., 3:4].astype(np.float32) / 255
    return (rgba[..., :3] * al + base * (1 - al)).astype(np.uint8)

def sample():
    fs = white_bg_files()
    # разнотипная выборка: по «корню» (до пробела и без _N)
    import re
    seen = {}
    for f in fs:
        n = Path(f).stem
        root = re.sub(r"_\d+$", "", n).split(" ")[0]
        key = re.sub(r"[\dWBGR-]+$", "", root) or root  # грубый тип по префиксу
        seen.setdefault(key, f)
    picks = list(seen.values())[:12]
    TEST.mkdir(parents=True, exist_ok=True)
    tiles = []
    for f in picks:
        rgba, info = cutout(to_bgr(f), remove_openings=is_frame(f))
        print("%-34s cov=%-5s %s" % (Path(f).name[:34], info["coverage"], "OK" if qa_ok(info) else "⚠FLAG"))
        def fit(img, h=300):
            s = h / img.shape[0]; return cv2.resize(img, (int(img.shape[1] * s), h))
        orig = fit(cv2.cvtColor(to_bgr(f), cv2.COLOR_BGR2RGB))
        cut = fit(on_checker(rgba)); cutd = fit(on_checker(rgba, dark=True))
        g = np.full((orig.shape[0], 6, 3), 255, np.uint8)
        row = np.hstack([orig, g, cut, g, cutd])
        cv2.putText(row, Path(f).name[:40], (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 200), 1, cv2.LINE_AA)
        tiles.append(row)
    wmax = max(t.shape[1] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 4, 4, 0, wmax - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
    out = TEST / "_КАТАЛОГ-проба.png"
    cv2.imencode(".png", cv2.cvtColor(np.vstack(tiles), cv2.COLOR_RGB2BGR))[1].tofile(str(out))
    print("\nКонтактный лист:", out)

def run_all(apply=False):
    fs = white_bg_files()
    STAGE.mkdir(parents=True, exist_ok=True)
    flagged = []; done = 0
    for i, f in enumerate(fs):
        rgba, info = cutout(to_bgr(f), remove_openings=is_frame(f))
        name = Path(f).name
        if not qa_ok(info):
            flagged.append((name, info["coverage"])); continue
        Image.fromarray(rgba, "RGBA").save(STAGE / name, "WEBP", quality=90, method=6)
        if apply:
            Image.fromarray(rgba, "RGBA").save(f, "WEBP", quality=90, method=6)
        done += 1
        if (i + 1) % 50 == 0:
            print("  ...%d/%d" % (i + 1, len(fs)))
    print("Обработано (QA ok): %d; во flagged: %d; apply=%s" % (done, len(flagged), apply))
    if flagged:
        (TEST).mkdir(parents=True, exist_ok=True)
        (TEST / "_flagged.txt").write_text("\n".join("%s\t%s%%" % x for x in flagged), encoding="utf-8")
        print("Список flagged:", TEST / "_flagged.txt")

def scanpack(thr=9.0):
    """Найти вероятную упаковку среди БЕЛО-ФОНОВЫХ фото + контактный лист флагнутых.
    (детектор валиден только на чистом белом фоне; прозрачные фото пропускаем)"""
    fs = white_bg_files()
    scored = []
    for f in fs:
        try:
            scored.append((packaging_score(to_bgr(f)), f))
        except Exception:
            pass
    flagged = sorted([x for x in scored if x[0] >= thr], reverse=True)
    print("Всего фото: %d; флаг упаковки (score>=%s): %d" % (len(fs), thr, len(flagged)))
    for sc, f in flagged:
        print("  %5.1f  %s" % (sc, Path(f).name))
    if flagged:
        TEST.mkdir(parents=True, exist_ok=True)
        thumbs, row = [], []
        for sc, f in flagged:
            im = cv2.imdecode(np.fromfile(f, np.uint8), cv2.IMREAD_COLOR)
            im = cv2.resize(im, (150, 150))
            cv2.putText(im, "%.0f %s" % (sc, Path(f).stem[:12]), (2, 146), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1, cv2.LINE_AA)
            row.append(im)
            if len(row) == 6:
                thumbs.append(np.hstack(row)); row = []
        if row:
            while len(row) < 6: row.append(np.full((150, 150, 3), 255, np.uint8))
            thumbs.append(np.hstack(row))
        cv2.imencode(".png", np.vstack(thumbs))[1].tofile(str(TEST / "_УПАКОВКА-флаг.png"))
        (TEST / "_packaging_flagged.txt").write_text("\n".join(Path(f).name for _, f in flagged), encoding="utf-8")
        print("Контактный лист:", TEST / "_УПАКОВКА-флаг.png")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "sample"
    if mode == "sample":
        sample()
    elif mode == "scanpack":
        scanpack(float(sys.argv[2]) if len(sys.argv) > 2 else 9.0)
    elif mode == "all":
        run_all(apply="--apply" in sys.argv)
