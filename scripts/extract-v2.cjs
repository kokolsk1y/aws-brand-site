// V2 — извлекает только «свои» фото товара по UUID-префиксу.
// Битрикс именует файлы как UUID_товара_UUID_фото. Берём первый файл из главной
// галереи (.bx_item_detail), вытаскиваем UUID товара, фильтруем по нему все остальные.
// Также вытаскивает description и specs из той же страницы.

const fs = require('fs');
const path = require('path');

const tasks = require('c:/tmp/stv-cards-tasks.json');
const aws = require('c:/tmp/stv-aws.json');
const artByUrl = new Map(aws.map(x => [x.url.replace(/^http:/, 'https:'), x]));

function decodeHtmlEntities(s) {
    return s
        .replace(/&nbsp;/g, ' ')
        .replace(/&amp;/g, '&')
        .replace(/&quot;/g, '"')
        .replace(/&#?(\w+);/g, (_, c) => {
            if (c[0] === 'x') return String.fromCharCode(parseInt(c.slice(1), 16));
            if (/^\d+$/.test(c)) return String.fromCharCode(+c);
            const named = { lt: '<', gt: '>', laquo: '«', raquo: '»', mdash: '—', ndash: '–', hellip: '…' };
            return named[c] || _;
        });
}

function stripTags(s) {
    return decodeHtmlEntities(s.replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim();
}

function extractFromHtml(html) {
    // 1) Главная галерея — между bx_item_detail и первой prod-carousel/related
    const start = html.indexOf('bx_item_detail');
    const endCands = ['prod-carousel', 'products-list', 'similar-products'].map(s => html.indexOf(s, start)).filter(n => n > start);
    const end = endCands.length ? Math.min(...endCands) : html.length;
    const block = html.slice(start, end);

    // 2) Извлекаем все URL фото в этом блоке
    const allUrls = [...block.matchAll(/\/upload\/[^"'\s]+\.(?:webp|jpg|jpeg|png)/gi)].map(m => m[0]);
    // 3) Находим UUID-префикс товара по первому файлу с UUID-паттерном
    let productUuid = null;
    for (const u of allUrls) {
        const fname = u.split('/').pop();
        const m = fname.match(/^([a-f0-9]{8}_[a-f0-9]{4}_[a-f0-9]{4}_[a-f0-9]{4}_[a-f0-9]+)_/i);
        if (m) { productUuid = m[1]; break; }
    }
    let photos = [];
    if (productUuid) {
        photos = [...new Set(allUrls.filter(u => u.includes(productUuid)))];
    }
    // Полные URL
    photos = photos.map(u => u.startsWith('//') ? 'https:' + u : (u.startsWith('/') ? 'https://stv39.ru' + u : u));

    // 4) Описание — обычно в блоке с классом .detail-text или после <h2>Описание
    let description = '';
    const dm = html.match(/(?:Описание|описание товара)[\s\S]{0,3000}?<(?:p|div)[^>]*>([\s\S]+?)<\/(?:p|div)>/i);
    if (dm) description = stripTags(dm[1]).slice(0, 800);
    // Альтернативный вариант — блок с itemprop="description"
    if (!description) {
        const im = html.match(/itemprop=["']description["'][^>]*>([\s\S]+?)<\/[^>]+>/i);
        if (im) description = stripTags(im[1]).slice(0, 800);
    }

    // 5) Характеристики — таблица с tr/td
    const specs = [];
    const tableMatch = html.match(/(?:Характеристики|характеристики товара)[\s\S]{0,200}?<table[^>]*>([\s\S]+?)<\/table>/i);
    if (tableMatch) {
        const rows = tableMatch[1].matchAll(/<tr[^>]*>([\s\S]+?)<\/tr>/gi);
        for (const r of rows) {
            const cells = [...r[1].matchAll(/<t[hd][^>]*>([\s\S]+?)<\/t[hd]>/gi)].map(c => stripTags(c[1]));
            if (cells.length >= 2 && cells[0] && cells[1]) {
                specs.push([cells[0], cells[1]]);
            }
        }
    }
    // Альтернатива — блоки <dl>
    if (!specs.length) {
        const dl = html.matchAll(/<dt[^>]*>([\s\S]+?)<\/dt>\s*<dd[^>]*>([\s\S]+?)<\/dd>/gi);
        for (const m of dl) {
            const k = stripTags(m[1]); const v = stripTags(m[2]);
            if (k && v) specs.push([k, v]);
        }
    }

    return { photos, description, specs, productUuid };
}

const out = [];
for (const t of tasks) {
    const fp = path.join('c:/tmp', t.file);
    if (!fs.existsSync(fp)) continue;
    const html = fs.readFileSync(fp, 'utf8');
    if (html.length < 5000) continue;
    const data = extractFromHtml(html);
    const fromPrice = artByUrl.get('https://stv39.ru' + t.url);
    out.push({
        slug: t.slug,
        razdel: t.razdel,
        url: 'https://stv39.ru' + t.url,
        article: fromPrice ? fromPrice.art : t.slug,
        name: fromPrice ? fromPrice.name : '',
        price: fromPrice ? fromPrice.price : '',
        productUuid: data.productUuid,
        photos: data.photos,
        description: data.description,
        specs: data.specs
    });
}

fs.writeFileSync('c:/tmp/stv-products-v2.json', JSON.stringify(out, null, 2));
const stats = {
    total: out.length,
    withPhotos: out.filter(x => x.photos.length > 0).length,
    avgPhotos: (out.reduce((s, x) => s + x.photos.length, 0) / out.length).toFixed(2),
    withDesc: out.filter(x => x.description).length,
    withSpecs: out.filter(x => x.specs.length > 0).length
};
console.log(JSON.stringify(stats, null, 2));
