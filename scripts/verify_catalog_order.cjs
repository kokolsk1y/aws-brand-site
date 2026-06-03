// Проверка: воспроизводит логику src/utils/catalog.js на series.json + реальных
// файлах public/img/products и печатает видимый/отсортированный каталог.
// Цель — глазами свериться, что фильтр по фото, сортировка (тип→цвет) и отсев
// махагона работают ДО визуальной проверки на сайте.
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const series = JSON.parse(fs.readFileSync(path.join(ROOT, 'src/data/series.json'), 'utf-8'));
const FILES = fs.readdirSync(path.join(ROOT, 'public/img/products'));

function hasPhoto(article) {
  const safe = article.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp('^' + safe + '\\.(webp|png|jpg|jpeg)$', 'i');
  return FILES.some(f => re.test(f));
}
const keysCount = n => { const m = n.match(/(\d+)\s*-?\s*кл(?![а-яё])/i); return m ? +m[1] : 1; };
const postsCount = n => { if (/для двойной розетки/i.test(n)) return 90; const m = n.match(/(\d+)\s*-\s*я(?![а-яё])/i); return m ? +m[1] : 1; };
const orient = n => /вертикальн/i.test(n) ? 1 : 0;
const swFunc = n => { n = n.toLowerCase();
  if (/звонк/.test(n)) return 6; if (/жалюзи/.test(n)) return 5;
  if (/перекрёстн|перекрестн/.test(n)) return 4;
  if (/проходн/.test(n)) return /подсветк/.test(n) ? 3 : 2;
  if (/подсветк/.test(n)) return 1; return 0; };
const skType = n => { n = n.toLowerCase();
  if (/для двойной розетки/.test(n)) return 90;
  if (/rj45/.test(n) && /tv|тв/.test(n)) return 5;
  if (/rj45/.test(n)) return 4; if (/\btv\b|телевиз|тв\b/.test(n)) return 3;
  if (/usb|type\s*c/.test(n)) return 2; if (/с крышкой/.test(n)) return 1; return 0; };
const skSize = n => { const m = n.match(/(\d+)\s*-\s*я(?![а-яё])/i); return m ? +m[1] : 1; };

function cmp(groupKey, order) {
  const cr = c => { const i = order.indexOf(c); return i === -1 ? 999 : i; };
  const by = (...fns) => (a, b) => { for (const f of fns) { const d = f(a) - f(b); if (d) return d; } return a.article.localeCompare(b.article, 'ru'); };
  if (groupKey === 'switches') return by(x => keysCount(x.name), x => swFunc(x.name), x => cr(x.color));
  if (groupKey === 'sockets') return by(x => skType(x.name), x => skSize(x.name), x => cr(x.color));
  if (groupKey === 'frames') return by(x => postsCount(x.name), x => orient(x.name), x => cr(x.color));
  return by(x => cr(x.color));
}

for (const slug of ['uno', 'aura', 'design']) {
  const s = series[slug];
  const order = s.colors.map(c => c.key);
  console.log(`\n${'='.repeat(70)}\n${s.name} (${slug})`);
  // палитра
  const present = new Set();
  for (const gk of Object.keys(s.groups)) for (const it of s.groups[gk]) if (it.color && hasPhoto(it.article)) present.add(it.color);
  const palette = s.colors.filter(c => present.has(c.key) && c.img).map(c => c.label);
  console.log(`Палитра (видимые цвета): ${palette.join(', ')}`);
  console.log(`Махагон в палитре: ${palette.includes('Махагон') ? '❌ ДА (ошибка!)' : '✅ нет'}`);
  for (const gk of ['switches', 'sockets', 'frames']) {
    const all = s.groups[gk] || [];
    const vis = all.filter(it => hasPhoto(it.article)).sort(cmp(gk, order));
    console.log(`\n  ${gk}: всего ${all.length}, с фото ${vis.length}, скрыто ${all.length - vis.length}`);
    vis.forEach(it => console.log(`     ${it.name}  [${it.color}]  <${it.article}>`));
  }
}
