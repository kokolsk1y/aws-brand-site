// Импорт АУРЫ v2 — через photos-sorted/ (sync применит дальше)
//
// 1. Удаляем все артикулы серии АУРА из photos-sorted/07-Серия-АУРА/
//    кроме тех что есть в новой папке инфографики
// 2. Копируем для каждого артикула:
//      <АРТ> 1 без фона_nobg.png → photos-sorted/07-Серия-АУРА/<АРТ>/main.png
//      <АРТ> 2 обратная_nobg.png → photos-sorted/07-Серия-АУРА/<АРТ>/2.png
// 3. Папка _back_only НЕ трогается

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SRC = 'c:/Users/ikoko/Projects/infografika/assets/aura';
const DST = path.join(ROOT, 'photos-sorted', '07-Серия-АУРА');

const auraArts = fs.readdirSync(SRC).filter(name => {
    if (name.startsWith('_')) return false;
    return fs.statSync(path.join(SRC, name)).isDirectory();
});
const newSet = new Set(auraArts);
console.log(`Артикулов в инфографике: ${auraArts.length}`);

// 1. Удаляем папки Ауры которых больше нет
let removedDirs = 0;
if (fs.existsSync(DST)) {
    for (const art of fs.readdirSync(DST)) {
        if (!newSet.has(art)) {
            fs.rmSync(path.join(DST, art), { recursive: true, force: true });
            removedDirs++;
        }
    }
}
console.log(`Удалено старых папок Ауры: ${removedDirs}`);

// 2. Копируем новые / обновляем существующие
fs.mkdirSync(DST, { recursive: true });
let mainCopied = 0, backCopied = 0;
for (const art of auraArts) {
    const srcDir = path.join(SRC, art);
    const dstDir = path.join(DST, art);
    fs.mkdirSync(dstDir, { recursive: true });
    // Удалить всё что было в этой папке
    for (const f of fs.readdirSync(dstDir)) fs.unlinkSync(path.join(dstDir, f));
    const files = fs.readdirSync(srcDir);
    const main = files.find(f => /1\s*без\s*фона_nobg\.png$/i.test(f));
    const back = files.find(f => /2\s*обратная_nobg\.png$/i.test(f));
    if (main) {
        fs.copyFileSync(path.join(srcDir, main), path.join(dstDir, 'main.png'));
        mainCopied++;
    }
    if (back) {
        fs.copyFileSync(path.join(srcDir, back), path.join(dstDir, '2.png'));
        backCopied++;
    }
}
console.log(`Скопировано: main=${mainCopied}, обратная=${backCopied}`);
console.log('\nТеперь запусти: node scripts/sync-photos.cjs');
