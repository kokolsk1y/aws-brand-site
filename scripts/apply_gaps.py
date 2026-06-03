"""
apply_gaps.py — переносит новые товары и цвета из stv_data.json в src/data/series.json.

Идемпотентен: повторный запуск не создаёт дубликаты (проверка по article).
Не трогает существующие товары (article+name+price остаются).
Цены новых товаров: null (заполнить руками).
Картинки новых цветов в colors[].img: пустая строка.
"""

from __future__ import annotations
import json
import re
import sys
from pathlib import Path

# импортируем нормализацию артикулов из compare_catalog
sys.path.insert(0, str(Path(__file__).parent))
from compare_catalog import parse_article  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
SERIES_JSON = ROOT / "src" / "data" / "series.json"
STV_JSON = ROOT / "scripts" / "audit" / "stv_data.json"

# карта серий: ключ → русская подпись в кавычках в имени stv
SERIES_LABEL = {"uno": "Уно", "aura": "Аура", "design": "Дизайн"}

# нормализованный цвет (из parse_article) → ключ в colors[].key
COLOR_TO_KEY = {
    "белый": "white",
    "чёрный": "black",
    "серый": "grey",
    "тёмно-серый": "dark_grey",
    "серебро": "silver",
    "золото": "gold",
    "бронза": "bronze",
    "хром": "chrome",
    "алюминий": "aluminium",
}
# подпись цвета на UI (для colors[].label)
COLOR_LABEL = {
    "white": "Белый",
    "black": "Чёрный",
    "grey": "Серый",
    "dark_grey": "Тёмно-серый",
    "silver": "Серебро",
    "gold": "Золото",
    "matte_black": "Чёрный матовый",
    "bronze": "Бронза",
    "chrome": "Хром",
    "aluminium": "Алюминий",
    "mahogany": "Махагон",
}

# матовый чёрный для UNO (U2B-* + "matte black" в названии)
def color_key_for(item: dict) -> str:
    article = item.get("article", "")
    stv_color = (item.get("color") or "").lower()
    # ручное распознавание матового
    if "матов" in stv_color or "matte" in article.lower():
        return "matte_black"
    # ручное — махагон (W30 в АУРЕ)
    if article.upper().startswith("W30") and "матов" not in stv_color:
        return "mahogany"
    _, color_label_ru = parse_article(article, item.get("color", ""))
    return COLOR_TO_KEY.get(color_label_ru, "")


# ---------------------------------------------------------------- name clean

def clean_name(stv_name: str, series_label: str) -> str:
    """Очищает name со stv до нашего короткого стиля."""
    n = stv_name

    # 1. убрать "AWSproducts" в конце
    n = re.sub(r"\s*AWSproducts\s*$", "", n, flags=re.I)

    # 2. убрать ток в конце ("10A", "16A", " 10A ")
    n = re.sub(r"\s*\d+\s*A\s*$", "", n)

    # 3. убрать "Серия" в кавычках: "Уно" / "Аура" / "Дизайн"
    n = re.sub(rf'\s*[«"]{series_label}[»"]\s*', " ", n, flags=re.I)

    # 4. убрать артикул + опциональный суффикс цвета
    art_re = (
        r"\s+(?:U1A|U2B|A-D|A|PD80|PG51|G51|G50|P50|B30|W30)"
        r"[-\s]?[A-Z0-9-]+(?:\s+(?:white|black|grey|silver|gold|dark\s+grey|matte\s+black))?"
    )
    n = re.sub(art_re, " ", n, flags=re.I)

    # 5. свернуть пробелы
    n = re.sub(r"\s+", " ", n).strip()

    return n


# ---------------------------------------------------------------- group detect

def detect_group(name: str) -> str:
    """По названию определяет группу: switches/sockets/frames/other."""
    lower = name.lower()
    if "выключател" in lower:
        return "switches"
    if "розетк" in lower:
        return "sockets"
    if "рамка" in lower or "рамки" in lower:
        return "frames"
    return "other"


# ---------------------------------------------------------------- main apply

def apply_series(skey: str, series_obj: dict, stv_items: list[dict]) -> dict:
    """Возвращает (stats) — изменения по серии."""
    label = SERIES_LABEL[skey]
    groups = series_obj.setdefault("groups", {"switches": [], "sockets": [], "frames": [], "accessories": [], "other": []})
    for g in ("switches", "sockets", "frames", "accessories", "other"):
        groups.setdefault(g, [])

    existing_articles = set()
    for g, items in groups.items():
        for it in items:
            existing_articles.add(it["article"].strip())

    added_by_group = {"switches": 0, "sockets": 0, "frames": 0, "other": 0}
    added_colors = set()

    for stv in stv_items:
        article = stv.get("article", "").strip()
        if not article:
            continue
        if article in existing_articles:
            continue

        name = clean_name(stv.get("name", ""), label)
        if not name:
            continue

        color_key = color_key_for(stv)
        group = detect_group(name)
        if group not in groups:
            group = "other"

        groups[group].append({
            "article": article,
            "name": name,
            "color": color_key,
            "price": None,
        })
        existing_articles.add(article)
        added_by_group[group] += 1
        if color_key:
            added_colors.add(color_key)

    # обновим массив colors на уровне серии
    existing_color_keys = {c.get("key") for c in series_obj.get("colors", [])}
    series_obj.setdefault("colors", [])
    for ck in sorted(added_colors):
        if ck and ck not in existing_color_keys:
            series_obj["colors"].append({
                "key": ck,
                "label": COLOR_LABEL.get(ck, ck.title()),
                "img": "",
            })
    # фиксированный порядок: белый, чёрный, остальные «тёплые» → «холодные»
    color_order = ["white", "black", "grey", "dark_grey", "silver",
                   "gold", "bronze", "chrome", "aluminium", "matte_black", "mahogany"]
    series_obj["colors"].sort(key=lambda c: (
        color_order.index(c["key"]) if c["key"] in color_order else 999,
        c.get("key", ""),
    ))

    return {
        "added": sum(added_by_group.values()),
        "by_group": added_by_group,
        "new_colors": sorted(added_colors - existing_color_keys),
    }


def activate_design(design_obj: dict) -> None:
    """ДИЗАЙН — снимаем «в разработке», делаем серию активной."""
    design_obj["tagline"] = "Геометрия и контраст."
    design_obj["badge"] = "Новинка"
    design_obj["description"] = (
        "Серия ДИЗАЙН — выразительная геометрия для современных интерьеров. "
        "Чёткие линии, контрастная палитра и расширенная функциональность: подсветка, "
        "перекрёстные и проходные выключатели, телевизионные и компьютерные розетки. "
        "Подходит для тех, кто строит интерьер на акцентах."
    )


def main() -> None:
    series = json.loads(SERIES_JSON.read_text(encoding="utf-8"))
    stv = json.loads(STV_JSON.read_text(encoding="utf-8"))

    print("=== apply_gaps ===")
    for skey in ("uno", "aura", "design"):
        items_before = sum(len(g) for g in series[skey].get("groups", {}).values())
        stats = apply_series(skey, series[skey], stv[skey]["items"])
        items_after = sum(len(g) for g in series[skey].get("groups", {}).values())
        print(f"\n  {skey}: {items_before} -> {items_after}  (+{stats['added']})")
        print(f"    by group: {stats['by_group']}")
        if stats["new_colors"]:
            print(f"    new colors in colors[]: {stats['new_colors']}")

    activate_design(series["design"])
    print(f"\n  design: header rewritten (tagline/badge/description)")

    SERIES_JSON.write_text(
        json.dumps(series, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\n  saved -> {SERIES_JSON}")


if __name__ == "__main__":
    main()
