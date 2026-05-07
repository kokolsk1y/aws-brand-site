"""Batch rembg: убираем фон у всех фото из c:/tmp/stv-photos-raw → c:/tmp/stv-photos-clean
Сохраняем как WebP с alpha (прозрачный фон).
"""
import os
import sys
from pathlib import Path
from rembg import remove, new_session
from PIL import Image
from io import BytesIO

SRC = Path("c:/tmp/stv-photos-raw")
DST = Path("c:/tmp/stv-photos-clean")
DST.mkdir(parents=True, exist_ok=True)

# isnet-general-use — отличная универсальная модель, точнее старого u2net
session = new_session("isnet-general-use")

files = sorted([f for f in SRC.iterdir() if f.suffix.lower() in (".webp", ".jpg", ".jpeg", ".png")])
print(f"Файлов на обработку: {len(files)}")

ok = 0
fail = 0
for idx, fp in enumerate(files, 1):
    out = DST / (fp.stem + ".webp")
    if out.exists() and out.stat().st_size > 1000:
        ok += 1
        continue
    try:
        with open(fp, "rb") as f:
            inp = f.read()
        result = remove(inp, session=session)
        # Конвертим в PIL Image для сохранения как webp с alpha
        img = Image.open(BytesIO(result)).convert("RGBA")
        # Опционально: trim — обрезаем прозрачные края, чтобы товар занимал максимум кадра
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        img.save(out, "WEBP", quality=92, method=6)
        ok += 1
        if idx % 10 == 0:
            print(f"  progress {ok}/{len(files)}")
    except Exception as e:
        fail += 1
        print(f"  fail {fp.name}: {e}")

print(f"rembg done: ok={ok}, fail={fail}")
