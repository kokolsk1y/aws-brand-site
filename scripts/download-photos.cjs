// Скачивает все фото из stv-products.json в _pipeline/photos-raw/<ARTICLE>__<idx>.webp
// idx = 0 для главного, 1..N для дополнительных
const fs = require('fs');
const path = require('path');
const https = require('https');

const products = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/stv-products.json');
const OUT = 'c:/Users/ikoko/Projects/aws-brand-site/_pipeline/photos-raw';
fs.mkdirSync(OUT, { recursive: true });

function safeArt(a) { return String(a).replace(/[^A-Za-z0-9_\-]/g, '_'); }

function dl(url, file) {
    return new Promise((resolve) => {
        const f = fs.createWriteStream(file);
        const req = https.get(url, { headers: { 'User-Agent': 'Mozilla/5.0' } }, (res) => {
            if (res.statusCode === 301 || res.statusCode === 302) {
                f.close(); fs.unlinkSync(file);
                return resolve(dl(res.headers.location, file));
            }
            if (res.statusCode !== 200) { f.close(); fs.unlinkSync(file); return resolve(false); }
            res.pipe(f);
            f.on('finish', () => f.close(() => resolve(true)));
        });
        req.on('error', () => { try { fs.unlinkSync(file); } catch (e) { } resolve(false); });
        req.setTimeout(30000, () => { req.destroy(); resolve(false); });
    });
}

async function main() {
    let total = 0, ok = 0, fail = 0;
    for (const p of products) {
        if (!p.photos.length) continue;
        const art = safeArt(p.article);
        // Ограничим до 6 фото на товар (потом отфильтруем)
        const list = p.photos.slice(0, 6);
        for (let i = 0; i < list.length; i++) {
            total++;
            const ext = (list[i].match(/\.(webp|jpe?g|png)/i) || [, 'webp'])[1].toLowerCase();
            const file = path.join(OUT, `${art}__${i}.${ext}`);
            if (fs.existsSync(file) && fs.statSync(file).size > 1000) { ok++; continue; }
            const r = await dl(list[i], file);
            if (r) ok++; else fail++;
            // pause 0.3s
            await new Promise(r => setTimeout(r, 300));
            if (total % 25 === 0) console.log(`  progress ${ok}/${total}`);
        }
    }
    console.log(`download: ok=${ok}, fail=${fail}, total=${total}`);
}
main();
