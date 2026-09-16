const CACHE='einvite-checkin-v15';
const PRECACHE=[
  '/checkin.html','/bundle-checkin-v15.css','/bundle-checkin-v15.js',
  '/theme-init.js','/backend-mode-v14.js','/manifest.webmanifest'
];
const STATIC=new Set(PRECACHE.filter(path=>path!=='/checkin.html'));
self.addEventListener('install',event=>event.waitUntil(
  caches.open(CACHE).then(cache=>cache.addAll(PRECACHE)).then(()=>self.skipWaiting())
));
self.addEventListener('activate',event=>event.waitUntil(
  caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())
));
async function networkFirst(request,fallback){
  try{const response=await fetch(request);if(response.ok){const cache=await caches.open(CACHE);await cache.put(fallback||request,response.clone())}return response}
  catch(error){const cached=await caches.match(fallback||request);if(cached)return cached;throw error}
}
self.addEventListener('fetch',event=>{
  const request=event.request,url=new URL(request.url);
  if(request.method!=='GET'||url.origin!==location.origin||url.pathname.startsWith('/api/'))return;
  const isCheckinNavigation=request.mode==='navigate'&&(url.pathname==='/checkin.html'||/^\/invitations\/[^/]+\/checkin$/.test(url.pathname));
  if(isCheckinNavigation){event.respondWith(networkFirst(request,'/checkin.html'));return}
  if(!STATIC.has(url.pathname))return;
  event.respondWith(networkFirst(request,request));
});
