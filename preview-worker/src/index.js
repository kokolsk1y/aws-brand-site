const ORIGIN = 'https://awsproducts.ru';

const rootFiles = new Set([
  '/style.css',
  '/script.js',
  '/bg-switch.css',
  '/bg-switch.js',
  '/constructor-data.json',
  '/hero-1-glass.mp4',
  '/hero-kitchen.mp4',
  '/hero-living.mp4',
  '/hero-softtouch.mp4',
]);

const assetPrefixes = ['/preview/', '/img/', '/logo/', '/video-reviews/'];

function isAsset(pathname) {
  return rootFiles.has(pathname) || assetPrefixes.some((prefix) => pathname.startsWith(prefix));
}

export default {
  async fetch(request) {
    const incoming = new URL(request.url);

    if (incoming.pathname !== '/' && incoming.pathname !== '/index.html' && !isAsset(incoming.pathname)) {
      return Response.redirect(`${incoming.origin}/`, 302);
    }

    const originPath = incoming.pathname === '/' || incoming.pathname === '/index.html'
      ? '/preview/index.html'
      : incoming.pathname;
    const originUrl = new URL(originPath, ORIGIN);
    originUrl.search = incoming.search;

    const response = await fetch(new Request(originUrl, request));
    const headers = new Headers(response.headers);
    headers.set('X-Robots-Tag', 'noindex, nofollow');
    headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  },
};
