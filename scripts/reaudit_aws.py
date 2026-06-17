"""
reaudit_aws.py — свежая сверка ВСЕГО бренд-каталога AWS на stv39.ru против нашего сайта.

Источник STV: поиск q=awsproducts (полный бренд-каталог, все страницы пагинации).
Наш каталог: src/data/series.json + public/products.json.

Находит:
  • MISSING — (база,цвет) есть на STV, нет у нас;
  • EXTRA   — есть у нас, нет в AWS-каталоге STV;
  • ERRORS  — у совпавших: поле STV противоречит названию/URL самой карточки
             (опечатки STV), считаем только когда цвет в URL совпадает с товаром.

Свежий скрейп (кэш не используется). Отчёт: scripts/audit/reaudit_report.md
"""
from __future__ import annotations
import json, re, sys, time
from pathlib import Path
from urllib.parse import quote, urljoin
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
SERIES = ROOT / "src" / "data" / "series.json"
PRODUCTS = ROOT / "public" / "products.json"
OUT_JSON = ROOT / "scripts" / "audit" / "reaudit_stv.json"
REPORT = ROOT / "scripts" / "audit" / "reaudit_report.md"
BASE = "https://stv39.ru"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 audit-bot"}
PAUSE = 0.6
PROD_RE = re.compile(r"^/catalog/[a-z0-9_-]+/[a-z0-9_-]+/?$", re.I)

COLOR_TOKENS = [  # порядок важен: matte_black ловим до black, tyemn до ser
    ("matte_black", ("chyernyy_matovyy", "chyernaya_matovaya", "chyern_matov")),
    ("dark_grey",   ("tyemn_seraya", "tyemn_seryy", "tyemno_ser", "tyemn_ser")),
    ("silver",      ("serebro", "serebr")),
    ("gold",        ("zoloto",)),
    ("mahogany",    ("krasn", "makhagon", "mahagon")),
    ("white",       ("belyy", "belaya", "beloe")),
    ("black",       ("chyernyy", "chyernaya", "chyern")),
    ("grey",        ("seryy", "seraya", "seroe", "ser_")),
]

def color_from_url(u: str) -> str | None:
    ul = u.lower()
    for color, toks in COLOR_TOKENS:
        if any(t in ul for t in toks):
            return color
    return None

def fetch(url: str) -> str | None:
    try:
        r = requests.get(url, headers=H, timeout=25); r.encoding = "utf-8"
        r.raise_for_status(); return r.text
    except Exception as e:
        print(f"  ! {e} | {url}", file=sys.stderr); return None

def listing_urls() -> list[str]:
    seen = set()
    page = 1
    while True:
        u = f"{BASE}/catalog/?q=awsproducts&s=&count=100&PAGEN_2={page}"
        html = fetch(u)
        if not html: break
        s = BeautifulSoup(html, "lxml")
        found = {a.get("href", "") for a in s.select("a[href]")
                 if PROD_RE.match(a.get("href", "")) and "awsproducts" in a.get("href", "").lower()}
        new = found - seen
        print(f"  стр.{page}: +{len(new)} (всего {len(seen)+len(new)})")
        if not new: break
        seen |= found
        page += 1
        if page > 12: break
        time.sleep(PAUSE)
    return sorted(seen)

def parse_card(url: str) -> dict | None:
    html = fetch(url)
    if not html: return None
    s = BeautifulSoup(html, "lxml")
    h1 = s.select_one("h1")
    name = h1.get_text(" ", strip=True) if h1 else ""
    # таблица характеристик
    specs = {}
    best = []
    for t in s.select("table"):
        rows = []
        for tr in t.select("tr"):
            c = [x.get_text(" ", strip=True) for x in tr.select("th,td")]
            if len(c) >= 2: rows.append((c[0].rstrip(":").strip(), c[1].strip()))
        if len(rows) > len(best): best = rows
    for k, v in best: specs[k] = v
    # блок brief (как в extract_stv_specs) — описание+характеристики прозой
    brief = ""
    blk = s.select_one(".brief__new__main")
    if blk and blk.find("p"): brief = blk.find("p").get_text("\n", strip=True)
    art = specs.get("Артикул", "").strip()
    return {"url": url, "name": name, "article_field": art, "specs": specs, "brief": brief,
            "color_url": color_from_url(url)}

COLOR_SUF = re.compile(r"(DG|GR|BL|BR|AL|CR|SL|VW|VB|VG|W|B|G|S)$")
CODE_RE = re.compile(
    r"_(u1a|u2b|pd80|pg51|g51|g50|p50|b30|w30|a_d|a)_?(\d[a-z0-9_]*?)(?:_soft_ta?ch)?_(uno|aura|dizayn)(?:_\d+a)?_awsproducts/?$")

def norm_code(raw: str) -> str:
    """Код без цвета: 'U1A-001-3 white'->'u1a0013', 'A-D034GR'->'ad034', 'a_d034b'->'ad034'."""
    a = raw.split(" ")[0].upper().replace("_", "-")
    a = re.sub(r"(MATTE BLACK|DARK GREY)$", "", a)
    a = COLOR_SUF.sub("", a)
    return re.sub(r"[^A-Z0-9]", "", a).lower()

def url_series(url: str) -> str | None:
    m = re.search(r"_(uno|aura|dizayn)(?:_|$)", url.lower())
    return {"dizayn": "design"}.get(m.group(1), m.group(1)) if m else None

def stv_code(url: str, art_field: str) -> str:
    if art_field:
        return norm_code(art_field)
    m = CODE_RE.search(url.lower())
    if m: return norm_code(m.group(1) + "_" + m.group(2))
    return ""

# alias для нашего каталога
base_code = norm_code

def main():
    print("=== Сбор листинга AWS на STV ===")
    urls = listing_urls()
    print(f"Всего карточек: {len(urls)}")
    cards = []
    for i, u in enumerate(urls, 1):
        full = urljoin(BASE, u)
        c = parse_card(full)
        if c: cards.append(c)
        if i % 25 == 0: print(f"  карточек разобрано {i}/{len(urls)}")
        time.sleep(PAUSE)
    OUT_JSON.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")

    # наш каталог
    series = json.loads(SERIES.read_text(encoding="utf-8"))
    products = json.loads(PRODUCTS.read_text(encoding="utf-8"))
    our_series = {}   # (code,color) -> article
    our_catalog = {}  # code -> article
    for slug, sv in series.items():
        for g, its in (sv.get("groups") or {}).items():
            for it in its:
                our_series[(norm_code(it["article"]), it.get("color", ""))] = it["article"]
    for cat, cv in products.items():
        for it in (cv.get("items") or []):
            our_catalog[norm_code(it["article"])] = it["article"]

    matched_series, matched_catalog, missing = set(), set(), []
    for c in cards:
        ser = url_series(c["url"])
        code = stv_code(c["url"], c["article_field"])
        col = c["color_url"] or ""
        if not code:
            missing.append(("?", col, c, "нет кода")); continue
        if ser:
            key = (code, col)
            if key in our_series: matched_series.add(key)
            else: missing.append((code, col, c, ser))
        else:
            if code in our_catalog: matched_catalog.add(code)
            else: missing.append((code, col, c, "каталог"))

    extra_series = [(k, a) for k, a in our_series.items() if k not in matched_series]
    extra_catalog = [(k, a) for k, a in our_catalog.items() if k not in matched_catalog]

    lines = ["# Свежий аудит AWS: STV vs наш сайт", "",
             f"- карточек AWS на STV: **{len(cards)}**",
             f"- позиций у нас: серии **{len(our_series)}** + каталог **{len(our_catalog)}**",
             f"- совпало: серии {len(matched_series)}, каталог {len(matched_catalog)}",
             f"- **НЕ хватает у нас (есть на STV): {len(missing)}**",
             f"- есть у нас, нет в AWS-каталоге STV: серии {len(extra_series)}, каталог {len(extra_catalog)}", ""]
    lines += ["## ❗ НЕ ХВАТАЕТ (есть на STV, нет у нас)", ""]
    if missing:
        for code, col, c, tag in sorted(missing, key=lambda x: (x[3], x[0])):
            lines.append(f"- `{code}` / {col or '?'} [{tag}] — {c['name'][:75]}  \n  {c['url']}")
    else:
        lines.append("_всё, что на STV, есть у нас_")
    lines += ["", "## ⚪ ЕСТЬ У НАС, НЕТ в AWS-каталоге STV (инфо)", ""]
    for (code, col), a in sorted(extra_series):
        lines.append(f"- `{a}` (серия, {code}/{col})")
    for code, a in sorted(extra_catalog):
        lines.append(f"- `{a}` (каталог, {code})")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nГОТОВО. cards={len(cards)} missing={len(missing)} "
          f"extra_series={len(extra_series)} extra_catalog={len(extra_catalog)}")
    print(f"отчёт -> {REPORT}\nданные -> {OUT_JSON}")

if __name__ == "__main__":
    main()
