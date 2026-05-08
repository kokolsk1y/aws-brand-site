"""Перегоняет все фото через birefnet-general — лучшая на сегодня модель
для удаления фона. Обрабатывает тонкие детали, прозрачные участки между
проводами, серые товары на белом фоне.

Источник: _pipeline/photos-raw
Назначение: _pipeline/photos-clean (overwrite)

Параметры:
  alpha_matting=True — сохраняет полупрозрачные края (тени, размытие провода)
"""
import os
import sys
from pathlib import Path
from rembg import remove, new_session
from PIL import Image
from io import BytesIO

SRC = Path("c:/Users/ikoko/Projects/aws-brand-site/_pipeline/photos-raw")
DST = Path("c:/Users/ikoko/Projects/aws-brand-site/_pipeline/photos-clean")
DST.mkdir(parents=True, exist_ok=True)

print("Загружаю модель birefnet-general (первый раз ~400MB)...")
session = new_session("birefnet-general")
print("Модель готова")

files = sorted([f for f in SRC.iterdir() if f.suffix.lower() in (".webp", ".jpg", ".jpeg", ".png")])
print(f"Файлов на обработку: {len(files)}")

ok = 0
fail = 0
for idx, fp in enumerate(files, 1):
    out = DST / (fp.stem + ".webp")
    try:
        with open(fp, "rb") as f:
            inp = f.read()
        # alpha_matting сильно медленнее, но даёт точные края на тонких деталях
        result = remove(
            inp,
            session=session,
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
            alpha_matting_erode_size=10
        )
        img = Image.open(BytesIO(result)).convert("RGBA")
        # Trim прозрачные края
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        img.save(out, "WEBP", quality=92, method=6)
        ok += 1
        if idx % 20 == 0:
            print(f"  progress {ok}/{len(files)}")
    except Exception as e:
        fail += 1
        print(f"  fail {fp.name}: {e}")

print(f"birefnet done: ok={ok}, fail={fail}")
