// Извлекает из каждой HTML карточки stv39 URL всех фото в галерее.
// Парсит Битрикс-разметку: ищет блок галереи и берёт оригиналы.
// Сохраняет в _pipeline/stv-products.json: [{ slug, razdel, article, name, price, photos:[url], detail_url }]
const fs = require('fs');
const path = require('path');

const tasks = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/html-products-tasks.json');
const aws = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/stv-aws.json');
const artByUrl = new Map(aws.map(x => [x.url.replace(/^http:/, 'https:'), x]));

function extractFromHtml(html, url) {
    // Артикул из <span class="article">...</span> или из <div class="article-value">XXX</div>
    let article = '';
    const m1 = html.match(/Артикул[^<]*<[^>]+>\s*([A-Za-z0-9\-_,\s]+?)\s*</);
    if (m1) article = m1[1].trim();

    // Имя из <h1>...</h1>
    const h1 = html.match(/<h1[^>]*>([^<]+)<\/h1>/);
    const name = h1 ? h1[1].trim() : '';

    // Цена — берём из data-price-value или из блока цены
    let price = '';
    const p1 = html.match(/data-price[^=]*="([0-9]+(?:[.,][0-9]+)?)"/);
    if (p1) price = p1[1];
    else {
        const p2 = html.match(/(\d{1,6})\s*₽/);
        if (p2) price = p2[1];
    }

    // Фото галереи: ищем все <img> с src/data-src, которые ведут на /upload/.../iblock/
    // Битрикс часто использует data-src для lazy + src для thumb.
    // Берём только URL вида /upload/.../iblock/... .webp/.jpg/.png
    const photos = new Set();
    const reImg = /(?:src|data-src|href)\s*=\s*["']([^"']*\/upload\/[^"']+\.(?:webp|jpg|jpeg|png))["']/gi;
    let m;
    while ((m = reImg.exec(html))) {
        let u = m[1];
        if (u.startsWith('//')) u = 'https:' + u;
        else if (u.startsWith('/')) u = 'https://stv39.ru' + u;
        // Исключаем preview/_thumb/иконки
        if (/\/upload\/(?:medialibrary|main\/|iblock\/.{3}\/iblock|favicon|logo)/i.test(u)) continue;
        if (!/\/upload\/.+\/iblock\//i.test(u)) continue;
        photos.add(u);
    }

    return { article, name, price, photos: [...photos] };
}

const out = [];
let ok = 0, miss = 0;
for (const t of tasks) {
    const fp = path.resolve("c:/Users/ikoko/Projects/aws-brand-site", t.file);
    if (!fs.existsSync(fp)) { miss++; continue; }
    const html = fs.readFileSync(fp, 'utf8');
    if (html.length < 5000) { miss++; continue; }
    const data = extractFromHtml(html, t.url);
    // Артикул из прайса по URL — надёжнее
    const fromPrice = artByUrl.get('https://stv39.ru' + t.url);
    const article = fromPrice ? fromPrice.art : data.article;
    const name = fromPrice ? fromPrice.name : data.name;
    const price = data.price || (fromPrice ? fromPrice.price : '');
    out.push({
        slug: t.slug,
        razdel: t.razdel,
        url: 'https://stv39.ru' + t.url,
        article: article || t.slug,
        name: name,
        price: price,
        photos: data.photos
    });
    ok++;
}
fs.writeFileSync('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/stv-products.json', JSON.stringify(out, null, 2));
console.log(`extracted: ok=${ok}, miss=${miss}, total=${out.length}`);
console.log(`avg photos per product: ${(out.reduce((s, x) => s + x.photos.length, 0) / out.length).toFixed(1)}`);
console.log(`без фото: ${out.filter(x => x.photos.length === 0).length}`);
