// SYNC photos-sorted/ → public/img/products/ + products.json + series.json
//
// photos-sorted/ — ИСТОЧНИК ПРАВДЫ.
//
// Логика:
//   1. main.webp/.png → главное фото (АРТИКУЛ.webp)
//   2. 2.webp / 5.webp / 7.webp (с пропусками) → переномеровываются последовательно
//      → АРТИКУЛ_2.webp, АРТИКУЛ_3.webp, АРТИКУЛ_4.webp (без дырок)
//   3. Папка пустая (0 файлов) → товар удаляется из products.json/series.json
//   4. Папки нет → товар не трогаем (артикул был без фото изначально)

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const PSORT = path.join(ROOT, 'photos-sorted');
const PUB = path.join(ROOT, 'public', 'img', 'products');

function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

// 1. Сканируем photos-sorted/<КАТ>/<АРТ>/ — собираем актуальное состояние
const articleFiles = new Map(); // article → [ {file, idx | 'main', ext} ] упорядоченный
const articleDirs = new Set();   // все артикулы у которых есть папка

if (!fs.existsSync(PSORT)) {
    console.error('Нет папки photos-sorted/');
    process.exit(1);
}

for (const cat of fs.readdirSync(PSORT)) {
    const catDir = path.join(PSORT, cat);
    if (!fs.statSync(catDir).isDirectory()) continue;
    for (const art of fs.readdirSync(catDir)) {
        const artDir = path.join(catDir, art);
        if (!fs.statSync(artDir).isDirectory()) continue;
        articleDirs.add(art);
        const files = fs.readdirSync(artDir).filter(f => /\.(webp|png|jpg|jpeg)$/i.test(f));
        const items = [];
        for (const f of files) {
            const ext = path.extname(f);
            const base = f.slice(0, -ext.length).toLowerCase();
            if (base === 'main') items.push({ file: f, sort: 0, ext, isMain: true });
            else if (/^\d+$/.test(base)) items.push({ file: f, sort: parseInt(base, 10), ext, isMain: false });
        }
        items.sort((a, b) => a.sort - b.sort);
        articleFiles.set(art, items);
    }
}

// 2. Применяем к public/img/products/
let placedMain = 0, placedExtra = 0, removedFiles = 0;
const articlesToRemove = new Set(); // для products.json/series.json

for (const [art, items] of articleFiles) {
    // Удаляем все существующие файлы артикула в public
    const reAll = new RegExp('^' + escapeRe(art) + '(_\\d+)?\\.(webp|png|jpg|jpeg)$', 'i');
    for (const f of fs.readdirSync(PUB)) {
        if (reAll.test(f)) {
            fs.unlinkSync(path.join(PUB, f));
            removedFiles++;
        }
    }
    if (items.length === 0) {
        // Папка пустая → товар удаляем из каталога
        articlesToRemove.add(art);
        continue;
    }
    // Кладём main первым
    const main = items.find(it => it.isMain);
    let idx = 1;
    if (main) {
        const dst = `${art}.webp`; // всегда webp на выходе
        // Если исходник .png — копируем как .png (auto-detect ловит и его)
        const dstName = main.ext.toLowerCase() === '.png' ? `${art}.png` : `${art}.webp`;
        const srcPath = findArtPath(art, main.file);
        if (srcPath) {
            fs.copyFileSync(srcPath, path.join(PUB, dstName));
            placedMain++;
        }
        idx = 2;
    } else {
        // main нет, первый numerated станет main
        const first = items[0];
        if (first) {
            const dstName = first.ext.toLowerCase() === '.png' ? `${art}.png` : `${art}.webp`;
            const srcPath = findArtPath(art, first.file);
            if (srcPath) {
                fs.copyFileSync(srcPath, path.join(PUB, dstName));
                placedMain++;
            }
            idx = 2;
        }
    }
    // Numerated extras (без main) — переномеровка по порядку 2, 3, 4 ...
    const extras = items.filter(it => !it.isMain);
    for (const it of extras) {
        const dstName = it.ext.toLowerCase() === '.png' ? `${art}_${idx}.png` : `${art}_${idx}.webp`;
        const srcPath = findArtPath(art, it.file);
        if (srcPath) {
            fs.copyFileSync(srcPath, path.join(PUB, dstName));
            placedExtra++;
            idx++;
        }
    }
}

function findArtPath(art, file) {
    for (const cat of fs.readdirSync(PSORT)) {
        const fp = path.join(PSORT, cat, art, file);
        if (fs.existsSync(fp)) return fp;
    }
    return null;
}

// 3. ЖЁСТКАЯ зачистка — products.json / series.json: оставляем ТОЛЬКО артикулы
//    у которых ЕСТЬ папка в photos-sorted (с файлами или пустая).
//    Артикулы без папки = «удалил пользователь» → убрать из каталога + удалить
//    оставшиеся файлы из public.
const products = require(path.join(ROOT, 'public', 'products.json'));
const series = require(path.join(ROOT, 'src', 'data', 'series.json'));

const allArtsInCatalog = new Set();
for (const k of Object.keys(products)) {
    for (const it of (products[k].items || [])) allArtsInCatalog.add(it.article);
}
for (const sl of Object.keys(series)) {
    for (const gr of Object.keys(series[sl].groups || {})) {
        for (const it of (series[sl].groups[gr] || [])) allArtsInCatalog.add(it.article);
    }
}

// Артикулы которых в каталоге есть, но папки в photos-sorted НЕТ → удалить
const orphanArts = [...allArtsInCatalog].filter(a => !articleDirs.has(a));
let pubExtraRemoved = 0;
for (const art of orphanArts) {
    articlesToRemove.add(art);
    // Удаляем все файлы из public для этого артикула
    const reAll = new RegExp('^' + escapeRe(art) + '(_\\d+)?\\.(webp|png|jpg|jpeg)$', 'i');
    for (const f of fs.readdirSync(PUB)) {
        if (reAll.test(f)) {
            fs.unlinkSync(path.join(PUB, f));
            pubExtraRemoved++;
        }
    }
}

let prodRemoved = 0, seriesRemoved = 0;
for (const k of Object.keys(products)) {
    if (!products[k].items) continue;
    const before = products[k].items.length;
    products[k].items = products[k].items.filter(it => !articlesToRemove.has(it.article));
    prodRemoved += before - products[k].items.length;
}
for (const sl of Object.keys(series)) {
    if (!series[sl].groups) continue;
    for (const gr of Object.keys(series[sl].groups)) {
        const before = series[sl].groups[gr].length;
        series[sl].groups[gr] = series[sl].groups[gr].filter(it => !articlesToRemove.has(it.article));
        seriesRemoved += before - series[sl].groups[gr].length;
    }
}

fs.writeFileSync(path.join(ROOT, 'public', 'products.json'), JSON.stringify(products, null, 2));
fs.writeFileSync(path.join(ROOT, 'src', 'data', 'series.json'), JSON.stringify(series, null, 2));

if (orphanArts.length) {
    console.log(`\nУдалено товаров без папки в photos-sorted: ${orphanArts.length}`);
    console.log('  ', orphanArts.slice(0, 30).join(', ') + (orphanArts.length > 30 ? '...' : ''));
    console.log(`  + удалено файлов в public: ${pubExtraRemoved}`);
}

console.log(`Артикулов с папкой в photos-sorted: ${articleFiles.size}`);
console.log(`Удалено старых файлов в public: ${removedFiles}`);
console.log(`Скопировано: main=${placedMain}, extras=${placedExtra}`);
console.log(`Артикулов с пустой папкой (удалены из каталога): ${articlesToRemove.size}`);
if (articlesToRemove.size > 0) console.log('  ', [...articlesToRemove].slice(0, 20).join(', '));
console.log(`Из products.json убрано: ${prodRemoved}`);
console.log(`Из series.json убрано: ${seriesRemoved}`);
