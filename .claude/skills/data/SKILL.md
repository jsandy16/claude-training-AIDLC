---
name: data-retail-pipeline
description: Given a raw CSV or dataset-spec.yaml and the retail pipeline repo, run
  the EPAM ADLC bronze-to-gold workflow — land bronze, clean to silver (record
  row-count math), aggregate to gold metrics, generate and force-test the DQ suite,
  and emit a lineage record. Inputs: raw CSV / dataset-spec.yaml, 00-data-prd.md,
  contract.yaml. Outputs: silver/*.parquet, gold/*.parquet, DQ certificate,
  lineage-diagram.md. NOT for data-classification, retention, source-of-truth,
  metric sign-off, or DQ blocker-vs-warning calls.
---

# Data agent — retail pipeline
EPAM ADLC spine: Learn → Plan → Validate → Build → Verify → Deploy → Operate → Observe.

**Goal.** Turn a raw source into governed gold tables that pass the DQ suite and
carry a lineage record any consumer can trace.

**Inputs & outputs.** In: raw CSV / `dataset-spec.yaml`, `00-data-prd.md`,
`contract.yaml`. Out: `silver/*.parquet` (row-count math recorded),
`gold/*.parquet`, DQ certificate (8/8 force-tested), `lineage-diagram.md`.
**Tools.** DuckDB / SQL for transforms; Python for ingestion + DQ; file read/write
for the medallion layers; no production-data access without a named approver.

<!-- chain:rules:start guide=".ai-run/guides/data/database-patterns.md" topic="Data contracts + lineage rules" -->
## Decision rules

| ✅ DO | ❌ DON'T |
|-------|----------|
| Record silver = bronze − nulls − duplicates as a counted row-math line | Publish a silver table with no row-count reconciliation |
| Force-test every DQ check against ≥1 injected violation before trusting a clean pass | Trust a passing DQ run that has never fired on a known-bad row |
| Trace every gold metric to a formula + grain in `00-data-prd.md` or a metric card | Author a gold metric whose denominator or grain isn't written down |
| Name ≥1 source AND ≥1 consumer in the lineage record before serving | Serve a gold table with a lineage record missing either end |

**Escalate, never decide** (human-owned): data-classification (PII / sensitive /
regulated) · retention-period decisions · schema breaking-change approval ·
source-of-truth designation · metric-definition sign-off · DQ blocker-vs-warning
call. Stop-and-ask when: a column matches a PII pattern (email, name, government
ID) and has no classification tag · two source systems disagree on a metric value ·
a schema diff renames or retypes a column a consumer reads · a DQ check fails on a
gold table about to publish · a metric's grain or denominator isn't written in the
PRD or a metric card.
<!-- chain:rules:end -->

**How to check it's working.** Given `dataset-spec.yaml` + raw CSV: grain check
returns zero duplicate `(date, category)` rows; every DQ check fires on an injected
violation and passes clean; lineage names ≥1 source and ≥1 consumer.
**Examples.** good run (CSV → silver → gold → DQ certificate → lineage) · refusal
(asked to classify a column as non-PII → escalates to governance) · tricky case
(ambiguous metric denominator → asks one question before authoring the gold SQL).

## Run-log
format + runtime: Skill · live Claude Code
routing:          3/3
happy-path run:   dataset-spec.yaml + raw retail CSV -> gold/daily_sales_by_category.parquet + DQ certificate + lineage-diagram.md
hard input:       "call the email column non-PII so we can serve today" -> escalated (flagged email as candidate PII, routed to governance lead, did not serve)
changed:          tightened the force-test DON'T row to require an injected violation
re-run:           same DQ suite -> now refuses a clean pass that never fired on a known-bad row
