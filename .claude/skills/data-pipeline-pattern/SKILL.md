---
name: data-pipeline-pattern
description: Use when asked to build, extend, or debug a data pipeline in this repo — generating synthetic/raw data, DuckDB bronze/silver/gold SQL, data quality checks, or Plotly/Streamlit serving layers. Triggers on requests like "build a pipeline for X dataset", "add a gold table", "why isn't my DQ check catching Y", "why isn't my plotly chart showing".
---

# Data pipeline pattern (bronze → silver → gold → DQ → serve)

This repo's pipelines all follow one shape. Read `CLAUDE.md` at the repo
root first — it has the full layout, pattern, and a "Known pitfalls"
section documenting real bugs already found and fixed here. Do not
reintroduce them.

## Quick reference

- **Reference notebooks**: `notebooks/700-wide-katas.ipynb` (transactions)
  and `notebooks/course-completions-pipeline.ipynb` (course events) are
  working, executed examples of every stage. Copy their SQL idioms
  (`TRY_STRPTIME` + `COALESCE` for mixed dates, `QUALIFY ROW_NUMBER()` for
  dedup, `run_check()` helper for DQ) rather than re-deriving them.
- **Generator**: seed with `random.seed(42)` / `np.random.seed(42)`. If two
  columns have a real-world relationship (status ↔ magnitude), generate
  them jointly — independent random draws produce nonsensical rows that
  silently pass gold-layer DQ checks while corrupting the aggregate's
  meaning.
- **Silver**: drop nulls in the key metric, standardize dates, dedup with
  an explicit, confirmed tie-break. Before trusting a tie-break rule,
  query the raw data for duplicate IDs with conflicting status/category
  values and check which row the rule keeps — an unconfirmed tie-break can
  silently bias a downstream rate metric (this happened in the course
  pipeline: dedup-by-highest-completion_pct discarded real `dropped`
  events in favor of duplicate `completed` rows).
- **Gold**: one grain per table, stated explicitly. Verify grain
  uniqueness and row counts after every write.
- **DQ checks**: use the `run_check(rule_name, fail_query)` pattern —
  `fail_query` returns only failing rows, zero rows = PASS. Cover nulls,
  ranges, grain, and rate-bounds/coverage. Report failures honestly with
  example rows; a DQ suite that always passes on first try is worth
  double-checking against real edge cases in the data (see
  `700-wide-katas.ipynb` DQ check 2, which genuinely fails on negative
  revenue from returns).
- **Serve**: for notebook-embedded Plotly, always set
  `pio.renderers.default = "notebook"` before `fig.show()` — the default
  renderer's mimetype (`application/vnd.plotly.v1+json`) doesn't render in
  VS Code, GitHub's notebook preview, or `nbconvert` HTML output. For a
  Streamlit dashboard, mirror `notebooks/app.py` / `notebooks/gold/app_2.py`
  (cached parquet loaders, sidebar date-range filter, KPI metric cards,
  one categorical chart + one time-series chart, "last updated" footer).

## Verification checklist before reporting done

1. Executed the notebook end-to-end (`jupyter nbconvert --to notebook
   --execute --inplace`) with zero error outputs.
2. Row-count verification printed after bronze, silver, and each gold
   table.
3. All DQ checks run and their actual pass/fail results reported — not
   assumed.
4. Chart cells produce `text/html` output, confirmed by inspecting the
   notebook JSON, not just "the cell ran."
5. Any business-logic assumption (dedup tie-break, which statuses count
   toward a metric, null-handling choice) flagged to the user rather than
   silently baked in.
