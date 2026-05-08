// Миграция плоской структуры /img/products/АРТИКУЛ.webp → иерархия
// /img/products/<категория>/<АРТИКУЛ>/<N>.webp
//
// Категория определяется по products.json + series.json. Если артикул не
// найден ни там, ни там — кладём в _orphans/ (пользователь решит сам).

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const PRODUCTS_DIR = path.join(ROOT, 'public', 'img', 'products');

const productsJson = require(path.join(ROOT, 'public', 'products.json'));
const seriesJson = require(path.join(ROOT, 'src', 'data', 'series.json'));

// 1. Маппинг артикул → slug категории (или серии)
const artToCat = new Map();
const catSlugMap = {
    'udl_home': 'extensions-home',
    'udl_garden': 'extensions-garden',
    'power': 'power-connectors',
    'clamps': 'clamps',
    'patch': 'patch-cords',
    'cable': 'cables'
};
for (const [key, data] of Object.entries(productsJson)) {
    const slug = catSlugMap[key];
    if (!slug || !data.items) continue;
    for (const it of data.items) {
        artToCat.set(it.article, slug);
    }
}
for (const [seriesSlug, series] of Object.entries(seriesJson)) {
    if (!series.groups) continue;
    for (const g of ['switches', 'sockets', 'frames', 'accessories', 'other']) {
        for (const it of (series.groups[g] || [])) {
            artToCat.set(it.article, 'series-' + seriesSlug);
        }
    }
}

// 2. Сканируем плоские файлы и группируем по артикулу
const allFiles = fs.readdirSync(PRODUCTS_DIR).filter(f => /\.(webp|png|jpg|jpeg)$/i.test(f));
const byArt = new Map();
for (const f of allFiles) {
    const ext = path.extname(f);
    const base = f.slice(0, -ext.length);
    const m = base.match(/^(.+)_(\d+)$/);
    let art, idx;
    if (m) { art = m[1]; idx = parseInt(m[2], 10); }
    else { art = base; idx = 1; }
    if (!byArt.has(art)) byArt.set(art, []);
    byArt.get(art).push({ file: f, idx, ext });
}

// 3. Раскладываем по папкам
let moved = 0, orphans = 0;
for (const [art, files] of byArt) {
    const cat = artToCat.get(art) || '_orphans';
    if (cat === '_orphans') orphans++;
    const targetDir = path.join(PRODUCTS_DIR, cat, art);
    fs.mkdirSync(targetDir, { recursive: true });
    files.sort((a, b) => a.idx - b.idx);
    for (let i = 0; i < files.length; i++) {
        const item = files[i];
        const dstName = (i === 0 ? 'main' : String(i + 1)) + item.ext;
        const src = path.join(PRODUCTS_DIR, item.file);
        const dst = path.join(targetDir, dstName);
        if (fs.existsSync(dst)) continue; // уже мигрирован
        fs.renameSync(src, dst);
        moved++;
    }
}

console.log(`Переехало файлов: ${moved}, артикулов в _orphans: ${orphans}`);
console.log(`Артикулов с папкой: ${byArt.size}`);
