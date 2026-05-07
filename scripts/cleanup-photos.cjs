// После того как ты удалил часть фото в /public/img/products/, этот скрипт:
//  1) Если у товара пропало главное фото (АРТИКУЛ.webp), но остались ракурсы —
//     повышает первый ракурс в главное фото
//  2) Переномеровывает ракурсы по порядку без пропусков (если удалил _3, остался _4 — _4 станет _3)
//
// Запуск: node scripts/cleanup-photos.cjs
//
// После запуска — npm run build && git add -A && git commit + push

const fs = require('fs');
const path = require('path');

const DIR = path.resolve(__dirname, '..', 'public', 'img', 'products');
const files = fs.readdirSync(DIR);

// Группируем по артикулу
const byArt = new Map();
for (const f of files) {
    if (!/\.(webp|png|jpg|jpeg)$/i.test(f)) continue;
    // Сначала пробуем match на ракурс (АРТИКУЛ_N)
    const ext = path.extname(f);
    const base = f.slice(0, -ext.length);
    const m = base.match(/^(.+)_(\d+)$/);
    let art, idx;
    if (m) { art = m[1]; idx = parseInt(m[2], 10); }
    else { art = base; idx = 1; } // главное = индекс 1
    if (!byArt.has(art)) byArt.set(art, []);
    byArt.get(art).push({ file: f, idx, ext });
}

const PRIO = { '.webp': 0, '.png': 1, '.jpg': 2, '.jpeg': 2 };
let renamed = 0, promoted = 0;

for (const [art, items] of byArt) {
    items.sort((a, b) => a.idx - b.idx || (PRIO[a.ext.toLowerCase()] ?? 9) - (PRIO[b.ext.toLowerCase()] ?? 9));
    // Берём по одному файлу на индекс (если случайно есть .png и .webp — приоритет webp)
    const seen = new Set();
    const ordered = [];
    for (const it of items) {
        if (seen.has(it.idx)) continue;
        seen.add(it.idx);
        ordered.push(it);
    }
    // Переномеровка: первый файл должен стать главным (без _N), остальные _2, _3, ...
    for (let i = 0; i < ordered.length; i++) {
        const item = ordered[i];
        const wantedName = i === 0
            ? `${art}${item.ext}`
            : `${art}_${i + 1}${item.ext}`;
        if (item.file === wantedName) continue;
        const src = path.join(DIR, item.file);
        const dst = path.join(DIR, wantedName);
        // Если целевое имя уже занято — пропускаем во избежание перезаписи
        if (fs.existsSync(dst)) continue;
        fs.renameSync(src, dst);
        if (item.idx > 1 && i === 0) promoted++;
        else renamed++;
        console.log(`  ${item.file} → ${wantedName}`);
    }
}

console.log(`\nГотово: повышено в главные ${promoted}, переномеровано ${renamed}`);
