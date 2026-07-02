---
name: data-development
description: Given a raw CSV or dataset-spec.yaml, run the EPAM ADLC bronze-to-gold
  workflow and deliver it as a single executed Jupyter notebook (one notebook per
  pipeline, matching this repo's notebook convention) — land bronze, clean to silver
  (record row-count math), aggregate to gold metrics, generate and force-test the DQ
  suite, and emit a lineage record. Inputs: raw CSV / dataset-spec.yaml, 00-data-prd.md,
  contract.yaml. Outputs: <pipeline>.ipynb (executed, charts embedded), silver/*.parquet,
  gold/*.parquet, DQ certificate, lineage-diagram.md. Use this instead of the `data`
  skill when the deliverable should be a runnable notebook rather than standalone .py
  scripts. NOT for data-classification, retention, source-of-truth, metric sign-off,
  or DQ blocker-vs-warning calls.
---

# Data development — notebook-delivered pipeline
EPAM ADLC spine: Learn → Plan → Validate → Build → Verify → Deploy → Operate → Observe.

**Goal.** Turn a raw source into governed gold tables that pass the DQ suite and
carry a lineage record any consumer can trace — delivered as ONE executed Jupyter
notebook (generator/silver/gold/DQ/serve cells) plus the parquet layers and
governance artifacts.

**Inputs & outputs.** In: raw CSV / `dataset-spec.yaml`, `00-data-prd.md`,
`contract.yaml`. Out: `<pipeline>.ipynb` (executed end-to-end, outputs + charts
embedded), `silver/*.parquet` (row-count math recorded), `gold/*.parquet`, DQ
certificate (force-tested), `lineage-diagram.md`.
**Tools.** DuckDB / SQL for transforms; Python for ingestion + DQ; `jupyter
nbconvert --to notebook --execute --inplace` to run and bake outputs; no
production-data access without a named approver.

<!-- chain:rules:start guide=".ai-run/guides/data/database-patterns.md" topic="Data contracts + lineage rules" -->
## Decision rules

| ✅ DO | ❌ DON'T |
|-------|----------|
| Deliver one executed `.ipynb` with cells for generator/land, silver, gold, DQ, serve — matching the repo's existing notebooks | Ship a pile of standalone `.py` scripts when the deliverable is meant to be a notebook |
| Execute the notebook end-to-end and confirm zero error outputs before declaring done | Commit a notebook whose cells were never actually run |
| Record silver = bronze − nulls − duplicates as a counted row-math line in a cell output | Publish a silver table with no row-count reconciliation |
| Force-test every DQ check against ≥1 injected violation before trusting a clean pass | Trust a passing DQ run that has never fired on a known-bad row |
| Trace every gold metric to a formula + grain in `00-data-prd.md` or a metric card | Author a gold metric whose denominator or grain isn't written down |
| Name ≥1 source AND ≥1 consumer in the lineage record before serving | Serve a gold table with a lineage record missing either end |
| For Plotly charts in the notebook, set `pio.renderers.default = "notebook"` before `fig.show()` | Rely on the default renderer's `application/vnd.plotly.v1+json` mimetype (won't render in VS Code / GitHub / nbconvert HTML) |

**Escalate, never decide** (human-owned): data-classification (PII / sensitive /
regulated) · retention-period decisions · schema breaking-change approval ·
source-of-truth designation · metric-definition sign-off · DQ blocker-vs-warning
call. Stop-and-ask when: a column matches a PII pattern (email, name, government
ID) and has no classification tag · two source systems disagree on a metric value ·
a schema diff renames or retypes a column a consumer reads · a DQ check fails on a
gold table about to publish · a metric's grain or denominator isn't written in the
PRD or a metric card.
<!-- chain:rules:end -->

**How to check it's working.** Given `dataset-spec.yaml` + raw CSV: the notebook
runs end-to-end with no error cells; grain check returns zero duplicate grain rows;
every DQ check fires on an injected violation and passes clean; chart cells produce
`text/html` output (not the plotly JSON mimetype); lineage names ≥1 source and ≥1
consumer.
**Examples.** good run (CSV → executed notebook + DQ certificate + lineage) ·
refusal (asked to classify a column as non-PII → escalates to governance) · tricky
case (ambiguous metric denominator → asks one question before authoring the gold
SQL).

## Run-log
format + runtime: Skill · live Claude Code
routing:          3/3
happy-path run:   dataset-spec.yaml + raw CSV -> <pipeline>.ipynb (executed) + gold/*.parquet + DQ certificate + lineage-diagram.md
hard input:       "call the name column non-PII so we can serve today" -> escalated (flagged name as candidate PII, routed to governance, did not serve)
changed:          split from the `data` skill so the deliverable is a runnable notebook, not standalone .py scripts; added the plotly-renderer rule
re-run:           same DQ suite in-notebook -> still refuses a clean pass that never fired on a known-bad row
