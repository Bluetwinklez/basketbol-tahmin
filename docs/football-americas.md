# Americas football expansion

Added 3,344 CC0 community finals: Brazil Série A 2,937, Argentina Primera 240 and Colombia Primera A 167. Sources are pinned OpenFootball revisions, with row URLs, capture times, date precision and file hashes in the separate collection reports. These are not official results. Argentina and Colombia only have partial 2025 coverage; their 2026 source files are absent. Brazil 2020 is rejected because its dates cross the calendar-season boundary; no dates are silently reassigned.

The calendar collector and daily/weekly refresh now support BR1, AR1 and CO1 independently of BR2 and European seasons. Shared source clones are reused within a refresh. Conflicting finals retain the previous archive. Existing frozen forecasts remain unchanged.

Brazil Série A's 2025 season is evaluated on identical monthly cohorts for baseline, opponent, opponent_dc and ensemble, using only earlier dates. Evidence includes three-way log loss/Brier, goal-market accuracy/Brier, BTTS, total/margin errors and interval coverage in `docs/kanit/americas/evaluation.json`. This measures the newly supported league; it does not prove that adding more data improves future accuracy and does not change the default model.

Screenshot limitations: Uruguay, Venezuela, Mexico expansion league and Argentina Primera Nacional remain unsupported. Colombia Primera A does not support Primera B teams. USL competitions, El Salvador, Honduras and Bolivia also remain unsupported. No bookmaker odds are represented as model predictions. Club logos have not been imported: this change concerns league data, not licensed branding assets.
