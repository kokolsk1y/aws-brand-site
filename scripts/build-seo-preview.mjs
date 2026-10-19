import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const option = process.argv.indexOf('--directory');
const directory = path.resolve(option >= 0 ? process.argv[option + 1] : 'tmp/seo-local');
if (!directory.startsWith(path.resolve('tmp') + path.sep)) throw new Error('Preview directory must be inside tmp');
const output = path.join(directory, 'site');
if (fs.existsSync(output) && fs.readdirSync(output).length) throw new Error('Refusing to overwrite a nonempty preview. Existing files will not be removed.');
process.env.ASTRO_TELEMETRY_DISABLED = '1';
const { build } = await import('astro');
await build({
  outDir: output,
  cacheDir: path.join(directory, 'astro-cache'),
  vite: { cacheDir: path.join(directory, 'vite-cache'), build: { emptyOutDir: false } },
  logLevel: 'warn',
});
const args = ['scripts/verify-seo.mjs', '--out-dir', output, '--report', path.join(directory, 'verification.json')];
if (fs.existsSync('tmp/seo-safety-audit/baseline')) args.push('--baseline', 'tmp/seo-safety-audit/baseline');
if (fs.existsSync('tmp/seo-safety-audit/protected-before.json')) args.push('--protected-manifest', 'tmp/seo-safety-audit/protected-before.json');
execFileSync(process.execPath, args, { stdio: 'inherit', windowsHide: true });
