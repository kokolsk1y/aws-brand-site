# -*- coding: utf-8 -*-
"""
ДИЗАЙН: обработка новых фото из «Дизайн остальное.zip».
Фаза STAGE (по умолчанию): распаковать -> cutout каждого ракурса -> сложить webp в стейджинг
  _pipeline/_design_cutout/ + контактные листы per-источник (_pipeline/_design_contact/).
  НИЧЕГО не кладёт в public/. Печатает packaging_score по каждому кадру.
Фаза DEPLOY (--deploy): по карте PACKAGING (исключить упаковку) разложить финал в
  public/img/products как {target}.webp + _2/_3..., включая делящие пары.

Источник->цель и тип (рамка прорезает проёмы):
  A-D001(серый) -> A-D001GR (+копия A-D002GR)   выключатели — без проёмов
  A-D003GR -> A-D003GR (+копия A-D004GR)
  A-D011GR, A-D012B                              выключатели
  A-D022GR, A-D030GR, A-D055GR                   розетки — без проёмов
  PD80-3B/3GR/6GR/7VB/7VGR                        рамки — проёмы прорезаем
"""
import sys, re, zipfile, glob, shutil
from pathlib import Path
import numpy as np
import cv2
from PIL import Image
from whitebg_cutout import cutout, packaging_score

ROOT = Path("c:/Users/ikoko/Projects/aws-brand-site")
ZIP = ROOT / "Дизайн остальное.zip"
RAW = ROOT / "_pipeline" / "_design_raw"
STAGE = ROOT / "_pipeline" / "_design_cutout"
CONTACT = ROOT / "_pipeline" / "_design_contact"
PROD = ROOT / "public" / "img" / "products"

# источник -> [цели] (первая = основная, остальные делят то же фото)
SRC_TO_TARGETS = {
    "A-D001":   ["A-D001GR", "A-D002GR"],
    "A-D003GR": ["A-D003GR", "A-D004GR"],
    "A-D011GR": ["A-D011GR"],
    "A-D012B":  ["A-D012B"],
    "A-D022GR": ["A-D022GR"],
    "A-D030GR": ["A-D030GR"],
    "A-D055GR": ["A-D055GR"],
    "PD80-3B":  ["PD80-3B"],
    "PD80-3GR": ["PD80-3GR"],
    "PD80-6GR": ["PD80-6GR"],
    "PD80-7VB": ["PD80-7VB"],
    "PD80-7VGR":["PD80-7VGR"],
}
# рамки (имя начинается с «Рамка») — у них прорезаем внутренние проёмы
FRAME_SRCS = {"PD80-3B", "PD80-3GR", "PD80-6GR", "PD80-7VB", "PD80-7VGR"}

# Кадры-упаковка / лишние (исключить на DEPLOY). Подтверждено визуально по контактным листам.
# ключ = "{src}_{angle}". Держим <=4 продуктовых ракурса (конвенция каталога ДИЗАЙН).
PACKAGING = {
    "A-D001_5",                       # пакет с лого
    "A-D003GR_5", "A-D003GR_6",       # пакет
    "A-D022GR_5", "A-D022GR_6",       # _5 дубль-механизм, _6 пакет (кап до 4)
    "A-D030GR_4", "A-D030GR_5",       # пакет
    "A-D055GR_4", "A-D055GR_5",       # _4 зад с наклейкой, _5 пакет
    "PD80-3B_3", "PD80-3B_4",         # пакет
    "PD80-3GR_3", "PD80-3GR_4",       # пакет
    "PD80-6GR_3", "PD80-6GR_4",       # пакет
    "PD80-7VB_3", "PD80-7VB_4",       # пакет
    "PD80-7VGR_3", "PD80-7VGR_4",     # пакет
}

def extract():
    RAW.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP) as z:
        for n in z.namelist():
            if n.endswith("/"):
                continue
            stem = Path(n).name  # A-D001_1.jpg
            data = z.read(n)
            (RAW / stem).write_bytes(data)
    print("Extracted:", len(list(RAW.glob('*.jpg'))), "files ->", RAW)

def to_bgr(path):
    return cv2.cvtColor(np.array(Image.open(path).convert("RGB")), cv2.COLOR_RGB2BGR)

def smooth_alpha(alpha, ss=4, blur_frac=0.9):
    """Выровнять «лесенку»/волну на кромке + мягкий анти-алиас.
    Маску апскейлим x4 -> гаусс -> порог 0.5 (выпрямляет мелкую волну) ->
    лёгкий гаусс -> даунскейл INTER_AREA. Форму НЕ меняет, только кромку."""
    fg = (alpha > 0).astype(np.uint8)
    h, w = fg.shape
    big = cv2.resize(fg * 255, (w * ss, h * ss), interpolation=cv2.INTER_NEAREST)
    sm = cv2.GaussianBlur(big.astype(np.float32), (0, 0), ss * blur_frac)
    st = (sm >= 127.5).astype(np.float32) * 255
    st = cv2.GaussianBlur(st, (0, 0), ss * 0.5)
    return cv2.resize(st, (w, h), interpolation=cv2.INTER_AREA).clip(0, 255).astype(np.uint8)

def on_checker(rgba, cell=14, dark=False):
    H, W = rgba.shape[:2]; yy, xx = np.mgrid[0:H, 0:W]; chk = (((xx // cell) + (yy // cell)) % 2)
    base = np.where(chk[..., None] == 0, 210 if not dark else 80, 150 if not dark else 25).astype(np.uint8).repeat(3, 2)
    al = rgba[..., 3:4].astype(np.float32) / 255
    return (rgba[..., :3] * al + base * (1 - al)).astype(np.uint8)

def angles_of(src):
    out = []
    for f in RAW.glob(src + "_*.jpg"):
        m = re.match(re.escape(src) + r"_(\d+)$", f.stem)
        if m:
            out.append((int(m.group(1)), f))
    return sorted(out)

def stage():
    STAGE.mkdir(parents=True, exist_ok=True); CONTACT.mkdir(parents=True, exist_ok=True)
    for src in sorted(SRC_TO_TARGETS):
        is_frame = src in FRAME_SRCS
        angs = angles_of(src)
        if not angs:
            print("  !! нет файлов для", src); continue
        tiles = []
        print(f"\n{src}  (frame={is_frame})  ракурсов={len(angs)}")
        for ang, f in angs:
            bgr = to_bgr(f)
            pk = packaging_score(bgr)
            rgba, info = cutout(bgr, remove_openings=is_frame)
            rgba[..., 3] = smooth_alpha(rgba[..., 3])   # выровнять кромку + AA
            outp = STAGE / f"{src}_{ang}.webp"
            Image.fromarray(rgba, "RGBA").save(outp, "WEBP", quality=90, method=6)
            flag = "  <== УПАКОВКА?" if pk >= 9.0 else ""
            print(f"   _{ang}: pkg={pk:5.1f}  cov={info['coverage']:5.1f}%{flag}")
            def fit(img, h=260):
                s = h / img.shape[0]; return cv2.resize(img, (int(img.shape[1]*s), h))
            orig = fit(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            cut = fit(on_checker(rgba)); cutd = fit(on_checker(rgba, dark=True))
            g = np.full((orig.shape[0], 6, 3), 255, np.uint8)
            row = np.hstack([orig, g, cut, g, cutd])
            cv2.putText(row, f"{src}_{ang}  pkg={pk:.0f} cov={info['coverage']:.0f}", (4,20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200,0,0), 2, cv2.LINE_AA)
            tiles.append(row)
        wmax = max(t.shape[1] for t in tiles)
        tiles = [cv2.copyMakeBorder(t,4,4,0,wmax-t.shape[1],cv2.BORDER_CONSTANT,value=(255,255,255)) for t in tiles]
        out = CONTACT / f"{src}.png"
        cv2.imencode(".png", cv2.cvtColor(np.vstack(tiles), cv2.COLOR_RGB2BGR))[1].tofile(str(out))
    print("\nКонтактные листы:", CONTACT)
    print("Стейджинг webp:", STAGE)

def deploy():
    # финал: исключить упаковку, переиндексировать ракурсы, разложить (вкл. делящие пары)
    n_files = 0
    for src, targets in SRC_TO_TARGETS.items():
        angs = [a for a in angles_of(src) if f"{src}_{a[0]}" not in PACKAGING]
        if not angs:
            print("  !! после фильтра пусто:", src); continue
        # пути готовых webp из стейджинга в порядке ракурса
        staged = [STAGE / f"{src}_{ang}.webp" for ang, _ in angs]
        staged = [p for p in staged if p.exists()]
        for tgt in targets:
            # чистый перезапуск артикула
            for old in glob.glob(str(PROD/(tgt+".webp"))) + glob.glob(str(PROD/(tgt+"_*.webp"))):
                Path(old).unlink()
            for idx, sp in enumerate(staged):
                name = f"{tgt}.webp" if idx == 0 else f"{tgt}_{idx+1}.webp"
                shutil.copyfile(sp, PROD / name)
                n_files += 1
            print(f"  {tgt}: {len(staged)} фото (из {src})")
    print("\nРазложено файлов:", n_files)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "stage"
    if mode in ("stage", "all"):
        extract(); stage()
    elif mode == "deploy":
        if not PACKAGING:
            print("ВНИМАНИЕ: PACKAGING пуст — ни один кадр не помечен упаковкой. Проверь контактные листы.")
        deploy()
