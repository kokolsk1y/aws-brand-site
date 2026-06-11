# -*- coding: utf-8 -*-
"""Пакетный вырез ¾-рамок УНО методом сайта (whitebg_cutout, режим рамок).
Источники: белые + 030 grey — из корня проекта (дропнул пользователь);
остальные цвета — из архива _photo-source-archive (новые-исходники-2026-06-08).
Пишет ТОЛЬКО превью на шахматке в scripts/cache/frame_batch/ + RGBA-результаты.
В public/ НЕ пишет."""
import os, sys, re, io, zipfile
import numpy as np
import cv2
from PIL import Image, ImageDraw

ROOT = "c:/Users/ikoko/Projects/aws-brand-site"
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from whitebg_cutout import cutout

ARCH = os.path.join(ROOT, "_photo-source-archive_2026-06-03.zip")
NEW = "новые-исходники-2026-06-08/"
OUT = os.path.join(ROOT, "scripts", "cache", "frame_batch")
os.makedirs(OUT, exist_ok=True)

z = zipfile.ZipFile(ARCH)
NAMES = [n for n in z.namelist() if n.startswith(NEW) and not n.endswith("/")]

NUMS = ["028", "029", "030", "031", "032"]
# (site_color, archive_folder, src_article_prefix)  src в архиве: matte хранится как U1A!
COLORS = [
    ("dark grey", "dark_grey", "U1A"),
    ("grey",      "grey",      "U1A"),
    ("silver",    "silver",    "U1A"),
    ("matte black", "mette_black", "U1A"),  # site = U2B-0xx matte black
    ("black",     "black",     "U2B"),
]

def find_in_arch(folder, prefix, num):
    pat = re.compile(re.escape(prefix) + r"-0*" + num.lstrip("0") + r"\b", re.I)
    # сверяем по имени файла, учитывая папку
    for n in NAMES:
        parts = n.split("/")
        if parts[1] != folder:
            continue
        base = parts[-1]
        if re.search(re.escape(prefix) + r"-" + num + r"\b", base, re.I):
            return n
    return None

def imdecode_u(data):
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

# ---- собрать список заданий: (site_article, color_label, loader) ----
jobs = []  # (site_article, src_tag, bgr)
def add(site_article, src_tag, bgr):
    if bgr is None:
        print("  ПРОПУСК (нет источника):", site_article, src_tag); return
    jobs.append((site_article, src_tag, bgr))

# белые — из корня
for num in NUMS:
    p = os.path.join(ROOT, f"U1A-{num} white.webp")
    bgr = cv2.imdecode(np.fromfile(p, np.uint8), cv2.IMREAD_COLOR) if os.path.exists(p) else None
    add(f"U1A-{num} white", "корень/white", bgr)

# 030 grey — из корня (Алиса)
pg = os.path.join(ROOT, "U1A-030 grey.jpeg")
add("U1A-030 grey", "корень/grey(Алиса)",
    cv2.imdecode(np.fromfile(pg, np.uint8), cv2.IMREAD_COLOR) if os.path.exists(pg) else None)

# цветные — из архива
for num in NUMS:
    for site_color, folder, prefix in COLORS:
        # 030 grey уже взяли из корня
        if num == "030" and site_color == "grey":
            continue
        site_prefix = "U2B" if site_color in ("matte black", "black") else "U1A"
        site_article = f"{site_prefix}-{num} {site_color}"
        n = find_in_arch(folder, prefix, num)
        bgr = imdecode_u(z.read(n)) if n else None
        add(site_article, f"арх/{folder}", bgr)

print(f"\nвсего задач: {len(jobs)}\n")

# ---- вырез + сохранение ----
def checker_pair(rgba, cell=18):
    h, w = rgba.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    chk = ((xx // cell) + (yy // cell)) % 2
    a = rgba[..., 3:4].astype(np.float32) / 255
    rgb = rgba[..., :3].astype(np.float32)
    light = np.where(chk[..., None] == 0, 215, 165).astype(np.uint8).repeat(3, 2)
    dark = np.where(chk[..., None] == 0, 70, 30).astype(np.uint8).repeat(3, 2)
    cl = (rgb * a + light * (1 - a)).astype(np.uint8)
    cd = (rgb * a + dark * (1 - a)).astype(np.uint8)
    return cl, cd

tiles = []
for site_article, src_tag, bgr in jobs:
    # white_tol=8 (не 28): не съедать яркие блики материала (серебро/серый) по торцу.
    rgba, info = cutout(bgr, white_tol=8, grad_tol=9, remove_openings=True, adaptive=True)
    cov = info["coverage"]
    flag = "  <-- ПРОВЕРИТЬ (низкое покрытие)" if cov < 12 else ""
    print(f"{site_article:24} cov={cov:<5} src={src_tag}{flag}")
    Image.fromarray(rgba, "RGBA").save(os.path.join(OUT, f"{site_article}.png"))
    cl, cd = checker_pair(rgba)
    # плитка превью: тёмная шахматка (на ней повреждения виднее), высота 240
    h = 240; s = h / cd.shape[0]; cd_s = cv2.resize(cd, (int(cd.shape[1] * s), h))
    cap = np.full((22, max(cd_s.shape[1], 220), 3), 255, np.uint8)
    pim = Image.fromarray(cap); ImageDraw.Draw(pim).text((3, 3), f"{site_article}  cov{cov}", fill=(0, 0, 0))
    cap = np.array(pim)
    w = cap.shape[1]
    cd_s = cv2.copyMakeBorder(cd_s, 0, 0, 0, w - cd_s.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))
    tiles.append(np.vstack([cap, cd_s]))

# ---- монтаж сеткой по 4 в ряд ----
PERROW = 4
rows = []
for i in range(0, len(tiles), PERROW):
    chunk = tiles[i:i + PERROW]
    hmax = max(t.shape[0] for t in chunk); wmax = max(t.shape[1] for t in chunk)
    chunk = [cv2.copyMakeBorder(t, 0, hmax - t.shape[0], 0, wmax - t.shape[1] + 6,
             cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in chunk]
    rows.append(np.hstack(chunk))
wmax = max(r.shape[1] for r in rows)
rows = [cv2.copyMakeBorder(r, 6, 6, 0, wmax - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]
montage = np.vstack(rows)
Image.fromarray(montage).save(os.path.join(OUT, "_МОНТАЖ_все.png"))
print("\nмонтаж:", os.path.join(OUT, "_МОНТАЖ_все.png"))
