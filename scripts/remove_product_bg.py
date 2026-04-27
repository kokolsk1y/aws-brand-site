"""
Удаляет белый/светло-серый фон у WEBP-изображений товаров серии UNO/AURA
через flood fill из углов. Не задевает внутренние светлые пиксели
(белые клавиши выключателя останутся белыми, потому что они не связаны
с фоном по альфе через краевой flood).

Запуск:
    python scripts/remove_product_bg.py

Перезаписывает файлы in-place. Бэкап в scripts/products_backup/ для отката.
"""
from pathlib import Path
from PIL import Image
import shutil
import glob

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = ROOT / "public" / "img" / "products"
BACKUP_DIR = ROOT / "scripts" / "products_backup"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Все товары — серия UNO (U1A/U2B), AURA (A-*) и категории
PATTERNS = ["*.webp"]

# Допуск маленький: 5 единиц на канал. Не захватит белые клавиши
# выключателя (отделены от внешнего фона серой рамой).
# Лёгкие jpeg-артефакты на самой кромке белого фона всё равно попадут.
TOLERANCE = 5


def color_close(a, b, tol):
    return all(abs(int(a[i]) - int(b[i])) <= tol for i in range(3))


def is_white(px, tol=10):
    return all(c >= 255 - tol for c in px[:3])


def remove_bg(path: Path):
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    pixels = img.load()

    # Стартуем flood ТОЛЬКО из тех углов где явно белый фон —
    # иначе если в углу торчит часть товара (кабель и т.п.),
    # скрипт примет его за фон и стирёт.
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    white_corners = [(x, y) for x, y in corners if is_white(pixels[x, y])]
    if not white_corners:
        return None  # ни одного белого угла — фон не белый, пропускаем
    bg = (255, 255, 255)

    visited = bytearray(w * h)
    stack = list(white_corners)

    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        idx = y * w + x
        if visited[idx]:
            continue
        visited[idx] = 1
        r, g, b, a = pixels[x, y]
        if not color_close((r, g, b), bg, TOLERANCE):
            continue
        pixels[x, y] = (r, g, b, 0)
        stack.append((x + 1, y))
        stack.append((x - 1, y))
        stack.append((x, y + 1))
        stack.append((x, y - 1))

    # WebP сохраняем с потерями умеренного качества (визуально неотличимо)
    img.save(path, "WEBP", quality=90, method=6)
    return bg


def main():
    files = []
    for pat in PATTERNS:
        files.extend(sorted(PRODUCTS_DIR.glob(pat)))
    if not files:
        print("Файлы не найдены")
        return
    print(f"Найдено {len(files)} файлов. Обработка...")
    ok = 0
    skipped = 0
    for path in files:
        backup = BACKUP_DIR / path.name
        if not backup.exists():
            shutil.copy2(path, backup)
        try:
            bg = remove_bg(path)
            print(f"OK {path.name} (фон был {bg})")
            ok += 1
        except Exception as e:
            print(f"SKIP {path.name}: {e}")
            skipped += 1
    print(f"\nГотово: {ok} обработано, {skipped} пропущено. Бэкап в {BACKUP_DIR}")


if __name__ == "__main__":
    main()
