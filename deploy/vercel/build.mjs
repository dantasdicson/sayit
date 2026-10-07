import {mkdirSync, writeFileSync} from 'node:fs';

const origin = new URL(process.env.RENDER_ORIGIN || '');
if (origin.protocol !== 'https:' || origin.username || origin.password || origin.pathname !== '/' || origin.search || origin.hash || !origin.hostname.endsWith('.onrender.com')) {
  throw new Error('Configure RENDER_ORIGIN como https://nome-do-servico.onrender.com');
}
mkdirSync('.vercel/output', {recursive: true});
writeFileSync('.vercel/output/config.json', JSON.stringify({
  version: 3,
  routes: [{src: '/(.*)', dest: `${origin.origin}/$1`, headers: {
    'Cache-Control': 'private, no-store',
    'CDN-Cache-Control': 'no-store',
    'Vercel-CDN-Cache-Control': 'no-store'
  }}]
}, null, 2));
