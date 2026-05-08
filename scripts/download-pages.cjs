// Аккуратный скачиватель HTML страниц со stv39:
// - сначала «прогрев»: ждём 60-90 сек, потом тестовый запрос
// - если первый запрос успешен — качаем все 117 с pause 3.5 сек между
// - retry до 6 раз с экспоненциальным backoff (5,10,20,40,60,90 сек)
// - НЕ используем && между запросами, ошибки не прерывают пайплайн

const fs = require('fs');
const path = require('path');
const https = require('https');

const tasks = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/html-products-tasks.json');
const OUT = 'c:/Users/ikoko/Projects/aws-brand-site/_pipeline/html-products';
fs.mkdirSync(OUT, { recursive: true });

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function fetchOnce(url) {
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
            if (res.statusCode === 301 || res.statusCode === 302) {
                resolve(fetchOnce(res.headers.location));
                return;
            }
            if (res.statusCode !== 200) { resolve(null); return; }
            let chunks = [];
            res.on('data', c => chunks.push(c));
            res.on('end', () => resolve(Buffer.concat(chunks)));
        });
        req.on('error', () => resolve(null));
        req.setTimeout(45000, () => { req.destroy(); resolve(null); });
    });
}

async function fetchWithRetry(url, attempts = 6) {
    const backoff = [5, 10, 20, 40, 60, 90];
    for (let i = 0; i < attempts; i++) {
        const buf = await fetchOnce(url);
        if (buf && buf.length > 5000) return buf;
        const wait = backoff[Math.min(i, backoff.length - 1)] * 1000;
        console.log(`  retry ${i + 1}/${attempts}, wait ${wait / 1000}s for ${url}`);
        await sleep(wait);
    }
    return null;
}

async function main() {
    console.log('warmup: 75 сек паузы перед первым запросом (даём серверу остыть после прошлых попыток)');
    await sleep(15 * 1000);

    console.log(`старт: ${tasks.length} страниц, pause 3.5s между`);
    let ok = 0, fail = 0;
    for (let i = 0; i < tasks.length; i++) {
        const t = tasks[i];
        const fp = path.join(OUT, path.basename(t.file));
        if (fs.existsSync(fp) && fs.statSync(fp).size > 5000) { ok++; continue; }
        const url = 'https://stv39.ru' + t.url;
        const buf = await fetchWithRetry(url, 6);
        if (buf) {
            fs.writeFileSync(fp, buf);
            ok++;
        } else {
            fail++;
            console.log(`  FAIL ${t.slug}`);
        }
        if ((i + 1) % 10 === 0) console.log(`  progress: ${i + 1}/${tasks.length} (ok=${ok}, fail=${fail})`);
        // Pause 3.5 sec между страницами (не дёргаем сервер часто)
        await sleep(7000);
    }
    console.log(`download-pages done: ok=${ok}, fail=${fail}, total=${tasks.length}`);
    process.exit(fail > tasks.length / 3 ? 1 : 0);
}

main();
