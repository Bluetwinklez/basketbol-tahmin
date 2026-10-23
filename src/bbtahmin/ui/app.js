"use strict";
const names = {
  ARG_LNB: 'Argentina Liga Nacional',
  ABA: 'ABA League',
  UKR: 'Ukraine SuperLeague',
  TR_BSL: 'Turkish BSL',
  ECW: 'EuroCup Women',
  FEC: 'FIBA Europe Cup',
  E: "EuroLeague",
  KBL: "Korean Basketball League",
  JP_B1: "Japan B1",
  JP_B2: "Japan B2",
  PBA_GOV: "PBA Governors Cup",
};
const $ = (id) => document.getElementById(id);
const token = document.querySelector('meta[name="app-token"]').content;
let snapshot = null,
  fetching = false,
  submitting = false,
  renderedReportKey = null,
  interactionError = null;
const fmt = (n, d = 1) =>
  typeof n === "number" && Number.isFinite(n) ? n.toFixed(d) : "—";
const percent = (n) =>
  typeof n === "number" && Number.isFinite(n)
    ? `${(n * 100).toFixed(1)}%`
    : "—";
const time = (value) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Unknown time"
    : new Intl.DateTimeFormat("en-GB", {
        timeZone: "Europe/Istanbul",
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      }).format(date);
};
function node(tag, cls, text) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== undefined) el.textContent = text;
  return el;
}
function notice(message, kind = "") {
  const el = $("notice");
  if (el.textContent !== message) el.textContent = message;
  el.className = `notice ${kind}`;
  el.hidden = !message;
}
function showError(message) {
  interactionError = message;
  notice(message, "error");
}
function settings() {
  const selected = [
    ...document.querySelectorAll("#run-leagues input:checked"),
  ].map((el) => el.value);
  $("settings-summary").textContent =
    `${selected.length} leagues · next ${$("hours").value} hours · ${$("threshold").value}% filter`;
  return {
    leagues: selected,
    hours: Number($("hours").value),
    threshold: Number($("threshold").value) / 100,
  };
}
function init() {
  for (const [code, name] of Object.entries(names)) {
    const label = node("label"),
      input = node("input");
    input.type = "checkbox";
    input.value = code;
    input.checked = true;
    label.append(
      input,
      document.createTextNode(
        ` ${name === "Korean Basketball League" ? "KBL" : name}`,
      ),
    );
    $("run-leagues").append(label);
    const option = node("option", "", name);
    option.value = code;
    $("league-filter").append(option);
  }
  for (const id of ["search", "league-filter", "passed-only"])
    $(id).addEventListener("input", renderCards);
  for (const id of ["hours", "threshold", "run-leagues"])
    $(id).addEventListener("input", settings);
  $("refresh-run").addEventListener("click", () => start(true));
  $("local-run").addEventListener("click", () => start(false));
  $("today").textContent =
    `${new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Istanbul", weekday: "short", day: "numeric", month: "short", year: "numeric" }).format(new Date())} · Istanbul`;
  load();
  setInterval(load, 2000);
}
async function load() {
  if (fetching) return;
  fetching = true;
  try {
    const response = await fetch("/api/state", { cache: "no-store" });
    if (!response.ok) throw Error(`Server returned ${response.status}`);
    snapshot = await response.json();
    render();
  } catch (error) {
    notice(
      `Connection unavailable: ${error.message}. Check that the local app is still running.`,
      "error",
    );
  } finally {
    fetching = false;
  }
}
async function start(refresh) {
  if (submitting || snapshot?.job.status === "running") return;
  const config = settings();
  if (!config.leagues.length) {
    showError("Select at least one league in Run settings.");
    return;
  }
  if (
    !Number.isInteger(config.hours) ||
    config.hours < 1 ||
    config.hours > 168 ||
    config.threshold < 0.5 ||
    config.threshold > 1
  ) {
    showError("Use 1–168 hours and a probability filter of 50–100%.");
    return;
  }
  interactionError = null;
  submitting = true;
  $("local-run").disabled = $("refresh-run").disabled = true;
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-App-Token": token },
      body: JSON.stringify({ ...config, refresh }),
    });
    const body = await response.json();
    if (!response.ok)
      throw Error(body.error || `Server returned ${response.status}`);
    await load();
  } catch (error) {
    showError(error.message);
  } finally {
    submitting = false;
    if (snapshot?.job.status !== "running")
      $("local-run").disabled = $("refresh-run").disabled = false;
  }
}
function render() {
  const r = snapshot.report,
    j = snapshot.job,
    running = j.status === "running";
  $("local-run").disabled = $("refresh-run").disabled = running || submitting;
  if (running)
    notice(
      `${j.message}. You can continue browsing the previous report.`,
      "running",
    );
  else if (j.status === "failed")
    notice(
      `Run failed: ${j.message}. The previous report and frozen records are preserved.`,
      "error",
    );
  else if (interactionError) notice(interactionError, "error");
  else if (snapshot.sample)
    notice(
      `Saved verification run · ${time(r.checked_at_utc)}. This is a historical snapshot. Run a check to create your local report.`,
    );
  else if (snapshot.report_age_minutes > 24 * 60)
    notice(
      `Saved report from ${time(r.checked_at_utc)} is older than 24 hours. Refresh sources before treating fixtures as current.`,
    );
  else if (j.status === "partial")
    notice(
      "Check completed with unresolved inputs. Review Input checks below.",
    );
  else notice("");
  const p = r?.performance || {};
  $("metric-upcoming").textContent = r ? r.upcoming.length : "—";
  $("metric-pending").textContent = r
    ? `${p.pending_games || 0} awaiting a verified final`
    : "No report loaded";
  $("metric-finals").textContent = r ? p.settled_games : "—";
  $("metric-accuracy").textContent = percent(p.winner_accuracy);
  $("accuracy-note").textContent = p.settled_games
    ? `Based on ${p.settled_games} verified finals · limited sample`
    : "Needs verified final results";
  $("metric-error").textContent = fmt(p.mean_score_mae);
  $("report-time").textContent = r
    ? `${snapshot.sample ? "Saved verification" : "Last check"}: ${time(r.checked_at_utc)} · probabilities are model estimates`
    : "Load saved fixtures or refresh sources to start.";
  const key = `${r?.checked_at_utc || "empty"}:${snapshot.sample}`;
  if (key !== renderedReportKey) {
    renderedReportKey = key;
    renderCards();
    renderResults();
    renderChecks();
  }
}
function renderCards() {
  const opened = new Set([...document.querySelectorAll('.match-card[data-event]')]
    .filter(el => el.querySelector('details')?.open).map(el => el.dataset.event));
  const r = snapshot?.report,
    query = $("search").value.trim().toLocaleLowerCase(),
    league = $("league-filter").value,
    passed = $("passed-only").checked;
  const entries = (r?.upcoming || []).filter(
    (e) =>
      (!league || e.fixture.league === league) &&
      (!passed || e.selected) &&
      `${e.fixture.home_name} ${e.fixture.away_name} ${e.fixture.home} ${e.fixture.away}`
        .toLocaleLowerCase()
        .includes(query),
  );
  $("visible-count").textContent = entries.length;
  $("empty").hidden = entries.length > 0;
  $("forecast-grid").replaceChildren(...entries.map(card));
  for (const el of document.querySelectorAll('.match-card[data-event]'))
    if (opened.has(el.dataset.event)) el.querySelector('details').open = true;
}
function card(entry) {
  const f = entry.fixture,
    p = entry.prediction,
    el = node("article", "match-card");
  el.dataset.event = `${f.league}:${f.event_id}`;
  const top = node("div", "card-top");
  top.append(
    node("span", "league-tag", (names[f.league] || f.league).toUpperCase()),
    node(
      "span",
      `pill ${entry.selected ? "good" : "review"}`,
      entry.selected ? "FILTER PASSED" : "REVIEW INPUTS",
    ),
  );
  const date = node("div", "card-time");
  date.append(
    node("span", "", time(f.start_utc)),
    node(
      "span",
      "",
      new Date(f.start_utc) <= new Date()
        ? "Started · saved forecast"
        : entry.record_status === "existing_immutable"
          ? "Original reused"
          : "Forecast frozen",
    ),
  );
  el.append(top, date);
  for (const [code, name, score, away] of [
    [f.home, f.home_name, p.ev_skor, false],
    [f.away, f.away_name, p.dep_skor, true],
  ]) {
    const row = node("div", `team-row ${away ? "away" : ""}`);
    const abbr = String(code)
      .replace(/^(KBL_|JP_|PBA_)/, "")
      .slice(0, 3)
      .toUpperCase();
    row.append(
      node("span", "team-icon", abbr),
      node("span", "team-name", name || code),
      node("span", "team-score", fmt(score)),
    );
    el.append(row);
  }
  const prob = node("div", "prob-area"),
    labels = node("div", "prob-labels"),
    track = node("div", "prob-track"),
    fill = node("div", "prob-home");
  labels.append(
    node("span", "", `Home ${percent(p.ev_kazanir)}`),
    node("span", "", `Away ${percent(1 - p.ev_kazanir)}`),
  );
  fill.style.width = `${Math.max(0, Math.min(100, p.ev_kazanir * 100))}%`;
  track.append(fill);
  prob.append(labels, track);
  el.append(prob);
  const meta = node("div", "card-meta");
  for (const [label, value] of [
    ["TOTAL", fmt(p.toplam)],
    ["HOME MARGIN", `${p.fark > 0 ? "+" : ""}${fmt(p.fark)}`],
  ]) {
    const item = node("span", "", label);
    item.append(node("strong", "", value));
    meta.append(item);
  }
  el.append(meta);
  const details = node("details"),
    summary = node("summary", "", "Forecast details"),
    body = node("div", "detail-body");
  body.append(
    node(
      "div",
      "",
      `80% total range: ${fmt(p.toplam_80?.[0])} to ${fmt(p.toplam_80?.[1])}`,
    ),
    node(
      "div",
      "",
      `80% home-margin range: ${fmt(p.fark_80?.[0])} to ${fmt(p.fark_80?.[1])}`,
    ),
    node("div", "", `Model: ${p.model}`),
    node("div", "", `Source captured: ${time(f.captured_at)}`),
  );
  const issues = [...(p.data_quality?.issues || [])];
  if (!entry.source_confirmation_fresh)
    issues.push("Source confirmation was not fresh at the recorded check.");
  if (new Date() - new Date(f.captured_at) > 24 * 3600000)
    issues.push("Source capture is now older than 24 hours.");
  if (!entry.threshold_passed)
    issues.push("Below the configured probability filter at this check.");
  if (issues.length) {
    const list = node("ul");
    for (const issue of issues) list.append(node("li", "", issue));
    body.append(list);
  } else
    body.append(
      node(
        "div",
        "",
        "Observed data checks passed. This does not validate prediction accuracy.",
      ),
    );
  try {
    const url = new URL(f.source_url);
    if (url.protocol === "https:") {
      const link = node("a", "", "Fixture source ↗");
      link.href = url.href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      body.append(link);
    }
  } catch {}
  details.append(summary, body);
  if (entry.total_estimates?.length) {
    body.append(node('p', '', 'Estimated totals · normal interval approximation, not separately calibrated'));
    for (const estimate of entry.total_estimates)
      body.append(node('div', '', `${estimate.line} points: Over ${percent(estimate.over)} / Under ${percent(estimate.under)}`));
  }
  el.append(details);
  return el;
}
function renderResults() {
  const rows = snapshot?.results || [];
  $("results-empty").hidden = rows.length > 0;
  $("results-body").replaceChildren(
    ...rows.map((row) => {
      const g = row.game,
        f = row.fixture,
        p = row.prediction,
        tr = node("tr"),
        match = node(
          "td",
          "",
          f
            ? `${f.home_name || f.home} – ${f.away_name || f.away}`
            : `${g.home} – ${g.away}`,
        );
      match.append(
        node("small", "", f ? names[f.league] || f.league : g.event_id),
      );
      tr.append(
        match,
        node(
          "td",
          "",
          p ? `${fmt(p.ev_skor)} – ${fmt(p.dep_skor)}` : "Unavailable",
        ),
      );
      const final = g.status === "final";
      tr.append(
        node(
          "td",
          "",
          final ? `${g.actual_home} – ${g.actual_away}` : "Pending",
        ),
        node(
          "td",
          "",
          final ? (g.winner_correct ? "Correct" : "Incorrect") : "—",
        ),
        node(
          "td",
          "",
          final
            ? `${fmt(g.home_absolute_error)} / ${fmt(g.away_absolute_error)}`
            : "—",
        ),
        node("td", "", final ? fmt(g.total_absolute_error) : "—"),
        node("td", "", final ? fmt(g.margin_absolute_error) : "—"),
        node(
          "td",
          "",
          final
            ? `${g.total_in_80 ? "Inside" : "Outside"} / ${g.margin_in_80 ? "Inside" : "Outside"}`
            : "—",
        ),
      );
      return tr;
    }),
  );
}
function renderChecks() {
  const r = snapshot?.report;
  $("source-checks").replaceChildren();
  const sources = Object.entries(r?.sources || {});
  if (!sources.length)
    $("source-checks").append(
      node(
        "span",
        "",
        r
          ? "Saved source snapshots · no refresh in this check"
          : "No sources checked yet",
      ),
    );
  for (const [code, outcome] of sources)
    $("source-checks").append(
      node("span", "", `${names[code] || code}: ${outcome.status}`),
    );
  const issues = [
    ...(r?.skipped || []).map(
      (s) => `${s.league || s.event_id || "Record"}: ${s.reason}`,
    ),
    ...sources
      .filter(([, s]) => s.status === "failed")
      .map(([c, s]) => `${names[c] || c}: ${s.error}`),
  ];
  $("issues").replaceChildren(...issues.map((text) => node("li", "", text)));
}
init();

