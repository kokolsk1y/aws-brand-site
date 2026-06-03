import zipfile, os, shutil

SRC = "."
DST = "scripts/audit/photos_from_supplier/unpacked"
zips = [
    "УНО серый.zip", "УНО Фото dark grey2.zip", "УНО Матово черный.zip",
    "АУРА.zip", "Фото Дизайн Серый.zip", "Фото Дизайн белый.zip",
    "Фото Дизайн черный.zip", "УНО серебро.zip",
]


def fix_name(n):
    """Recover mojibake from zips created on Windows (cp437 misdecode)."""
    for enc in ('cp866', 'cp1251'):
        try:
            return n.encode('cp437').decode(enc)
        except Exception:
            continue
    return n


os.makedirs(DST, exist_ok=True)
for z in zips:
    path = os.path.join(SRC, z)
    if not os.path.exists(path):
        print("MISSING", z)
        continue
    folder = os.path.splitext(z)[0]
    out = os.path.join(DST, folder)
    os.makedirs(out, exist_ok=True)
    cnt = 0
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            raw = info.filename
            flag_utf8 = info.flag_bits & 0x800
            name = raw if flag_utf8 else fix_name(raw)
            name = name.replace("\\", "/")
            target = os.path.join(out, name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(info) as s, open(target, 'wb') as d:
                shutil.copyfileobj(s, d)
            cnt += 1
    print(f"{z}: {cnt} files -> {folder}")
