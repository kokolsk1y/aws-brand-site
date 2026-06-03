// Генератор данных конструктора + блока «Три серии».
// Источник правды: src/data/series.json (цвета/лейблы) + реально лежащие
// combo-webp в public/img/constructor/<series>/ (определяют доступные комбинации).
//
// Пишет public/constructor-data.json — его подгружает src/scripts/main.js
// и строит АДАПТИВНЫЕ кнопки: при смене серии набор цветов и материалов
// рамок перестраивается под то, что реально есть.
//
// Запуск: node scripts/build_constructor_data.cjs   (или хук prebuild)

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SERIES_JSON = path.join(ROOT, 'src/data/series.json');
const COMBO_DIR = path.join(ROOT, 'public/img/constructor');
const OUT = path.join(ROOT, 'public/constructor-data.json');

// Порядок и человекочитаемые названия материалов рамок (по категоризации stv).
const MATERIALS = [
  { key: 'plain',        label: 'Матовая' },   // P50
  { key: 'glossy',       label: 'Глянцевая' }, // PG51
  { key: 'glass',        label: 'Стекло' },     // G50
  { key: 'glass_relief', label: 'Стекло рельеф' }, // G51
  { key: 'aluminum',     label: 'Алюминий' },   // B30
];
const MATERIAL_LABEL = Object.fromEntries(MATERIALS.map(m => [m.key, m.label]));

// Fallback-свотчи (если у цвета в series.json нет поля swatch). Основной
// источник цвета кружков — series.json colors[].swatch (подобран по фото).
const SWATCH = {
  white: '#eceae6', black: '#161616', grey: '#9a9a9a', gold: '#c4a052',
  mahogany: '#6e4636', dark_grey: '#555555', silver: '#b3b8bc', matte_black: '#2b2b2e',
};

const series = JSON.parse(fs.readFileSync(SERIES_JSON, 'utf-8'));

function listCombos(slug) {
  const dir = path.join(COMBO_DIR, slug);
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter(f => f.endsWith('.webp'));
}

// Для серии возвращаем: цвета (только те, у кого есть combo) и по каждому —
// доступные материалы + путь к картинке.
function buildSeries(slug, meta) {
  const files = listCombos(slug);
  const labelByKey = Object.fromEntries((meta.colors || []).map(c => [c.key, c.label]));
  const swatchByKey = Object.fromEntries((meta.colors || []).map(c => [c.key, c.swatch]).filter(([, v]) => v));

  // Разбор имён: "<color>-<material>.webp" (АУРА) или "<color>.webp" (УНО/ДИЗАЙН)
  const byColor = {};            // color -> { material -> imgPath }  (material '' = без рамок-вариаций)
  for (const f of files) {
    const stem = f.replace(/\.webp$/i, '');
    const m = stem.match(/^(.+?)-(plain|glossy|glass_relief|glass|aluminum)$/);
    let color, material;
    if (m) { color = m[1]; material = m[2]; }
    else { color = stem; material = ''; }
    (byColor[color] ||= {})[material] = `/img/constructor/${slug}/${f}`;
  }

  const hasFrames = files.some(f => /-(plain|glossy|glass_relief|glass|aluminum)\.webp$/.test(f));

  // Порядок цветов — как в series.json (colors[]), берём только имеющиеся в combo.
  const order = (meta.colors || []).map(c => c.key);
  const colorKeys = Object.keys(byColor).sort((a, b) => order.indexOf(a) - order.indexOf(b));

  // Обложки одиночного выключателя (для блока «Три серии») — из series.json colors[].img
  const coverByKey = Object.fromEntries(
    (meta.colors || []).filter(c => c.img).map(c => [c.key, c.img])
  );

  // Цвета для UI: все из series.json, у кого есть обложка ИЛИ combo. Порядок — как в series.json.
  const allKeys = (meta.colors || []).map(c => c.key)
    .filter(k => coverByKey[k] || byColor[k]);

  const colors = allKeys.map(key => {
    const combo = byColor[key] || {};
    const mats = Object.keys(combo).filter(Boolean);
    mats.sort((a, b) => MATERIALS.findIndex(x => x.key === a) - MATERIALS.findIndex(x => x.key === b));
    return {
      key,
      label: labelByKey[key] || key,
      swatch: swatchByKey[key] || SWATCH[key] || '#999',
      light: ['white', 'silver'].includes(key),   // нужна обводка у светлого свотча
      cover: coverByKey[key] || null,             // одиночный выключатель (Три серии)
      materials: mats,                            // доступные материалы рамок (конструктор)
      img: combo,                                 // { material|'' : path } (конструктор)
      hasCombo: Object.keys(combo).length > 0,
    };
  });

  return { slug, label: meta.name || slug.toUpperCase(), hasFrames, colors };
}

const out = {
  generatedFrom: 'series.json + public/img/constructor',
  materialLabels: MATERIAL_LABEL,
  materialOrder: MATERIALS.map(m => m.key),
  series: {},
};
// Порядок серий для UI
const ORDER = ['uno', 'aura', 'design'];
for (const slug of ORDER) {
  if (series[slug]) out.series[slug] = buildSeries(slug, series[slug]);
}

fs.writeFileSync(OUT, JSON.stringify(out, null, 2), 'utf-8');

// Короткий отчёт
console.log('Записан', path.relative(ROOT, OUT));
for (const slug of ORDER) {
  const s = out.series[slug];
  if (!s) continue;
  const cols = s.colors.map(c => `${c.key}${c.materials.length ? '['+c.materials.length+']' : ''}`).join(', ');
  console.log(`  ${slug} (рамки:${s.hasFrames ? 'да' : 'нет'}): ${cols}`);
}
