# -*- coding: utf-8 -*-
"""
Раскладывает pro-фото серии ДИЗАЙН (архив Сергея) по артикулам
в public/img/products/ как ГЛАВНОЕ фото (АРТИКУЛ.webp, перезапись).
Источник: incoming/design_raw/IMG_*.jpg
Карта — incoming/design_photo_mapping.json (составлена визуально).
Доп. ракурсы _2/_3/_4 не трогаются.
"""
import os, glob, sys, io
from PIL import Image

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'incoming', 'design_raw')
OUT = os.path.join(ROOT, 'public', 'img', 'products')
MAXLONG = 2000
Q = 86

# article -> stem (IMG_<stem>.* в incoming/design_raw)
MAP = {
    # --- 3-клавишные ---
    'A-D015W': '5114', 'A-D015B': '5139', 'A-D015GR': '5188',
    # --- жалюзи 2-кл ---
    'A-D013W': '5102', 'A-D013B': '5147', 'A-D013GR': '5194',
    # --- звонок ---
    'A-D005W': '5117', 'A-D005B': '5155', 'A-D005GR': '5176',
    # --- розетки 1-я / крышка / USB ---
    'A-D021W': '5093', 'A-D021B': '5137', 'A-D021GR': '5173',
    'A-D022W': '5094', 'A-D022B': '5149', 'A-D022GR': '5175',
    'A-D025W': '5097', 'A-D025B': '5162', 'A-D025GR': '5183',  # GR нет в каталоге — флаг
    # --- двойная ---
    'A-D055W': '5104', 'A-D055B': '5157', 'A-D055GR': '5186',
    # --- RJ45 / TV ---
    'A-D030W': '5109', 'A-D030B': '5151', 'A-D030GR': '5199',
    'A-D032W': '5113', 'A-D032B': '5152', 'A-D032GR': '5192',
    'A-D037W': '5108', 'A-D037B': '5153', 'A-D037GR': '5182',
    'A-D034W': '5110', 'A-D034B': '5158', 'A-D034GR': '5174',
    # --- рамки ---
    'PD80-1W': '5208',
    'PD80-2W': '5207', 'PD80-2B': '5220', 'PD80-2GR': '5238',
    'PD80-7VW': '5225', 'PD80-7VB': '5222', 'PD80-7VGR': '5232',
    'PD80-3W': '5206', 'PD80-3B': '5214', 'PD80-3GR': '5237',
    'PD80-8VW': '5226', 'PD80-8VB': '5228', 'PD80-8VGR': '5231',
    'PD80-4W': '5203', 'PD80-4B': '5213', 'PD80-4GR': '5235',
    'PD80-5W': '5202', 'PD80-5B': '5212', 'PD80-5GR': '5234',
    # --- НЕОДНОЗНАЧНЫЕ (фронт идентичен) ---
    # 1-кл без подсветки: обычный/проходной/перекрёстный (3 фото = 3 арт)
    'A-D001W': '5100', 'A-D002W': '5115', 'A-D007W': '5118',
    'A-D001B': '5133', 'A-D002B': '5143', 'A-D007B': '5146',
    'A-D001GR': '5171', 'A-D002GR': '5179', 'A-D007GR': '5189-111',
    # 1-кл с подсветкой: обычный/проходной (1 фото -> 2 арт)
    'A-D003W': '5112', 'A-D004W': '5112',
    'A-D003B': '5142', 'A-D004B': '5142',
    'A-D003GR': '5189', 'A-D004GR': '5189',
    # 2-кл без подсветки: обычный/проходной (1 фото -> 2 арт)
    'A-D011W': '5103', 'A-D012W': '5103',
    'A-D011B': '5159', 'A-D012B': '5159',
    'A-D011GR': '5180', 'A-D012GR': '5180',
    # 2-кл с подсветкой: обычный/проходной
    'A-D009W': '5116', 'A-D010W': '5116',
    'A-D009B': '5141', 'A-D010B': '5141',
    'A-D009GR': '5196', 'A-D010GR': '5198',
}

def resolve(stem):
    hits = glob.glob(os.path.join(RAW, f'IMG_{stem}.*'))
    # точное совпадение стема (чтобы IMG_5189 не схватил IMG_5189-111)
    hits = [h for h in hits if os.path.splitext(os.path.basename(h))[0] == f'IMG_{stem}']
    return hits[0] if hits else None

def main():
    ok = 0; miss = []
    for art, stem in MAP.items():
        src = resolve(stem)
        if not src:
            miss.append((art, stem)); print('  НЕТ ИСХОДНИКА:', art, stem); continue
        im = Image.open(src).convert('RGB')
        im.thumbnail((MAXLONG, MAXLONG), Image.LANCZOS)
        dst = os.path.join(OUT, art + '.webp')
        existed = os.path.exists(dst)
        im.save(dst, 'WEBP', quality=Q, method=6)
        ok += 1
        print(f"{'~replace' if existed else '+new    '} {art:10s} <- IMG_{stem}  ({im.size[0]}x{im.size[1]})")
    print(f"\nИтого записано: {ok}, без исходника: {len(miss)}")

if __name__ == '__main__':
    main()
