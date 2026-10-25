# Licensed football supplement

The CC0 OpenFootball base snapshots remain unchanged. Rows under
`data/football/licensed_overlays/` and derived score matrices under
`data/football/licensed_source_evidence/` are adaptations of Wikipedia text/data
and are distributed under **CC BY-SA 4.0**. Attribution: Wikipedia contributors;
extraction and explicit fixture matching by this project. Each row includes its
page URL (which links to contributor history), capture time, source hash and the
license URL https://creativecommons.org/licenses/by-sa/4.0/ . Do not relabel these
rows CC0. No images or other separately licensed media are copied.

Reuse guidance: https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use#7._Licensing_of_Content .
The parser requires the individual source page's CC BY-SA 4.0 license link.
Score matrices do not supply match dates. A row enters the supplement only when
the existing archive's exact league, season, ordered clubs and date match one
unique independently observed publisher final, and both sources agree on score.
Publisher scores are used to check the licensed scores, not as a training feed.
An independently checked date may correct a training overlay only with its
explicit original date retained. The frozen forecast stays quarantined for a
separate pregame-timing review; no original forecast is rewritten or
automatically awarded a correct result. Source/score conflicts preserve the prior
league supplement. These are community/publisher observations, not official
verification or certified calendar completeness.

`python scripts/inspect_wikipedia_football.py` inspects current matrices;
`python scripts/confirm_football_fixtures.py --lookback 40` checks existing fixture
days for an initial limited backfill; `python scripts/collect_licensed_football.py`
performs the validated import. Normal daily confirmation uses a two-day lookback.
