// Создаёт КОПИИ фото в иерархической структуре для просмотра пользователем.
// Не трогает плоские оригиналы — сайт продолжит работать.
//
// Источник: /public/img/products/АРТИКУЛ.webp + АРТИКУЛ_N.webp
// Назначение: photos-sorted/<категория>/<АРТИКУЛ>/main.webp + 2.webp + ...
//
// Открой photos-sorted/ и пройдись по папкам — увидишь все товары
// разложенные по категориям и сериям.

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SRC = path.join(ROOT, 'public', 'img', 'products');
const DST = path.join(ROOT, 'photos-sorted');

const productsJson = require(path.join(ROOT, 'public', 'products.json'));
const seriesJson = require(path.join(ROOT, 'src', 'data', 'series.json'));

// Маппинг артикул → читаемое имя категории
const catName = {
    'udl_home': '01-Удлинители-бытовые',
    'udl_garden': '02-Удлинители-садовые',
    'power': '03-Силовые-разъёмы',
    'clamps': '04-Клеммы',
    'patch': '05-Патч-корды',
    'cable': '06-Кабель'
};
const seriesName = {
    'aura': '07-Серия-АУРА',
    'uno': '08-Серия-УНО',
    'design': '09-Серия-ДИЗАЙН'
};

const artToFolder = new Map();
for (const [key, data] of Object.entries(productsJson)) {
    const folder = catName[key];
    if (!folder || !data.items) continue;
    for (const it of data.items) artToFolder.set(it.article, folder);
}
for (const [key, data] of Object.entries(seriesJson)) {
    const folder = seriesName[key];
    if (!folder || !data.groups) continue;
    for (const g of ['switches', 'sockets', 'frames', 'accessories', 'other']) {
        for (const it of (data.groups[g] || [])) artToFolder.set(it.article, folder);
    }
}

if (!fs.existsSync(SRC)) { console.error('NO SRC'); process.exit(1); }
if (fs.existsSync(DST)) fs.rmSync(DST, { recursive: true, force: true });
fs.mkdirSync(DST, { recursive: true });

// Группируем по артикулу
const allFiles = fs.readdirSync(SRC).filter(f => /\.(webp|png|jpg|jpeg)$/i.test(f));
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

let copied = 0, orphan = 0;
for (const [art, files] of byArt) {
    const folder = artToFolder.get(art) || '99-Без-категории';
    if (folder === '99-Без-категории') orphan++;
    const targetDir = path.join(DST, folder, art);
    fs.mkdirSync(targetDir, { recursive: true });
    files.sort((a, b) => a.idx - b.idx);
    for (let i = 0; i < files.length; i++) {
        const item = files[i];
        const dstName = (i === 0 ? 'main' : String(i + 1)) + item.ext;
        fs.copyFileSync(path.join(SRC, item.file), path.join(targetDir, dstName));
        copied++;
    }
}

console.log(`Готово. Файлов скопировано: ${copied}`);
console.log(`Артикулов разложено: ${byArt.size}, без категории: ${orphan}`);
console.log(`\nОткрой папку: ${DST}`);
