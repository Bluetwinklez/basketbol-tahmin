# Turkish last-50 history and additional leagues

The last-50 audit exports all available Süper Lig team identities, their most recent up to 50 earlier finals, win/draw/loss and goals for/against, and per-match provenance. It excludes same-day results, unfinished games and other leagues. Missing counts are explicit. Run `PYTHONPATH=src python scripts/audit_turkish_last50.py`; evidence lives in `docs/kanit/turkish_last50/coverage.json.gz`.

This is the last 50 **available league records**, not proof of each Turkish club's actual latest 50 games. Cup and European games are absent, seasons are partial, club names may have unresolved aliases, and 2021–22/2022–23 Süper Lig source files are missing. No old or missing fixture is invented to fill a quota. No new Turkish finals were imported in this change.

Added 1,391 CC0 community finals across MLS (164), Japan J1 (748) and China Super League (479). Each has its own league identity, pinned source paths and refresh report. These are partial historical archives; no current 2026 source is supplied. MLS does not cover USL League One or Championship.

Historical licensed archives for Uruguay, Venezuela, Mexico expansion, Argentina Primera Nacional, El Salvador, Honduras and Bolivia were subsequently integrated; see screenshot-leagues.md and regional-football.md. Their current-season and fixture gaps remain separate. This release increases auditable coverage and exposes gaps; it makes no accuracy improvement claim and changes neither the default prediction model nor frozen forecasts. Data completeness must be established before testing an actual latest-50 feature.
