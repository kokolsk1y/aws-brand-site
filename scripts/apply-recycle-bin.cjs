// Применяет ручную чистку пользователя из Корзины Windows.
// Список вида "АРТИКУЛ/N.webp" → удаляем АРТИКУЛ_N.webp из /public/img/products/

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const PUB = path.join(ROOT, 'public', 'img', 'products');

// Список из скриншотов корзины (артикул → массив индексов файлов)
const DELETIONS = {
    // === Скриншот 1 ===
    "AWS-H05K-1,5": [3, 4, 5],
    "SLN-214": [4],
    "AWS-G03-5": [3, 4, 5],
    "AWS-G03K-1,5": [4, 5],
    "A-001B": [2, 3, 4, 5],
    "SLN-1152": [2, 4],
    "A-002B": [2, 3, 4, 6],
    "AWS-HZ2-01-25": [2, 4],
    "A-003B": [3, 4, 5, 6],
    "AWS-13010": [2, 3, 4],
    "AWS-H03K-5": [3, 4, 5],
    "AWS-H05K-3": [2, 3, 5],
    "AWS-H03-1,5": [3, 4, 5],
    "AWS-H03-3": [2, 3, 5],
    "SLN-123K": [3, 4, 5],
    "A-001W": [3, 4, 5, 6],
    "AWS-H05-1,5": [3, 4, 5],
    "SLN-1252": [5],
    "SLN-115K": [3, 5],
    "A-002W": [2, 3, 5],
    "SLN-125K": [2, 4, 5],
    "AWS-H03K-1,5": [3, 4, 5],
    // === Скриншот 2 ===
    "SLN-1352": [2, 3],
    "SLN-2232": [3],
    "AWS-12982": [2, 3],
    "SLN-2142": [3],
    "SLN-0452": [3, 4],
    "SLN-0342": [2, 4],
    "SLN-113K": [4],
    "SLN-114K": [3, 4],
    "SLN-015": [3, 4],
    "SLN-1142": [2, 4],
    "SLN-1242": [3, 4],
    "SLN-225": [4],
    "AWS-H05-3": [2, 3, 4],
    "SLN-2352": [3, 4],
    "AWS-HZ2-01-10": [2, 4],
    "SLN-0352": [2, 4],
    "SLN-1132": [4],
    // === Скриншот 3 ===
    "AWS-12985": [2, 3],
    "AWS-12992": [2, 3],
    "AWS-12988": [2, 3],
    "SLN-1232": [3],
    "SLN-0232": [3],
    "AWS-HZ2-01-15": [2, 3],
    "SLN-2252": [3],
    "AWS-13000": [2, 3],
    "AWS-12991": [2, 3],
    "AWS-12997": [2, 3],
    "SLN-014": [3],
    // === Скриншот 4 ===
    "SLN-025": [2],
    "SLN-213": [2],
    "SLN-1342": [2],
    "SLN-0252": [2],
    "SLN-2452": [2, 3],
    "SN-221412": [2],
    "SN-222415": [2],
    "SLN-2132": [2],
    "SLN-215": [2],
    "SLN-1452": [2],
    "AWS-12983": [2, 3],
    "AWS-12989": [2, 3],
    "AWS-12998": [2, 3],
    // === Скриншот 5 ===
    "SLN-223": [2],
    "SLN-0242": [2],
    "AWS-13001": [2],
    "SN-53": [2],
    "SN-221412N": [2],
    "SLN-2152": [2],
};

let removed = 0, missing = 0;
for (const [art, indexes] of Object.entries(DELETIONS)) {
    for (const idx of indexes) {
        // 1.webp = main = АРТИКУЛ.webp/.png
        // 2.webp+ = АРТИКУЛ_2.webp+
        const candidates = idx === 1
            ? [`${art}.webp`, `${art}.png`]
            : [`${art}_${idx}.webp`, `${art}_${idx}.png`];
        let found = false;
        for (const f of candidates) {
            const fp = path.join(PUB, f);
            if (fs.existsSync(fp)) {
                fs.unlinkSync(fp);
                removed++;
                found = true;
                break;
            }
        }
        if (!found) missing++;
    }
}
console.log(`Удалено: ${removed}, не найдено (уже не было): ${missing}`);
