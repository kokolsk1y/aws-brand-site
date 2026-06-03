"""
audit_catalog.py — собирает каталог УНО/АУРА/ДИЗАЙН из двух источников:

  1) НАШ:  src/data/series.json  →  scripts/audit/our_data.json
  2) STV:  https://stv39.ru/catalog/?q=...  →  scripts/audit/stv_data.json

Только серии brand=AWSProducts. Без цен и наличия.
HTML кэшируется в scripts/cache/stv/<sha1>.html.
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
OUR_SERIES_JSON = ROOT / "src" / "data" / "series.json"
OUT_DIR = ROOT / "scripts" / "audit"
CACHE_DIR = ROOT / "scripts" / "cache" / "stv"
OUR_OUT = OUT_DIR / "our_data.json"
STV_OUT = OUT_DIR / "stv_data.json"

BASE = "https://stv39.ru"
SEARCH_TPL = BASE + "/catalog/?q={q}&s=&count=100"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 audit-bot"}
PAUSE_SEC = 0.7

# серии для скрейпа: ключ в нашем series.json → поисковый запрос на stv
SERIES_QUERIES = {
    "uno": "УНО",
    "aura": "АУРА",
    "design": "дизайн",
}


# ---------------------------------------------------------------- helpers

def fetch(url: str) -> str:
    """GET с кэшем по URL. Возвращает HTML (UTF-8)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()
    cache_file = CACHE_DIR / f"{key}.html"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    print(f"  GET {url}", file=sys.stderr)
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    r.encoding = "utf-8"
    cache_file.write_text(r.text, encoding="utf-8")
    time.sleep(PAUSE_SEC)
    return r.text


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


# ---------------------------------------------------------------- our_data

def collect_our() -> dict:
    data = json.loads(OUR_SERIES_JSON.read_text(encoding="utf-8"))
    out = {}
    for skey in SERIES_QUERIES:
        s = data.get(skey)
        if not s:
            continue
        items = []
        for group_name, group_items in (s.get("groups") or {}).items():
            for it in group_items:
                items.append({
                    "article": it.get("article"),
                    "name": it.get("name"),
                    "group": group_name,
                    "color": it.get("color"),
                    "price": it.get("price"),
                })
        out[skey] = {
            "name": s.get("name"),
            "slug": s.get("slug"),
            "colors_declared": [c.get("key") for c in s.get("colors") or []],
            "items": items,
            "items_count": len(items),
        }
    return out


# ---------------------------------------------------------------- stv listing

PRODUCT_URL_RE = re.compile(r"^/catalog/[a-z0-9_-]+/[a-z0-9_-]+/?$", re.I)
PAGEN_RE = re.compile(r"PAGEN_2=(\d+)")


def listing_product_urls(query_word: str) -> list[str]:
    """Собирает URL карточек по поисковому запросу со всех страниц пагинации."""
    seen: set[str] = set()
    q_enc = quote(query_word)
    page_urls = [SEARCH_TPL.format(q=q_enc)]
    discovered_pages: set[int] = {1}
    while page_urls:
        url = page_urls.pop(0)
        html = fetch(url)
        soup = soup_of(html)
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if PRODUCT_URL_RE.match(href):
                seen.add(href)
        # пагинация
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            m = PAGEN_RE.search(href)
            if m and f"q={q_enc}" in href:
                pn = int(m.group(1))
                if pn not in discovered_pages:
                    discovered_pages.add(pn)
                    page_urls.append(urljoin(BASE, href))
    return sorted(seen)


# ---------------------------------------------------------------- stv product

# нормализация заголовков характеристик к каноничным ключам
SPEC_ALIASES = {
    "артикул": "article",
    "бренд": "brand",
    "тип": "type",
    "серия": "series",
    "цвет": "color",
    "назначение": "purpose",
    "степень защиты, ip": "ip",
    "степень защиты ip": "ip",
    "номинальный ток, а": "current_a",
    "номинальный ток,а": "current_a",
    "номинальный ток": "current_a",
    "номинальное напряжение, в": "voltage_v",
    "номинальное напряжение,в": "voltage_v",
    "количество клавиш": "keys",
    "количество постов": "posts",
    "количество модулей": "modules",
    "материал": "material",
    "способ монтажа": "mount",
    "гарантия": "warranty",
}


AWS_URL_MARKER = "awsproducts"
AWS_NAME_MARKER = "awsproducts"


def parse_product(url: str) -> dict | None:
    """Парсит карточку. Возвращает None если товар НЕ принадлежит AWSProducts.

    Принадлежность определяется по URL (содержит '_awsproducts/') или H1
    (содержит 'AWSproducts'/'AWSProducts'). Поле «Бренд» в таблице характеристик
    у части AWS-товаров отсутствует, поэтому им фильтровать нельзя.
    """
    full_url = urljoin(BASE, url)
    html = fetch(full_url)
    soup = soup_of(html)

    h1 = soup.select_one("h1")
    name = h1.get_text(" ", strip=True) if h1 else ""

    is_aws = (AWS_URL_MARKER in full_url.lower()) or (AWS_NAME_MARKER in name.lower())
    if not is_aws:
        return None

    # выбираем самую большую таблицу характеристик
    best: list[tuple[str, str]] = []
    for t in soup.select("table"):
        rows: list[tuple[str, str]] = []
        for tr in t.select("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.select("th,td")]
            if len(cells) >= 2:
                rows.append((cells[0], cells[1]))
        if len(rows) > len(best):
            best = rows

    specs_raw: dict[str, str] = {}
    specs: dict[str, str] = {}
    for key, val in best:
        k_clean = key.rstrip(":").strip()
        specs_raw[k_clean] = val
        canon = SPEC_ALIASES.get(k_clean.lower())
        if canon:
            specs[canon] = val

    # артикул: из таблицы, иначе пробуем достать из H1 (паттерн U1A-XXX / A-XXX / PD80-XXX / G50-XX / P50-XX)
    article = specs.get("article", "").strip()
    if not article and name:
        m = re.search(r"\b(?:U1A|U2B|A|PD80|G50|P50|B30|PG51|G51|A-D)[-\s]?[A-Z0-9]+[A-Z]*\b", name)
        if m:
            article = m.group(0).strip()

    # картинка товара — пытаемся отделить от баннеров/иконок сайта.
    # Известный баннер на stv39: 1080-DR26.webp; favicon: android-chrome*.
    # Принимаем только если в имени файла фигурирует код артикула или его slug.
    img_url = None
    article_tokens: list[str] = []
    if article:
        a_norm = article.lower().replace(" ", "_").replace("-", "_")
        article_tokens.append(a_norm)
        # упрощённый токен — только буквы+цифры из артикула
        article_tokens.append(re.sub(r"[^a-z0-9]", "", article.lower()))
    BAD_TOKENS = ("1080-dr26", "android-chrome", "favicon", "logo", "/uf/", ".svg")
    for img in soup.select("img"):
        src = (img.get("src") or img.get("data-src") or "").lower()
        if "/upload/" not in src:
            continue
        if any(b in src for b in BAD_TOKENS):
            continue
        if not article_tokens or any(tok and tok in src.replace("-", "_") for tok in article_tokens):
            img_url = urljoin(BASE, img.get("src") or img.get("data-src") or "")
            break

    return {
        "url": full_url,
        "name": name,
        "article": article,
        "brand": specs.get("brand", "") or "AWSProducts",
        "type": specs.get("type", ""),
        "series": specs.get("series", ""),
        "color": specs.get("color", ""),
        "purpose": specs.get("purpose", ""),
        "ip": specs.get("ip", ""),
        "current_a": specs.get("current_a", ""),
        "voltage_v": specs.get("voltage_v", ""),
        "keys": specs.get("keys", ""),
        "posts": specs.get("posts", ""),
        "modules": specs.get("modules", ""),
        "material": specs.get("material", ""),
        "mount": specs.get("mount", ""),
        "warranty": specs.get("warranty", ""),
        "image_url": img_url,
        "specs_raw": specs_raw,
    }


# ---------------------------------------------------------------- main

def collect_stv() -> dict:
    out = {}
    for skey, qword in SERIES_QUERIES.items():
        print(f"\n[stv] series={skey} query={qword!r}")
        urls = listing_product_urls(qword)
        print(f"  listing: {len(urls)} product urls")
        items = []
        skipped_brand = 0
        for i, u in enumerate(urls, 1):
            try:
                p = parse_product(u)
            except Exception as e:
                print(f"  ! error on {u}: {e}", file=sys.stderr)
                continue
            if p is None:
                skipped_brand += 1
                continue
            items.append(p)
            if i % 20 == 0:
                print(f"  parsed {i}/{len(urls)} (skipped non-AWS: {skipped_brand})")
        # дедуп по article
        seen_arts: set[str] = set()
        uniq: list[dict] = []
        for it in items:
            a = it["article"]
            if a in seen_arts:
                continue
            seen_arts.add(a)
            uniq.append(it)
        # дополнительно отсеиваем по серии: оставляем только товары, у которых
        # серия в карточке либо в URL соответствует тому, что мы искали.
        # Это защита от того, что поиск "дизайн" вернёт товары Уны/Ауры с упоминанием слова "дизайн".
        SERIES_HINTS = {
            "uno":    ("уно", "_uno_"),
            "aura":   ("аура", "_aura_"),
            "design": ("дизайн", "_dizayn_"),
        }
        hints = SERIES_HINTS[skey]
        filtered = []
        skipped_series = 0
        for it in uniq:
            series_field = (it.get("series") or "").lower()
            url_l = (it.get("url") or "").lower()
            if hints[0] in series_field or hints[1] in url_l:
                filtered.append(it)
            else:
                skipped_series += 1
        print(f"  AWS items: {len(uniq)}  ->  in-series: {len(filtered)}  (skipped wrong-series: {skipped_series}, non-AWS: {skipped_brand})")
        out[skey] = {
            "query": qword,
            "items": filtered,
            "items_count": len(filtered),
            "skipped_non_aws": skipped_brand,
            "skipped_wrong_series": skipped_series,
        }
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=== our_data ===")
    our = collect_our()
    OUR_OUT.write_text(json.dumps(our, ensure_ascii=False, indent=2), encoding="utf-8")
    for k, v in our.items():
        print(f"  {k}: {v['items_count']} items, colors={v['colors_declared']}")
    print(f"  saved -> {OUR_OUT}")

    print("\n=== stv_data ===")
    stv = collect_stv()
    STV_OUT.write_text(json.dumps(stv, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  saved -> {STV_OUT}")

    print("\n=== summary ===")
    for k in SERIES_QUERIES:
        our_n = our.get(k, {}).get("items_count", 0)
        stv_n = stv.get(k, {}).get("items_count", 0)
        print(f"  {k}: our={our_n}  stv={stv_n}  diff={stv_n - our_n:+d}")


if __name__ == "__main__":
    main()
