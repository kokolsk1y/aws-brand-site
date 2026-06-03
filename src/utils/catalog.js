// Нормализация каталога серий для рендера: фильтр по наличию фото + сортировка.
//
// Правила (согласованы с владельцем):
//   1. Показываем ТОЛЬКО товары, у которых реально есть фото в public/img/products.
//      Товары без фото (новые цвета без съёмки, махагон и т.п.) скрываются.
//   2. Цвет показываем в палитре, только если в серии есть хотя бы один ВИДИМЫЙ
//      (с фото) товар этого цвета. Так махагон уходит сам собой — у него нет фото.
//   3. Порядок внутри группы: СНАЧАЛА ТИП, ПОТОМ ЦВЕТ.
//      - Выключатели: число клавиш (1→2→3) → функция → цвет.
//      - Розетки:     тип (силовая→крышка→USB→TV→RJ45→…) → размер → цвет.
//      - Рамки:       число постов (1→2→3→4→5) → ориентация (гориз→верт) → цвет.
//
// Парсим РУССКОЕ name товара (оно регулярно), а не артикул — артикулы
// кодируют номер непоследовательно (УНО: 030=4-я, 031=3-я).

import { getProductPhotos } from './photos.js';

export function hasPhoto(article) {
  return getProductPhotos(article).length > 0;
}

// ---- извлечение признаков из name ----------------------------------------

// Число клавиш выключателя: "Выключатель 2-кл." → 2
// (не используем \b — в JS он не срабатывает после кириллицы; вместо него
//  проверяем, что после «кл» не идёт буква — чтобы не цеплять «клавиша»)
function keysCount(name) {
  const m = name.match(/(\d+)\s*-?\s*кл(?![а-яё])/i);
  return m ? parseInt(m[1], 10) : 1;
}

// Число постов рамки/розетки: "Рамка 3-я" → 3. «для двойной розетки» → в конец.
function postsCount(name) {
  if (/для двойной розетки/i.test(name)) return 90;
  const m = name.match(/(\d+)\s*-\s*я(?![а-яё])/i);
  return m ? parseInt(m[1], 10) : 1;
}

// Ориентация рамки: горизонтальная/одинарная = 0, вертикальная = 1.
function orientationRank(name) {
  return /вертикальн/i.test(name) ? 1 : 0;
}

// Функция выключателя — порядок исполнений внутри одного числа клавиш.
function switchFuncRank(name) {
  const n = name.toLowerCase();
  if (/звонк/.test(n)) return 6;
  if (/жалюзи/.test(n)) return 5;
  if (/перекрёстн|перекрестн/.test(n)) return 4;
  if (/проходн/.test(n)) return /подсветк/.test(n) ? 3 : 2;
  if (/подсветк/.test(n)) return 1;
  return 0; // обычный
}

// Тип розетки — крупные группы.
function socketTypeRank(name) {
  const n = name.toLowerCase();
  if (/для двойной розетки/.test(n)) return 90;          // рамки в группе розеток — в конец
  if (/rj45/.test(n) && /tv|тв/.test(n)) return 5;        // комбо RJ45+TV
  if (/rj45/.test(n)) return 4;
  if (/\btv\b|телевиз|тв\b/.test(n)) return 3;
  if (/usb|type\s*c/.test(n)) return 2;
  if (/с крышкой/.test(n)) return 1;
  return 0;                                               // обычная силовая с/з
}

// Размер розетки: "Розетка 2-я" → 2 (иначе 1).
function socketSize(name) {
  const m = name.match(/(\d+)\s*-\s*я(?![а-яё])/i);
  return m ? parseInt(m[1], 10) : 1;
}

// ---- компараторы по группам ----------------------------------------------

function makeComparator(groupKey, colorOrder) {
  const colorRank = (c) => {
    const i = colorOrder.indexOf(c);
    return i === -1 ? 999 : i;
  };
  const by = (...fns) => (a, b) => {
    for (const f of fns) {
      const d = f(a) - f(b);
      if (d) return d;
    }
    return a.article.localeCompare(b.article, 'ru');
  };

  if (groupKey === 'switches') {
    return by(
      (x) => keysCount(x.name),
      (x) => switchFuncRank(x.name),
      (x) => colorRank(x.color),
    );
  }
  if (groupKey === 'sockets') {
    return by(
      (x) => socketTypeRank(x.name),
      (x) => socketSize(x.name),
      (x) => colorRank(x.color),
    );
  }
  if (groupKey === 'frames') {
    return by(
      (x) => postsCount(x.name),
      (x) => orientationRank(x.name),
      (x) => colorRank(x.color),
    );
  }
  // accessories / other — по имени, потом цвет
  return by(
    (x) => x.name.localeCompare(x.name, 'ru'),
    (x) => colorRank(x.color),
  );
}

// ---- публичное API --------------------------------------------------------

// Видимые товары группы: только с фото, отсортированы (тип → цвет).
export function visibleItems(items, groupKey, colorOrder) {
  return (items || [])
    .filter((it) => hasPhoto(it.article))
    .sort(makeComparator(groupKey, colorOrder));
}

// Цвета серии, у которых есть хотя бы один видимый (с фото) товар.
// Возвращает colors[] в исходном порядке series.json, без «пустых».
export function visibleColors(series) {
  const present = new Set();
  for (const groupKey of Object.keys(series.groups || {})) {
    for (const it of series.groups[groupKey] || []) {
      if (it.color && hasPhoto(it.article)) present.add(it.color);
    }
  }
  return (series.colors || []).filter((c) => present.has(c.key) && c.img);
}

// Порядок ключей цветов для сортировки (как в series.json).
export function colorOrderOf(series) {
  return (series.colors || []).map((c) => c.key);
}
