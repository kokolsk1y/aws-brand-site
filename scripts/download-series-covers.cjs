// Скачивает фото 6 одноклавишных выключателей — главные ассеты для блока серий на главной.
// Работает после основного pipeline. Также сохраняет копии как /public/img/series/<slug>-1kl-<color>.webp
// чтобы блок серий на главной их подхватил без ручной правки HTML.

const fs = require('fs');
const path = require('path');
const https = require('https');

const ITEMS = [
    { article: 'A-001W', series: 'aura', color: 'w', url: 'https://stv39.ru/catalog/rozetki_i_vyklyuchateli/vyklyuchatel_1_kl_belyy_a_001w_aura_awsproducts/' },
    { article: 'A-001B', series: 'aura', color: 'b', url: 'https://stv39.ru/catalog/rozetki_i_vyklyuchateli/vyklyuchatel_1_kl_chyernyy_a_001b_aura_awsproducts/' },
    { article: 'U1A-001-1', series: 'uno', color: 'w', url: 'https://stv39.ru/catalog/rozetki_i_vyklyuchateli/vyklyuchatel_1_kl_belyy_u1a_001_1_soft_tach_uno_awsproducts/' },
    { article: 'U2B-001-1', series: 'uno', color: 'b', url: 'https://stv39.ru/catalog/rozetki_i_vyklyuchateli/vyklyuchatel_1_kl_chyernyy_u2b_001_1_soft_tach_uno_awsproducts/' },
    { article: 'A-D001W', series: 'design', color: 'w', url: 'https://stv39.ru/catalog/rozetki_i_vyklyuchateli/vyklyuchatel_1_kl_belyy_a_d001w_dizayn_10a_awsproducts/' },
    { article: 'A-D001B', series: 'design', color: 'b', url: 'https://stv39.ru/catalog/rozetki_i_vyklyuchateli/vyklyuchatel_1_kl_chyernyy_a_d001b_dizayn_10a_awsproducts/' },
];

const PAUSE = 7000;
const RAW_DIR = 'c:/tmp/stv-photos-raw';
const CLEAN_DIR = 'c:/tmp/stv-photos-clean';
fs.mkdirSync(RAW_DIR, { recursive: true });

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function fetchHtml(url) {
    return new Promise((resolve) => {
        const req = https.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Accept-Encoding': 'identity',
                'Connection': 'close'
            }
        }, (res) => {
            if (res.statusCode === 301 || res.statusCode === 302) { resolve(fetchHtml(res.headers.location)); return; }
            if (res.statusCode !== 200) { resolve(null); return; }
            const chunks = [];
            res.on('data', c => chunks.push(c));
            res.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
        });
        req.on('error', () => resolve(null));
        req.setTimeout(30000, () => { req.destroy(); resolve(null); });
    });
}

function fetchBin(url, file) {
    return new Promise((resolve) => {
        const out = fs.createWriteStream(file);
        const req = https.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 Chrome/131.0',
                'Accept': 'image/webp,*/*',
                'Connection': 'close'
            }
        }, (res) => {
            if (res.statusCode === 301 || res.statusCode === 302) { out.close(); fs.unlinkSync(file); return resolve(fetchBin(res.headers.location, file)); }
            if (res.statusCode !== 200) { out.close(); fs.unlinkSync(file); return resolve(false); }
            res.pipe(out);
            out.on('finish', () => out.close(() => resolve(true)));
        });
        req.on('error', () => { try { fs.unlinkSync(file); } catch (e) { } resolve(false); });
        req.setTimeout(30000, () => { req.destroy(); resolve(false); });
    });
}

function pickPhotos(html) {
    // UUID-фильтр (как в extract-v2): берём только фото из bx_item_detail и
    // фильтруем по UUID-префиксу первого файла товара (отсеивает cross-sell).
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
    const own = [...new Set(allUrls.filter(u => u.includes(productUuid)))];
    return own.map(u => u.startsWith('//') ? 'https:' + u : (u.startsWith('/') ? 'https://stv39.ru' + u : u));
}

async function main() {
    console.log('warmup 12 sec...');
    await sleep(12000);

    for (const it of ITEMS) {
        console.log(`→ ${it.article}: загружаю страницу`);
        const html = await fetchHtml(it.url);
        if (!html) { console.log(`  FAIL ${it.article}: страница не открылась`); await sleep(PAUSE); continue; }
        const photos = pickPhotos(html);
        console.log(`  найдено фото: ${photos.length}`);
        if (!photos.length) { await sleep(PAUSE); continue; }
        // Скачиваем до 6 ракурсов
        const list = photos.slice(0, 6);
        for (let i = 0; i < list.length; i++) {
            const ext = (list[i].match(/\.(webp|jpe?g|png)/i) || [, 'webp'])[1].toLowerCase();
            const file = path.join(RAW_DIR, `${it.article}__${i}.${ext}`);
            const ok = await fetchBin(list[i], file);
            if (!ok) console.log(`    fail ${i}`);
            await sleep(400);
        }
        await sleep(PAUSE);
    }
    console.log('download-series-covers done');
}

main();
