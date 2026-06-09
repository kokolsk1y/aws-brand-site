"""
extract_stv_specs.py — вытаскивает ОПИСАНИЕ и ХАРАКТЕРИСТИКИ товаров со stv39.ru
для всех наших артикулов (серии series.json + не-серийные products.json).

Источник на карточке STV: <div class="brief__new__main"> → <p>.
Текст делится по строке "Характеристики:" на:
  • description — проза (маркетинговое описание)
  • specs       — список "ключ: значение" (для таблицы рядом с описанием)

Результат: scripts/audit/stv_specs.json  (ключ = наш артикул)
Сырьё, без переписывания стиля. HTML кэшируется в scripts/cache/stv/<sha1>.html.
"""

from __future__ import annotations
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
SERIES_JSON = ROOT / "src" / "data" / "series.json"
PRODUCTS_JSON = ROOT / "public" / "products.json"  # реальный источник сайта (root устарел)
STV_DATA = ROOT / "scripts" / "audit" / "stv_data.json"
CACHE_DIR = ROOT / "scripts" / "cache" / "stv"
OUT = ROOT / "scripts" / "audit" / "stv_specs.json"
REPORT = ROOT / "scripts" / "audit" / "stv_specs_report.md"

BASE = "https://stv39.ru"
SEARCH_TPL = BASE + "/catalog/?q={q}&s=&count=100"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 audit-bot"}
PAUSE_SEC = 0.7
PRODUCT_URL_RE = re.compile(r"^/catalog/[a-z0-9_-]+/[a-z0-9_-]+/?$", re.I)


# ---------------------------------------------------------------- fetch/cache

def fetch(url: str, allow_net: bool = True) -> str | None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()
    cf = CACHE_DIR / f"{key}.html"
    if cf.exists():
        return cf.read_text(encoding="utf-8")
    if not allow_net:
        return None
    print(f"  GET {url}", file=sys.stderr)
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        r.encoding = "utf-8"
    except Exception as e:
        print(f"  ! fetch failed {url}: {e}", file=sys.stderr)
        return None
    cf.write_text(r.text, encoding="utf-8")
    time.sleep(PAUSE_SEC)
    return r.text


# ---------------------------------------------------------------- parsing

KEY_PREFIX_RE = re.compile(r"^[\s•\-–—*·]+")
SPLIT_RE = re.compile(r"\n?Характеристики\s*:?\s*\n?", re.I)


def clean_key(k: str) -> str:
    k = KEY_PREFIX_RE.sub("", k).strip()
    return k.rstrip(":").strip()


# буллет-строка вида "• Номинальный ток: до 32 А" (характеристика вне блока "Характеристики:")
BULLET_SPEC_RE = re.compile(r"^[\s•\-–—*·]+(.{2,45}?):\s*(.+)$")


def _specs_from_lines(text: str) -> dict[str, str]:
    specs: dict[str, str] = {}
    for line in text.split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            k = clean_key(k)
            v = v.strip()
            if k and v:
                specs[k] = v
    return specs


def parse_card(html: str) -> dict | None:
    """{description, specs{}} из карточки STV, либо None если блок не найден.

    specs берём из секции после "Характеристики:". Если её нет — фолбэк:
    буллет-строки "• ключ: значение" из описания (клеммы/коннекторы/кабель так
    оформлены). Описание сохраняем дословно, как на STV.
    """
    s = BeautifulSoup(html, "lxml")
    block = s.select_one(".brief__new__main")
    if not block:
        return None
    p = block.find("p")
    if not p:
        return None
    txt = p.get_text("\n", strip=True)
    parts = SPLIT_RE.split(txt, maxsplit=1)
    description = parts[0].strip()
    if len(parts) > 1:
        specs = _specs_from_lines(parts[1])
    else:
        # фолбэк: только строки-буллеты с двоеточием (не вся проза)
        specs = {}
        for line in description.split("\n"):
            m = BULLET_SPEC_RE.match(line)
            if m:
                k = clean_key(m.group(1))
                v = m.group(2).strip()
                if k and v:
                    specs[k] = v
    return {"description": description, "specs": specs}


# ---------------------------------------------------------------- search STV

def search_article_url(article: str) -> str | None:
    """Ищет карточку STV по артикулу. Возвращает URL первой подходящей AWS-карточки."""
    # для поиска берём «ядро» артикула без цветового слова
    core = article.split(" ")[0]
    url = SEARCH_TPL.format(q=quote(core))
    html = fetch(url)
    if not html:
        return None
    s = BeautifulSoup(html, "lxml")
    cand: list[str] = []
    for a in s.select("a[href]"):
        href = a.get("href", "")
        if PRODUCT_URL_RE.match(href):
            cand.append(href)
    # приоритет — ссылки, где в slug встречается код артикула
    token = re.sub(r"[^a-z0-9]", "", core.lower())
    for href in cand:
        if token and token in re.sub(r"[^a-z0-9]", "", href.lower()):
            return urljoin(BASE, href)
    return urljoin(BASE, cand[0]) if cand else None


# ---------------------------------------------------------------- collect our articles

def our_articles() -> list[dict]:
    """[{article, name, source, group, color}] — все наши товары."""
    out = []
    series = json.loads(SERIES_JSON.read_text(encoding="utf-8"))
    for skey, sv in series.items():
        for gname, items in (sv.get("groups") or {}).items():
            for it in items:
                out.append({"article": it["article"], "name": it.get("name", ""),
                            "source": f"series:{skey}", "group": gname,
                            "color": it.get("color", "")})
    products = json.loads(PRODUCTS_JSON.read_text(encoding="utf-8"))
    for cat, v in products.items():
        for it in (v.get("items") or []):
            out.append({"article": it["article"], "name": it.get("name", ""),
                        "source": f"products:{cat}", "group": cat, "color": ""})
    return out


# ---------------------------------------------------------------- borrow from base

COLOR_RU = {
    "white": "белый", "black": "чёрный", "grey": "серый", "dark_grey": "тёмно-серый",
    "silver": "серебро", "matte_black": "чёрный матовый", "gold": "золото",
    "mahogany": "красное дерево",
}
COLOR_SUFFIX_RE = re.compile(r"(DG|GR|BL|BR|AL|CR|SL|VW|VB|VG|W|B|G|S)$")


def base_key(article: str) -> str:
    """Артикул без цветового суффикса: 'A-001GR'→'A-001', 'U1A-001-1 white'→'U1A-001-1'."""
    a = article.split(" ")[0].upper()
    a = COLOR_SUFFIX_RE.sub("", a)
    return a.rstrip("-_")


def borrow_from_base(result: dict, arts: list[dict]) -> int:
    """Цветовые варианты = тот же товар, характеристики идентичны.
    Заполняет пустые specs от собрата по базе (с корректным полем «Цвет»).
    Возвращает число дотянутых артикулов."""
    color_by_art = {a["article"]: a.get("color", "") for a in arts}
    groups: dict[str, list[str]] = {}
    for art in result:
        groups.setdefault(base_key(art), []).append(art)

    borrowed = 0
    for base, members in groups.items():
        donors = [m for m in members if result[m]["specs"]]
        if not donors:
            continue
        # донор с максимумом полей
        donor = max(donors, key=lambda m: len(result[m]["specs"]))
        donor_specs = result[donor]["specs"]
        for m in members:
            if result[m]["specs"]:
                continue
            specs = dict(donor_specs)
            ru = COLOR_RU.get(color_by_art.get(m, ""))
            if ru:
                specs["Цвет"] = ru
            result[m]["specs"] = specs
            result[m]["specs_borrowed"] = True
            result[m]["specs_borrowed_from"] = donor
            result[m]["found"] = True
            borrowed += 1
    return borrowed


def stv_url_index() -> dict[str, str]:
    """article -> stv url (из прошлого аудита)."""
    idx = {}
    if STV_DATA.exists():
        stv = json.loads(STV_DATA.read_text(encoding="utf-8"))
        for sv in stv.values():
            for it in sv.get("items", []):
                idx.setdefault(it["article"], it["url"])
    return idx


# ---------------------------------------------------------------- main

def main() -> None:
    arts = our_articles()
    url_idx = stv_url_index()
    print(f"Наших артикулов: {len(arts)}")

    result: dict[str, dict] = {}
    stats = {"from_cache": 0, "searched": 0, "no_url": 0, "no_block": 0, "with_specs": 0}

    for i, a in enumerate(arts, 1):
        art = a["article"]
        url = url_idx.get(art)
        searched = False
        if not url:
            url = search_article_url(art)
            searched = True
        if not url:
            stats["no_url"] += 1
            result[art] = {"our_name": a["name"], "source": a["source"],
                           "stv_url": None, "found": False,
                           "description": "", "specs": {}}
            continue
        html = fetch(url)
        if not html:
            stats["no_url"] += 1
            result[art] = {"our_name": a["name"], "source": a["source"],
                           "stv_url": url, "found": False,
                           "description": "", "specs": {}}
            continue
        parsed = parse_card(html)
        if searched:
            stats["searched"] += 1
        else:
            stats["from_cache"] += 1
        if not parsed:
            stats["no_block"] += 1
            result[art] = {"our_name": a["name"], "source": a["source"],
                           "stv_url": url, "found": False,
                           "description": "", "specs": {}}
            continue
        if parsed["specs"]:
            stats["with_specs"] += 1
        result[art] = {
            "our_name": a["name"],
            "source": a["source"],
            "stv_url": url,
            "found": bool(parsed["description"] or parsed["specs"]),
            "description": parsed["description"],
            "specs": parsed["specs"],
        }
        if i % 50 == 0:
            print(f"  {i}/{len(arts)} ...")

    # дотяжка характеристик цветовых вариантов от базового артикула
    borrowed = borrow_from_base(result, arts)
    print(f"\n  дотянуто характеристик от базы: {borrowed}")

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # ----- агрегаты по источникам -----
    from collections import defaultdict
    SHORT_DESC = 120   # порог «тонкого» описания, символов
    by = defaultdict(lambda: {"n": 0, "desc": 0, "specs": 0, "fields": 0,
                              "thin": [], "nospec": [], "miss": []})
    for art, v in result.items():
        b = by[v["source"]]
        b["n"] += 1
        if v["description"]:
            b["desc"] += 1
        if v["specs"]:
            b["specs"] += 1
            b["fields"] += len(v["specs"])
        else:
            if v["found"]:
                b["nospec"].append(art)
        if not v["found"]:
            b["miss"].append(art)
        elif len(v["description"]) < SHORT_DESC:
            b["thin"].append(art)

    found = sum(1 for v in result.values() if v["found"])
    with_specs = sum(1 for v in result.values() if v["specs"])
    total_desc = sum(1 for v in result.values() if v["description"])

    def pct(a, b):
        return f"{(100*a/b):.0f}%" if b else "—"

    lines = [
        "# STV — извлечение описаний и характеристик",
        "",
        "_Сырьё со stv39.ru для всех наших артикулов. Стиль не переписан._",
        "",
        "## Итог",
        "",
        f"- **всего наших артикулов (весь сайт AWS): {len(arts)}**",
        f"- найдено карточек на STV: **{found}** ({pct(found, len(arts))})",
        f"- получено описаний: **{total_desc}** ({pct(total_desc, len(arts))})",
        f"- получено характеристик (таблица): **{with_specs}** ({pct(with_specs, len(arts))})",
        f"  - из них дотянуто от базового цвета: **{borrowed}** (цветовые варианты, характеристики идентичны)",
        f"- источник данных: кэш {stats['from_cache']} • поиск по сети {stats['searched']}",
        "",
        "## По группам",
        "",
        "| Источник | Товаров | Описание | Характ-ки | Ср. полей | Не найдено |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for src in sorted(by):
        b = by[src]
        avg = b["fields"] / b["specs"] if b["specs"] else 0
        lines.append(
            f"| `{src}` | {b['n']} | {b['desc']} ({pct(b['desc'], b['n'])}) | "
            f"{b['specs']} ({pct(b['specs'], b['n'])}) | {avg:.1f} | {len(b['miss'])} |"
        )
    lines.append(f"| **ИТОГО** | **{len(arts)}** | **{total_desc}** | **{with_specs}** | | "
                 f"**{len(arts) - found}** |")

    # ----- детальные списки для ручной сверки -----
    lines += ["", "## Карточки без характеристик (описание есть, таблицы нет)",
              "_на STV эти карточки оформлены без списка характеристик_", ""]
    nospec_all = [a for v in by.values() for a in v["nospec"]]
    if nospec_all:
        for src in sorted(by):
            if by[src]["nospec"]:
                lines.append(f"- **{src}** ({len(by[src]['nospec'])}): "
                             + ", ".join(f"`{a}`" for a in by[src]["nospec"]))
    else:
        lines.append("_нет_")

    lines += ["", "## Тонкие описания (< 120 символов на STV)",
              "_кандидаты на доработку — у STV почти нет текста_", ""]
    thin_all = [a for v in by.values() for a in v["thin"]]
    if thin_all:
        for src in sorted(by):
            if by[src]["thin"]:
                lines.append(f"- **{src}** ({len(by[src]['thin'])}): "
                             + ", ".join(f"`{a}`" for a in by[src]["thin"]))
    else:
        lines.append("_нет_")

    lines += ["", "## Не найдены на STV", ""]
    miss = [art for art, v in result.items() if not v["found"]]
    if miss:
        lines += [f"- `{a}` ({result[a]['source']})" for a in miss]
    else:
        lines.append("_все артикулы найдены_")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n=== РЕЗУЛЬТАТ ===")
    print(f"  всего={len(arts)}  найдено={found}  описаний={total_desc}  характеристик={with_specs}")
    print(f"  кэш={stats['from_cache']} поиск={stats['searched']} "
          f"не_найдено={len(miss)} тонких_описаний={len(thin_all)}")
    print(f"  данные -> {OUT}")
    print(f"  отчёт  -> {REPORT}")


if __name__ == "__main__":
    main()
