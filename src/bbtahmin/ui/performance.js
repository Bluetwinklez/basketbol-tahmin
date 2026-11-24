"use strict";
const $ = (id) => document.getElementById(id);
let scorecard = null;
let activeSport = "basketball";

const pct = (value) =>
  typeof value === "number" && Number.isFinite(value)
    ? `${(value * 100).toFixed(1)}%`
    : "—";

const dec = (value, digits = 4) =>
  typeof value === "number" && Number.isFinite(value)
    ? value.toFixed(digits)
    : "—";

function node(tag, cls, text) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== undefined) el.textContent = text;
  return el;
}

function formatMetricWithCi(value, ci, isPercent) {
  const format = isPercent ? pct : dec;
  const main = format(value);
  if (main === "—") return "—";
  if (Array.isArray(ci) && ci.length === 2) {
    return `${main} [${format(ci[0])}, ${format(ci[1])}]`;
  }
  return main;
}

function formatCiOnly(ci, isPercent) {
  const format = isPercent ? pct : dec;
  if (Array.isArray(ci) && ci.length === 2) {
    return `95% CI [${format(ci[0])}, ${format(ci[1])}]`;
  }
  return "No CI (n = 0)";
}

function showError(message) {
  const el = $("perf-error");
  el.textContent = message;
  el.hidden = !message;
}

function buildMetricRow(leagueLabel, forecastLabel, metrics, rowClass = "") {
  const tr = node("tr", rowClass);
  const n = metrics && typeof metrics.n === "number" ? metrics.n : 0;
  const ci = (metrics && metrics.ci95) || {};
  tr.append(
    node("td", "", leagueLabel),
    node("td", "", forecastLabel),
    node("td", "", String(n)),
    node("td", "", formatMetricWithCi(metrics?.accuracy, ci.accuracy, true)),
    node("td", "", formatMetricWithCi(metrics?.log_loss, ci.log_loss, false)),
    node("td", "", formatMetricWithCi(metrics?.brier, ci.brier, false)),
  );
  return tr;
}

function buildGroupRows(leagueLabel, group) {
  const rows = [];
  if (!group) return rows;
  rows.push(buildMetricRow(leagueLabel, "Model", group.model, "perf-row-model"));
  rows.push(buildMetricRow(leagueLabel, "Always home", group.always_home));
  rows.push(
    buildMetricRow(leagueLabel, "Expanding league rate", group.expanding_rate),
  );
  const market = group.market;
  if (market && market.status === "available" && (market.metrics?.n || 0) > 0) {
    rows.push(buildMetricRow(leagueLabel, "Market", market.metrics));
    rows.push(
      buildMetricRow(
        leagueLabel,
        "Model on market games",
        market.model_same_games,
      ),
    );
  } else {
    const tr = node("tr", "perf-row-muted");
    tr.append(
      node("td", "", leagueLabel),
      node("td", "", "Market (no market data)"),
      node("td", "", "0"),
      node("td", "", "—"),
      node("td", "", "—"),
      node("td", "", "—"),
    );
    rows.push(tr);
  }
  return rows;
}

function clampPct(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, value * 100));
}

function renderCalibration(sportData) {
  const scope = $("calibration-scope").value || "total";
  const group =
    scope === "total"
      ? sportData?.total
      : sportData?.leagues?.[scope] || sportData?.total;
  const bins = group?.calibration || [];
  $("calibration-empty").hidden = bins.length > 0;
  const rows = bins.map((bin) => {
    const tr = node("tr");
    const lo = Math.round((bin.lower || 0) * 100);
    const hi = Math.round((bin.upper || 0) * 100);
    tr.append(
      node("td", "", `${lo}%–${hi}%`),
      node("td", "", String(bin.n ?? 0)),
      node("td", "", pct(bin.forecast_mean)),
      node("td", "", pct(bin.observed_frequency)),
    );
    const barCell = node("td", "perf-bar-cell");
    const stack = node("div", "perf-bar-stack");
    const fTrack = node("div", "perf-bar-track");
    const fFill = node("div", "perf-bar-fill perf-bar-forecast");
    fFill.style.width = `${clampPct(bin.forecast_mean)}%`;
    fTrack.append(fFill);
    const oTrack = node("div", "perf-bar-track");
    const oFill = node("div", "perf-bar-fill perf-bar-observed");
    oFill.style.width = `${clampPct(bin.observed_frequency)}%`;
    oTrack.append(oFill);
    stack.append(fTrack, oTrack);
    barCell.append(stack);
    tr.append(barCell);
    return tr;
  });
  $("calibration-body").replaceChildren(...rows);
}

function renderClassFrequencies(sportData) {
  const section = $("class-freq-section");
  const freqs = sportData?.total?.class_frequencies;
  if (!freqs || typeof freqs !== "object") {
    section.hidden = true;
    $("class-freq-body").replaceChildren();
    return;
  }
  const order = sportData.class_order || Object.keys(freqs);
  const rows = order
    .filter((label) => freqs[label])
    .map((label) => {
      const item = freqs[label];
      const tr = node("tr");
      tr.append(
        node("td", "", label),
        node("td", "", String(item.top_pick_n ?? 0)),
        node("td", "", pct(item.top_pick_rate)),
        node("td", "", String(item.actual_n ?? 0)),
        node("td", "", pct(item.actual_rate)),
      );
      return tr;
    });
  section.hidden = rows.length === 0;
  $("class-freq-body").replaceChildren(...rows);
}

function renderDefinitions() {
  const dl = $("definitions-list");
  const defs = scorecard?.definitions || {};
  const children = [];
  for (const [key, value] of Object.entries(defs)) {
    const label = key.replace(/_/g, " ");
    children.push(
      node("dt", "", label.charAt(0).toUpperCase() + label.slice(1)),
      node("dd", "", String(value)),
    );
  }
  dl.replaceChildren(...children);
}

function renderSport() {
  for (const btn of document.querySelectorAll(".sport-tab")) {
    const selected = btn.dataset.sport === activeSport;
    btn.setAttribute("aria-selected", String(selected));
    btn.classList.toggle("active", selected);
  }
  const sportData = scorecard?.sports?.[activeSport];
  if (!sportData) {
    $("sport-cutoff").textContent = `No scorecard data for ${activeSport}.`;
    $("sport-meta").textContent = "";
    $("perf-total-n").textContent = "—";
    $("perf-total-acc").textContent = "—";
    $("perf-total-ll").textContent = "—";
    $("perf-total-brier").textContent = "—";
    $("league-table-body").replaceChildren();
    $("league-table-empty").hidden = false;
    $("calibration-body").replaceChildren();
    $("calibration-empty").hidden = false;
    $("class-freq-section").hidden = true;
    return;
  }

  const cutoff = sportData.cutoff_utc || "unavailable";
  const classes = (sportData.class_order || []).join(", ");
  $("sport-cutoff").textContent =
    `${activeSport.charAt(0).toUpperCase() + activeSport.slice(1)} ledger cutoff (UTC): ${cutoff}`;

  const metaParts = [];
  if (classes) metaParts.push(`Class order: ${classes}`);
  if (
    typeof sportData.publisher_finals_excluded_no_verified_kickoff === "number"
  ) {
    metaParts.push(
      `Excluded ${sportData.publisher_finals_excluded_no_verified_kickoff} publisher finals without verified kickoff`,
    );
  }
  $("sport-meta").textContent = metaParts.join(" · ");

  const totalModel = sportData.total?.model;
  $("perf-total-n").textContent =
    typeof totalModel?.n === "number" ? String(totalModel.n) : "—";
  $("perf-total-note").textContent = `${Object.keys(sportData.leagues || {}).length} leagues tracked`;
  $("perf-total-acc").textContent = pct(totalModel?.accuracy);
  $("perf-total-acc-ci").textContent = formatCiOnly(
    totalModel?.ci95?.accuracy,
    true,
  );
  $("perf-total-ll").textContent = dec(totalModel?.log_loss);
  $("perf-total-ll-ci").textContent = formatCiOnly(
    totalModel?.ci95?.log_loss,
    false,
  );
  $("perf-total-brier").textContent = dec(totalModel?.brier);
  $("perf-total-brier-ci").textContent = formatCiOnly(
    totalModel?.ci95?.brier,
    false,
  );

  const rows = [];
  rows.push(...buildGroupRows("Total", sportData.total));
  const leagueEntries = Object.entries(sportData.leagues || {});
  for (const [leagueCode, group] of leagueEntries) {
    rows.push(...buildGroupRows(leagueCode, group));
  }
  $("league-table-empty").hidden = rows.length > 0;
  $("league-table-body").replaceChildren(...rows);

  const select = $("calibration-scope");
  const options = [node("option", "", "Total")];
  options[0].value = "total";
  for (const [leagueCode] of leagueEntries) {
    const opt = node("option", "", leagueCode);
    opt.value = leagueCode;
    options.push(opt);
  }
  select.replaceChildren(...options);
  select.value = "total";
  renderCalibration(sportData);
  renderClassFrequencies(sportData);
}

async function load() {
  try {
    const response = await fetch("/api/performance", { cache: "no-store" });
    if (!response.ok) {
      let detail = `Server returned ${response.status}`;
      try {
        const body = await response.json();
        if (body?.error) detail = body.error;
      } catch {}
      throw Error(detail);
    }
    scorecard = await response.json();
    showError("");
    $("data-cutoff").textContent =
      `Data cutoff (UTC): ${scorecard.data_cutoff_utc || "unavailable"}`;
    const availableSports = Object.keys(scorecard.sports || {});
    if (availableSports.length && !scorecard.sports[activeSport]) {
      activeSport = availableSports[0];
    }
    renderDefinitions();
    renderSport();
  } catch (error) {
    $("data-cutoff").textContent = "Data cutoff (UTC): unavailable";
    showError(`Could not load live scorecard: ${error.message}`);
  }
}

function init() {
  for (const btn of document.querySelectorAll(".sport-tab")) {
    btn.addEventListener("click", () => {
      activeSport = btn.dataset.sport;
      renderSport();
    });
  }
  $("calibration-scope").addEventListener("change", () => {
    renderCalibration(scorecard?.sports?.[activeSport]);
  });
  load();
}

init();
