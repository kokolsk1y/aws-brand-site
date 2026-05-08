// Восстанавливает имена из исходных stv данных + убирает ТОЛЬКО артикул
// (без затрагивания IP44/IP67/220В/RJ45 и т.п.)

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');

const stvCat = require(path.join(ROOT, '_pipeline', 'stv-products-v2.json'));
const stvRoz = require(path.join(ROOT, '_pipeline', 'html-rozetki-products.json'));
const stvDz = require(path.join(ROOT, '_pipeline', 'html-design-products.json'));

// Map: article → name из stv
const stvNames = new Map();
for (const arr of [stvCat, stvRoz, stvDz]) {
    for (const p of arr) {
        if (p.article && p.name) stvNames.set(p.article, p.name);
    }
}

// Точный regex ТОЛЬКО для артикулов AWS (не зацепит IP44/RJ45/PE+N)
const ART_RE = /\s+\b(?:A-D|A|U[12][AB]?|SN|SLN|AWS|SD|[PG]50)-[A-Z0-9,\-]*\d[A-Z0-9,\-]*\b/g;

function cleanName(n) {
    if (!n) return n;
    return n
        .replace(/\s*\(?AWSPRODUCTS\)?/gi, '')
        .replace(/\s*AWSproducts?/gi, '')
        .replace(/"[^"]*"/g, '')
        .replace(ART_RE, '')
        .replace(/\s*,\s*$/, '')   // запятая в конце
        .replace(/\s+/g, ' ')
        .trim();
}

// Применяем к series.json
const seriesPath = path.join(ROOT, 'src', 'data', 'series.json');
const series = JSON.parse(fs.readFileSync(seriesPath, 'utf8'));
let fixed = 0;
for (const sl of Object.keys(series)) {
    if (!series[sl].groups) continue;
    for (const gr of Object.keys(series[sl].groups)) {
        for (const it of series[sl].groups[gr]) {
            const orig = stvNames.get(it.article);
            if (orig) {
                const clean = cleanName(orig);
                if (clean !== it.name) { it.name = clean; fixed++; }
            }
        }
    }
}
fs.writeFileSync(seriesPath, JSON.stringify(series, null, 2));

// products.json
const prodPath = path.join(ROOT, 'public', 'products.json');
const prod = JSON.parse(fs.readFileSync(prodPath, 'utf8'));
for (const k of Object.keys(prod)) {
    for (const it of (prod[k].items || [])) {
        const orig = stvNames.get(it.article);
        if (orig) {
            const clean = cleanName(orig);
            if (clean !== it.name) { it.name = clean; fixed++; }
        }
    }
}
fs.writeFileSync(prodPath, JSON.stringify(prod, null, 2));

console.log('Восстановлено имён:', fixed);
console.log('Power пример:', JSON.stringify(prod.power.items[0]?.name));
console.log('Аура пример:', JSON.stringify(series.aura?.groups?.switches?.[0]?.name));
console.log('Кабель пример:', JSON.stringify(prod.cable.items[0]?.name));
