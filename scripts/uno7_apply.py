# -*- coding: utf-8 -*-
"""ЗАДАЧА 7 (УНО, цветные, не рамки): ¾ из архива -> главное, существующие фото сдвиг +1.
Источник ¾-вырезов: _pipeline/_uno7/cuts/{артикул}.webp (уже с прозрачными монтажными отверстиями).
Обратимо: существующие файлы git-трекаются (git checkout восстановит)."""
import os, re, json, glob, shutil
from collections import defaultdict

ROOT = "c:/Users/ikoko/Projects/aws-brand-site"
PROD = os.path.join(ROOT, "public/img/products")
DIST = os.path.join(ROOT, "dist/img/products")
CUTS = os.path.join(ROOT, "_pipeline/_uno7/cuts")
mapping = json.load(open(os.path.join(ROOT, "_pipeline/_uno7/mapping.json"), encoding="utf-8"))

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
    cut = os.path.join(CUTS, article + ".webp")
    assert os.path.exists(cut), "нет выреза: " + article
    main, extras = files_of(article, PROD)
    # 1) сдвиг ракурсов вниз, с конца (сохраняем расширение)
    for idx in sorted(extras, reverse=True):
        ext = extras[idx].rsplit(".", 1)[1]
        os.rename(os.path.join(PROD, extras[idx]),
                  os.path.join(PROD, f"{article}_{idx+1}.{ext}"))
    # 2) старое главное -> _2 (с его расширением)
    if main:
        ext = main.rsplit(".", 1)[1]
        os.rename(os.path.join(PROD, main), os.path.join(PROD, f"{article}_2.{ext}"))
    # 3) ¾-вырез -> новое главное
    shutil.copyfile(cut, os.path.join(PROD, article + ".webp"))

def sync_dist(article):
    safe = re.escape(article)
    pat = re.compile(safe + r"(_\d+)?\.(webp|png|jpg|jpeg)", re.I)
    # удалить все dist-файлы артикула
    for f in os.listdir(DIST):
        if pat.fullmatch(f):
            os.remove(os.path.join(DIST, f))
    # скопировать актуальные public-файлы
    for f in os.listdir(PROD):
        if pat.fullmatch(f):
            shutil.copyfile(os.path.join(PROD, f), os.path.join(DIST, f))

arts = sorted(mapping.keys())
for a in arts:
    apply_one(a)
print("perestanovka primenena:", len(arts), "artikulov")
if os.path.isdir(DIST):
    for a in arts:
        sync_dist(a)
    print("dist sinhronizirovan")
else:
    print("dist net (dev rezhim) — sync ne nuzhen")
