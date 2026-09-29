import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const sourceRoot = process.argv[2] || 'C:/Users/ikoko/Projects/infografika/data';
const sourceFiles = ['standard-products.json', 'standard-sd5-products.json'];
const contentPath = path.join(root, 'src/data/product_content.json');
const descriptionsPath = path.join(root, 'src/data/descriptions.json');

const readJson = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));
const products = sourceFiles.flatMap((file) => readJson(path.join(sourceRoot, file)).products || []);
const content = readJson(contentPath);
const descriptions = readJson(descriptionsPath);

function normalizeSourceText(article, text) {
  let value = String(text || '').replace(/\r/g, '').trim();
  if (article === 'SD-P1001B') value = value.replaceAll('SD-P1002B', 'SD-P1001B');
  if (article === 'SD-P1013W') {
    value = value
      .replaceAll('SD-P1013B', 'SD-P1013W')
      .replace(/ч[её]рная/gi, 'белая')
      .replace(/ч[её]рный/gi, 'белый')
      .replace(/ч[её]рном/gi, 'белом')
      .replace(/ч[её]рного/gi, 'белого')
      .replace(/ч[её]рную/gi, 'белую')
      .replace(/ч[её]рные/gi, 'белые');
  }
  return value;
}

function splitDescription(text) {
  return text.split(/\n\s*Характеристики:\s*\n/i, 2);
}

function parseSpecs(article, characteristics, meta) {
  const rows = [['Артикул', article]];
  const seen = new Set(['Артикул']);
  for (const raw of String(characteristics || '').split('\n')) {
    const line = raw.replace(/^\s*[–—•-]\s*/, '').trim();
    const match = line.match(/^([^:]{2,70}):\s*(.+)$/);
    if (!match) continue;
    const key = match[1].trim();
    const value = match[2].trim();
    if (!value || seen.has(key)) continue;
    rows.push([key, value]);
    seen.add(key);
  }

  if (!seen.has('Серия')) rows.splice(1, 0, ['Серия', 'Стандарт']);
  if (meta?.dims_known && ![...seen].some((key) => /размер/i.test(key))) {
    rows.push(['Размеры (Ш×В×Г)', `${meta.dim_width_mm}×${meta.dim_height_mm}×${meta.dim_depth_mm} мм`]);
  }
  rows.push(['Гарантия', '2 года']);
  rows.push(['Сертификация', 'EAC, ГОСТ']);
  rows.push(['Бренд', 'AWSProducts']);
  return rows;
}

for (const product of products) {
  const source = normalizeSourceText(product.article, product.description);
  const [descriptionPart, characteristicsPart = ''] = splitDescription(source);
  const description = descriptionPart.replace(/\n{3,}/g, '\n\n').trim();
  content[product.article] = {
    specs: parseSpecs(product.article, characteristicsPart, product.preparsed),
    description,
  };
  descriptions[product.article] = description;
}

const articles = new Set(products.map((product) => product.article));
if (articles.size !== 57) throw new Error(`Ожидалось 57 уникальных SKU, получено ${articles.size}`);

fs.writeFileSync(contentPath, `${JSON.stringify(content, null, 2)}\n`, 'utf8');
fs.writeFileSync(descriptionsPath, `${JSON.stringify(descriptions, null, 2)}\n`, 'utf8');
console.log(`Импортировано ${articles.size} описаний и наборов характеристик СТАНДАРТ.`);
