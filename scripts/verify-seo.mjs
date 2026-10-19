import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { parse, serialize } from 'parse5';
import { SITE, canonicalUrl, absoluteUrl, serializeSchema, searchName, productSearchMetadata } from '../src/utils/seo.js';

const args = process.argv.slice(2);
const argument = key => args.includes(key) ? args[args.indexOf(key) + 1] : undefined;
const out = path.resolve(argument('--out-dir') || 'dist');
const baseline = argument('--baseline') && path.resolve(argument('--baseline'));
const protectedManifest = argument('--protected-manifest');
const errors = [];
const warnings = [];
const hash = data => crypto.createHash('sha256').update(data).digest('hex');
const read = filename => fs.readFileSync(filename, 'utf8');
const json = filename => JSON.parse(read(filename));
const attr = (node, name) => node?.attrs?.find(item => item.name === name)?.value;
const text = node => node?.nodeName === '#text' ? node.value : (node?.childNodes || []).map(text).join('');
const hasClass = (node, name) => (attr(node, 'class') || '').split(/\s+/).includes(name);
function walk(node) { return [node, ...(node.childNodes || []).flatMap(walk)]; }
function schemaObjects(value) {
  if (!value || typeof value !== 'object') return [];
  return [value, ...Object.values(value).flatMap(schemaObjects)];
}
const isType = (value, type) => (Array.isArray(value['@type']) ? value['@type'] : [value['@type']]).includes(type);
function files(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => entry.isDirectory() ? files(path.join(dir, entry.name)) : [path.join(dir, entry.name)]).sort();
}
function check(condition, page, message) { if (!condition) errors.push({ page, message }); }
const relative = filename => path.relative(out, filename).replaceAll('\\', '/');
function localFile(value, pageUrl) {
  let url;
  try { url = new URL(value, pageUrl); } catch { return null; }
  if (url.origin !== SITE) return null;
  let decoded;
  try { decoded = decodeURIComponent(url.pathname); } catch { return ''; }
  const candidates = [decoded, url.pathname].flatMap(name => [name, `${name}.html`, `${name.replace(/\/$/, '')}/index.html`]);
  for (const candidate of candidates) {
    const filename = path.resolve(out, `.${candidate}`);
    if (!filename.startsWith(out + path.sep)) continue;
    if (fs.existsSync(filename) && fs.statSync(filename).isFile()) return filename;
  }
  return '';
}
function canonicalForFile(filename) {
  const name = relative(filename);
  return name === 'index.html' ? `${SITE}/` : new URL(`/${name}`, SITE).href;
}

// Контракты для URL и безопасного встраивания данных, включая ранее найденные крайние случаи.
assert.equal(canonicalUrl('/product/AWS-H03-1%2C5'), `${SITE}/product/AWS-H03-1,5.html`);
assert.equal(canonicalUrl('/product/ABC.123'), `${SITE}/product/ABC.123.html`);
assert.equal(canonicalUrl('/product/A%20white?x=1#photo'), `${SITE}/product/A%20white.html`);
assert.equal(canonicalUrl('/', '/brand/'), `${SITE}/brand/`);
assert.equal(canonicalUrl('/product/A', '/brand/'), `${SITE}/brand/product/A.html`);
assert.equal(canonicalUrl('/brand/product/A.html', '/brand/'), `${SITE}/brand/product/A.html`);
assert.equal(absoluteUrl('/img/a.webp?v=1', '/brand/'), `${SITE}/brand/img/a.webp?v=1`);
assert.equal(searchName('Выключатель 2-кл. белый'), 'Выключатель двухклавишный белый');
assert.equal(searchName('Удлинитель 1гн. 3м с/з'), 'Удлинитель 1 гнездо 3м с заземлением');
assert.equal(searchName('Удлинитель 11гн.'), 'Удлинитель 11 гнёзд');
const sampleMeta = productSearchMetadata({ article: 'TEST-1', name: 'Розетка IP67', seriesName: 'ТЕСТ' }, 'Розетка', [['Артикул', 'TEST-1'], ['Ток', '32 А']]);
assert.equal(sampleMeta.title, 'Розетка IP67 — AWS ТЕСТ — TEST-1');
assert.ok(sampleMeta.description.includes('Ток: 32 А'));
assert.ok(!sampleMeta.description.includes('Артикул:'));
assert.ok(!productSearchMetadata({ article: 'TEST-2', name: 'Вилка 380В' }, 'Вилка 380В', [['Напряжение', '220 В']]).description.includes('220 В'));
const hostile = { value: '</script><script>alert("x")</script>&\u2028' };
const encoded = serializeSchema(hostile);
assert.ok(!encoded.includes('<') && !encoded.includes('&'));
assert.deepEqual(JSON.parse(encoded), hostile);

const productsData = json('public/products.json');
const seriesData = json('src/data/series.json');
const categoryData = json('src/data/categories.json');
const expectedProducts = new Map();
function addProduct(item, context) {
  if (expectedProducts.has(item.article)) throw new Error(`Duplicate source SKU: ${item.article}`);
  expectedProducts.set(item.article, context);
}
for (const group of Object.values(productsData)) for (const item of group.items || []) addProduct(item, { type: 'category', name: item.name });
for (const [slug, series] of Object.entries(seriesData)) {
  if (slug === 'standard') continue;
  for (const key of ['switches', 'sockets', 'frames', 'surface', 'accessories', 'other']) {
    for (const item of series.groups?.[key] || []) addProduct(item, { type: 'series', seriesName: series.name, name: item.name });
  }
}
assert.ok(expectedProducts.size > 0, 'Catalog must not be empty');
const expected = new Set([
  `${SITE}/`, `${SITE}/video-concepts.html`,
  ...[...expectedProducts.keys()].map(article => canonicalUrl(`/product/${encodeURIComponent(article)}`)),
  ...Object.keys(categoryData).map(slug => canonicalUrl(`/category/${slug}`)),
  ...Object.keys(seriesData).filter(slug => slug !== 'standard').map(slug => canonicalUrl(`/series/${slug}`)),
]);
const exceptions = json('scripts/seo-resource-exceptions.json').images;
const htmlFiles = files(out).filter(filename => filename.endsWith('.html'));
const indexed = new Map();
const titleOwners = new Map();
const descriptionOwners = new Map();
const linkGraph = new Map();
let productCount = 0;
let jsonLdCount = 0;
let resourceCount = 0;

function comparableBody(tree, isProduct) {
  const body = walk(tree).find(node => node.tagName === 'body');
  if (isProduct) for (const node of walk(body)) {
    if (node.tagName === 'img' && hasClass(node, 'prod-hero__photo')) node.attrs = node.attrs.filter(item => !['alt', 'fetchpriority'].includes(item.name));
  }
  return JSON.stringify({ attributes: body.attrs, contents: serialize(body) });
}

for (const filename of htmlFiles) {
  const page = relative(filename);
  const currentUrl = canonicalForFile(filename);
  const tree = parse(read(filename));
  const nodes = walk(tree);
  const all = (tag, key, value) => nodes.filter(node => node.tagName === tag && (!key || attr(node, key) === value));
  const meta = name => attr(all('meta', 'name', name)[0], 'content');
  const robotsNodes = all('meta').filter(node => /^(?:robots|googlebot|yandex|bingbot)$/i.test(attr(node, 'name') || ''));
  const robotTokens = robotsNodes.flatMap(node => (attr(node, 'content') || '').toLowerCase().split(/[\s,]+/));
  if (expected.has(currentUrl)) check(!robotTokens.some(token => ['noindex', 'nofollow', 'none'].includes(token)), page, 'Indexable page has a blocking robot directive');
  if (!expected.has(currentUrl)) check(all('meta').some(node => /^robots$/i.test(attr(node, 'name') || '') && /(?:^|[\s,])(?:noindex|none)(?:$|[\s,])/i.test(attr(node, 'content') || '')), page, 'Non-catalog/service/demo page must have noindex or an explicit indexing policy');
  if (!expected.has(currentUrl)) continue;
  indexed.set(currentUrl, filename);
  const title = text(all('title')[0]);
  const description = meta('description');
  const canonical = attr(all('link', 'rel', 'canonical')[0], 'href');
  const ogTitle = attr(all('meta', 'property', 'og:title')[0], 'content');
  const ogDescription = attr(all('meta', 'property', 'og:description')[0], 'content');
  const ogImage = attr(all('meta', 'property', 'og:image')[0], 'content');
  for (const [label, list] of [['title', all('title')], ['description', all('meta', 'name', 'description')], ['canonical', all('link', 'rel', 'canonical')], ['og:title', all('meta', 'property', 'og:title')], ['og:description', all('meta', 'property', 'og:description')]]) check(list.length === 1, page, `${label} must occur exactly once`);
  check(all('h1').length === 1, page, 'Expected one main H1');
  check(typeof title === 'string' && title.trim() && !/\b(?:undefined|null)\b/.test(title), page, 'Invalid title');
  check(typeof description === 'string' && description.trim() && !/\b(?:undefined|null)\b/.test(description), page, 'Invalid description');
  check(title === ogTitle && description === ogDescription, page, 'OG metadata mismatch');
  check(canonical === currentUrl, page, `Canonical mismatch: ${canonical}`);
  check(!titleOwners.has(title), page, `Duplicate title with ${titleOwners.get(title)}`);
  check(!descriptionOwners.has(description), page, `Duplicate description with ${descriptionOwners.get(description)}`);
  titleOwners.set(title, page);
  descriptionOwners.set(description, page);
  check(!!ogImage && !!localFile(ogImage, currentUrl), page, 'Missing OG image');

  const graphs = [];
  for (const script of all('script', 'type', 'application/ld+json')) {
    try {
      const value = JSON.parse(text(script));
      check(value['@context'] === 'https://schema.org', page, 'Unexpected JSON-LD context');
      graphs.push(...(value['@graph'] || [value]));
      jsonLdCount++;
    } catch (error) { errors.push({ page, message: `Invalid JSON-LD: ${error.message}` }); }
  }
  const webpage = graphs.find(item => ['WebPage', 'CollectionPage'].includes(item['@type']));
  if (page === 'index.html') {
    const organization = graphs.find(item => item['@type'] === 'Organization');
    const website = graphs.find(item => item['@type'] === 'WebSite');
    check(graphs.filter(item => isType(item, 'Organization')).length === 1 && graphs.filter(item => isType(item, 'WebSite')).length === 1, page, 'Organization/WebSite must be unique');
    check(organization?.name === 'AWSProducts' && organization?.url === `${SITE}/` && organization?.email === 'info@awsproducts.ru', page, 'Organization mismatch');
    check(website?.url === `${SITE}/` && website?.publisher?.['@id'] === organization?.['@id'], page, 'WebSite mismatch');
  } else {
    check(graphs.filter(item => isType(item, 'WebPage') || isType(item, 'CollectionPage')).length === 1, page, 'WebPage must be unique');
    check(webpage?.url === canonical && webpage?.['@id'] === `${canonical}#webpage`, page, 'WebPage URL/id mismatch');
  }

  const crumbs = graphs.find(item => item['@type'] === 'BreadcrumbList');
  if (/^(?:product|category|series)\//.test(page)) {
    check(graphs.filter(item => isType(item, 'BreadcrumbList')).length === 1 && !!crumbs && crumbs.itemListElement.length >= 3, page, 'Missing or duplicated breadcrumb graph');
    if (crumbs) {
      check(webpage?.breadcrumb?.['@id'] === crumbs['@id'], page, 'WebPage breadcrumb reference mismatch');
      check(crumbs.itemListElement.every((item, index) => item.position === index + 1 && item.name && localFile(item.item, currentUrl)), page, 'Invalid breadcrumb order/name/target');
      check(crumbs.itemListElement.at(-1)?.item === canonical, page, 'Last breadcrumb must equal canonical');
    }
  }
  if (page.startsWith('product/')) {
    productCount++;
    const article = decodeURIComponent(path.basename(page, '.html'));
    const context = expectedProducts.get(article);
    const product = graphs.find(item => item['@type'] === 'Product');
    const allProducts = graphs.flatMap(schemaObjects).filter(item => isType(item, 'Product'));
    check(allProducts.length === 1, page, 'Expected exactly one Product');
    check(allProducts.every(item => !['offers', 'price', 'availability', 'aggregateRating', 'review', 'gtin', 'mpn'].some(key => key in item)), page, 'Unverified commercial fields in Product graph');
    const heroImages = nodes.filter(node => node.tagName === 'img' && hasClass(node, 'prod-hero__photo'));
    const actualImages = heroImages.map(node => attr(node, 'src')).filter(src => localFile(src, currentUrl)).map(src => new URL(src, currentUrl).href);
    const specs = nodes.filter(node => hasClass(node, 'prod-specs__row')).map(node => {
      const children = walk(node);
      return { '@type': 'PropertyValue', name: text(children.find(child => hasClass(child, 'prod-specs__label'))), value: text(children.find(child => hasClass(child, 'prod-specs__value'))) };
    });
    check(!!context && !!product, page, 'Product missing or not in source catalog');
    check(title.includes(article) && description.includes(article), page, 'SKU missing from metadata');
    check(!context?.seriesName || (title.includes(context.seriesName) && description.includes(context.seriesName)), page, 'Series missing from metadata');
    if (context) {
      const voltageInName = [...context.name.matchAll(/(\d+)\s*[ВV](?![а-яёa-z])/gi)].map(match => match[1]);
      const addedVoltage = description.match(/Напряжение:\s*([^;.]+)/i)?.[1];
      if (voltageInName.length && addedVoltage) check([...addedVoltage.matchAll(/(\d+)\s*[ВV](?![а-яёa-z])/gi)].every(match => voltageInName.includes(match[1])), page, 'Conflicting voltage added to search description');
      for (const token of context.name.match(/\bIP\s*\d{2}\b|\bCAT\.?\s*\d[a-z]*/gi) || []) check(title.toLowerCase().replace(/\s+/g, '').includes(token.toLowerCase().replace(/\s+/g, '')), page, 'Technical product attribute lost from search title');
      const meta = productSearchMetadata({ ...context, article }, text(all('h1')[0]), specs.map(item => [item.name, item.value]));
      check(title === meta.title && description === meta.description, page, 'Product metadata differs from visible title and specifications');
    }
    if (product) {
      check(product.sku === article && product.brand?.name === 'AWSProducts', page, 'Product SKU/brand mismatch');
      check(product.url === canonical && product['@id'] === `${canonical}#product` && product.mainEntityOfPage?.['@id'] === webpage?.['@id'], page, 'Product URL/id/WebPage mismatch');
      check(product.name === text(all('h1')[0]) && product.description === text(nodes.find(node => hasClass(node, 'prod-details__text'))), page, 'Product text differs from visible content');
      check(JSON.stringify(product.additionalProperty) === JSON.stringify(specs), page, 'Product properties differ from visible specifications');
      check(JSON.stringify(product.image || []) === JSON.stringify(actualImages), page, 'Product images differ from available gallery images');
      check(!['offers', 'price', 'availability', 'aggregateRating', 'review', 'gtin', 'mpn'].some(key => key in product), page, 'Unverified commercial fields in Product');
      check(webpage?.mainEntity?.['@id'] === product['@id'], page, 'Missing Product mainEntity reference');
    }
    check(ogImage === (actualImages[0] || `${SITE}/logo/AWS.png`), page, 'OG image does not match product');
    check(heroImages.every((node, index) => attr(node, 'alt')?.includes(article) && attr(node, 'loading') === (index ? 'lazy' : 'eager') && attr(node, 'fetchpriority') === (index ? undefined : 'high')), page, 'Gallery alt/loading/priority mismatch');
  }
  if (/^(?:category|series)\//.test(page)) {
    const list = graphs.find(item => item['@type'] === 'ItemList');
    check(graphs.filter(item => isType(item, 'ItemList')).length === 1, page, 'Expected exactly one catalog ItemList');
    const cards = nodes.filter(node => node.tagName === 'a' && (hasClass(node, 'prod-card') || hasClass(node, 'ser-lineup__card')));
    const urls = cards.map(node => canonicalUrl(attr(node, 'href')));
    check(webpage?.['@type'] === 'CollectionPage', page, 'Catalog page is not CollectionPage');
    check(list?.numberOfItems === cards.length && list?.itemListElement.length === cards.length, page, 'ItemList length differs from visible catalog');
    if (list) {
      check(webpage?.mainEntity?.['@id'] === list['@id'], page, 'Missing catalog mainEntity reference');
      check(list.itemListElement.every((item, index) => {
        const nameNode = walk(cards[index]).find(node => hasClass(node, 'prod-card__name') || hasClass(node, 'ser-lineup__name'));
        return item.position === index + 1 && item.url === urls[index] && item.name === text(nameNode).trim();
      }), page, 'ItemList order/URLs/names differ from visible cards');
    }
  }

  const outgoing = [];
  for (const node of nodes) {
    const key = node.tagName === 'img' || node.tagName === 'script' ? 'src' : node.tagName === 'a' || (node.tagName === 'link' && attr(node, 'rel') === 'stylesheet') ? 'href' : null;
    if (!key) continue;
    const value = attr(node, key);
    if (!value || /^(?:data:|mailto:|tel:|javascript:)/i.test(value)) continue;
    let target;
    try { target = new URL(value, currentUrl); } catch { check(false, page, `Invalid resource URL: ${value}`); continue; }
    if (target.origin !== SITE) continue;
    resourceCount++;
    const local = localFile(value, currentUrl);
    if (!local) {
      const known = node.tagName === 'img' && exceptions[page]?.includes(value);
      if (known) warnings.push({ page, existingMissingImage: value });
      else check(false, page, `Missing ${node.tagName}[${key}]: ${value}`);
    }
    if (node.tagName === 'a' && local) outgoing.push(canonicalForFile(local));
  }
  linkGraph.set(canonical, outgoing);
  if (baseline) {
    const old = path.join(baseline, page);
    check(fs.existsSync(old), page, 'Page absent in baseline');
    if (fs.existsSync(old)) check(comparableBody(tree, page.startsWith('product/')) === comparableBody(parse(read(old)), page.startsWith('product/')), page, 'Visible HTML differs beyond approved image alt/fetchpriority');
  }
}

check(indexed.size === expected.size && [...expected].every(url => indexed.has(url)), 'catalog', 'Generated page set differs from source catalog');
check(productCount === expectedProducts.size, 'catalog', 'Product count mismatch');
const reachable = new Set();
const queue = [`${SITE}/`];
while (queue.length) {
  const url = queue.pop();
  if (reachable.has(url)) continue;
  reachable.add(url);
  for (const next of linkGraph.get(url) || []) if (!reachable.has(next)) queue.push(next);
}
check([...expectedProducts.keys()].every(article => reachable.has(canonicalUrl(`/product/${encodeURIComponent(article)}`))), 'catalog', 'Product orphaned from homepage link graph');
const robots = read(path.join(out, 'robots.txt'));
check(/^Allow:\s*\/$/m.test(robots) && !/^Disallow:\s*\/$/m.test(robots), 'robots.txt', 'Catalog crawling must remain allowed');
check(/^Sitemap:\s*https:\/\/awsproducts\.ru\/sitemap-index\.xml\s*$/m.test(robots), 'robots.txt', 'Wrong Sitemap directive');
// Sitemap integration omits the root slash with trailingSlash:never; URL parsing restores its equivalent form.
const locs = xml => [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map(match => new URL(match[1].replaceAll('&amp;', '&')).href);
const sitemapUrls = [];
const childMaps = locs(read(path.join(out, 'sitemap-index.xml')));
check(childMaps.length > 0, 'sitemap-index.xml', 'Empty sitemap index');
for (const child of childMaps) {
  const filename = localFile(child, `${SITE}/`);
  check(!!filename, 'sitemap-index.xml', `Missing child sitemap ${child}`);
  if (filename) sitemapUrls.push(...locs(read(filename)));
}
const sitemapSet = new Set(sitemapUrls);
check(sitemapUrls.length === sitemapSet.size && sitemapSet.size === expected.size && [...expected].every(url => sitemapSet.has(url)), 'sitemap', 'Sitemap must exactly match indexable canonical URLs');
for (const url of sitemapSet) check(indexed.has(url) && !!localFile(url, `${SITE}/`), 'sitemap', `URL is not a canonical indexable page: ${url}`);

let protectedFilesChecked = 0;
if (protectedManifest) {
  const manifest = json(protectedManifest);
  const protectedPaths = Object.keys(manifest).filter(name => /^(?:src\/data\/|public\/img\/|src\/utils\/(?:photos|catalog)\.js$|src\/styles\/|public\/(?:style\.css|products\.json|script\.js|bg-switch\.))/.test(name));
  protectedFilesChecked = protectedPaths.length;
  for (const name of protectedPaths) check(fs.existsSync(name) && hash(fs.readFileSync(name)) === manifest[name], name, 'Protected data/photo/style/logic changed');
}
const report = { pass: errors.length === 0, node: process.version, indexablePages: indexed.size, products: productCount, sitemapUrls: sitemapSet.size, jsonLdBlocks: jsonLdCount, localReferencesChecked: resourceCount, uniqueTitles: titleOwners.size, uniqueDescriptions: descriptionOwners.size, knownMissingImagePairs: [...new Set(warnings.map(item => `${item.page}|${item.existingMissingImage}`))].length, baselineCompared: !!baseline, protectedManifestCompared: !!protectedManifest, protectedFilesChecked, errors, warnings };
const reportPath = argument('--report');
if (reportPath) fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
if (!report.pass) process.exitCode = 1;
