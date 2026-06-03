# -*- coding: utf-8 -*-
"""
Сверка фотографий от поставщика с артикулами series.json (price=null).

Каждый архив распакован в scripts/audit/photos_from_supplier/unpacked/<папка>/.
Имя папки → (серия, цвет). Парсер per-серия извлекает base-артикул и номер
ракурса, собирает article-ключ как в series.json и проверяет покрытие.

Запуск:  python scripts/verify_photos.py            — отчёт в консоль + coverage.md
         python scripts/verify_photos.py --debug    — показать разбор каждого файла
"""
import os, re, sys, json, collections

UNPACKED = "scripts/audit/photos_from_supplier/unpacked"
SERIES_JSON = "src/data/series.json"
REPORT = "scripts/audit/photos_coverage.md"

# Папка распаковки -> (серия-ключ, цвет-ключ в series.json)
FOLDER_MAP = {
    "УНО серый":            ("uno", "grey"),
    "УНО Фото dark grey2":  ("uno", "dark_grey"),
    "УНО Матово черный":    ("uno", "matte_black"),
    "УНО серебро":          ("uno", "silver"),
    "АУРА":                 ("aura", None),   # цвет в имени файла
    "Фото Дизайн белый":    ("design", "white"),
    "Фото Дизайн Серый":    ("design", "grey"),
    "Фото Дизайн черный":   ("design", "black"),
}

# Слово-цвет, добавляемое к base для построения article УНО
UNO_COLORWORD = {
    "grey": "grey",
    "dark_grey": "dark grey",
    "matte_black": "matte black",
    "silver": "silver",
    "white": "white",
    "black": "black",
}

JUNK = re.compile(r"(thumbs\.db|\.ini|rj45)", re.I)
# Любые цветовые метки в имени файла УНО, которые надо отбросить, оставив base
# (серебро/серебряная, серый/серая/серое, dark grey, grey)
UNO_LABEL = re.compile(r"\s*(серебр\w*|dark\s*grey|grey|сер\w*)\s*", re.I)

# Суффикс цвета для серий aura/design (если поставщик не дописал в имя файла)
COLOR_SUFFIX = {"white": "W", "black": "B", "grey": "GR", "gold": "G", "mahogany": ""}


def strip_ext(name):
    return os.path.splitext(name)[0]


def parse_uno(stem):
    """U1A-001-1_1 серебро / U1A-001-1 grey_3 / U2B-001-1_2 -> (base, view)."""
    s = stem
    # убрать цветовые слова
    s = UNO_LABEL.sub(" ", s).strip()
    # ракурс — подчёркивание + цифры в конце (без номера -> 0 = главное фото)
    m = re.search(r"_(\d+)\s*$", s)
    view = int(m.group(1)) if m else 0
    if m:
        s = s[:m.start()]
    base = s.strip()
    # base вида U1A-001-1 / U2B-003 / U1A-019
    return base, view


def parse_simple(stem):
    """A-001B-1 (aura, дефис) или A-D001W_1 (design, подчёрк.) -> (base, view)."""
    s = stem.strip()
    m = re.search(r"[-_](\d+)\s*$", s)
    view = int(m.group(1)) if m else 0
    if m:
        s = s[:m.start()]
    return s.strip(), view


def load_null_articles():
    data = json.load(open(SERIES_JSON, encoding="utf-8"))
    by_series = {}
    for skey in ("uno", "aura", "design"):
        s = data[skey]
        items = []
        for items_list in s["groups"].values():
            items.extend(items_list)
        by_series[skey] = items
    return by_series


def collect_files():
    """folder -> list of (filename, fullpath)."""
    out = {}
    for folder in sorted(os.listdir(UNPACKED)):
        full = os.path.join(UNPACKED, folder)
        if not os.path.isdir(full):
            continue
        files = []
        for dp, dn, fn in os.walk(full):
            for f in fn:
                files.append((f, os.path.join(dp, f)))
        out[folder] = files
    return out


def build_matches(debug=False):
    by_series = load_null_articles()
    folders = collect_files()

    # article-key -> {views:set, files:list, items:[(view,fullpath)], kind:str}
    matched = collections.defaultdict(lambda: {"views": set(), "files": [], "items": [], "kind": "exact"})
    junk_files = []
    unmatched_files = []   # (folder, filename, built_key)
    fuzzy_notes = []       # (folder, filename, built_key, matched_key) — спорные

    # построить множества артикулов по сериям
    art_index = {}  # skey -> {article_str: item}
    for skey, items in by_series.items():
        art_index[skey] = {it["article"]: it for it in items}

    def candidates(skey, base, color):
        """Список (key, kind) в порядке предпочтения."""
        out = []
        if skey == "uno":
            cw = UNO_COLORWORD.get(color, color)
            out.append((f"{base} {cw}", "exact"))
            # fuzzy: поставщик добавил лишний сегмент -1 (U2B-003-1 -> U2B-003)
            m = re.match(r"^(.*?)-\d+$", base)
            if m:
                out.append((f"{m.group(1)} {cw}", "fuzzy"))
        else:
            # base может уже содержать цветовую букву (A-D001W) — пробуем как есть
            out.append((base, "exact"))
            # либо поставщик не дописал цвет (PD80-1 -> PD80-1W)
            suf = COLOR_SUFFIX.get(color, "")
            if suf and not base.upper().endswith(suf):
                out.append((base + suf, "fixed"))
        return out

    for folder, files in folders.items():
        if folder not in FOLDER_MAP:
            for f in files:
                unmatched_files.append((folder, f, "(папка не в FOLDER_MAP)"))
            continue
        skey, color = FOLDER_MAP[folder]
        for f, fullpath in files:
            if JUNK.search(f):
                junk_files.append((folder, f))
                continue
            stem = strip_ext(f)
            if skey == "uno":
                base, view = parse_uno(stem)
            else:
                base, view = parse_simple(stem)
            hit = None
            for key, kind in candidates(skey, base, color):
                if key in art_index[skey]:
                    hit = (key, kind)
                    break
            if debug:
                print(f"[{folder}] {f!r} -> base={base!r} view={view} hit={hit}")
            if hit:
                key, kind = hit
                rec = matched[(skey, key)]
                rec["views"].add(view)
                rec["files"].append(f)
                rec["items"].append((view, fullpath))
                if kind != "exact":
                    rec["kind"] = kind
                    fuzzy_notes.append((folder, f, key, kind))
            else:
                unmatched_files.append((folder, f, candidates(skey, base, color)[0][0]))

    return matched, by_series, fuzzy_notes, unmatched_files, junk_files


def main():
    debug = "--debug" in sys.argv
    matched, by_series, fuzzy_notes, unmatched_files, junk_files = build_matches(debug)

    # ---- Анализ покрытия по null-артикулам ----
    report = []
    report.append("# Покрытие фото от поставщика\n")
    report.append(f"_Сгенерировано: scripts/verify_photos.py_\n")

    grand_null = grand_covered = 0
    for skey in ("uno", "aura", "design"):
        items = by_series[skey]
        null_items = [it for it in items if it.get("price") is None]
        covered, missing = [], []
        for it in null_items:
            if (skey, it["article"]) in matched:
                covered.append(it)
            else:
                missing.append(it)
        grand_null += len(null_items)
        grand_covered += len(covered)
        report.append(f"\n## {skey.upper()} — {len(covered)}/{len(null_items)} покрыто\n")
        # по цветам
        bycolor_null = collections.Counter(it["color"] for it in null_items)
        bycolor_cov = collections.Counter(it["color"] for it in covered)
        report.append("| Цвет | Покрыто | Всего null |\n|---|---|---|")
        for c in sorted(bycolor_null):
            report.append(f"| {c} | {bycolor_cov.get(c,0)} | {bycolor_null[c]} |")
        if missing:
            report.append(f"\n**Непокрыто ({len(missing)}):**\n")
            mbycolor = collections.defaultdict(list)
            for it in missing:
                mbycolor[it["color"]].append(it["article"])
            for c in sorted(mbycolor):
                report.append(f"- **{c}**: " + ", ".join(sorted(mbycolor[c])))

    report.append(f"\n## ИТОГО: {grand_covered}/{grand_null} артикулов покрыто фото\n")

    # покрытые с числом ракурсов
    report.append("\n## Покрытые артикулы (число ракурсов)\n")
    for (skey, key), info in sorted(matched.items()):
        report.append(f"- `{key}` — {len(info['views'])} ракурс(ов)")

    # спорные соответствия (требуют решения)
    if fuzzy_notes:
        report.append(f"\n## ⚠️ Спорные соответствия — требуют решения ({len(fuzzy_notes)})\n")
        report.append("Имя файла не совпало точно; сопоставлено по правилу. Проверить:\n")
        seen_fz = set()
        for folder, f, key, kind in sorted(fuzzy_notes):
            tag = "лишний сегмент -N" if kind == "fuzzy" else "дописан цвет"
            stem = strip_ext(f)
            uniq = (folder, re.sub(r"[-_]\d+\s*", "", stem), key)
            if uniq in seen_fz:
                continue
            seen_fz.add(uniq)
            report.append(f"- [{folder}] `{f}` → `{key}` ({tag})")

    # лишние / непривязанные файлы
    report.append(f"\n## Лишние / непривязанные файлы ({len(unmatched_files)})\n")
    ubyfolder = collections.defaultdict(list)
    for folder, f, key in unmatched_files:
        ubyfolder[folder].append((f, key))
    for folder in sorted(ubyfolder):
        report.append(f"\n**{folder}:**")
        for f, key in sorted(ubyfolder[folder]):
            report.append(f"- `{f}` → собран ключ `{key}` (нет в null-наборе)")

    report.append(f"\n## Мусорные файлы ({len(junk_files)}): Thumbs.db и т.п.\n")

    text = "\n".join(report)
    open(REPORT, "w", encoding="utf-8").write(text)
    # короткая сводка в консоль (utf-8)
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"ИТОГО покрыто: {grand_covered}/{grand_null}")
    for skey in ("uno", "aura", "design"):
        items = by_series[skey]
        null_items = [it for it in items if it.get("price") is None]
        cov = sum(1 for it in null_items if (skey, it["article"]) in matched)
        print(f"  {skey}: {cov}/{len(null_items)}")
    print(f"Лишних файлов: {len(unmatched_files)}, мусора: {len(junk_files)}")
    print(f"Отчёт: {REPORT}")


PRODUCTS_DIR = "public/img/products"
WEBP_QUALITY = 88


# Исходные ракурсы 5 и 6 — товар в упаковке (во всех сериях), не нужны на сайте.
DROP_VIEWS = {5, 6}


def deploy(dry=False, force=False):
    """Разложить покрытые фото в public/img/products/ как webp.

    - ракурс с наименьшим номером -> {article}.webp (главное),
      остальные -> {article}_2.webp ... (плотная переиндексация);
    - U2B-003-1/U2B-006-1 раскладываются как U2B-003/U2B-006 (на сайте без -1);
    - DESIGN: ракурсы 5/6 (упаковка) отбрасываются;
    - огромные исходники ужимаются до 2000px; идемпотентно (force — перезапись).
    """
    from PIL import Image
    sys.stdout.reconfigure(encoding="utf-8")
    matched, by_series, fuzzy_notes, unmatched_files, junk_files = build_matches()
    os.makedirs(PRODUCTS_DIR, exist_ok=True)

    written = skipped_fuzzy = 0
    collisions = []
    errors = []
    for (skey, key), rec in sorted(matched.items()):
        drop = DROP_VIEWS
        # один файл на ракурс (если на view несколько — берём png/первый)
        byview = {}
        for view, fp in rec["items"]:
            if view in drop:
                continue  # ненужный ракурс (напр. design 5/6 — упаковка)
            if view in byview:
                collisions.append((key, view, byview[view], fp))
                # предпочесть .png (часто это обработанный главный кадр)
                if fp.lower().endswith(".png"):
                    byview[view] = fp
                continue
            byview[view] = fp
        ordered = [byview[v] for v in sorted(byview)]
        for i, src in enumerate(ordered):
            suffix = "" if i == 0 else f"_{i+1}"
            dst = os.path.join(PRODUCTS_DIR, f"{key}{suffix}.webp")
            if dry:
                print(f"  [dry] {os.path.basename(src)} -> {key}{suffix}.webp")
                written += 1
                continue
            if not force and os.path.exists(dst):
                continue  # идемпотентность: не перезаписываем готовое
            try:
                im = Image.open(src)
                im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
                # огромные исходники ужимаем (память + вес); для веба хватает 2000px
                if max(im.size) > 2000:
                    im.thumbnail((2000, 2000), Image.LANCZOS)
                im.save(dst, "WEBP", quality=WEBP_QUALITY, method=4)
                written += 1
            except Exception as e:
                errors.append((os.path.basename(src), f"{key}{suffix}.webp", str(e)))

    print(f"{'[DRY] ' if dry else ''}Записано webp-файлов: {written}")
    if collisions:
        print(f"Коллизии ракурсов (>1 файл на номер): {len(collisions)}")
        for key, view, a, b in collisions[:10]:
            print(f"  {key} ракурс {view}: {os.path.basename(a)} / {os.path.basename(b)}")
    if errors:
        print(f"ОШИБКИ конвертации: {len(errors)}")
        for src, dst, e in errors[:15]:
            print(f"  {src} -> {dst}: {e}")


def cleanup_packaging(dry=False):
    """Удалить ракурсы 5 и 6 (товар в упаковке) — и с сайта (webp),
    и с ПК (исходники в unpacked). По данным сопоставления build_matches."""
    sys.stdout.reconfigure(encoding="utf-8")
    matched, *_ = build_matches()
    removed_web = removed_src = 0
    for (skey, key), rec in sorted(matched.items()):
        for view, fp in rec["items"]:
            if view not in DROP_VIEWS:
                continue
            # с ПК — исходник
            if os.path.exists(fp):
                if dry:
                    print(f"  [dry] ПК: {fp}")
                else:
                    os.remove(fp)
                removed_src += 1
    # с сайта — все *_5.webp / *_6.webp в products
    for f in os.listdir(PRODUCTS_DIR):
        m = re.search(r"_(\d+)\.webp$", f, re.I)
        if m and int(m.group(1)) in DROP_VIEWS:
            p = os.path.join(PRODUCTS_DIR, f)
            if dry:
                print(f"  [dry] сайт: {f}")
            else:
                os.remove(p)
            removed_web += 1
    print(f"{'[DRY] ' if dry else ''}Удалено с сайта (webp): {removed_web}; с ПК (исходники): {removed_src}")


def resync(dry=False):
    """Пересобрать сайт из текущего состояния unpacked/.

    Удаляет ВСЕ webp покрытых артикулов и раскладывает заново — так сайт
    отражает ручные правки пользователя в папках (удалённые кадры/ракурсы),
    с корректной перенумерацией ракурсов (без дыр). Запускать после того,
    как пользователь почистил подпапки в unpacked/.
    """
    sys.stdout.reconfigure(encoding="utf-8")
    matched, *_ = build_matches()
    removed = 0
    keys = sorted({key for (_s, key) in matched})
    existing = set(os.listdir(PRODUCTS_DIR)) if os.path.isdir(PRODUCTS_DIR) else set()
    for key in keys:
        for f in existing:
            if f == f"{key}.webp" or re.match(rf"^{re.escape(key)}_\d+\.webp$", f):
                if dry:
                    print(f"  [dry] удалить {f}")
                else:
                    os.remove(os.path.join(PRODUCTS_DIR, f))
                removed += 1
    print(f"{'[DRY] ' if dry else ''}Удалено старых webp покрытых артикулов: {removed}")
    if not dry:
        deploy(force=True)


if __name__ == "__main__":
    if "--cleanup56" in sys.argv:
        cleanup_packaging(dry="--dry" in sys.argv)
    elif "--resync" in sys.argv:
        resync(dry="--dry" in sys.argv)
    elif "--deploy" in sys.argv:
        deploy(dry="--dry" in sys.argv, force="--force" in sys.argv)
    else:
        main()
