// Перестраивает /public/products.json на основе stv-products-v2.json.
// Маппит разделы stv → ключи нашего products.json:
//   udliniteli_bytovye_i_sadovye → udl_home (бытовые)
//   udliniteli_sadovye → udl_garden (садовые)
//   professionalnye_razemy → power
//   kabelnye_klemmniki_soediniteli_i_kolodki → clamps
//   patch_kordy_shnury_i_zaryadniki → patch
//   kabel_svyazi_kompyuternyy_i_televizionnyy → cable
//
// Для каждого товара: article, name, photo (главное), price (с stv),
// description (с stv, raw — потом перепишем).

const fs = require('fs');
const path = require('path');

const products = require('c:/Users/ikoko/Projects/aws-brand-site/_pipeline/stv-products-v2.json');
const oldJson = require('c:/Users/ikoko/Projects/aws-brand-site/public/products.json');

const RAZDEL_MAP = {
    'udliniteli_bytovye_i_sadovye': 'udl_home',
    'udliniteli_sadovye': 'udl_garden',
    'professionalnye_razemy': 'power',
    'kabelnye_klemmniki_soediniteli_i_kolodki': 'clamps',
    'patch_kordy_shnury_i_zaryadniki': 'patch',
    'kabel_svyazi_kompyuternyy_i_televizionnyy': 'cable'
};

// Собираем новый products.json с сохранением title/sub из старого
const result = {};
for (const oldKey of Object.keys(oldJson)) {
    result[oldKey] = {
        title: oldJson[oldKey].title,
        sub: oldJson[oldKey].sub,
        items: []
    };
}

// Раскладываем товары
for (const p of products) {
    const key = RAZDEL_MAP[p.razdel];
    if (!key || !result[key]) continue;
    // Бытовые/садовые удлинители: разделение по подкатегории
    let targetKey = key;
    if (p.razdel === 'udliniteli_bytovye_i_sadovye') {
        // Если в названии «садовый» — кладём в garden, иначе в home
        if (/садов/i.test(p.name)) targetKey = 'udl_garden';
        else targetKey = 'udl_home';
    }
    if (!result[targetKey]) continue;
    result[targetKey].items.push({
        article: p.article,
        name: p.name,
        photo: `img/products/${p.article}.webp`,
        price: p.price ? Number(p.price) : null,
        description_raw: p.description || null
    });
}

// Сортировка по артикулу для стабильности
for (const k of Object.keys(result)) {
    result[k].items.sort((a, b) => a.article.localeCompare(b.article));
}

fs.writeFileSync(
    'c:/Users/ikoko/Projects/aws-brand-site/public/products.json',
    JSON.stringify(result, null, 2)
);

const summary = Object.entries(result).map(([k, v]) => `${k}: ${v.items.length}`).join(', ');
console.log('Готово —', summary);
console.log('Всего:', Object.values(result).reduce((s, v) => s + v.items.length, 0));
