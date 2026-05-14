import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://awsproducts.ru',
  trailingSlash: 'never',
  integrations: [sitemap()],
  build: {
    format: 'file'
  },
  server: {
    port: 4321,
    host: true
  }
});
