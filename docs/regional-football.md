# Requested regional league history

Imported 7,538 publisher results for the five explicitly requested screenshot leagues: Uruguay Primera División (1,693), Venezuela Primera División (1,627), El Salvador Primera División (1,496), Honduras Liga Nacional (1,132) and Bolivia División Profesional (1,590).

Source: David Schoch, schochastics/football-data, data/results/games.parquet. The source is offered under Open Data Commons Attribution License v1.0 (https://opendatacommons.org/licenses/by/1-0/). These transformed records retain that attribution/license per row. Pinned revision, source file hash, capture date and source URL are in data/football/regional_collection.json. The source warns of historical errors and unresolved club merges/splits; source club identity strings are preserved alongside normalized names. These data files are not covered by the code license.

Only 2018–2023, national league records explicitly marked F (90-minute finish) are imported. Extra-time E and penalty P records, missing/fractional scores, unknown teams, and self-pairings are excluded. Duplicate identities or conflicting final scores reject the entire affected league-season file. Source score validity also passes the existing 0–30 bounds. Existing immutable forecasts remain unchanged.

This closes the absence of historical archives for these leagues, not current coverage: the source ends in 2023. No 2026 match prediction, actual latest-50 history, fixture verification, official result verification or improved forward accuracy is implied. Old and sparse histories remain subject to the model's cutoff and freshness warnings. USL, Colombian Primera B, current Mexico and Turkish missing seasons remain separate requirements.

The large, static upstream archive is not downloaded daily. Reproduction: call bbtahmin.football.regional.collect with a local checkout of the pinned source repository. No new recurring download was added.
