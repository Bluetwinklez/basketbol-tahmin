# Shadow experiment identity

The `paired-forward-policy-v4` protocol identifies a paired cohort by its frozen
policy, numeric package versions, and `prediction_code_sha256`. The hash uses
the sorted repository-relative paths and raw bytes of the Python files listed
in `PREDICTION_MODULES` in `prospective.py`. The scope includes model fitting,
feature construction, calibration, team identity and runtime history loading,
eligibility checks, and metrics used for policy and paired comparisons.

Changes confined to collectors, fixture transport, exports, scorecards, or UI
can reuse the current cohort. Modules that combine collection with logic used at
prediction time stay in scope. Every new Python file under `src/bbtahmin/` needs
an explicit classification. The test lists excluded files with their reasons.
When changing an excluded file, review whether its role has changed as well.
The cycle continues to record its existing input hashes with each pair and
include its script hash and frozen pipeline registry in the policy.

The first v4 registration starts a new cohort. Earlier cohorts retain their
original pairs and remain available for settlement, with full-source snapshots
verified against their original digests. V4 snapshots store and verify the
scoped source bytes. Native basketball and football frozen forecasts and
evaluation scripts continue to use the full-source `fingerprint()`.
