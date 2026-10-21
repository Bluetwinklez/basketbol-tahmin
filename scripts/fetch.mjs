import fs from 'node:fs';
const [url, target, agent] = process.argv.slice(2);
try {
 const r=await fetch(url,{headers:{'User-Agent':agent},signal:AbortSignal.timeout(45000)});
 fs.writeFileSync(target,Buffer.from(await r.arrayBuffer()));
 console.log(JSON.stringify({status:r.status,url:r.url,headers:Object.fromEntries(r.headers)}));
} catch(e) { console.error(String(e)); process.exitCode=1; }
