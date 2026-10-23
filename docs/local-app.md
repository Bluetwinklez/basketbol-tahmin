# Local basketball application

The browser interface uses the same models, diagnostic gates and immutable forecast ledger as the command line. It adds a match board, search and league filters, forecast intervals, a results/error table and JSON/CSV/Markdown downloads. It does not change model selection or establish an accuracy improvement.

## Start

From the repository root, using Python 3.12+:

```bash
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
python -m bbtahmin app
```

The command opens `http://127.0.0.1:8765` in your browser. There are no additional runtime web dependencies and no frontend build step. The HTML, CSS and JavaScript are included in the Python installation package.

```bash
# Print the address without opening a browser.
python -m bbtahmin app --no-browser
# Choose another port if the default is in use.
python -m bbtahmin app --port 8766
# Continue the same ledger used by a previous command-line run.
python -m bbtahmin app --cikti rapor/my-ledger
```

The server binds to IPv4 loopback on the computer where it runs. Run it from the repository root so the models, source snapshots and original prospective records are available. Stop the server with Ctrl+C; an active model task is allowed to finish before shutdown.

## Daily use

1. If no local report exists, the panel labels the checked-in verification run as a **saved historical snapshot**. It is not presented as live data.
2. Open **Run settings** and choose leagues, a 1–168 hour horizon and a probability filter.
3. **Use saved sources** checks local snapshots and runs the existing forecasting/settlement workflow without provider requests. **Refresh & run** also refreshes the selected public sources. Japanese refreshes check all active-season pages and can take several minutes.
4. Browse forecasts while the task runs. One task can run at a time. Model/provider failures preserve the previous report and forecast files.
5. Review **Results & point errors** after another check. Pending/unverified results never enter measured accuracy. With no finals, accuracy remains unavailable.

Search, displayed-league filters and **Passed recorded filter only** change the view; they do not delete rejected forecasts or recalculate historical selections. The probability input is an estimated model threshold, not a promised success rate. Cards distinguish saved forecasts whose tipoff has already passed. Displayed times use Europe/Istanbul.

Forecast details include total and margin intervals, capture time, the model name, input issues and an HTTPS source link. The results table keeps team, total and margin errors separate. JSON retains full signed/percentage errors and probability metrics; CSV contains the main numeric comparison fields. CSV provider labels are escaped against spreadsheet-formula execution.

The default ledger is `rapor/daily`, shared with `gunluk`. Its immutable forecast files and timestamped checks are local and ignored by Git. Keep the same directory and back it up to retain your prospective history. Original checked-in EuroLeague forecasts are automatically reused. See [the daily workflow](daily-workflow.md) for timestamp, freshness, identity and PBA settlement limits.

## Implementation and checks

The HTTP service accepts only fixed application routes and validated run settings. Browser requests cannot choose output paths or execute shell commands. Host validation and a per-session request token protect the local mutation endpoint; cross-origin requests are rejected. Rendering uses text nodes for provider-owned values.

```bash
python -m pytest -q
# Optional developer-only DOM tests; Node 22 is used in CI.
npm ci --no-audit --no-fund
npm run test:ui
```

The Python suite covers local HTTP routing, exports, request validation, concurrent-job rejection and failure preservation. DOM tests cover search/filter behavior, input escaping, pending versus observed accuracy, separate error columns, request errors, and keeping details expanded across polling. These are software/DOM tests, not rendered-browser visual verification. Both Python and UI suites run in GitHub Actions.

The integration check exercised the actual local server with saved-source and refreshed EuroLeague runs. A remote test browser could not reach the isolated loopback server, so rendered desktop/mobile visual verification remains incomplete. The responsive styles are included, but a visual pass on the user's local browser is still needed. [Recorded validation](kanit/local_app/validation.json).


## Added competitions

The league selector now includes senior ABA League, EuroCup Women and FIBA Europe Cup alongside the original five daily competitions. Choose a 168-hour horizon to include next week's European cup fixtures. Data refresh and failures follow the same background workflow. Ukraine, Sweden and Turkey are still outside this trained daily model; the application does not substitute another league's weights for them.
