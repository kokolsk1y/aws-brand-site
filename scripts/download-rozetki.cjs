// Скачивание 161 страниц розеток stv (для серий УНО/АУРА/ДИЗАЙН/Стандарт).
// Pause 7 сек между запросами — чтобы не получить бан как в первый раз.
const fs = require('fs');
const path = require('path');
const https = require('https');

const tasks = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/html-rozetki-tasks.json');
const OUT_DIR = 'c:/Users/ikoko/Projects/aws-brand-site/_pipeline/html-rozetki';
fs.mkdirSync(OUT_DIR, { recursive: true });

const sleep = ms => new Promise(r => setTimeout(r, ms));

function fetchOnce(url) {
    return new Promise((resolve) => {
        const req = https.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Accept-Encoding': 'identity',
                'Connection': 'close'
            }
        }, (res) => {
            if ([301, 302].includes(res.statusCode)) { resolve(fetchOnce(res.headers.location)); return; }
            if (res.statusCode !== 200) { resolve(null); return; }
            let buf = [];
            res.on('data', c => buf.push(c));
            res.on('end', () => resolve(Buffer.concat(buf)));
        });
        req.on('error', () => resolve(null));
        req.setTimeout(45000, () => { req.destroy(); resolve(null); });
    });
}

async function fetchRetry(url, tries = 5) {
    const back = [5, 10, 20, 40, 60];
    for (let i = 0; i < tries; i++) {
        const buf = await fetchOnce(url);
        if (buf && buf.length > 5000) return buf;
        await sleep(back[Math.min(i, back.length - 1)] * 1000);
    }
    return null;
}

async function main() {
    console.log('warmup 15 sec...');
    await sleep(15000);
    let ok = 0, fail = 0;
    for (let i = 0; i < tasks.length; i++) {
        const t = tasks[i];
        const fp = path.join(OUT_DIR, path.basename(t.file));
        if (fs.existsSync(fp) && fs.statSync(fp).size > 5000) { ok++; continue; }
        const buf = await fetchRetry('https://stv39.ru' + t.url, 5);
        if (buf) { fs.writeFileSync(fp, buf); ok++; }
        else { fail++; console.log('  FAIL', t.slug); }
        if ((i + 1) % 10 === 0) console.log(`  progress: ${i + 1}/${tasks.length} ok=${ok} fail=${fail}`);
        await sleep(7000);
    }
    console.log(`download-rozetki done: ok=${ok}, fail=${fail}`);
}

main();
