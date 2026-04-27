"""
Заменяет фото товаров серии UNO/AURA в public/img/products/ на анфас-ракурс
из проекта инфографики (assets/uno/${article}/${article} 1_nobg.png).

Логика:
- Идём по папкам в c:/Users/ikoko/Projects/infografika/assets/uno/ и /aura/
- Для каждой берём файл "${article} 1_nobg.png" (анфас)
- Если такого нет — пропускаем
- Если артикул в нижнем регистре дубль (u1a-028 vs U1A-028) — пропускаем дубль
- Конвертируем PNG → WEBP с quality 90, прозрачный альфа сохраняется
- Бэкапим текущий public/img/products/${article}.webp → scripts/anfas_replaced_backup/

Запуск:
    python scripts/replace_with_anfas.py
"""
from pathlib import Path
from PIL import Image
import shutil

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = ROOT / "public" / "img" / "products"
BACKUP_DIR = ROOT / "scripts" / "anfas_replaced_backup"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_DIRS = [
    Path("c:/Users/ikoko/Projects/infografika/assets/uno"),
    Path("c:/Users/ikoko/Projects/infografika/assets/aura"),
]


def main():
    replaced = 0
    skipped = 0
    not_found = 0

    for source_dir in SOURCE_DIRS:
        if not source_dir.exists():
            print(f"Папка не найдена: {source_dir}")
            continue
        for article_dir in sorted(source_dir.iterdir()):
            if not article_dir.is_dir():
                continue
            article = article_dir.name
            # Пропускаем дубли в нижнем регистре
            if article.lower() == article and any(d.name == article.upper() for d in source_dir.iterdir()):
                continue
            anfas = article_dir / f"{article} 1_nobg.png"
            if not anfas.exists():
                # Пробуем альтернативные имена
                anfas = next(article_dir.glob("* 1_nobg.png"), None)
                if not anfas or not anfas.exists():
                    print(f"  SKIP {article}: нет 1_nobg.png")
                    not_found += 1
                    continue

            target = PRODUCTS_DIR / f"{article}.webp"
            if not target.exists():
                print(f"  SKIP {article}: нет целевого файла {target.name}")
                skipped += 1
                continue

            # Бэкап
            backup_path = BACKUP_DIR / target.name
            if not backup_path.exists():
                shutil.copy2(target, backup_path)

            # Конвертация PNG → WEBP
            img = Image.open(anfas).convert("RGBA")
            img.save(target, "WEBP", quality=90, method=6)
            print(f"OK {article}: заменено на анфас ({img.size[0]}x{img.size[1]})")
            replaced += 1

    print(f"\nИтого: {replaced} заменено, {skipped} пропущено (нет target), {not_found} без анфас-фото")
    print(f"Бэкапы в {BACKUP_DIR}")


if __name__ == "__main__":
    main()
