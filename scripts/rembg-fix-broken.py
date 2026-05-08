"""Перерабатывает 23 проблемных файла через birefnet БЕЗ alpha_matting
(быстрее, не падает на нехватке памяти).
"""
from pathlib import Path
from rembg import remove, new_session
from PIL import Image
from io import BytesIO

TARGETS = [
    ("AWS-H03K-1,5", 1),
    ("AWS-H03K-5", 1),
    ("AWS-H05K-1,5", 4),
    ("AWS-H05K-3", 3),
    ("AWS-HZ2-01-10", 0),
    ("AWS-HZ2-01-15", 0),
    ("AWS-HZ2-01-25", 0),
    ("SLN-113K", 0),
    ("SLN-114K", 0),
    ("SLN-0142", 1),
    ("SLN-0352", 2),
    ("SLN-0452", 0),
    ("SLN-1132", 0),
    ("SLN-1252", 0),
    ("SLN-1452", 0),
    ("SLN-1452", 2),
    ("SLN-2152", 0),
    ("SLN-2232", 0),
    ("SLN-2242", 0),
    ("SLN-2252", 0),
    ("SLN-2352", 0),
    ("SN-222415D", 0),
]


def safe_art(a):
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in a)


RAW = Path("c:/Users/ikoko/Projects/aws-brand-site/_pipeline/photos-raw")
CLEAN = Path("c:/Users/ikoko/Projects/aws-brand-site/_pipeline/photos-clean")

print("Загружаю birefnet-general...")
session = new_session("birefnet-general")
print("Готово. Обработка без alpha_matting (быстрее, стабильнее).")

ok = fail = missing = 0
for art, idx in TARGETS:
    sa = safe_art(art)
    src = None
    for ext in (".webp", ".jpg", ".jpeg", ".png"):
        cand = RAW / f"{sa}__{idx}{ext}"
        if cand.exists():
            src = cand
            break
    if not src:
        print(f"  MISSING raw для {art} idx={idx}")
        missing += 1
        continue
    dst = CLEAN / f"{sa}__{idx}.webp"
    # Удаляем старый (если есть)
    if dst.exists():
        dst.unlink()
    try:
        with open(src, "rb") as f:
            inp = f.read()
        # БЕЗ alpha_matting — намного быстрее и стабильнее
        result = remove(inp, session=session)
        img = Image.open(BytesIO(result)).convert("RGBA")
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        img.save(dst, "WEBP", quality=92, method=6)
        print(f"  OK {art} idx={idx}")
        ok += 1
    except Exception as e:
        print(f"  FAIL {art} idx={idx}: {str(e)[:100]}")
        fail += 1

print(f"\nИтог: ok={ok}, fail={fail}, missing={missing}")
