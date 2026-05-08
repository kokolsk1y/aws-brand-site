// Импорт серии АУРА из инфографики:
//   c:/Users/ikoko/Projects/infografika/assets/aura/<АРТИКУЛ>/<...>_nobg.png
// → public/img/products/<АРТИКУЛ>.webp + АРТИКУЛ_2.webp
//
// 1. Удаляет ВСЕ старые фото для артикулов из series.json (серия aura)
//    + всех артикулов из папки инфографики
// 2. Конвертирует _nobg.png в webp (через rembg/PIL — но проще через sharp)
//    Используем cp + переименование, .png будет работать. Для оптимальности
//    конвертируем через ImageMagick / sharp если есть.
//
// Также сравнивает: какие артикулы есть на сайте но нет в инфографике (нет фото)
// и наоборот (есть фото но не используются на сайте)

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SRC_DIR = 'c:/Users/ikoko/Projects/infografika/assets/aura';
const PUB = path.join(ROOT, 'public', 'img', 'products');
const PSORT = path.join(ROOT, 'photos-sorted', '07-Серия-АУРА');

// 1. Артикулы в папке инфографики (все папки кроме служебных _*)
const auraDirs = fs.readdirSync(SRC_DIR).filter(name => {
    if (name.startsWith('_')) return false;
    try { return fs.statSync(path.join(SRC_DIR, name)).isDirectory(); } catch { return false; }
});
console.log(`Артикулов в инфографике: ${auraDirs.length}`);

// 2. Артикулы серии АУРА на сайте
const series = require(path.join(ROOT, 'src', 'data', 'series.json'));
const auraOnSite = new Set();
for (const g of ['switches', 'sockets', 'frames', 'accessories', 'other']) {
    for (const it of (series.aura?.groups?.[g] || [])) {
        auraOnSite.add(it.article);
    }
}
console.log(`АУРА на сайте: ${auraOnSite.size}`);

// 3. Сравнение
const inInfoNotOnSite = auraDirs.filter(a => !auraOnSite.has(a));
const onSiteNoPhoto = [...auraOnSite].filter(a => !auraDirs.includes(a));
console.log(`\nВ папке но нет на сайте (${inInfoNotOnSite.length}): ${inInfoNotOnSite.join(', ') || '—'}`);
console.log(`\nНа сайте но нет фото в папке (${onSiteNoPhoto.length}):`);
onSiteNoPhoto.forEach(a => console.log('  ' + a));

// 4. Удаление старых фото для артикулов АУРЫ (всё что есть на сайте + что есть в папке)
const allArts = new Set([...auraOnSite, ...auraDirs]);
let removed = 0;
function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
for (const art of allArts) {
    const reMain = new RegExp('^' + escapeRe(art) + '\\.(webp|png|jpg|jpeg)$', 'i');
    const reExtra = new RegExp('^' + escapeRe(art) + '_\\d+\\.(webp|png|jpg|jpeg)$', 'i');
    for (const f of fs.readdirSync(PUB)) {
        if (reMain.test(f) || reExtra.test(f)) {
            try { fs.unlinkSync(path.join(PUB, f)); removed++; } catch (e) { }
        }
    }
}
console.log(`\nУдалено старых файлов: ${removed}`);

// 5. Копирование новых _nobg.png → public/img/products/АРТИКУЛ.webp / АРТИКУЛ_2.webp
// PNG → WebP без конвертации (Astro/браузер хорошо отдают .webp по mime, но имя расширения важно)
// Лучше оставить как есть — копировать в .webp с PNG content. Браузер декодирует по магии.
// Точнее — переименуем .png → .webp напрямую: это плохо потому что content всё ещё PNG.
// Простое решение: оставить как PNG, но имя как .webp — НЕТ, не работает.
// Правильно: либо конвертировать через sharp, либо хранить как .png (auto-detect ловит).
// utils/photos.js уже читает .png тоже — так что используем .png.
let copied = 0;
for (const art of auraDirs) {
    const srcDir = path.join(SRC_DIR, art);
    const files = fs.readdirSync(srcDir);
    // Ищем "1 без фона_nobg.png" (главное)
    const main = files.find(f => /1\s*без\s*фона_nobg\.png$/i.test(f));
    // "2 обратная_nobg.png" (обратная сторона)
    const back = files.find(f => /2\s*обратная_nobg\.png$/i.test(f));
    if (main) {
        fs.copyFileSync(path.join(srcDir, main), path.join(PUB, art + '.png'));
        copied++;
    }
    if (back) {
        fs.copyFileSync(path.join(srcDir, back), path.join(PUB, art + '_2.png'));
        copied++;
    }
}
console.log(`\nСкопировано из инфографики: ${copied}`);
