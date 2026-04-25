"""
Удаляет однотонный светло-серый/белый фон у PNG-логотипов через flood fill из углов.
Не трогает внутренние светлые пиксели иконки (например, белые буквы WB) — только
тот фон, который связан с краями.

Запуск:
    python scripts/remove_logo_bg.py

Перезаписывает файлы in-place. Бэкап в logos_backup/ на случай отката.
"""
from pathlib import Path
from PIL import Image
import shutil

ROOT = Path(__file__).resolve().parent.parent
LOGOS = [
    ROOT / "public" / "logo" / "retailers" / "ozon.png",
    ROOT / "public" / "logo" / "retailers" / "wildberries.png",
    ROOT / "public" / "logo" / "retailers" / "electrocentre.png",
]
BACKUP_DIR = ROOT / "scripts" / "logos_backup"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Допуск по каналу — пиксели в этом диапазоне от фонового цвета считаются фоном
TOLERANCE = 28


def color_close(a, b, tol):
    return all(abs(int(a[i]) - int(b[i])) <= tol for i in range(3))


def remove_bg(path: Path):
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    pixels = img.load()

    # Цвет фона = пиксель из угла (0,0)
    bg = pixels[0, 0][:3]

    # Flood fill из всех 4 углов — заполняем альфой 0 везде где цвет близок к bg
    visited = bytearray(w * h)
    stack = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]

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
        # Делаем прозрачным
        pixels[x, y] = (r, g, b, 0)
        # Соседи
        stack.append((x + 1, y))
        stack.append((x - 1, y))
        stack.append((x, y + 1))
        stack.append((x, y - 1))

    img.save(path, "PNG", optimize=True)
    return bg


def main():
    for path in LOGOS:
        if not path.exists():
            print(f"SKIP (не найден): {path}")
            continue
        # Бэкап
        backup = BACKUP_DIR / path.name
        if not backup.exists():
            shutil.copy2(path, backup)
        bg = remove_bg(path)
        print(f"OK: {path.name} (фон был {bg})")


if __name__ == "__main__":
    main()
