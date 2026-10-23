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
    forecasts:[{fixture:{league:'TR1',date:'2026-10-25',home_name:'<img src=x onerror=alert(1)>',away_name:'B',source_url:'javascript:alert(1)'},prediction:{expected_home_goals:1.5,expected_away_goals:1,probabilities:{home:.45,draw:.3,away:.25},over:{'1.5':.7,'2.5':.4,'3.5':.2},both_teams_score:.5,total_goals_80:[0,5],issues:[]},result:null}]
  }})});w.eval(script);await new Promise(setImmediate);
  const text=w.document.body.textContent;
  assert.match(text,/Draw 30.0%/);assert.match(text,/Over 2.5 40.0%/);assert.match(text,/Pending · no final result/);
  assert.match(text,/0 officially verified/);assert.match(text,/Saved demonstration/);
  assert.equal(w.document.querySelectorAll('#cards img').length,0);
  assert.equal(w.document.querySelector('#cards a').getAttribute('href'),'#');
});
