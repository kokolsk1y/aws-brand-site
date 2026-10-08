import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const publicDir = resolve(projectRoot, 'public');
const previewDir = resolve(publicDir, 'preview');

await mkdir(previewDir, { recursive: true });

const sourceHtml = await readFile(resolve(publicDir, 'motion-integration.html'), 'utf8');
const sourceCss = await readFile(resolve(publicDir, 'motion-integration.css'), 'utf8');
const sourceJs = await readFile(resolve(publicDir, 'motion-integration.js'), 'utf8');

const html = sourceHtml
  .replace(
    '<title>AWSProducts — локальная интеграция серий</title>',
    '<title>AWSProducts — демонстрация обновлённой главной</title>',
  )
  .replace(
    '<meta property="og:url" content="https://awsproducts.ru/">',
    '<meta property="og:url" content="https://preview.awsproducts.ru/">',
  )
  .replace(
    '<link rel="canonical" href="https://awsproducts.ru/">',
    '<link rel="canonical" href="https://preview.awsproducts.ru/">',
  )
  .replace('/motion-integration.css?v=20261007', '/preview/motion-integration.css?v=20261008-5')
  .replace('/motion-integration.js?v=20261007', '/preview/motion-integration.js?v=20261008-5')
  .replace(/href="\/(series|category)\//g, 'href="https://awsproducts.ru/$1/');

const js = sourceJs.replace(
  'seriesLink.href = `/series/${key}`;',
  'seriesLink.href = `https://awsproducts.ru/series/${key}`;',
);

await Promise.all([
  writeFile(resolve(previewDir, 'index.html'), html, 'utf8'),
  writeFile(resolve(previewDir, 'motion-integration.css'), sourceCss, 'utf8'),
  writeFile(resolve(previewDir, 'motion-integration.js'), js, 'utf8'),
]);

console.log('Created /preview/ release for preview.awsproducts.ru');
