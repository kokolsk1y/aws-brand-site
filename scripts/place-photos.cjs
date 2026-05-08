// Раскладывает обработанные rembg-фото в /public/img/products/.
// Источник: _pipeline/photos-clean/АРТИКУЛ__N.webp
// Назначение: public/img/products/АРТИКУЛ.webp / АРТИКУЛ_2.webp / АРТИКУЛ_3.webp ...
//
// Берёт только «свои» фото по UUID-фильтру (через stv-products-v2.json).
// Если файла в clean ещё нет (rembg не дошёл) — пропускает, не падает.
//
// Также поддерживает несколько запусков: при каждом перезаписывает то, что есть.

const fs = require('fs');
const path = require('path');

const SRC = 'c:/Users/ikoko/Projects/aws-brand-site/_pipeline/photos-clean';
const DST = 'c:/Users/ikoko/Projects/aws-brand-site/public/img/products';

const products = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/stv-products-v2.json');

if (!fs.existsSync(SRC)) {
    console.log('Нет папки', SRC);
    process.exit(1);
}
fs.mkdirSync(DST, { recursive: true });

let placed = 0, skippedNoSrc = 0, productsWithFoto = 0;
const log = [];

for (const p of products) {
    if (!p.photos.length) continue;
    let count = 0;
    for (let i = 0; i < p.photos.length; i++) {
        // Ожидаемое имя файла: АРТИКУЛ__N.webp (rembg сохраняет с расширением .webp)
        const safeArt = String(p.article).replace(/[^A-Za-z0-9_\-]/g, '_');
        const srcFile = path.join(SRC, `${safeArt}__${i}.webp`);
        if (!fs.existsSync(srcFile)) {
            // Возможно ещё не обработан rembg — пропускаем тихо
            skippedNoSrc++;
            continue;
        }
        // Назначение: i=0 → АРТИКУЛ.webp, i>=1 → АРТИКУЛ_<i+1>.webp (через подчёркивание)
        const dstName = i === 0 ? `${p.article}.webp` : `${p.article}_${i + 1}.webp`;
        const dstFile = path.join(DST, dstName);
        fs.copyFileSync(srcFile, dstFile);
        placed++;
        count++;
    }
    if (count > 0) productsWithFoto++;
    log.push({ article: p.article, photosTotal: p.photos.length, placed: count });
}

// PNG-файлы НЕ трогаем — некоторые используются в HTML напрямую с явным
// расширением (advantages блок на главной). Оставляем их как есть.
const deletedPng = 0;

console.log(JSON.stringify({
    placed,
    skippedNoSrcYet: skippedNoSrc,
    productsWithAtLeastOnePhoto: productsWithFoto,
    productsTotal: products.length,
    deletedPngDuplicates: deletedPng
}, null, 2));
