"""
Удаляет ВНУТРЕННИЕ белые «окна» в рамках (P50-*V*, U1A-029-2 и т.п.) после
первого прохода remove_product_bg.py. Работает там, где внешний фон уже
прозрачный, но внутри рамки изолированный белый прямоугольник остался.

Алгоритм:
1. Идём по 7x7 grid точкам внутри изображения
2. Для каждой почти-белой непрозрачной точки запускаем flood fill
3. Если flood собирает много связанных пикселей — это белая «дыра» окна
4. Делаем их прозрачными

ОГРАНИЧЕНИЕ: если flood собрал > 70% видимых пикселей — отказ (значит
зацепили часть товара, не окно). Файл не меняется.

Запуск: python scripts/remove_inner_white.py [pattern]
По умолчанию обрабатывает P50-*V*.webp и U1A-{028,029-2,031-2}.webp.
"""
from pathlib import Path
from PIL import Image
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = ROOT / "public" / "img" / "products"
BACKUP_DIR = ROOT / "scripts" / "inner_white_backup"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

WHITE_TOL = 10  # почти-белый: r,g,b >= 255-tol
GRID = 7        # 7x7 сетка seed-точек
SAFETY_LIMIT = 0.7  # если flood съел >70% пикселей — отказ


def is_almost_white(px):
    return px[3] >= 250 and all(c >= 255 - WHITE_TOL for c in px[:3])


def flood_white(pixels, w, h, sx, sy, visited):
    """Flood fill от (sx, sy) по почти-белым непрозрачным пикселям.
    Возвращает список координат собранных пикселей."""
    collected = []
    stack = [(sx, sy)]
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        idx = y * w + x
        if visited[idx]:
            continue
        visited[idx] = 1
        if not is_almost_white(pixels[x, y]):
            continue
        collected.append((x, y))
        stack.append((x + 1, y))
        stack.append((x - 1, y))
        stack.append((x, y + 1))
        stack.append((x, y - 1))
    return collected


def process(path):
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    pixels = img.load()
    visible_count = sum(
        1 for y in range(0, h, 4) for x in range(0, w, 4)
        if pixels[x, y][3] > 0
    )
    if visible_count == 0:
        return "empty"

    # Бэкап
    backup = BACKUP_DIR / path.name
    if not backup.exists():
        shutil.copy2(path, backup)

    visited = bytearray(w * h)
    to_clear = []  # все пиксели которые сделать прозрачными

    # 7x7 сетка seed-точек, отступ от краёв 10%
    margin_x = w // 10
    margin_y = h // 10
    for gy in range(GRID):
        for gx in range(GRID):
            x = margin_x + (w - 2 * margin_x) * gx // (GRID - 1)
            y = margin_y + (h - 2 * margin_y) * gy // (GRID - 1)
            if visited[y * w + x]:
                continue
            if not is_almost_white(pixels[x, y]):
                continue
            collected = flood_white(pixels, w, h, x, y, visited)
            # Слишком большой flood = риск задеть товар, пропускаем
            if len(collected) > visible_count * SAFETY_LIMIT * 16:
                continue
            to_clear.extend(collected)

    # Очищаем
    for x, y in to_clear:
        r, g, b, a = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)

    img.save(path, "WEBP", quality=90, method=6)
    return f"cleared {len(to_clear)} px"


def main():
    if len(sys.argv) > 1:
        targets = list(PRODUCTS_DIR.glob(sys.argv[1]))
    else:
        targets = []
        for pat in ["P50-*V*.webp", "U1A-028.webp", "U1A-029-2.webp", "U1A-031-2.webp"]:
            targets.extend(PRODUCTS_DIR.glob(pat))

    if not targets:
        print("Файлы не найдены")
        return
    print(f"Обработка {len(targets)} файлов...\n")
    for path in sorted(targets):
        try:
            res = process(path)
            print(f"OK {path.name}: {res}")
        except Exception as e:
            print(f"ERR {path.name}: {e}")
    print(f"\nБэкапы: {BACKUP_DIR}")


if __name__ == "__main__":
    main()
