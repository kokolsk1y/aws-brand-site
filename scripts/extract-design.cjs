// Extract по UUID для скачанных страниц Дизайна + скачивание фото
const fs = require('fs');
const path = require('path');
const https = require('https');

const tasks = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/html-design-tasks.json');
const sleep = ms => new Promise(r => setTimeout(r, ms));

function dl(url, file) {
    return new Promise(r => {
        const f = fs.createWriteStream(file);
        https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } }, res => {
            if ([301, 302].includes(res.statusCode)) { f.close(); fs.unlinkSync(file); return r(dl(res.headers.location, file)); }
            if (res.statusCode !== 200) { f.close(); fs.unlinkSync(file); return r(false); }
            res.pipe(f);
            f.on('finish', () => f.close(() => r(true)));
        }).on('error', () => { try { fs.unlinkSync(file); } catch (e) { } r(false); });
    });
}

function extractPhotos(html) {
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
    if (!productUuid) return [];
    return [...new Set(allUrls.filter(u => u.includes(productUuid)))]
        .map(u => u.startsWith('//') ? 'https:' + u : (u.startsWith('/') ? 'https://stv39.ru' + u : u));
}

const RAW = 'c:/Users/ikoko/Projects/aws-brand-site/_pipeline/photos-raw';
const products = [];
for (const t of tasks) {
    const fp = path.resolve("c:/Users/ikoko/Projects/aws-brand-site", t.file);
    if (!fs.existsSync(fp)) continue;
    const html = fs.readFileSync(fp, 'utf8');
    if (html.length < 5000) continue;
    const photos = extractPhotos(html);
    products.push({ article: t.article, name: t.name, price: t.price, photos });
}
fs.writeFileSync('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/html-design-products.json', JSON.stringify(products, null, 2));
console.log(`extracted ${products.length}, with photos ${products.filter(p => p.photos.length).length}, avg ${(products.reduce((s, p) => s + p.photos.length, 0) / products.length).toFixed(2)}`);

(async () => {
    let ok = 0, fail = 0, total = 0;
    for (const p of products) {
        if (!p.photos.length) continue;
        const safeArt = p.article.replace(/[^A-Za-z0-9_\-]/g, '_');
        const list = p.photos.slice(0, 6);
        for (let i = 0; i < list.length; i++) {
            total++;
            const ext = (list[i].match(/\.(webp|jpe?g|png)/i) || [, 'webp'])[1].toLowerCase();
            const file = path.join(RAW, `${safeArt}__${i}.${ext}`);
            if (fs.existsSync(file) && fs.statSync(file).size > 1000) { ok++; continue; }
            const r = await dl(list[i], file);
            if (r) ok++; else fail++;
            await sleep(300);
        }
        if (total % 30 === 0) console.log(`progress ${ok}/${total}`);
    }
    console.log(`design photos done: ok=${ok}, fail=${fail}, total=${total}`);
})();
