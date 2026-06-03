"""
compare_catalog.py — сравнивает our_data.json и stv_data.json,
пишет scripts/audit/gaps_report.md с тремя секциями для каждой серии:
  • Новые товары (база отсутствует у нас)
  • Новые цвета для существующих баз
  • Пропавшее у них (контрольная секция)

Никаких автоматических правок series.json не делает.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "scripts" / "audit"
OUR = json.loads((AUDIT / "our_data.json").read_text(encoding="utf-8"))
STV = json.loads((AUDIT / "stv_data.json").read_text(encoding="utf-8"))
OUT = AUDIT / "gaps_report.md"

SERIES_TITLE = {"uno": "УНО", "aura": "АУРА", "design": "ДИЗАЙН"}

# ---------------------------------------------------------------- color maps

LETTER_COLOR = {
    "W": "белый",
    "B": "чёрный",
    "BL": "чёрный",
    "G": "золото",
    "GR": "серый",
    "BR": "бронза",
    "AL": "алюминий",
    "CR": "хром",
    "S": "серебро",
    "SL": "серебро",
    "DG": "тёмно-серый",
}
WORD_COLOR = {
    "white": "белый",
    "black": "чёрный",
    "matte black": "чёрный матовый",
    "grey": "серый",
    "gray": "серый",
    "dark grey": "тёмно-серый",
    "dark gray": "тёмно-серый",
    "dark": "тёмно-серый",
    "silver": "серебро",
    "gold": "золото",
}
STV_FIELD_COLOR = {
    "белый": "белый",
    "черный": "чёрный",
    "чёрный": "чёрный",
    "черный матовый": "чёрный матовый",
    "чёрный матовый": "чёрный матовый",
    "серый": "серый",
    "темно-серый": "тёмно-серый",
    "тёмно-серый": "тёмно-серый",
    "серебряный": "серебро",
    "серебро": "серебро",
    "золото": "золото",
    "бронза": "бронза",
}


# ---------------------------------------------------------------- normalize

ARTICLE_SPACE_COLOR = re.compile(r"^(.+?)\s+([A-Za-z][A-Za-z ]*)$")

# цветовые суффиксы в порядке убывания длины — чтобы GR матчился раньше G
COLOR_SUFFIXES = ["DG", "GR", "BL", "BR", "AL", "CR", "SL", "W", "B", "G", "S"]


def parse_article(article: str, stv_color_field: str = "") -> tuple[str, str]:
    """Возвращает (base, color_label). color_label — нормализованное слово или ''."""
    if not article:
        return "", ""
    a = article.strip()

    # 1) "U1A-001-1 white", "U2B-028 matte black"
    m = ARTICLE_SPACE_COLOR.match(a)
    if m:
        base = m.group(1).strip().upper()
        word = m.group(2).strip().lower()
        color = WORD_COLOR.get(word, word)
        return base, color

    # 2) "A-033G", "PD80-1GR", "B30-8VGR" (V — модификатор «вертикальная»)
    # пытаемся отрезать с конца самый длинный известный цветовой суффикс
    upper = a.upper()
    if re.search(r"\d", upper):
        for cs in COLOR_SUFFIXES:
            if upper.endswith(cs):
                base = upper[: -len(cs)].rstrip("-_ ")
                # база должна оканчиваться чем-то осмысленным (цифра или буква-модификатор)
                if base and re.search(r"\d", base):
                    return base, LETTER_COLOR[cs]
    # запас — по полю «Цвет» из карточки
    if stv_color_field:
        color = STV_FIELD_COLOR.get(stv_color_field.lower().strip(), "")
        return upper, color

    # 3) запасной вариант — по полю Цвет из карточки
    color = STV_FIELD_COLOR.get(stv_color_field.lower().strip(), "")
    return a.upper(), color


def make_index(items: list[dict], source: str) -> dict[str, dict]:
    """index[base] = {colors: {color: [article,...]}, items: [orig_item,...]}."""
    idx: dict[str, dict] = {}
    for it in items:
        article = it.get("article", "")
        stv_color = it.get("color", "") if source == "stv" else ""
        base, color = parse_article(article, stv_color)
        if not base:
            continue
        entry = idx.setdefault(base, {"colors": {}, "items": []})
        entry["colors"].setdefault(color or "—", []).append(article)
        entry["items"].append(it)
    return idx


# ---------------------------------------------------------------- report

def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x).replace("|", "\\|") for x in r) + " |")
    return "\n".join(out)


def report_series(skey: str) -> str:
    our_idx = make_index(OUR.get(skey, {}).get("items", []), "our")
    stv_idx = make_index(STV.get(skey, {}).get("items", []), "stv")

    title = SERIES_TITLE[skey]
    md: list[str] = [f"\n## {title}\n"]
    md.append(f"- наших баз артикулов: **{len(our_idx)}**  (items: {len(OUR.get(skey,{}).get('items',[]))})")
    md.append(f"- баз stv: **{len(stv_idx)}**  (items: {len(STV.get(skey,{}).get('items',[]))})")

    # 1) Новые товары — базы которые есть у stv, нет у нас
    new_bases = sorted(set(stv_idx) - set(our_idx))
    md.append(f"\n### 1. Новые товары (база отсутствует у нас) — {len(new_bases)}")
    if new_bases:
        rows = []
        for base in new_bases:
            entry = stv_idx[base]
            # один товар представительный
            sample = entry["items"][0]
            colors = sorted(entry["colors"].keys())
            rows.append([
                f"`{base}`",
                sample.get("type", "") or "—",
                ", ".join(colors),
                len(entry["items"]),
                f"[stv]({sample['url']})",
            ])
        md.append(md_table(["База", "Тип", "Цвета", "Шт. вариаций", "Пример"], rows))
    else:
        md.append("_нет_")

    # 2) Новые цвета для общих баз
    common = sorted(set(stv_idx) & set(our_idx))
    color_gaps_rows = []
    for base in common:
        our_colors = set(our_idx[base]["colors"].keys()) - {"—"}
        stv_colors = set(stv_idx[base]["colors"].keys()) - {"—"}
        new_colors = stv_colors - our_colors
        if new_colors:
            sample = stv_idx[base]["items"][0]
            color_gaps_rows.append([
                f"`{base}`",
                ", ".join(sorted(our_colors)) or "—",
                ", ".join(sorted(stv_colors)),
                ", ".join(sorted(new_colors)),
                f"[stv]({sample['url']})",
            ])
    md.append(f"\n### 2. Новые цвета для существующих баз — {len(color_gaps_rows)}")
    if color_gaps_rows:
        md.append(md_table(["База", "Наши цвета", "Цвета stv", "**Новые**", "Пример"], color_gaps_rows))
    else:
        md.append("_нет_")

    # 3) Пропавшее у них — базы у нас, не у stv (контроль)
    missing_at_stv = sorted(set(our_idx) - set(stv_idx))
    md.append(f"\n### 3. Есть у нас, нет у stv — {len(missing_at_stv)} _(контрольная сверка)_")
    if missing_at_stv:
        md.append(", ".join(f"`{b}`" for b in missing_at_stv))
    else:
        md.append("_нет_")

    # 4) Развёрнутый список новых артикулов (для удобства глазами проверять)
    md.append(f"\n### 4. Полный список новых артикулов (детально)")
    detail_rows = []
    for base in new_bases:
        entry = stv_idx[base]
        for it in entry["items"]:
            detail_rows.append([
                f"`{it.get('article','')}`",
                it.get("name", "")[:70],
                it.get("type", "") or "—",
                it.get("color", "") or "—",
                it.get("ip", "") or "—",
                f"[link]({it['url']})",
            ])
    # цвета базы тоже добавим (новые цвета существующих баз)
    for row in color_gaps_rows:
        base = row[0].strip("`")
        entry = stv_idx[base]
        for it in entry["items"]:
            article = it.get("article", "")
            _, c = parse_article(article, it.get("color", ""))
            # только варианты с новыми цветами
            if c and c in set(row[3].split(", ")):
                detail_rows.append([
                    f"`{article}`",
                    it.get("name", "")[:70],
                    it.get("type", "") or "—",
                    c,
                    it.get("ip", "") or "—",
                    f"[link]({it['url']})",
                ])
    if detail_rows:
        md.append(md_table(["Артикул", "Название", "Тип", "Цвет", "IP", "URL"], detail_rows))
    else:
        md.append("_нет_")

    return "\n".join(md)


def main() -> None:
    today = date.today().isoformat()
    out: list[str] = [
        "# AWS — отчёт по аудиту каталога",
        f"_дата: {today}_  ",
        "",
        "Сравнение `src/data/series.json` ↔ stv39.ru для серий **УНО / АУРА / ДИЗАЙН**.",
        "Принадлежность к бренду на stv определена по URL/H1 (поле «Бренд» в карточках часто пустое).",
        "",
        "## Сводка",
    ]
    sum_rows = []
    for skey in ("uno", "aura", "design"):
        our_idx = make_index(OUR.get(skey, {}).get("items", []), "our")
        stv_idx = make_index(STV.get(skey, {}).get("items", []), "stv")
        new_bases = sorted(set(stv_idx) - set(our_idx))
        color_gaps = 0
        for base in set(stv_idx) & set(our_idx):
            oc = set(our_idx[base]["colors"].keys()) - {"—"}
            sc = set(stv_idx[base]["colors"].keys()) - {"—"}
            if sc - oc:
                color_gaps += 1
        sum_rows.append([
            SERIES_TITLE[skey],
            len(OUR.get(skey, {}).get("items", [])),
            len(STV.get(skey, {}).get("items", [])),
            len(new_bases),
            color_gaps,
        ])
    out.append(md_table(
        ["Серия", "items у нас", "items stv", "Новых баз", "Баз с новыми цветами"],
        sum_rows,
    ))

    for skey in ("uno", "aura", "design"):
        out.append(report_series(skey))

    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
