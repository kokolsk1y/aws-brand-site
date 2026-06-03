"""
Повторная обработка фото серии УНО через birefnet.

Источник: _pipeline/photos-raw/U1A-*__N.webp и U2B-*__N.webp
Какие ракурсы нужны: читаем из photos-sorted/08-Серия-УНО/
Результат: public/img/products/

Исправляет проблему: предыдущий скрипт использовал alpha_matting с
foreground_threshold=240, что обрезало чёрные товары (они тоже тёмные).
Теперь alpha_matting отключён — birefnet справляется сам без дополнительной
эвристики по яркости.

Маппинг файлов:
  photos-sorted/ARTICLE/main.webp  → raw __0  → products/ARTICLE.webp
  photos-sorted/ARTICLE/2.webp     → raw __1  → products/ARTICLE_2.webp
  photos-sorted/ARTICLE/4.webp     → raw __3  → products/ARTICLE_2.webp (второй оставленный)
  (нумерация в products/ последовательная, не по исходному индексу)
"""

import os
import sys
import shutil
from pathlib import Path
from rembg import remove, new_session
from PIL import Image
from io import BytesIO

BASE     = Path("C:/Users/ikoko/Projects/aws-brand-site")
SORTED   = BASE / "photos-sorted/08-Серия-УНО"
RAW      = BASE / "_pipeline/photos-raw"
PRODUCTS = BASE / "public/img/products"


def sorted_files(folder):
    """Возвращает файлы из папки: main.webp первым, затем по номеру."""
    files = list(folder.iterdir())
    main = [f for f in files if f.stem == "main"]
    nums = sorted([f for f in files if f.stem != "main"], key=lambda f: int(f.stem))
    return main + nums


def raw_index(stem):
    """'main' → 0, '2' → 1, '4' → 3 (1-indexed имя → 0-indexed raw)."""
    if stem == "main":
        return 0
    return int(stem) - 1


print("=" * 60)
print("Загружаю birefnet-general (первый раз ~400 MB)...")
session = new_session("birefnet-general")
print("Модель готова")
print("=" * 60)

# 1. Удаляем все старые UNО-файлы из products/
old = [f for f in PRODUCTS.iterdir() if f.name.startswith(("U1A-", "U2B-"))]
print(f"\nУдаляю {len(old)} старых UNO-файлов из products/...")
for f in old:
    f.unlink()
print("Удалено.")

# 2. Обрабатываем только то, что осталось в photos-sorted
article_folders = sorted([d for d in SORTED.iterdir() if d.is_dir()])
print(f"\nАртикулов к обработке: {len(article_folders)}")

ok = 0
fail = 0
skipped = 0

for folder in article_folders:
    article = folder.name            # "U1A-028 white"
    raw_prefix = article.replace(" ", "_")  # "U1A-028_white"

    src_files = sorted_files(folder)
    if not src_files:
        print(f"[ПРОПУСК] {article} — пустая папка")
        skipped += 1
        continue

    print(f"\n{article} ({len(src_files)} ракурс(а))")

    extra_idx = 2  # первый доп. ракурс получит суффикс _2

    for src in src_files:
        stem = src.stem  # "main", "2", "4", "5" ...
        raw_n = raw_index(stem)
        raw_path = RAW / f"{raw_prefix}__{raw_n}.webp"

        if not raw_path.exists():
            print(f"  [НЕТ ОРИГИНАЛА] {raw_path.name}")
            fail += 1
            continue

        # Имя выходного файла
        if stem == "main":
            out_name = f"{article}.webp"
        else:
            out_name = f"{article}_{extra_idx}.webp"
            extra_idx += 1

        out_path = PRODUCTS / out_name

        try:
            with open(raw_path, "rb") as f:
                data = f.read()

            # Без alpha_matting — birefnet сам определяет границы объекта
            # alpha_matting с threshold=240 срезал чёрные товары
            result = remove(data, session=session)

            img = Image.open(BytesIO(result)).convert("RGBA")
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)

            img.save(out_path, "WEBP", quality=92, method=6)
            print(f"  OK  {out_name}")
            ok += 1

        except Exception as e:
            print(f"  FAIL {out_name}: {e}")
            fail += 1

print("\n" + "=" * 60)
print(f"Готово: OK={ok}  FAIL={fail}  ПРОПУСК={skipped}")
print("Проверь public/img/products/ — там должны быть только свежие UNO файлы.")
