// Финальная раскладка ВСЕХ фото из 3 источников + перестройка products.json + series.json
//
// Источники:
//   _pipeline/stv-products-v2.json — 117 не-розеточных (категории)
//   _pipeline/html-rozetki-products.json — 161 розеточных (серии: УНО/АУРА/Стандарт)
//   _pipeline/html-design-products.json — 66 дизайн
//
// Что делает:
//   1. Раскладывает все фото в /public/img/products/АРТИКУЛ.webp + АРТИКУЛ_2/3/...webp
//   2. Перестраивает public/products.json (категории)
//   3. Перестраивает src/data/series.json (серии: aura/uno/design)
//   4. ФИЛЬТР серий: только Выключатель/Розетка/Рамка
//   5. Не трогает SN-222415.png (используется в advantages)

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SRC = 'c:/Users/ikoko/Projects/aws-brand-site/_pipeline/photos-clean';
const DST = path.join(ROOT, 'public', 'img', 'products');
fs.mkdirSync(DST, { recursive: true });

const cat = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/stv-products-v2.json');
const roz = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/html-rozetki-products.json');
const dz = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/html-design-products.json');

function safeArt(a) { return String(a).replace(/[^A-Za-z0-9_\-]/g, '_'); }

// === 1. Раскладка фото ===
function placePhotos(items) {
    let placed = 0, missing = 0;
    for (const p of items) {
        if (!p.photos || !p.photos.length) continue;
        const sa = safeArt(p.article);
        for (let i = 0; i < p.photos.length; i++) {
            const srcFile = path.join(SRC, `${sa}__${i}.webp`);
            if (!fs.existsSync(srcFile)) { missing++; continue; }
            const dstName = i === 0 ? `${p.article}.webp` : `${p.article}_${i + 1}.webp`;
            fs.copyFileSync(srcFile, path.join(DST, dstName));
            placed++;
        }
    }
    return { placed, missing };
}

const cats = placePhotos(cat);
const rozs = placePhotos(roz);
const dzs = placePhotos(dz);
console.log('Раскладка: категории', cats, ', розетки', rozs, ', дизайн', dzs);

// === 2. Перестройка products.json ===
const RAZDEL_MAP = {
    'udliniteli_bytovye_i_sadovye': 'udl_home',
    'udliniteli_sadovye': 'udl_garden',
    'professionalnye_razemy': 'power',
    'kabelnye_klemmniki_soediniteli_i_kolodki': 'clamps',
    'patch_kordy_shnury_i_zaryadniki': 'patch',
    'kabel_svyazi_kompyuternyy_i_televizionnyy': 'cable'
};
const old = require('c:/Users/ikoko/Projects/aws-brand-site/public/products.json');
const fresh = {};
for (const k of Object.keys(old)) fresh[k] = { title: old[k].title, sub: old[k].sub, items: [] };
for (const p of cat) {
    const key = RAZDEL_MAP[p.razdel];
    if (!key || !fresh[key]) continue;
    let target = key;
    if (p.razdel === 'udliniteli_bytovye_i_sadovye') {
        target = /садов/i.test(p.name) ? 'udl_garden' : 'udl_home';
    }
    if (!fresh[target]) continue;
    fresh[target].items.push({
        article: p.article,
        name: p.name,
        photo: `img/products/${p.article}.webp`,
        price: p.price ? Number(p.price) : null,
        description_raw: p.description || null
    });
}
for (const k of Object.keys(fresh)) fresh[k].items.sort((a, b) => a.article.localeCompare(b.article));
fs.writeFileSync(path.join(ROOT, 'public', 'products.json'), JSON.stringify(fresh, null, 2));
const catSummary = Object.entries(fresh).map(([k, v]) => `${k}:${v.items.length}`).join(' ');
console.log('products.json:', catSummary);

// === 3. Перестройка series.json ===
// Соответствие серий по артикулу/названию:
//   aura: ^A-(?!D) или /Аура/i
//   design: ^A-D или /Дизайн/i
//   uno: ^U[12] или /Уно/i или /Софт-тач/i
//   stnd: ^SD или /Стандарт/i (пока не используем)
function detectSeries(p) {
    const a = p.article || '';
    const n = p.name || '';
    if (/^A-D/i.test(a) || /дизайн/i.test(n)) return 'design';
    if (/^U[12]/i.test(a) || /уно/i.test(n) || /софт-тач/i.test(n)) return 'uno';
    if (/^A-/i.test(a) || /аура/i.test(n)) return 'aura';
    return null; // пропускаем Стандарт и прочее
}
function detectGroup(p) {
    const n = p.name || '';
    if (/^Выключатель/i.test(n)) return 'switches';
    if (/^Розетка/i.test(n)) return 'sockets';
    if (/^Рамка/i.test(n)) return 'frames';
    return null; // отсеиваем накладки/выводы/диммеры/etc
}
function detectColor(name) {
    if (/чёрн|черн/i.test(name)) return 'black';
    if (/бел/i.test(name)) return 'white';
    if (/сер/i.test(name)) return 'gray';
    if (/золот/i.test(name)) return 'gold';
    return null;
}
// Сжимаем имя — убираем артикул и Серию из конца
function shortName(n) {
    return n
        .replace(/\s*\(?AWSPRODUCTS\)?/gi, '')
        .replace(/\s*AWSproducts?/gi, '')
        .replace(/"[^"]*"/g, '')
        .replace(/[A-Z]\d+\S*/g, '')
        .replace(/\s+/g, ' ')
        .trim();
}

const oldSeries = require('c:/Users/ikoko/Projects/aws-brand-site/src/data/series.json');
const allSeriesItems = [...roz, ...dz];
const series = {
    uno: { ...oldSeries.uno, groups: { switches: [], sockets: [], frames: [], accessories: [], other: [] } },
    aura: { ...oldSeries.aura, groups: { switches: [], sockets: [], frames: [], accessories: [], other: [] } },
    design: { ...oldSeries.design, groups: { switches: [], sockets: [], frames: [], accessories: [], other: [] } }
};
let inSeries = 0, filtered = 0;
for (const p of allSeriesItems) {
    const sl = detectSeries(p);
    const gr = detectGroup(p);
    if (!sl || !gr || !series[sl]) { filtered++; continue; }
    series[sl].groups[gr].push({
        article: p.article,
        name: shortName(p.name),
        color: detectColor(p.name),
        price: p.price ? Number(p.price) : null
    });
    inSeries++;
}
// Сортировка по артикулу
for (const sl of Object.keys(series)) {
    for (const gr of Object.keys(series[sl].groups)) {
        series[sl].groups[gr].sort((a, b) => a.article.localeCompare(b.article));
    }
}
fs.writeFileSync(path.join(ROOT, 'src', 'data', 'series.json'), JSON.stringify(series, null, 2));
console.log(`series.json: в серии ${inSeries}, отфильтровано (не Выкл/Роз/Рамка) ${filtered}`);
for (const [k, s] of Object.entries(series)) {
    console.log(`  ${k}: switches=${s.groups.switches.length}, sockets=${s.groups.sockets.length}, frames=${s.groups.frames.length}`);
}
