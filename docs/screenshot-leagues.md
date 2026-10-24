# Screenshot competition delivery and remaining gaps

This update imports the requested Argentine Primera Nacional (AR2), current Argentine Primera (AR1) and Mexican second tier (MX2), rather than substituting unrelated competitions.

AR2: 2,594 regular-stage records for 2023–2026. AR1: 438 additional 2026 regular-stage records. Only directly attributed Spanish Wikipedia rows are imported from rhinoah/futbol-argentino-data; mixed-source, neutral, elimination and penalty records are excluded. Transformed Argentine data is CC BY-SA 4.0, attributed per row to Wikipedia contributors and the publisher. The publisher's source/license document is preserved at data/football/ARGENTINA-LICENSE-DATOS.md. Code remains under the repository's existing license. Source publisher results are not official verification.

MX2: 3,717 community CC0 records in historical seasons through 2024–25. Seasons are partial. Missing 2025–26/2026–27 and the rejected 2014–15 file are not silently filled. A 2026 Venados–Durango recommendation remains unsupported by current history. Mexican text-parser score semantics retain the existing regulation-score assumptions; playoff records are historical research, not certified official outcomes.

Daily source refresh fetches the current Argentine year; weekly backfill includes prior Argentine years and the Mexico archive. Cached git clones prevent redundant full downloads. Conflicting finals are rejected atomically. The source-kind label remains distinct from CC0 and official verification. No frozen forecast has changed.

The AR2 2025 chronological monthly same-cohort evaluation compares all four existing candidates and includes 1/X/2, total/margin errors, intervals, BTTS and goal-market metrics in docs/kanit/screenshot_leagues/evaluation.json. This is retrospective, publication timestamps are unknown, and no accuracy gain or default model promotion is claimed.

## Requested items still incomplete

- Uruguay (Maldonado–Danubio), Venezuela (Caracas–Táchira): no verified redistributable dataset integrated.
- Colombia Primera B (Bogotá–Real Santander, Cundinamarca–Yumbo): Primera A history is not a substitute.
- USL League One/Championship (Hearts of Pine–Charlotte, Loudoun–Brooklyn): MLS is not a substitute.
- El Salvador (Alianza–Metapán, Águila–FAS), Honduras (Choloma–Genesis), Bolivia (Bulo Bulo–Potosí): no integrated dataset.
- Turkish clubs: the earlier last-50 audit is available, but missing seasons, cup/European fixtures and club alias splits mean true latest-50 all-competition histories are not complete.
- Calibration reports and fixed model comparisons already exist. No validated current probability calibration, lineup/injury/xG integration, or measured forward accuracy improvement is asserted.

These are explicit unresolved requirements, not completed work. No unsupported screenshot match receives invented model output. Newly available matches must still pass identity, cutoff, freshness and fixture-verification checks before freezing a forecast.
