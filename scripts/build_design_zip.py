# -*- coding: utf-8 -*-
"""Собирает zip: вырезанные webp серии ДИЗАЙН БЕЗ ФОНА (прозрачные), имя = артикул, + README."""
import sys, os, shutil, zipfile
sys.path.insert(0, 'scripts')
from place_design_photos import MAP

PROD = 'public/img/products'
STAGE = 'incoming/design_delivery'
ZIP = 'ДИЗАЙН-фото-БЕЗ-ФОНА.zip'
OLD_ZIP = 'ДИЗАЙН-фото-по-артикулам.zip'   # старый «с фоном» — удаляем

AMBIG = {
    'A-D001/A-D002/A-D007 (×W/B/GR)': '1-кл. без подсветки: обычный/проходной/перекрёстный — фронт идентичен',
    'A-D003 = A-D004 (×W/B/GR)': '1-кл. с подсветкой: обычный/проходной — одно фото на пару',
    'A-D011 = A-D012 (×W/B/GR)': '2-кл. без подсветки: обычный/проходной — одно фото на пару',
    'A-D009 = A-D010 (×W/B/GR)': '2-кл. с подсветкой: обычный/проходной — одно фото на пару',
}
MISSING = [
    'PD80-1B  — рамка 1-я чёрная (не отснято)',
    'PD80-1GR — рамка 1-я серебро (не отснято)',
    'PD80-6W / PD80-6B / PD80-6GR — рамка для двойной розетки (отдельно нет; видна в сборе на A-D055*)',
    'A-D038W / A-D038B / A-D038GR — вывод для кабеля (не отснято)',
    'A-D039W / A-D039B / A-D039GR — заглушка (не отснято)',
]

def main():
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    os.makedirs(STAGE)
    copied, miss = [], []
    for art in MAP:
        src = f'{PROD}/{art}.webp'
        if os.path.exists(src):
            shutil.copy2(src, f'{STAGE}/{art}.webp'); copied.append(art)
        else:
            miss.append(art)
    readme = []
    readme.append('ФОТО СЕРИИ ДИЗАЙН — БЕЗ ФОНА (прозрачный webp с альфой). Имя файла = АРТИКУЛ.')
    readme.append('Товар отцентрован в квадрате 1600x1600, длинная сторона ~86%% холста.')
    readme.append('Рамки — со сквозными прозрачными проёмами.')
    readme.append('')
    readme.append('ВСЕГО ФАЙЛОВ: %d' % len(copied))
    readme.append('')
    readme.append('=== НЕОДНОЗНАЧНЫЕ (фронт одинаков, артикул на глаз не отличить) ===')
    for k, v in AMBIG.items():
        readme.append('  %s\n      %s' % (k, v))
    readme.append('')
    readme.append('=== ЧЕГО НЕ ХВАТАЕТ (фото нет — нужно доснять) ===')
    for m in MISSING:
        readme.append('  - ' + m)
    readme.append('')
    readme.append('ВНИМАНИЕ: A-D025GR (серебр. розетка USB+TypeC) — фото есть, но артикула нет в каталоге.')
    with open(f'{STAGE}/README.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(readme))

    for z in (ZIP, OLD_ZIP):
        if os.path.exists(z):
            os.remove(z)
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(STAGE)):
            z.write(f'{STAGE}/{fn}', fn)
    print('ZIP (без фона):', os.path.abspath(ZIP))
    print('файлов:', len(copied), '| без webp:', len(miss), miss)

if __name__ == '__main__':
    main()
