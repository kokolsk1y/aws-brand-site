// Вырез чёрного фона у исправленных фронтальных фото УНО (закрыта щель клавиша/рамка)
// и подгонка под рамки сайта: конструктор 1000×1000 (товар ~93%), обложки 800×800 (~85%).
//
// Метод: flood-fill от краёв кадра по тёмным пикселям (lum < T) — всё, что связано
// с границей кадра, становится прозрачным; тёмные участки ВНУТРИ товара (швы, щель)
// остаются непрозрачными, поэтому вырез не «прогрызает» чёрные/матовые варианты.
//
// Запуск: node scripts/uno_gap_cutout.cjs preview   — только превью в папку на раб.столе
//         node scripts/uno_gap_cutout.cjs apply     — записать webp в public/img/...

const s = require('sharp');
const fs = require('fs');

const DESK = 'C:/Users/ikoko/OneDrive/Desktop/UNO-фото-исправить';
const ROOT = 'C:/Users/ikoko/Projects/aws-brand-site';

// цвет → [исходный исправленный файл, имя конструктора, имя обложки]
const MAP = [
  ['white',       '1-белый (white) - исправленная',          'white.webp',       'uno-1kl-w.webp'],
  ['black',       '2-чёрный (black) - исправленная',         'black.webp',       'uno-1kl-b.webp'],
  ['grey',        '3-серый (grey) - исправленная',           'grey.webp',        'uno-1kl-grey.webp'],
  ['dark_grey',   '4-тёмно-серый (dark_grey) - исправленная','dark_grey.webp',   'uno-1kl-dark_grey.webp'],
  ['silver',      '5-серебро (silver) - исправленная',       'silver.webp',      'uno-1kl-silver.webp'],
  ['matte_black', '6-чёрный матовый (matte_black) - исправленная','matte_black.webp','uno-1kl-matte_black.webp'],
];

const T = 14; // порог яркости фона (фон = чистый чёрный rgb 0,0,0)

// Вырезает чёрный фон, возвращает {data,info} RGBA с тугим кропом по товару (+небольшой запас)
async function cutout(srcPath) {
  const { data, info } = await s(srcPath).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  const W = info.width, H = info.height, C = info.channels;
  const lum = (i) => 0.299 * data[i * C] + 0.587 * data[i * C + 1] + 0.114 * data[i * C + 2];

  // flood-fill от всех граничных пикселей по тёмному (lum < T)
  const isBg = new Uint8Array(W * H); // 1 = фон (связан с краем)
  const stack = [];
  const pushIf = (idx) => { if (!isBg[idx] && lum(idx) < T) { isBg[idx] = 1; stack.push(idx); } };
  for (let x = 0; x < W; x++) { pushIf(x); pushIf((H - 1) * W + x); }
  for (let y = 0; y < H; y++) { pushIf(y * W); pushIf(y * W + W - 1); }
  while (stack.length) {
    const idx = stack.pop();
    const x = idx % W, y = (idx - x) / W;
    if (x > 0) pushIf(idx - 1);
    if (x < W - 1) pushIf(idx + 1);
    if (y > 0) pushIf(idx - W);
    if (y < H - 1) pushIf(idx + W);
  }

  // альфа: 0 для фона, иначе 255; заодно bbox товара
  let minX = W, minY = H, maxX = 0, maxY = 0, cnt = 0;
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const idx = y * W + x;
    if (isBg[idx]) { data[idx * C + 3] = 0; }
    else { data[idx * C + 3] = 255; cnt++; if (x < minX) minX = x; if (x > maxX) maxX = x; if (y < minY) minY = y; if (y > maxY) maxY = y; }
  }
  const bw = maxX - minX + 1, bh = maxY - minY + 1;
  return { buf: Buffer.from(data), W, H, C, minX, minY, bw, bh, cnt };
}

// Подгонка вырезанного товара под квадрат size с долей заполнения fill (по большей стороне)
async function fitSquare(cut, size, fill) {
  // вырезаем тугой кроп товара, лёгкий feather альфы, ресайз до fill, центрируем на прозрачном квадрате
  const cropped = s(cut.buf, { raw: { width: cut.W, height: cut.H, channels: cut.C } })
    .extract({ left: cut.minX, top: cut.minY, width: cut.bw, height: cut.bh });
  const target = Math.round(size * fill);
  const inner = await cropped
    .resize(target, target, { fit: 'inside', background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .png()
    .toBuffer();
  const meta = await s(inner).metadata();
  // материализуем в PNG-буфер: иначе resize в превью применится ДО composite (sharp так устроен)
  return s({ create: { width: size, height: size, channels: 4, background: { r: 0, g: 0, b: 0, alpha: 0 } } })
    .composite([{ input: inner, left: Math.round((size - meta.width) / 2), top: Math.round((size - meta.height) / 2) }])
    .png().toBuffer();
}

(async () => {
  const mode = process.argv[2] || 'preview';
  for (const [color, src, cName, coverName] of MAP) {
    const cut = await cutout(`${DESK}/${src}`);
    console.log(`${color.padEnd(12)}| вырез: товар ${cut.bw}x${cut.bh} (${(100 * cut.bw / cut.W).toFixed(0)}% шир), пикселей ${(100 * cut.cnt / (cut.W * cut.H)).toFixed(1)}%`);

    const constr = await fitSquare(cut, 1000, 0.93);
    const cover = await fitSquare(cut, 800, 0.85);

    if (mode === 'apply') {
      await s(constr).webp({ quality: 92 }).toFile(`${ROOT}/public/img/constructor/uno/${cName}`);
      await s(cover).webp({ quality: 90 }).toFile(`${ROOT}/public/img/series/${coverName}`);
      console.log(`   → записано: constructor/uno/${cName} + series/${coverName}`);
    } else {
      // превью: вырезанный товар на фоне сайта warm-100 (#f7f4ef) — как будет на странице
      const onSite = await s(constr).flatten({ background: { r: 247, g: 244, b: 239 } })
        .resize(420, 420).jpeg({ quality: 82 }).toBuffer();
      // и на шахматке — чтобы видеть края выреза и дыры
      const checker = await makeChecker(420, 420);
      const onCheck = await s(checker)
        .composite([{ input: await s(constr).resize(420, 420).png().toBuffer() }])
        .jpeg({ quality: 82 }).toBuffer();
      await s({ create: { width: 860, height: 420, channels: 3, background: { r: 255, g: 255, b: 255 } } })
        .composite([{ input: onSite, left: 0, top: 0 }, { input: onCheck, left: 440, top: 0 }])
        .jpeg({ quality: 82 }).toFile(`${DESK}/_proof_${color}.jpg`);
      console.log(`   → превью: _proof_${color}.jpg (слева фон сайта, справа шахматка)`);
    }
  }
  console.log('Готово:', mode);
})();

// Шахматный фон для контроля прозрачности
async function makeChecker(w, h) {
  const cell = 20;
  const raw = Buffer.alloc(w * h * 3);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const v = (((x / cell) | 0) + ((y / cell) | 0)) % 2 ? 210 : 245;
    const i = (y * w + x) * 3; raw[i] = raw[i + 1] = raw[i + 2] = v;
  }
  return s(raw, { raw: { width: w, height: h, channels: 3 } }).png().toBuffer();
}
