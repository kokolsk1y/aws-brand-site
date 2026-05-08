// Extract по UUID для скачанных розеточных страниц + скачивание фото.
// Похож на extract-v2 но для другой категории.

const fs = require('fs');
const path = require('path');
const https = require('https');

const tasks = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/html-rozetki-tasks.json');
const aws = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/stv-aws.json');
const artByUrl = new Map(aws.map(x => [x.url.replace(/^http:/, 'https:'), x]));

function decodeHtmlEntities(s) {
    return s.replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&quot;/g, '"');
}
function stripTags(s) { return decodeHtmlEntities(s.replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim(); }

function extractFromHtml(html) {
    const start = html.indexOf('bx_item_detail');
    const endCands = ['prod-carousel', 'products-list', 'similar-products'].map(s => html.indexOf(s, start)).filter(n => n > start);
    const end = endCands.length ? Math.min(...endCands) : html.length;
    const block = html.slice(start, end);
    const allUrls = [...block.matchAll(/\/upload\/[^"'\s]+\.(?:webp|jpg|jpeg|png)/gi)].map(m => m[0]);
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
    photos = photos.map(u => u.startsWith('//') ? 'https:' + u : (u.startsWith('/') ? 'https://stv39.ru' + u : u));
    let description = '';
    const dm = html.match(/(?:Описание)[\s\S]{0,3000}?<(?:p|div)[^>]*>([\s\S]+?)<\/(?:p|div)>/i);
    if (dm) description = stripTags(dm[1]).slice(0, 800);
    return { photos, description, productUuid };
}

const out = [];
for (const t of tasks) {
    const fp = path.resolve("c:/Users/ikoko/Projects/aws-brand-site", t.file);
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
        description: data.description
    });
}
fs.writeFileSync('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/html-rozetki-products.json', JSON.stringify(out, null, 2));
console.log(`extracted ${out.length}, with photos ${out.filter(x => x.photos.length).length}, avg photos ${(out.reduce((s, x) => s + x.photos.length, 0) / out.length).toFixed(2)}`);
console.log('design articles with photos:', out.filter(x => /^A-D/i.test(x.article) && x.photos.length).length, '/', out.filter(x => /^A-D/i.test(x.article)).length);
