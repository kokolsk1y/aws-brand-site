import fs from 'node:fs';
import path from 'node:path';

export const SITE = 'https://awsproducts.ru';

export function absoluteUrl(value, base = '/') {
  const url = new URL(value, `${SITE}/`);
  const prefix = base.replace(/^\/+|\/+$/g, '');
  if (url.origin === SITE && prefix && url.pathname !== `/${prefix}` && !url.pathname.startsWith(`/${prefix}/`)) url.pathname = `/${prefix}${url.pathname}`;
  return url.href;
}

// Сохраняем действующую .html форму canonical; маршруты и входящие ссылки не меняются.
export function canonicalUrl(value, base = '/') {
  const url = new URL(absoluteUrl(value, base));
  url.search = '';
  url.hash = '';
  const rootPath = `/${base.replace(/^\/+|\/+$/g, '')}`.replace(/\/$/, '') + '/';
  if (url.pathname === rootPath.replace(/\/$/, '') || url.pathname === rootPath) url.pathname = rootPath;
  else if (!url.pathname.endsWith('.html') && (/\/(?:product|category|series)\//.test(url.pathname) || !path.posix.extname(url.pathname))) url.pathname = `${url.pathname.replace(/\/$/, '')}.html`;
  url.pathname = url.pathname.replace(/%2c/gi, ',');
  return url.href;
}

export function serializeSchema(value) {
  return JSON.stringify(value).replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
}

export function searchName(value) {
  const keys = { 1: 'одноклавишный', 2: 'двухклавишный', 3: 'трёхклавишный' };
  return value
    .replace(/([1-3])\s*-\s*кл\./gi, (_, count) => keys[count])
    .replace(/с\/з(?=\s|$)/g, 'с заземлением')
    .replace(/б\/з(?=\s|$)/g, 'без заземления')
    .replace(/(\d+)\s*гн\./g, (_, count) => {
      const n = Number(count);
      const form = n % 100 >= 11 && n % 100 <= 14 ? 'гнёзд' : n % 10 === 1 ? 'гнездо' : [2, 3, 4].includes(n % 10) ? 'гнезда' : 'гнёзд';
      return `${count} ${form}`;
    })
    .replace(/\s+/g, ' ')
    .trim();
}

export function publicImages(images) {
  return images.filter(image => {
    const url = new URL(image, `${SITE}/`);
    if (url.origin !== SITE) return false;
    const filename = path.resolve('public', `.${decodeURIComponent(url.pathname)}`);
    return filename.startsWith(path.resolve('public') + path.sep) && fs.existsSync(filename);
  });
}

export function productSearchMetadata(product, visibleTitle, specs) {
  let name = searchName(visibleTitle || product.article);
  // Короткий видимый H1 убирает IP/Cat; возвращаем их только в поисковый заголовок.
  const technical = [product.name.match(/\bIP\s*\d{2}\b/i)?.[0], product.name.match(/\bCAT\.?\s*\d[a-z]*/i)?.[0]]
    .filter(Boolean).map(value => value.replace(/\s+/g, ''));
  for (const value of technical) if (!name.toLowerCase().replace(/\s+/g, '').includes(value.toLowerCase())) name += ` ${value}`;
  const brand = product.seriesName ? `AWS ${product.seriesName}` : 'AWSProducts';
  const nameVoltage = [...product.name.matchAll(/(\d+)\s*[ВV](?![а-яёa-z])/gi)].map(match => match[1]);
  const features = specs.filter(([key, value]) =>
    !/артикул|бренд|производитель|серия|страна|гарантия|сертификац/i.test(key)
    && String(value).trim() && String(value).length <= 80
    // Не переносим существующие расхождения исходного имени и таблицы в сниппет.
    && !(/напряжен/i.test(key) && nameVoltage.length && [...String(value).matchAll(/(\d+)\s*[ВV](?![а-яёa-z])/gi)].some(match => !nameVoltage.includes(match[1])))
  ).slice(0, 3).map(([key, value]) => `${key}: ${String(value).trim()}`).join('; ');
  return {
    title: `${name} — ${brand} — ${product.article}`,
    description: `${name}. Артикул ${product.article}. ${product.seriesName ? `Серия AWS ${product.seriesName}.` : 'Бренд AWSProducts.'}${features ? ` ${features}.` : ''} Фотографии, характеристики и где купить.`,
  };
}

export function breadcrumbs(url, items, base = '/') {
  return {
    '@type': 'BreadcrumbList',
    '@id': `${url}#breadcrumbs`,
    itemListElement: items.map(([name, item], index) => ({ '@type': 'ListItem', position: index + 1, name, item: absoluteUrl(item, base) })),
  };
}

export function itemList(url, items, base = '/') {
  return {
    '@type': 'ItemList',
    '@id': `${url}#items`,
    numberOfItems: items.length,
    itemListElement: items.map((item, index) => ({ '@type': 'ListItem', position: index + 1, name: item.name, url: canonicalUrl(`/product/${encodeURIComponent(item.article)}`, base) })),
  };
}

export function productSchema(product, name, description, specs, base = '/') {
  const url = canonicalUrl(`/product/${encodeURIComponent(product.article)}`, base);
  const images = publicImages(product.photos);
  return {
    '@type': 'Product',
    '@id': `${url}#product`,
    url,
    name,
    sku: product.article,
    description,
    brand: { '@type': 'Brand', name: 'AWSProducts' },
    mainEntityOfPage: { '@id': `${url}#webpage` },
    ...(images.length ? { image: images.map(image => absoluteUrl(image, base)) } : {}),
    additionalProperty: specs.map(([key, value]) => ({ '@type': 'PropertyValue', name: key, value: String(value) })),
  };
}

export const categoryTitles = {
  'extensions-home': 'Бытовые удлинители AWS — каталог',
  'extensions-garden': 'Садовые удлинители AWS — каталог',
  'power-connectors': 'Силовые вилки, розетки и разъёмы AWS',
  clamps: 'Соединительные клеммы AWS — каталог',
  'patch-cords': 'Патч-корды AWS — сетевые кабели RJ45',
  cables: 'Сетевой и телевизионный кабель AWS',
};

export const seriesLatin = { uno: 'UNO', aura: 'AURA', design: 'DESIGN' };
