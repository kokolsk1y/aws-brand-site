import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { canonicalUrl } from './src/utils/seo.js';

export default defineConfig({
  site: 'https://awsproducts.ru',
  trailingSlash: 'never',
  integrations: [sitemap({
    filter: page => !/^\/randomizer(?:\.html)?\/?$/.test(new URL(page).pathname),
    serialize: item => ({ ...item, url: canonicalUrl(item.url) }),
  })],
  build: {
    format: 'file'
  },
  server: {
    port: 4321,
    host: true
  }
});
