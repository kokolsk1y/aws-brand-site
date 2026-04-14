import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://kokolsk1y.github.io',
  base: '/aws-brand-site',
  trailingSlash: 'never',
  build: {
    format: 'file'
  },
  server: {
    port: 4321,
    host: true
  }
});
