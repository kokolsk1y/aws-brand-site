// Auto-detect фотографий товара по артикулу.
// Соглашение по именованию файлов в /public/img/products/:
//   АРТИКУЛ.webp / .png / .jpg                ← главное фото
//   АРТИКУЛ-2.webp ... АРТИКУЛ-N.webp         ← дополнительные ракурсы
//
// Чтобы добавить новый ракурс — положите файл с правильным именем,
// пересоберите проект — фото автоматически попадёт в галерею.

import fs from 'node:fs';
import path from 'node:path';

const PRODUCTS_DIR = path.resolve('public/img/products');
const PRODUCTS_FILES = fs.existsSync(PRODUCTS_DIR) ? fs.readdirSync(PRODUCTS_DIR) : [];

export function getProductPhotos(article) {
  if (!article) return [];
  const safe = String(article).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const reMain = new RegExp('^' + safe + '\\.(webp|png|jpg|jpeg)$', 'i');
  const reExtra = new RegExp('^' + safe + '-(\\d+)\\.(webp|png|jpg|jpeg)$', 'i');
  const main = PRODUCTS_FILES.find(f => reMain.test(f));
  const extras = PRODUCTS_FILES
    .map(f => { const m = f.match(reExtra); return m ? { f, n: parseInt(m[1], 10) } : null; })
    .filter(Boolean)
    .sort((a, b) => a.n - b.n)
    .map(x => x.f);
  return [main, ...extras].filter(Boolean).map(f => `/img/products/${f}`);
}
