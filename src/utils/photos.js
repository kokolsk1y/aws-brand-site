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
const STANDARD_WITHOUT_SEPARATE_ANGLE = new Set([
  'SD-P1001W',
  'SD-P1009B',
  'SD-P1012W',
  'SD-P1016W',
  'SD-V1001WG',
]);
const ORANGE_LEVER_TERMINALS = new Set([
  'SN-221412',
  'SN-221412N',
  'SN-221413',
  'SN-221413N',
  'SN-221414',
  'SN-221414N',
  'SN-221415',
  'SN-221415N',
  'SN-222411D',
  'SN-222412',
  'SN-222412D',
  'SN-222413',
  'SN-222413D',
  'SN-222414',
  'SN-222414D',
  'SN-222415',
  'SN-222415D',
]);
const ORANGE_LEVER_IMAGE_VERSION = '20261009';
const CLASSIC_TERMINALS = new Set([
  'SN-202',
  'SN-203',
  'SN-204',
  'SN-205',
  'SN-206',
  'SN-208',
]);
const CLASSIC_TERMINAL_IMAGE_VERSION = '20261009';
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
  const normalizedArticle = String(article).toUpperCase();
  const isStandard = normalizedArticle.startsWith('SD-');
  // В выгрузке СТАНДАРТ перспективный ¾-ракурс сохранён как _2.
  // У пяти товаров отдельного перспективного файла нет — там первым остаётся main.
  const HERO = isStandard && !STANDARD_WITHOUT_SEPARATE_ANGLE.has(normalizedArticle) ? 2 : 1;
  if (isStandard && !main && !byIdx.has(HERO)) return [];

  // Последовательность (индекс, файл): выразительный ¾-ракурс перед анфасом,
  // затем остальные технические виды. Для других серий канонический hero — _1.
  const seq = [];
  if (byIdx.has(HERO)) seq.push([HERO, pickByFormat(byIdx.get(HERO))]);
  if (main) seq.push([1, main]);
  for (const idx of [...byIdx.keys()].sort((a, b) => a - b)) {
    if (idx === HERO) continue;
    if (ORANGE_LEVER_TERMINALS.has(normalizedArticle) && idx > 2) continue;
    seq.push([idx, pickByFormat(byIdx.get(idx))]);
  }

  // Тыльная сторона — всегда в конец (первое фото не трогаем).
  // Карта src/data/uno_photo_order.json: артикул → индекс тыльного ракурса (УНО).
  const backIdx = backOrder[article];
  if (backIdx != null && seq.length > 1) {
    const pos = seq.findIndex(([i]) => i === backIdx);
    if (pos > 0) seq.push(seq.splice(pos, 1)[0]);
  }

  let version = '';
  if (ORANGE_LEVER_TERMINALS.has(normalizedArticle)) {
    version = `?v=${ORANGE_LEVER_IMAGE_VERSION}`;
  } else if (CLASSIC_TERMINALS.has(normalizedArticle)) {
    version = `?v=${CLASSIC_TERMINAL_IMAGE_VERSION}`;
  }
  return seq.map(([, f]) => f).filter(Boolean).map(f => `/img/products/${f}${version}`);
}
