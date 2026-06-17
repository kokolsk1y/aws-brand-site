"""
build_product_content.py — собирает src/data/product_content.json для карточек товара.

Вход:
  scripts/audit/stv_specs.json   (specs_norm — нормализованные характеристики STV)
  src/data/descriptions.json     (AWS-описания по базам, опционально; пишу вручную)
Выход:
  src/data/product_content.json  { article: { specs: [[k,v]...], description|null } }
  scripts/audit/borrow_frames_report.md  (сверка дотянутых рамок/кабелей)

Дотяжка для товаров без характеристик:
  • рамки   → от рамки ТОГО ЖЕ семейства (B30/P50/PG51…) и числа постов
  • кабель  → от базового артикула (AWS-XXXX-50/-100 ← AWS-XXXX)
Аксессуары (вывод/заглушка) без донора — остаются на фолбэке карточки.
Серия проставляется авторитетно из нашей series.json (не из мусорного поля STV).
Визуал карточки не трогается: меняется только источник данных.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STV = ROOT / "scripts" / "audit" / "stv_specs.json"
SERIES = ROOT / "src" / "data" / "series.json"
DESCR = ROOT / "src" / "data" / "descriptions.json"
OUT = ROOT / "src" / "data" / "product_content.json"
REPORT = ROOT / "scripts" / "audit" / "borrow_frames_report.md"

COLOR_SUFFIX_RE = re.compile(r"(DG|GR|BL|BR|AL|CR|SL|VW|VB|VG|W|B|G|S)$")
COLOR_RU = {"white": "белый", "black": "чёрный", "grey": "серый",
            "dark_grey": "тёмно-серый", "silver": "серебро",
            "matte_black": "чёрный матовый", "gold": "золото",
            "mahogany": "красное дерево"}

# материал рамок по буквенному префиксу артикула (когда на STV данных нет)
FRAME_MATERIAL = {
    "B": "Алюминий",            # B30 — «алюминий» в названии
    "G": "Стекло",              # G50/G51 — «(стекло)»
    "PG": "Стекло",             # PG51 — стекло (премиум)
    "W": "Дерево (МДФ)",        # W30 — «махогон»
    "P": "Поликарбонат + ABS",  # P50
    "PD": "Поликарбонат",       # PD80 (ДИЗАЙН)
    "U": "Поликарбонат + ABS",  # U1A/U2B (УНО)
}
COVER_BY_MAT = {"Стекло": "Глянцевое", "Алюминий": "Матовое", "Дерево (МДФ)": "Матовое"}
# семейства, чей материал не подтверждён на STV — пометить в отчёте для сверки
UNCERTAIN = {"B", "G", "PG", "W"}


def base_key(article: str) -> str:
    a = article.split(" ")[0].upper()
    return COLOR_SUFFIX_RE.sub("", a).rstrip("-_")


def desc_key(article: str) -> str:
    # УНО: U2B-0NN (чёрная серия) шерит описание с U1A-0NN — это тот же товар
    return re.sub(r"^U2B-", "U1A-", base_key(article))


def family(article: str) -> str:
    # B30-1B → B30 ; PG51-2W → PG51 ; P50-3GR → P50 ; U1A-029-2 white → U1A-029
    return re.sub(r"-\d+$", "", base_key(article))


def cable_base(article: str) -> str:
    return re.sub(r"-\d+$", "", article)


def posts_from_name(name: str) -> str | None:
    m = re.search(r"(\d+)[-\s]?я\b", name)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d+)\s*пост", name, re.I)
    return m.group(1) if m else None


def warranty_for(name: str) -> str:
    if re.search(r"удлинител|клемм|кабель|коннектор|разъ[её]м|патч", name, re.I):
        return "1 год"
    return "2 года"


# ---- чистильщик описаний STV → голос AWS (ближе к STV, короче, без воды) ----
_DROP = [re.compile(p, re.I) for p in (
    r"рамка не входит", r"приобрета[ею]тся отдельно",
    r"(спальн|гостин|на кухне|офис|гостиничн).*(везде|размещ|удобн)",
    r"(удобн|особенно).*(спальн|гостин|кухне|офис)",
    r"классическ\w*\s+\w+\s+цвет", r"цвет\w*\s+делает.*интерьер",
)]


def clean_description(desc: str, source_article: str) -> str:
    if not desc:
        return ""
    t = re.sub(r"\bAWSPRODUCTS\b|\bAWSproducts?\b", "", desc)
    t = re.sub(re.escape(source_article), "", t)
    t = re.sub(r"«[^»]*»|\"[^\"]*\"", "", t)
    t = re.sub(r"soft[\s\-]?touch", "Софт-тач", t, flags=re.I)
    t = re.sub(r"надежн", "надёжн", t)
    t = re.sub(r"^.{0,200}?—\s*это\s+", "Это ", t, count=1, flags=re.I)
    parts = re.split(r"(?<=[.!?])\s+", t)
    keep = [s.strip() for s in parts if s.strip() and not any(p.search(s) for p in _DROP)]
    out = " ".join(keep)
    out = re.sub(r"\s{2,}", " ", out).replace(" ,", ",").replace(" .", ".").strip()
    out = re.sub(r"^[—\-\s]+", "", out)
    return " ".join(re.split(r"(?<=[.!?])\s+", out)[:3]).strip()


def main() -> None:
    stv = json.loads(STV.read_text(encoding="utf-8"))
    series = json.loads(SERIES.read_text(encoding="utf-8"))
    descr = json.loads(DESCR.read_text(encoding="utf-8")) if DESCR.exists() else {}
    series_name = {slug: sv.get("name") for slug, sv in series.items()}

    # лучшая (самая полная) STV-проза на базу описания → цвето-нейтральный текст
    best_desc: dict[str, tuple[str, str]] = {}
    for art, v in stv.items():
        k = desc_key(art)
        dsc = v.get("description", "") or ""
        if len(dsc) > len(best_desc.get(k, ("", ""))[1]):
            best_desc[k] = (art, dsc)

    fam_donors: dict[tuple, list] = {}
    slug_donors: dict[str, list] = {}
    article_series: dict[str, str] = {}
    article_color: dict[str, str] = {}
    for slug, sv in series.items():
        for gname, items in (sv.get("groups") or {}).items():
            for it in items:
                article_series[it["article"]] = slug
                article_color[it["article"]] = it.get("color", "")
                if gname == "frames":
                    v = stv.get(it["article"])
                    sp = v and v.get("specs_norm")
                    if sp:
                        rec = (posts_from_name(it.get("name", "")), sp)
                        fam_donors.setdefault((slug, family(it["article"])), []).append(rec)
                        slug_donors.setdefault(slug, []).append(rec)

    borrowed_rows: list[list[str]] = []

    def pick(donors, posts):
        return next((d for d in donors if d[0] == posts), donors[0])

    def borrow_specs(article: str, v: dict) -> dict:
        sp = v.get("specs_norm") or {}
        if sp:
            return dict(sp)
        name = v["our_name"]
        if v["source"] == "products:cable":
            cb = cable_base(article)
            dv = stv.get(cb)
            if dv and dv.get("specs_norm") and cb != article:
                borrowed_rows.append([article, name[:40], "cable", "—", f"кабель←{cb}"])
                return dict(dv["specs_norm"])
        if re.search(r"рамк", name, re.I):
            slug = article_series.get(article)
            pref = re.match(r"[A-Z]+", base_key(article))
            pref = pref.group() if pref else ""
            mat = FRAME_MATERIAL.get(pref)
            cov = COVER_BY_MAT.get(mat) or ("Матовое, Софт-тач" if slug == "uno" else "Глянцевое")
            specs: dict[str, str] = {"Серия": series_name.get(slug, "")}
            col = COLOR_RU.get(article_color.get(article, ""))
            if col:
                specs["Цвет"] = col
            if mat:
                specs["Материал"] = mat
            if cov:
                specs["Покрытие"] = cov
            p = posts_from_name(name)
            if p:
                specs["Постов"] = p
            specs["Ориентация"] = "вертикальная" if re.search(r"вертикал", name, re.I) else "горизонтальная"
            specs["Защита"] = "IP20"
            borrowed_rows.append([article, name[:40], slug or "?",
                                  f"постов={p or '?'}", f"{mat or '?'}{' ⚠' if pref in UNCERTAIN else ''}"])
            return specs
        return {}

    content: dict[str, dict] = {}

    def add(art, v, slug):
        specs = borrow_specs(art, v)
        if slug and "Серия" in specs:
            specs["Серия"] = series_name.get(slug, specs["Серия"])
        # ДИЗАЙН: покрытие строго по цвету (STV-проверено: белый — глянцевое,
        # чёрный и серый — матовое). Дотяжка цветовых вариантов от белого донора
        # копировала «глянцевое» и на чёрный/серый — здесь переопределяем.
        if slug == "design" and "Покрытие" in specs:
            specs["Покрытие"] = "Глянцевое" if article_color.get(art) == "white" else "Матовое"
        rows = [["Артикул", art]]
        rows += [[k, val] for k, val in specs.items()]
        rows.append(["Гарантия", warranty_for(v["our_name"])])
        rows.append(["Сертификация", "EAC, ГОСТ"])
        rows.append(["Бренд", "AWSProducts"])
        # описание: ручная правка (приоритет) → чистка лучшей STV-прозы базы
        desc = descr.get(desc_key(art)) or descr.get(base_key(art)) or descr.get(art)
        if not desc:
            src = best_desc.get(desc_key(art))
            if src:
                desc = clean_description(src[1], src[0]) or None
        # ДИЗАЙН-рамки (PD80): покрытие у белого/чёрного/серого разное, а описание
        # общее на базу — убираем упоминание поверхности, чтобы текст не противоречил
        # таблице. + правка опечатки STV «однин».
        if slug == "design" and desc and re.search(r"рамк", v["our_name"], re.I):
            desc = re.sub(r"\s*с\s+(?:глянцевой|матовой)\s+поверхностью", "", desc, flags=re.I)
            desc = desc.replace("однин", "один").replace("подрозетник..", "подрозетник.")
            desc = re.sub(r"\s{2,}", " ", desc).replace(" .", ".").strip()
        content[art] = {"specs": rows, "description": desc}

    for slug, sv in series.items():
        for gname, items in (sv.get("groups") or {}).items():
            for it in items:
                v = stv.get(it["article"])
                if v:
                    add(it["article"], v, slug)
    products = json.loads((ROOT / "public" / "products.json").read_text(encoding="utf-8"))
    for cat, cv in products.items():
        for it in (cv.get("items") or []):
            v = stv.get(it["article"])
            if v:
                add(it["article"], v, None)

    OUT.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# Дотяжка рамок/кабеля — сверка", "",
             f"Дотянуто товаров: {len(borrowed_rows)}", "",
             "| Артикул | Название | Серия | Постов | Способ |",
             "|---|---|---|---|---|"]
    lines += ["| " + " | ".join(r) + " |" for r in borrowed_rows]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with_specs = sum(1 for c in content.values() if len(c["specs"]) > 4)
    with_descr = sum(1 for c in content.values() if c["description"])
    print(f"product_content.json: {len(content)} товаров")
    print(f"  с характеристиками (>4 строк): {with_specs}")
    print(f"  с AWS-описанием: {with_descr}")
    print(f"  дотянуто рамок/кабеля: {len(borrowed_rows)}")
    print(f"  saved -> {OUT}\n  report -> {REPORT}")


if __name__ == "__main__":
    main()
