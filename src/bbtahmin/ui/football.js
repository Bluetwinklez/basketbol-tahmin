"use strict";
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="app-token"]').content;
let state=null, busy=false;
const pct = n => `${(100*n).toFixed(1)}%`;
function el(tag,text) {const n=document.createElement(tag); if(text!==undefined)n.textContent=text;return n;}
function render() {
  const report=state?.report;
  const running=busy||state?.job?.status==='running';
  $('saved').disabled=running;$('refresh').disabled=running;
  $('status').textContent=state?.job?.message||'Ready';
  if(!report){$('cards').replaceChildren();$('issues').replaceChildren();$('summary').textContent='No saved forecasts for this model. Run saved sources or refresh to create its separate ledger.';return;}
  $('summary').textContent=`${state.sample?'Saved demonstration · ':''}${report.forecasts.length} recorded forecasts · ${report.pending} pending · ${report.publisher_performance.games} community finals · 0 officially verified. Checked ${report.checked_at_utc}.`;
  const search=$('search').value.toLocaleLowerCase();const league=$('league').value;
  $('cards').replaceChildren();
  for(const item of report.forecasts) {
    const f=item.fixture,p=item.prediction;
    if(league&&f.league!==league)continue;
    if(search&&!`${f.home_name} ${f.away_name}`.toLocaleLowerCase().includes(search))continue;
    const card=el('article');card.className='forecast-card';
    card.append(el('small',`${f.league} · ${f.date} · time unavailable`),el('h2',`${f.home_name} – ${f.away_name}`),
      el('p',`Expected goals ${p.expected_home_goals.toFixed(2)} – ${p.expected_away_goals.toFixed(2)}`),
      el('p',`Home ${pct(p.probabilities.home)} · Draw ${pct(p.probabilities.draw)} · Away ${pct(p.probabilities.away)}`),
      el('p',`Over 1.5 ${pct(p.over['1.5'])} · Over 2.5 ${pct(p.over['2.5'])} · Over 3.5 ${pct(p.over['3.5'])}`),
      el('p',`Both teams score ${pct(p.both_teams_score)} · Total 80% range ${p.total_goals_80.join('–')}`),
      el('p',item.result?`Community final ${item.result.actual_home}–${item.result.actual_away}; outcome ${item.result.winner_correct?'correct':'incorrect'}; total error ${item.result.total_absolute_error.toFixed(2)}; margin error ${item.result.margin_absolute_error.toFixed(2)}`:'Pending · no final result'));
    if(p.issues.length)card.append(el('p',p.issues.join('; ')));
    const a=el('a','Data source');a.href=/^https:\/\/github\.com\/openfootball\//.test(f.source_url)?f.source_url:'#';a.target='_blank';a.rel='noopener noreferrer';card.append(a);$('cards').append(card);
  }
  $('issues').replaceChildren();
  for(const issue of [...report.source_errors,...report.skipped])$('issues').append(el('li',JSON.stringify(issue)));
}
async function poll() {
  try {const res=await fetch('/api/football?model='+encodeURIComponent($('model').value),{cache:'no-store'});if(!res.ok)throw Error('Could not load report');state=await res.json();
    const leagues=[...new Set((state.report?.forecasts||[]).map(x=>x.fixture.league))].sort();
    const value=$('league').value;$('league').replaceChildren(el('option','All football leagues'));$('league').firstChild.value='';
    for(const code of leagues){const o=el('option',code);o.value=code;$('league').append(o);}$('league').value=value;render();
  }catch(e){$('status').textContent=e.message;}
}
async function run(refresh) {
  if(busy||state?.job?.status==='running')return;busy=true;render();
  try {const res=await fetch('/api/football/run',{method:'POST',headers:{'Content-Type':'application/json','X-App-Token':token},body:JSON.stringify({refresh,days:7,model:$('model').value})});if(!res.ok){const data=await res.json();throw Error(data.error||'Run failed');}await poll();}
  catch(e){$('status').textContent=e.message;}finally{busy=false;$('saved').disabled=false;$('refresh').disabled=false;}
}
$('saved').addEventListener('click',()=>run(false));$('refresh').addEventListener('click',()=>run(true));
$('model').addEventListener('change',poll);
$('search').addEventListener('input',render);$('league').addEventListener('change',render);
poll();setInterval(poll,3000);
