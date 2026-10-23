"use strict";
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="app-token"]').content;
let state = null, busy = false, fetching = false, interactionError = null, renderedKey = null;
const pct = n => typeof n === 'number' && Number.isFinite(n) ? `${(100*n).toFixed(1)}%` : '—';
function el(tag, text) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; return n; }
function controls() {
  const running = busy || state?.job?.status === 'running';
  $('saved').disabled = running; $('refresh').disabled = running;
  const message = interactionError || state?.job?.message || 'Ready';
  if ($('status').textContent !== message) $('status').textContent = message;
  $('status').className = `notice ${interactionError || state?.job?.status === 'failed' ? 'error' : ''}`;
  for (const link of document.querySelectorAll('.exports a')) {
    link.setAttribute('aria-disabled', String(!state?.report));
    if (!state?.report) link.removeAttribute('href'); else link.href = link.dataset.export;
  }
}
function render() {
  controls();
  const report = state?.report;
  if (!report) { $('empty').hidden = false; return; }
  $('summary').textContent = `${state.sample ? 'Saved demonstration · ' : ''}${report.forecasts.length} recorded forecasts · ${report.pending} pending · ${report.publisher_performance.games} community finals · 0 officially verified. Checked ${report.checked_at_utc}.`;
  const search = $('search').value.toLocaleLowerCase(), league = $('league').value, status = $('result-status').value;
  const opened = new Set([...document.querySelectorAll('#cards article')].filter(c => c.querySelector('details')?.open).map(c => c.dataset.event));
  const cards = [];
  for (const item of report.forecasts) {
    const f = item.fixture, p = item.prediction;
    if (league && f.league !== league) continue;
    if (status && item.status !== status) continue;
    if (search && !`${f.home_name} ${f.away_name}`.toLocaleLowerCase().includes(search)) continue;
    const card = el('article'); card.className = 'forecast-card match-card'; card.dataset.event = f.event_id || `${f.league}:${f.date}:${f.home_name}`;
    card.append(el('small', `${f.league} · ${f.date} · time unavailable`), el('h2', `${f.home_name} - ${f.away_name}`),
      el('p', `Expected goals ${p.expected_home_goals.toFixed(2)} - ${p.expected_away_goals.toFixed(2)}`),
      el('p', `Home ${pct(p.probabilities.home)} · Draw ${pct(p.probabilities.draw)} · Away ${pct(p.probabilities.away)}`),
      el('p', `Over 1.5 ${pct(p.over['1.5'])} · Over 2.5 ${pct(p.over['2.5'])} · Over 3.5 ${pct(p.over['3.5'])}`),
      el('p', `Both teams score ${pct(p.both_teams_score)} · Total 80% range ${p.total_goals_80.join('-')}`),
      el('p', item.result ? `Community final ${item.result.actual_home}-${item.result.actual_away}; outcome ${item.result.winner_correct ? 'correct' : 'incorrect'}; total error ${item.result.total_absolute_error.toFixed(2)}; margin error ${item.result.margin_absolute_error.toFixed(2)}` : 'Pending · no final result'));
    const details = el('details'); details.open = opened.has(card.dataset.event);
    details.append(el('summary', 'Model and source details'), el('p', `Model: ${p.model || 'saved model'} · recorded ${item.recorded_at_utc || 'time unavailable'}`));
    if (p.most_likely_score) details.append(el('p', `Most likely score ${p.most_likely_score.join('-')} · not an exact-score guarantee`));
    if (p.issues?.length) details.append(el('p', p.issues.join('; ')));
    const a = el('a', 'Data source'); a.href = /^https:\/\/github\.com\/openfootball\//.test(f.source_url) ? f.source_url : '#'; a.target = '_blank'; a.rel = 'noopener noreferrer';
    details.append(a); card.append(details); cards.push(card);
  }
  $('cards').replaceChildren(...cards); $('visible-count').textContent = cards.length; $('empty').hidden = cards.length > 0;
  $('issues').replaceChildren();
  for (const issue of [...report.source_errors, ...report.skipped]) $('issues').append(el('li', JSON.stringify(issue)));
}
async function poll() {
  if (fetching) return;
  fetching = true;
  try {
    const res = await fetch('/api/football', {cache:'no-store'});
    if (!res.ok) throw Error('Could not load report');
    state = await res.json();
    const leagues = state.leagues || Object.fromEntries([...new Set((state.report?.forecasts || []).map(x => x.fixture.league))].map(c => [c, c]));
    const value = $('league').value, key = JSON.stringify(Object.keys(leagues));
    if ($('league').dataset.options !== key) {
      $('league').replaceChildren(el('option', 'All football leagues')); $('league').firstChild.value = '';
      for (const [code,name] of Object.entries(leagues)) { const o = el('option', `${code} · ${name}`); o.value = code; $('league').append(o); }
      $('league').value = value; $('league').dataset.options = key;
    }
    const reportKey = `${state.report?.checked_at_utc}:${state.sample}`;
    if (reportKey !== renderedKey) { renderedKey = reportKey; render(); } else controls();
  } catch (e) { interactionError = `Connection unavailable: ${e.message}`; controls(); }
  finally { fetching = false; }
}
async function run(refresh) {
  if (busy || state?.job?.status === 'running') return;
  busy = true; interactionError = null; controls();
  try {
    const res = await fetch('/api/football/run', {method:'POST', headers:{'Content-Type':'application/json','X-App-Token':token}, body:JSON.stringify({refresh, days:7})});
    if (!res.ok) { const data = await res.json(); throw Error(data.error || 'Run failed'); }
    await poll();
  } catch (e) { interactionError = e.message; }
  finally { busy = false; controls(); }
}
$('saved').addEventListener('click', () => run(false)); $('refresh').addEventListener('click', () => run(true));
$('search').addEventListener('input', render); $('league').addEventListener('change', render); $('result-status').addEventListener('change', render);
poll(); setInterval(poll, 3000);
