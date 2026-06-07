# -*- coding: utf-8 -*-
"""Белые рамки U1A-028..032: правило владельца — удалить угловое главное,
фронтальное _3 сделать главным, оставить тыл _2. Итог: ровно 2 фото [фронт, тыл] -> 2 кружочка.
Фон у всех уже убран (прозрачный) -> только конвертация/переименование, без повторного cutout."""
from pathlib import Path
from PIL import Image

P = Path("c:/Users/ikoko/Projects/aws-brand-site/public/img/products")
ARTS = ["U1A-028 white", "U1A-029 white", "U1A-030 white", "U1A-031 white", "U1A-032 white"]

def find(a, suf):
    for ext in ("webp", "png"):
        f = P / f"{a}{suf}.{ext}"
        if f.exists():
            return f
    return None

for a in ARTS:
    main = P / f"{a}.webp"
    f2 = find(a, "_2")            # тыл — оставляем как _2
    f3 = find(a, "_3")            # фронт — станет главным
    if not f3:
        print("!! нет _3:", a); continue
    # 1) фронт (_3) -> главное (webp, альфа сохраняется)
    Image.open(f3).convert("RGBA").save(main, "WEBP", quality=90, method=6)
    # 2) удалить исходный файл _3 (если это был .png или .webp с суффиксом _3)
    if f3.name != main.name:
        f3.unlink()
    # 3) тыл _2 — конвертировать в webp, если был png (чтобы 2-е фото тоже webp)
    if f2 and f2.suffix.lower() == ".png":
        Image.open(f2).convert("RGBA").save(P / f"{a}_2.webp", "WEBP", quality=90, method=6)
        f2.unlink()
    # итог: остаются ровно {a}.webp (фронт) + {a}_2.webp (тыл)
    left = sorted(p.name for p in P.glob(a + "*") )
    print(f"{a}: ->", left)
