// Auto-detect фотографий товара по артикулу.
// Соглашение по именованию файлов в /public/img/products/:
//   АРТИКУЛ.webp / .png / .jpg                ← главное фото
//   АРТИКУЛ_2.webp ... АРТИКУЛ_N.webp         ← дополнительные ракурсы (через подчёркивание!)
//
// ⚠️ Подчёркивание, не дефис — потому что в артикулах сами есть дефисы
// (AWS-12982-50 — это вариант длины, не ракурс). Дефис используется только
// в артикуле, подчёркивание — только для номера ракурса.
//
// Чтобы добавить новый ракурс — положите файл с правильным именем,
// пересоберите проект — фото автоматически попадёт в галерею.

import fs from 'node:fs';
import path from 'node:path';
import backOrder from '../data/uno_photo_order.json' with { type: 'json' };

const PRODUCTS_DIR = path.resolve('public/img/products');
const PRODUCTS_FILES = fs.existsSync(PRODUCTS_DIR) ? fs.readdirSync(PRODUCTS_DIR) : [];

// Приоритет форматов для главного фото: webp > png > jpg
// (webp обычно в 5-10 раз легче — экономия трафика).
const FMT_PRIORITY = { webp: 0, png: 1, jpg: 2, jpeg: 2 };
function pickByFormat(matches) {
  if (!matches.length) return null;
  return matches.sort((a, b) => {
    const ea = a.split('.').pop().toLowerCase();
    const eb = b.split('.').pop().toLowerCase();
    return (FMT_PRIORITY[ea] ?? 9) - (FMT_PRIORITY[eb] ?? 9);
  })[0];
}

export function getProductPhotos(article) {
  if (!article) return [];
  const safe = String(article).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const reMain = new RegExp('^' + safe + '\\.(webp|png|jpg|jpeg)$', 'i');
  const reExtra = new RegExp('^' + safe + '_(\\d+)\\.(webp|png|jpg|jpeg)$', 'i');
  const main = pickByFormat(PRODUCTS_FILES.filter(f => reMain.test(f)));
  // Группируем доп. ракурсы по индексу — берём по 1 файлу на индекс (webp в приоритете)
  const byIdx = new Map();
  for (const f of PRODUCTS_FILES) {
    const m = f.match(reExtra);
    if (!m) continue;
    const idx = parseInt(m[1], 10);
    if (!byIdx.has(idx)) byIdx.set(idx, []);
    byIdx.get(idx).push(f);
  }
  // Последовательность (индекс, файл).
  // Индекс _1 — канонический ¾-ракурс АУРА («ракурс 3х4»): он ГЕРОЙСКИЙ,
  // ставим его ПЕРВЫМ — перед лицом/main (плоское лицо АУРА невыразительно).
  // У золото/серых main-файла нет; у чёрных/белых main = лицо → ¾ всё равно впереди.
  // У остальных серий файлов _1 нет — поведение не меняется.
  const HERO = 1;
  const seq = [];
  if (byIdx.has(HERO)) seq.push([HERO, pickByFormat(byIdx.get(HERO))]);
  if (main) seq.push([1, main]);
  for (const idx of [...byIdx.keys()].sort((a, b) => a - b)) {
    if (idx === HERO) continue;
    seq.push([idx, pickByFormat(byIdx.get(idx))]);
  }

  // Тыльная сторона — всегда в конец (первое фото не трогаем).
  // Карта src/data/uno_photo_order.json: артикул → индекс тыльного ракурса (УНО).
  const backIdx = backOrder[article];
  if (backIdx != null && seq.length > 1) {
    const pos = seq.findIndex(([i]) => i === backIdx);
    if (pos > 0) seq.push(seq.splice(pos, 1)[0]);
  }

  return seq.map(([, f]) => f).filter(Boolean).map(f => `/img/products/${f}`);
}
