// Скачивание 66 страниц Дизайна напрямую из прайса (на витрине партнёра их нет)
const fs = require('fs');
const path = require('path');
const https = require('https');

const tasks = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/html-design-tasks.json');
const OUT = 'c:/Users/ikoko/Projects/aws-brand-site/_pipeline/html-design';
fs.mkdirSync(OUT, { recursive: true });
const sleep = ms => new Promise(r => setTimeout(r, ms));

function fetchOnce(url) {
    return new Promise((resolve) => {
        const req = https.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 Chrome/131.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9',
                'Accept-Encoding': 'identity',
                'Connection': 'close'
            }
        }, (res) => {
            if ([301, 302].includes(res.statusCode)) { resolve(fetchOnce(res.headers.location)); return; }
            if (res.statusCode !== 200) { resolve(null); return; }
            let buf = []; res.on('data', c => buf.push(c)); res.on('end', () => resolve(Buffer.concat(buf)));
        });
        req.on('error', () => resolve(null));
        req.setTimeout(45000, () => { req.destroy(); resolve(null); });
    });
}
async function fetchRetry(url, t = 4) {
    const back = [5, 10, 20, 40];
    for (let i = 0; i < t; i++) {
        const buf = await fetchOnce(url);
        if (buf && buf.length > 5000) return buf;
        await sleep(back[Math.min(i, back.length - 1)] * 1000);
    }
    return null;
}
async function main() {
    console.log('warmup 10s...');
    await sleep(10000);
    let ok = 0, fail = 0;
    for (let i = 0; i < tasks.length; i++) {
        const t = tasks[i];
        const fp = path.join(OUT, path.basename(t.file));
        if (fs.existsSync(fp) && fs.statSync(fp).size > 5000) { ok++; continue; }
        const buf = await fetchRetry('https://stv39.ru' + t.url, 4);
        if (buf) { fs.writeFileSync(fp, buf); ok++; }
        else { fail++; console.log('FAIL', t.article); }
        if ((i + 1) % 10 === 0) console.log(`progress ${i + 1}/${tasks.length} ok=${ok}`);
        await sleep(7000);
    }
    console.log(`design pages done: ok=${ok}, fail=${fail}`);
}
main();
