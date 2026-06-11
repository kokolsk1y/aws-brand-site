# -*- coding: utf-8 -*-
"""Публикация ¾-рамок УНО: ¾-вырез -> главное фото, существующие ракурсы сдвиг +1.
Та же логика, что scripts/uno7_apply.py (задача 7), но для 30 рамок.
Источник ¾: scripts/cache/frame_batch/{артикул}.png (RGBA, фон удалён).
Обратимо: текущие файлы под git -> git checkout восстановит.
В public/ пишет; dist/ синхронизирует если есть."""
import os, re, glob, shutil
from PIL import Image

ROOT = "c:/Users/ikoko/Projects/aws-brand-site"
PROD = os.path.join(ROOT, "public/img/products")
DIST = os.path.join(ROOT, "dist/img/products")
CUTS = os.path.join(ROOT, "scripts/cache/frame_batch")
MAXPX = 2000

def cut_articles():
    out = []
    for f in glob.glob(os.path.join(CUTS, "*.png")):
        b = os.path.splitext(os.path.basename(f))[0]
        if not b.startswith("_"):
            out.append(b)
    return sorted(out)

def png_to_webp_bytes(png_path, dst_webp):
    im = Image.open(png_path).convert("RGBA")
    w, h = im.size
    if max(w, h) > MAXPX:
        s = MAXPX / max(w, h)
        im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    im.save(dst_webp, "WEBP", quality=90, method=6)

def files_of(article, folder):
    safe = re.escape(article)
    main = None; extras = {}
    for f in os.listdir(folder):
        if re.fullmatch(safe + r"\.(webp|png|jpg|jpeg)", f, re.I):
            main = f
        else:
            m = re.fullmatch(safe + r"_(\d+)\.(webp|png|jpg|jpeg)", f, re.I)
            if m:
                extras[int(m.group(1))] = f
    return main, extras

def apply_one(article):
    cut = os.path.join(CUTS, article + ".png")
    assert os.path.exists(cut), "нет выреза: " + article
    main, extras = files_of(article, PROD)
    # 1) сдвиг ракурсов вниз, с конца
    for idx in sorted(extras, reverse=True):
        ext = extras[idx].rsplit(".", 1)[1]
        os.rename(os.path.join(PROD, extras[idx]),
                  os.path.join(PROD, f"{article}_{idx+1}.{ext}"))
    # 2) старое главное -> _2
    if main:
        ext = main.rsplit(".", 1)[1]
        os.rename(os.path.join(PROD, main), os.path.join(PROD, f"{article}_2.{ext}"))
    # 3) ¾-вырез -> новое главное (webp)
    png_to_webp_bytes(cut, os.path.join(PROD, article + ".webp"))

def sync_dist(article):
    safe = re.escape(article)
    pat = re.compile(safe + r"(_\d+)?\.(webp|png|jpg|jpeg)", re.I)
    for f in os.listdir(DIST):
        if pat.fullmatch(f):
            os.remove(os.path.join(DIST, f))
    for f in os.listdir(PROD):
        if pat.fullmatch(f):
            shutil.copyfile(os.path.join(PROD, f), os.path.join(DIST, f))

arts = cut_articles()
for a in arts:
    apply_one(a)
    m, e = files_of(a, PROD)
    print(f"{a:24} главное=¾  ракурсы _2..={sorted(e)}")
print("\nперестановка применена:", len(arts), "рамок")
if os.path.isdir(DIST):
    for a in arts:
        sync_dist(a)
    print("dist синхронизирован")
else:
    print("dist нет (dev режим) — sync не нужен")
