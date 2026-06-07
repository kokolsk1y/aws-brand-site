# -*- coding: utf-8 -*-
"""
АНАЛИЗ (read-only): сопоставить новые архивы фото с каталогом.
Ничего не меняет на сайте. Строит карту:
  архив-файл -> целевой(ые) артикул(ы) -> НОВОЕ (дыра) / ЗАМЕНА (фото уже есть) / НЕ-В-КАТАЛОГЕ.
И обратную: артикулы серий без фото, которые архив НЕ закрывает.

Запуск:  python scripts/analyze_photo_intake.py
Отчёт:   scripts/audit/photo_intake_report.md  (+ краткое ASCII-резюме в консоль)
"""
import json, re, zipfile, glob
from pathlib import Path
from collections import defaultdict

ROOT = Path("c:/Users/ikoko/Projects/aws-brand-site")
PROD = ROOT / "public" / "img" / "products"
SERIES = json.load(open(ROOT / "src/data/series.json", encoding="utf-8"))

# ---- каталог: все артикулы UNO + DESIGN ----
CAT = {}  # article -> (series, color, name)
for sk in ("uno", "design"):
    for g, items in SERIES[sk]["groups"].items():
        for it in items:
            CAT[it["article"]] = (sk, it.get("color"), it.get("name", ""))

EXTS = ("webp", "png", "jpg", "jpeg")

def disk_photos(article):
    """как getProductPhotos: главное + _N ракурсы (любой ext)."""
    safe = re.escape(article)
    re_main = re.compile(r"^" + safe + r"\.(" + "|".join(EXTS) + r")$", re.I)
    re_ex = re.compile(r"^" + safe + r"_(\d+)\.(" + "|".join(EXTS) + r")$", re.I)
    main, extras = [], []
    for f in PROD.iterdir():
        if re_main.match(f.name): main.append(f.name)
        elif re_ex.match(f.name): extras.append(f.name)
    return main, extras

# ---- нормализация имени из архива в артикул каталога ----
def norm_color_token(s):
    s = s.replace("mette black", "matte black")
    s = s.replace(" gery", " grey").replace("gery", "grey")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def labels_from_entry(stem):
    """вернуть список меток-артикулов из имени файла (через ';'), нормализованных."""
    parts = [norm_color_token(p) for p in stem.split(";")]
    return [p for p in parts if p]

def map_to_catalog(label, zipname):
    """label вида 'U1A-016-1 silver' / 'U1A-003 matte black' / 'A-D001_1' -> артикул каталога или None + примечание."""
    note = ""
    # matte: архив помечен U1A, каталог хранит как U2B
    if "matte black" in label:
        cand = re.sub(r"^U1A", "U2B", label)
        if cand in CAT: return cand, "U1A→U2B (matte)"
        if label in CAT: return label, ""
        return None, "matte: нет в каталоге"
    if label in CAT:
        return label, ""
    return None, "нет точного совпадения"

# ---- DESIGN: спец-карта источник->цель (включая 'делёж' фото) ----
DESIGN_SRC_TO_TARGETS = {
    "A-D001":   ["A-D001GR", "A-D002GR"],   # A-D001 = серый; A-D002GR делит фото
    "A-D003GR": ["A-D003GR", "A-D004GR"],   # A-D004GR делит фото
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

def analyze_uno_zip(zpath, color_hint):
    rows = []
    with zipfile.ZipFile(zpath) as z:
        for n in z.namelist():
            if n.endswith("/"): continue
            stem = Path(n).stem
            for label in labels_from_entry(stem):
                art, note = map_to_catalog(label, zpath.name)
                if art is None:
                    rows.append((n, label, None, "✗ " + note, ""))
                    continue
                main, extras = disk_photos(art)
                state = "ЗАМЕНА" if (main or extras) else "НОВОЕ"
                cnt = f"{len(main)}+{len(extras)}ex" if (main or extras) else "—"
                rows.append((n, label, art, state, cnt))
    return rows

def analyze_design_zip(zpath):
    rows = []
    # сгруппировать архивные файлы по источнику-артикулу
    src_files = defaultdict(list)
    with zipfile.ZipFile(zpath) as z:
        for n in z.namelist():
            if n.endswith("/"): continue
            stem = Path(n).stem  # 'A-D001_1'
            m = re.match(r"(.+?)_(\d+)$", stem)
            if not m:
                rows.append((n, stem, None, "✗ нет _N", "")); continue
            src, ang = m.group(1), int(m.group(2))
            src_files[src].append((ang, n))
    for src in sorted(src_files):
        angles = sorted(a for a, _ in src_files[src])
        targets = DESIGN_SRC_TO_TARGETS.get(src)
        if not targets:
            rows.append((src, f"angles={angles}", None, "✗ источник не в карте", "")); continue
        for tgt in targets:
            if tgt not in CAT:
                rows.append((src, f"->{tgt}", None, "✗ цель не в каталоге", "")); continue
            main, extras = disk_photos(tgt)
            state = "ЗАМЕНА" if (main or extras) else "НОВОЕ"
            cnt = f"{len(main)}+{len(extras)}ex" if (main or extras) else "—"
            shared = "  (делит фото)" if targets.index(tgt) > 0 else ""
            rows.append((src, f"angles={angles} -> {tgt}{shared}", tgt, state, cnt))
    return rows

def main():
    out = ["# Карта приёмки фото (read-only анализ)\n"]
    covered = set()  # артикулы, которые архивы закрывают

    uno_zips = [
        (ROOT / "white.zip", "white"),
        (ROOT / "silver.zip", "silver"),
        (ROOT / "dark_grey.zip", "dark_grey"),
        (ROOT / "grey.zip", "grey"),
        (ROOT / "black.zip", "black"),
        (ROOT / "mette_black.zip", "matte_black"),
    ]
    for zp, color in uno_zips:
        if not zp.exists():
            out.append(f"\n## {zp.name} — НЕ НАЙДЕН\n"); continue
        rows = analyze_uno_zip(zp, color)
        out.append(f"\n## {zp.name}  ({color})  — {len(rows)} целей\n")
        out.append("| архив-файл | метка | артикул каталога | статус | фото на диске |")
        out.append("|---|---|---|---|---|")
        for n, label, art, state, cnt in rows:
            short = Path(n).name
            out.append(f"| {short} | {label} | {art or '—'} | {state} | {cnt} |")
            if art: covered.add(art)

    # DESIGN
    zp = ROOT / "Дизайн остальное.zip"
    if zp.exists():
        rows = analyze_design_zip(zp)
        out.append(f"\n## {zp.name}  (design)  — {len(rows)} строк\n")
        out.append("| источник | маппинг | артикул | статус | фото на диске |")
        out.append("|---|---|---|---|---|")
        for src, info, art, state, cnt in rows:
            out.append(f"| {src} | {info} | {art or '—'} | {state} | {cnt} |")
            if art: covered.add(art)

    # ---- обратная сторона: артикулы серий БЕЗ фото, которые архивы НЕ закрывают ----
    out.append("\n## Артикулы UNO/DESIGN без фото на диске, НЕ закрытые архивами\n")
    out.append("| артикул | серия | цвет | name |")
    out.append("|---|---|---|---|")
    miss = 0
    for art, (sk, color, name) in sorted(CAT.items()):
        main, extras = disk_photos(art)
        if not main and not extras and art not in covered:
            out.append(f"| {art} | {sk} | {color} | {name[:40]} |")
            miss += 1

    # ---- сводка ASCII ----
    rep = ROOT / "scripts" / "audit" / "photo_intake_report.md"
    rep.write_text("\n".join(out), encoding="utf-8")
    print("Report:", rep)
    print("Covered by archives:", len(covered), "articles")
    print("Still missing (not in archives):", miss, "articles")

if __name__ == "__main__":
    main()
