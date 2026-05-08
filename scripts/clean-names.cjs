// Удаляет артикул из всех имён в series.json и products.json
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');

function clean(n) {
    if (!n) return n;
    return n
        .replace(/\s*\(?AWSPRODUCTS\)?/gi, '')
        .replace(/\s*AWSproducts?/gi, '')
        .replace(/"[^"]*"/g, '')
        // Артикулы: A-001W, A-D025GR, U1A-001-1, U2B-001-1, SLN-0142, SN-222415, AWS-13010, AWS-H05K-1,5
        .replace(/\s+[A-ZА-Я][A-ZА-Я0-9\-]*\d[A-ZА-Я0-9\-,]*\b/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

let fixed = 0;

// series.json
const seriesPath = path.join(ROOT, 'src', 'data', 'series.json');
const series = JSON.parse(fs.readFileSync(seriesPath, 'utf8'));
for (const sl of Object.keys(series)) {
    if (!series[sl].groups) continue;
    for (const gr of Object.keys(series[sl].groups)) {
        for (const it of series[sl].groups[gr]) {
            const old = it.name;
            it.name = clean(old);
            if (it.name !== old) fixed++;
        }
    }
}
fs.writeFileSync(seriesPath, JSON.stringify(series, null, 2));

// products.json
const prodPath = path.join(ROOT, 'public', 'products.json');
const prod = JSON.parse(fs.readFileSync(prodPath, 'utf8'));
for (const k of Object.keys(prod)) {
    for (const it of (prod[k].items || [])) {
        const old = it.name;
        it.name = clean(old);
        if (it.name !== old) fixed++;
    }
}
fs.writeFileSync(prodPath, JSON.stringify(prod, null, 2));

console.log('Очищено имён:', fixed);
console.log('Пример Аура:', JSON.stringify(series.aura?.groups?.switches?.[0]?.name));
console.log('Пример Удлинитель:', JSON.stringify(prod.udl_home?.items?.[0]?.name));
