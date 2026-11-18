// Service worker lifecycle and offline fallback logic simulation.
// This is a unit test (not an actual installation in iOS Safari).
const fs=require('fs'),vm=require('vm'),path=require('path');
const root=path.resolve(__dirname,'..');
const source=fs.readFileSync(path.join(root,'sw.js'),'utf8');
const handlers={};const storage=new Map();const CACHE_NAME='second-era-rundenplan-v5';
const cacheStore = new Map();let online=false;let skip=false,claimed=false;
const cache={
  addAll: async files=>{for(const f of files){const fp=path.resolve(root,f.replace(/^\.\//,''));if(f==='./'){cacheStore.set(f,'index');continue;}if(!fs.existsSync(fp))throw Error('missing: '+f);cacheStore.set(f,fs.readFileSync(fp));}},
};
const api={
  open:async name=>{storage.set(name,cacheStore);return cache;},
  keys:async()=>[...storage.keys()],
  delete:async name=>storage.delete(name),
  match:async request=>cacheStore.get(request.url) || null
};
const sandbox={
  caches:api,
  fetch:async r=>{if(!online)throw Error('offline');return 'network';},
  self:{addEventListener:(name,cb)=>handlers[name]=cb,skipWaiting:()=>{skip=true},clients:{claim:()=>{claimed=true}}}
};
vm.createContext(sandbox);vm.runInContext(source,sandbox);
function lifecycle(kind){let work;handlers[kind]({waitUntil:p=>{work=p}});return work}
(async()=>{
  await lifecycle('install');
  if(!skip||cacheStore.size<8)throw Error('missing install/caches');
  const keys=[...cacheStore.keys()];for(const required of ['./','./index.html','./app.js','./styles.css','./manifest.webmanifest'])if(!keys.includes(required))throw Error('uncached '+required);
  await lifecycle('activate');if(!claimed)throw Error('not claimed');
  let response;
  handlers.fetch({request:{method:'GET',url:'./index.html'},respondWith:p=>{response=p}});
  const offline=await response;
  if(!offline || offline.byteLength<200)throw Error('offline cache miss');
  console.log('PASS Service worker caches all assets, activates, and serves cached HTML offline (mocked environment)');
})().catch(e=>{console.error('FAIL service worker',e);process.exit(1)});
