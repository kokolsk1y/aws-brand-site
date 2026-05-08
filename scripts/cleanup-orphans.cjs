// Удаляет все артикулы из 99-Без-категории + связанные файлы во всех местах
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const ORPHAN = path.join(ROOT, 'photos-sorted', '99-Без-категории');
if (!fs.existsSync(ORPHAN)) { console.log('Папка orphans уже отсутствует'); process.exit(0); }

const arts = fs.readdirSync(ORPHAN);
console.log(`Удаляю файлы для ${arts.length} артикулов`);

function safeArt(a) { return a.replace(/[^A-Za-z0-9_\-]/g, '_'); }
function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

const PUB = path.join(ROOT, 'public', 'img', 'products');
const CLEAN = path.join(ROOT, '_pipeline', 'photos-clean');
const RAW = path.join(ROOT, '_pipeline', 'photos-raw');

let pub = 0, cl = 0, rw = 0;
for (const art of arts) {
    const sa = safeArt(art);
    const reArtNum = new RegExp('^' + escapeRe(art) + '_\\d+\\.(webp|png|jpg|jpeg)$', 'i');
    const reArtMain = new RegExp('^' + escapeRe(art) + '\\.(webp|png|jpg|jpeg)$', 'i');
    const reSafe = new RegExp('^' + escapeRe(sa) + '__\\d+\\.(webp|png|jpg|jpeg)$', 'i');

    if (fs.existsSync(PUB)) {
        for (const f of fs.readdirSync(PUB)) {
            if (reArtMain.test(f) || reArtNum.test(f)) {
                try { fs.unlinkSync(path.join(PUB, f)); pub++; } catch (e) { }
            }
        }
    }
    if (fs.existsSync(CLEAN)) {
        for (const f of fs.readdirSync(CLEAN)) {
            if (reSafe.test(f)) {
                try { fs.unlinkSync(path.join(CLEAN, f)); cl++; } catch (e) { }
            }
        }
    }
    if (fs.existsSync(RAW)) {
        for (const f of fs.readdirSync(RAW)) {
            if (reSafe.test(f)) {
                try { fs.unlinkSync(path.join(RAW, f)); rw++; } catch (e) { }
            }
        }
    }
}

fs.rmSync(ORPHAN, { recursive: true, force: true });
console.log(`Удалено: public=${pub}, clean=${cl}, raw=${rw}`);
console.log('Папка 99-Без-категории удалена');
