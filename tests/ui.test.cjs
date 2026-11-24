const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { JSDOM } = require("jsdom");

const html = fs
  .readFileSync("src/bbtahmin/ui/index.html", "utf8")
  .replace("__CSRF_TOKEN__", "test-token");
const script = fs.readFileSync("src/bbtahmin/ui/app.js", "utf8");
function entry(league, home, selected) {
  return {
    fixture: {
      event_id: league + "_1",
      league,
      home,
      away: "Away",
      home_name: home,
      away_name: "Away",
      start_utc: "2026-10-23T17:00:00Z",
      captured_at: "2026-10-23T12:00:00Z",
      source_url: "https://example.org/game",
    },
    prediction: {
      ev_kazanir: 0.76,
      ev_skor: 90,
      dep_skor: 80,
      toplam: 170,
      fark: 10,
      toplam_80: [140, 200],
      fark_80: [-5, 25],
      model: "score",
      data_quality: { issues: [] },
    },
    selected,
    threshold_passed: true,
    source_confirmation_fresh: true,
    record_status: "new_immutable",
  };
}
function state() {
  return {
    sample: false,
    report_age_minutes: 1,
    job: { status: "idle", message: "Ready" },
    results: [],
    report: {
      checked_at_utc: "2026-10-23T12:00:00Z",
      upcoming: [entry("E", "Zalgiris", true), entry("KBL", "Seoul", false)],
      performance: {
        settled_games: 0,
        pending_games: 2,
        winner_accuracy: null,
        mean_score_mae: null,
      },
      sources: {},
      skipped: [],
    },
  };
}
async function setup(t) {
  let value = state(),
    poll,
    request = null,
    postError = null;
  const dom = new JSDOM(html, {
      url: "http://127.0.0.1:8765",
      runScripts: "outside-only",
    }),
    w = dom.window;
  w.setInterval = (fn) => {
    poll = fn;
    return 1;
  };
  w.fetch = async (path, options) => {
    if (options?.method === "POST") {
      request = JSON.parse(options.body);
      if (postError)
        return {
          ok: false,
          status: 409,
          json: async () => ({ error: postError }),
        };
      value.job = { status: "running", message: "Checking fixtures" };
      return {
        ok: true,
        status: 202,
        json: async () => ({ status: "running" }),
      };
    }
    return { ok: true, json: async () => structuredClone(value) };
  };
  w.eval(script);
  await new Promise(setImmediate);
  t.after(() => w.close());
  return {
    w,
    doc: w.document,
    set: (s) => (value = s),
    state: () => value,
    poll: () => poll(),
    request: () => request,
    error: (e) => (postError = e),
    flush: () => new Promise(setImmediate),
  };
}

test("model probability is never substituted for unsettled accuracy", async (t) => {
  const a = await setup(t);
  assert.equal(a.doc.querySelector("#metric-accuracy").textContent, "—");
  assert.equal(a.doc.querySelector("#metric-finals").textContent, "0");
  assert.match(a.doc.querySelector(".prob-labels").textContent, /76.0%/);
  assert.equal(a.doc.querySelectorAll(".match-card").length, 2);
});
test("search, league and recorded-filter controls include rejected forecasts by default", async (t) => {
  const a = await setup(t),
    d = a.doc;
  const search = d.querySelector("#search");
  search.value = "Seoul";
  search.dispatchEvent(new a.w.Event("input"));
  assert.equal(d.querySelectorAll(".match-card").length, 1);
  search.value = "";
  search.dispatchEvent(new a.w.Event("input"));
  const filter = d.querySelector("#passed-only");
  filter.checked = true;
  filter.dispatchEvent(new a.w.Event("input"));
  assert.equal(d.querySelectorAll(".match-card").length, 1);
  filter.checked = false;
  filter.dispatchEvent(new a.w.Event("input"));
  const league = d.querySelector("#league-filter");
  league.value = "KBL";
  league.dispatchEvent(new a.w.Event("input"));
  assert.match(d.querySelector(".match-card").textContent, /Seoul/);
});
test("periodic status polling preserves an expanded forecast card", async (t) => {
  const a = await setup(t),
    details = a.doc.querySelector(".match-card details");
  details.open = true;
  await a.poll();
  assert.equal(details.isConnected, true);
  assert.equal(details.open, true);
});
test("provider names and non-HTTPS links cannot become executable markup", async (t) => {
  const a = await setup(t),
    s = a.state();
  s.report.checked_at_utc = "2026-10-23T12:01:00Z";
  s.report.upcoming[0].fixture.home_name = "<img src=x onerror=alert(1)>";
  s.report.upcoming[0].fixture.source_url = "javascript:alert(1)";
  a.set(s);
  await a.poll();
  assert.equal(a.doc.querySelectorAll(".match-card img").length, 0);
  assert.match(a.doc.querySelector(".team-name").textContent, /<img/);
  assert.equal(
    a.doc.querySelector(".match-card").querySelector("details a"),
    null,
  );
});
test("a saved-source run sends validated selections and stays nonblocking", async (t) => {
  const a = await setup(t);
  for (const box of a.doc.querySelectorAll("#run-leagues input"))
    box.checked = box.value === "E";
  a.doc.querySelector("#hours").value = "24";
  a.doc.querySelector("#threshold").value = "70";
  a.doc.querySelector("#local-run").click();
  await a.flush();
  assert.deepEqual(a.request(), {
    leagues: ["E"],
    hours: 24,
    threshold: 0.7,
    refresh: false,
  });
  assert.equal(a.doc.querySelector("#refresh-run").disabled, true);
  assert.equal(a.doc.querySelectorAll(".match-card").length, 2);
});
test("request failures preserve prior report and show an actionable error", async (t) => {
  const a = await setup(t);
  a.error("A run is already in progress");
  a.doc.querySelector("#local-run").click();
  await a.flush();
  assert.match(
    a.doc.querySelector("#notice").textContent,
    /already in progress/,
  );
  assert.equal(a.doc.querySelectorAll(".match-card").length, 2);
  assert.equal(a.doc.querySelector("#local-run").disabled, false);
  await a.poll();
  assert.match(
    a.doc.querySelector("#notice").textContent,
    /already in progress/,
  );
});
test("final outcome and each point error retain their own columns", async (t) => {
  const a = await setup(t),
    s = a.state(),
    e = entry("E", "Home", true);
  s.report.checked_at_utc = "2026-10-23T13:00:00Z";
  s.report.performance = {
    settled_games: 1,
    pending_games: 0,
    winner_accuracy: 1,
    mean_score_mae: 3.5,
  };
  s.results = [
    {
      fixture: e.fixture,
      prediction: e.prediction,
      game: {
        home: "H",
        away: "A",
        status: "final",
        actual_home: 85,
        actual_away: 82,
        winner_correct: true,
        home_absolute_error: 5,
        away_absolute_error: 2,
        total_absolute_error: 3,
        margin_absolute_error: 7,
        total_in_80: true,
        margin_in_80: false,
      },
    },
  ];
  a.set(s);
  await a.poll();
  const cells = [...a.doc.querySelectorAll("#results-body td")].map(
    (el) => el.textContent,
  );
  assert.deepEqual(cells.slice(1), [
    "90.0 – 80.0",
    "85 – 82",
    "Correct",
    "5.0 / 2.0",
    "3.0",
    "7.0",
    "Inside / Outside",
  ]);
  assert.equal(a.doc.querySelector("#metric-accuracy").textContent, "100.0%");
  assert.match(
    a.doc.querySelector("#accuracy-note").textContent,
    /limited sample/,
  );
});
test("saved verification and failed provider outcomes are visibly distinct", async (t) => {
  const a = await setup(t),
    s = a.state();
  s.sample = true;
  s.report.sources = { E: { status: "failed", error: "HTTP 403" } };
  a.set(s);
  await a.poll();
  assert.match(
    a.doc.querySelector("#notice").textContent,
    /historical snapshot/,
  );
  assert.match(a.doc.querySelector("#issues").textContent, /HTTP 403/);
  assert.match(a.doc.querySelector("#source-checks").textContent, /failed/);
});

test('football board separates draws, goal markets and unverified results', async (t) => {
  const html=fs.readFileSync('src/bbtahmin/ui/football.html','utf8').replace('__CSRF_TOKEN__','test-token');
  const script=fs.readFileSync('src/bbtahmin/ui/football.js','utf8');
  const dom=new JSDOM(html,{url:'http://127.0.0.1:8765/football',runScripts:'outside-only'});t.after(()=>dom.window.close());
  const w=dom.window;w.setInterval=()=>1;
  w.fetch=async()=>({ok:true,json:async()=>({sample:true,job:{status:'idle',message:'Ready'},report:{
    checked_at_utc:'2026-10-23T12:00Z',pending:1,publisher_performance:{games:0},source_errors:[],skipped:[],
    forecasts:[{fixture:{league:'TR1',date:'2026-10-25',home_name:'<img src=x onerror=alert(1)>',away_name:'B',source_url:'javascript:alert(1)'},prediction:{expected_home_goals:1.5,expected_away_goals:1,predicted_outcome:'home',probabilities:{home:.45,draw:.3,away:.25},over:{'1.5':.7,'2.5':.4,'3.5':.2},both_teams_score:.5,total_goals_80:[0,5],issues:[]},result:null}]
  }})});w.eval(script);await new Promise(setImmediate);
  const text=w.document.body.textContent;
  const card=w.document.querySelector('#cards article');
  assert.match(card.textContent,/Top pick: Home · Draw 30\.0%/);
  assert.match(card.textContent,/Best double chance: 1X 75\.0%/);
  assert.match(text,/A draw can be nearly as likely as the top pick/);
  assert.match(text,/Over 2.5 40.0%/);assert.match(text,/Pending · no final result/);
  assert.match(text,/0 officially verified/);assert.match(text,/Saved demonstration/);
  assert.equal(w.document.querySelectorAll('#cards img').length,0);
  assert.equal(w.document.querySelector('#cards a').getAttribute('href'),'#');
});

test('football date conflicts remain visible in pending and review filters', async (t) => {
  const html=fs.readFileSync('src/bbtahmin/ui/football.html','utf8');
  const dom=new JSDOM(html,{url:'http://127.0.0.1:8765/football',runScripts:'outside-only'});
  t.after(()=>dom.window.close());const w=dom.window;w.setInterval=()=>1;
  w.fetch=async()=>({ok:true,json:async()=>({job:{status:'idle'},report:{checked_at_utc:'2026-10-25T12:00Z',pending:1,publisher_performance:{games:0},source_errors:[],skipped:[],forecasts:[{
    status:'fixture_review_required',fixture:{event_id:'x',league:'TR1',date:'2026-10-25',home_name:'A',away_name:'B',source_url:''},
    prediction:{expected_home_goals:1,expected_away_goals:1,probabilities:{home:.4,draw:.3,away:.3},over:{'1.5':.6,'2.5':.4,'3.5':.2},both_teams_score:.5,total_goals_80:[0,4]},
    fixture_review:{observed_start_utc:'2026-10-26T18:30Z',source_url:'https://www.espn.com/soccer/game/_/gameId/1'},result:null}]}})});
  w.eval(fs.readFileSync('src/bbtahmin/ui/football.js','utf8'));await new Promise(setImmediate);
  assert.match(w.document.querySelector('#cards').textContent,/Review required.*2026-10-26/);
  for(const filter of ['pending','fixture_review_required']) {
    const select=w.document.getElementById('result-status');select.value=filter;select.dispatchEvent(new w.Event('change'));
    assert.equal(w.document.querySelectorAll('#cards article').length,1);
  }
});

test('performance page renders sport tabs, baselines, market availability, zero-game leagues and calibration', async (t) => {
  const perfHtml = fs.readFileSync('src/bbtahmin/ui/performance.html', 'utf8');
  const perfScript = fs.readFileSync('src/bbtahmin/ui/performance.js', 'utf8');
  const emptyMetrics = { n: 0, accuracy: null, log_loss: null, brier: null, ci95: { accuracy: null, log_loss: null, brier: null } };
  const sampleMetric = (n, acc, ll, brier) => ({
    n, accuracy: acc, log_loss: ll, brier,
    ci95: { accuracy: [acc - 0.1, acc + 0.1], log_loss: [ll - 0.05, ll + 0.05], brier: [brier - 0.02, brier + 0.02] },
  });
  const syntheticScorecard = {
    spec: 'live-scorecard-v1',
    data_cutoff_utc: '2026-11-23T18:40:38+00:00',
    definitions: { cohort: 'Synthetic cohort <img src=x onerror=alert(1)>' },
    sports: {
      basketball: {
        cutoff_utc: '2026-11-23T18:39:45+00:00',
        class_order: ['home', 'away'],
        total: {
          model: sampleMetric(10, 0.7, 0.58, 0.2),
          always_home: sampleMetric(10, 0.5, 14.0, 0.4),
          expanding_rate: sampleMetric(10, 0.6, 0.69, 0.25),
          market: {
            status: 'available',
            metrics: sampleMetric(8, 0.75, 0.55, 0.19),
            model_same_games: sampleMetric(8, 0.625, 0.6, 0.21),
          },
          calibration: [
            { lower: 0.5, upper: 0.6, n: 6, forecast_mean: 0.55, observed_frequency: 0.667 },
            { lower: 0.9, upper: 1.0, n: 0, forecast_mean: null, observed_frequency: null },
          ],
        },
        leagues: {
          ABA: {
            model: sampleMetric(10, 0.7, 0.58, 0.2),
            always_home: sampleMetric(10, 0.5, 14.0, 0.4),
            expanding_rate: sampleMetric(10, 0.6, 0.69, 0.25),
            market: {
              status: 'available',
              metrics: sampleMetric(8, 0.75, 0.55, 0.19),
              model_same_games: sampleMetric(8, 0.625, 0.6, 0.21),
            },
            calibration: [
              { lower: 0.5, upper: 0.6, n: 6, forecast_mean: 0.55, observed_frequency: 0.667 },
            ],
          },
        },
      },
      football: {
        cutoff_utc: '2026-11-23T18:40:38+00:00',
        class_order: ['home', 'draw', 'away'],
        publisher_finals_excluded_no_verified_kickoff: 5,
        kickoff_exclusions_by_league: { TR1: 5 },
        total: {
          model: sampleMetric(12, 0.583, 0.95, 0.56),
          always_home: sampleMetric(12, 0.417, 19.2, 1.1),
          expanding_rate: sampleMetric(12, 0.417, 1.0986, 0.6667),
          market: { status: 'no market data', metrics: emptyMetrics, model_same_games: emptyMetrics },
          calibration: [
            { lower: 0.3, upper: 0.4, n: 4, forecast_mean: 0.38, observed_frequency: 0.5 },
            { lower: 0.9, upper: 1.0, n: 0, forecast_mean: null, observed_frequency: null },
          ],
          class_frequencies: {
            home: { top_pick_n: 8, top_pick_rate: 0.667, actual_n: 5, actual_rate: 0.417 },
            draw: { top_pick_n: 0, top_pick_rate: 0.0, actual_n: 3, actual_rate: 0.25 },
            away: { top_pick_n: 4, top_pick_rate: 0.333, actual_n: 4, actual_rate: 0.333 },
          },
        },
        leagues: {
          DE1: {
            model: sampleMetric(12, 0.583, 0.95, 0.56),
            always_home: sampleMetric(12, 0.417, 19.2, 1.1),
            expanding_rate: sampleMetric(12, 0.417, 1.0986, 0.6667),
            market: { status: 'no market data', metrics: emptyMetrics, model_same_games: emptyMetrics },
            calibration: [{ lower: 0.3, upper: 0.4, n: 4, forecast_mean: 0.38, observed_frequency: 0.5 }],
          },
          TR1: {
            model: emptyMetrics,
            always_home: emptyMetrics,
            expanding_rate: emptyMetrics,
            market: { status: 'no market data', metrics: emptyMetrics, model_same_games: emptyMetrics },
            calibration: [{ lower: 0.3, upper: 0.4, n: 0, forecast_mean: null, observed_frequency: null }],
          },
        },
      },
    },
  };
  const dom = new JSDOM(perfHtml, { url: 'http://127.0.0.1:8765/performance', runScripts: 'outside-only' });
  t.after(() => dom.window.close());
  const w = dom.window;
  w.fetch = async (url) => {
    assert.equal(url, '/api/performance');
    return { ok: true, json: async () => structuredClone(syntheticScorecard) };
  };
  w.eval(perfScript);
  await new Promise(setImmediate);

  const d = w.document;
  assert.match(d.querySelector('#data-cutoff').textContent, /2026-11-23T18:40:38\+00:00/);
  assert.match(d.body.textContent, /Baselines are on the same games\. This is not evidence of beating the market\./);
  assert.equal(d.querySelectorAll('img').length, 0);

  const bbText = d.querySelector('#league-table-body').textContent;
  assert.match(bbText, /Total/);
  assert.match(bbText, /ABA/);
  assert.match(bbText, /Model/);
  assert.match(bbText, /Always home/);
  assert.match(bbText, /Expanding league rate/);
  assert.match(bbText, /Market/);
  assert.match(bbText, /Model on market games/);
  assert.match(bbText, /70\.0%/);
  assert.match(d.querySelector('#calibration-body').textContent, /50%–60%/);
  assert.match(d.querySelector('#calibration-body').textContent, /90%–100%/);
  assert.equal(d.querySelector('#class-freq-section').hidden, true);

  d.querySelector('#tab-football').click();
  const fbText = d.querySelector('#league-table-body').textContent;
  assert.match(fbText, /DE1/);
  assert.match(fbText, /TR1/);
  assert.match(fbText, /no market data/);
  assert.doesNotMatch(fbText, /NaN/);
  const tr1Rows = [...d.querySelectorAll('#league-table-body tr')].filter((tr) => tr.firstChild.textContent === 'TR1');
  assert.equal(tr1Rows.length, 4);
  assert.equal(tr1Rows[0].children[2].textContent, '0');
  assert.equal(tr1Rows[0].children[3].textContent, '—');
  assert.equal(d.querySelector('#class-freq-section').hidden, false);
  assert.match(d.querySelector('#sport-meta').textContent, /Excluded 5 publisher finals/);
});
