# claude-training-AIDLC

Training repository for building DuckDB-based data pipelines in Jupyter
notebooks, following a consistent bronze → silver → gold → DQ → serve
pattern.

## Repository layout

```
notebooks/
  <pipeline>.ipynb          # one notebook per pipeline (generator, silver, gold, DQ, charts)
  bronze/                   # raw landed CSVs (as-generated, uncleaned)
  silver/                   # cleaned parquet (nulls removed, types standardized, deduped)
  gold/                     # business-metric parquet tables + optional Streamlit app(s)
  artefacts/                # profiling markdown, generated reports
```

Existing pipelines:
- `notebooks/700-wide-katas.ipynb` — retail transactions (`transactions_raw.csv` → `transactions_clean.parquet` → `daily_sales_by_category` / `returns_rate`), served via `notebooks/app.py`.
- `notebooks/course-completions-pipeline.ipynb` — online course completion events (`course_events_raw.csv` → `course_events_clean.parquet` → `daily_completions_by_category` / `dropout_rate`), served inline via Plotly and via `notebooks/gold/app_2.py`.

## Pipeline pattern

1. **Generator** — synthetic data with seeded reproducibility (`random.seed(42)`, `np.random.seed(42)`), 500 rows, deliberately messy (nulls, duplicates, mixed date formats). Print a row-count verification after writing to `bronze/`.
2. **Bronze → Silver** — DuckDB SQL: drop nulls in the key business metric, standardize mixed date formats via `COALESCE(TRY_STRPTIME(...), TRY_STRPTIME(...), ...)`, deduplicate via `QUALIFY ROW_NUMBER() OVER (PARTITION BY <id> ORDER BY <tiebreak>) = 1`. Print before/after row counts, null counts, duplicate counts.
3. **Silver → Gold** — 2+ aggregated parquet tables, each with an explicit grain (state it in a comment). Verify grain uniqueness (`GROUP BY <grain> HAVING COUNT(*) > 1`) and row counts after writing.
4. **DQ checks** — a `run_check(rule_name, fail_query)` helper that prints PASS/FAIL + example failing rows. Cover nulls, ranges, grain uniqueness, and rate-bound/coverage checks per gold table.
5. **Serve** — Plotly charts. Set `pio.renderers.default = "notebook"` before calling `fig.show()` (see "Known pitfalls" below). Optionally also a Streamlit `app.py`-style dashboard reading directly from the gold parquet files.

## Known pitfalls (found and fixed in this repo — don't reintroduce)

- **Plotly charts not rendering**: the default `fig.show()` renderer emits `application/vnd.plotly.v1+json`, which many viewers (VS Code, GitHub notebook preview, `nbconvert` HTML) don't render. Always set `pio.renderers.default = "notebook"` first so charts embed as self-contained HTML.
- **Uncorrelated generator fields**: when a business rule links two columns (e.g. `status='returned'` should imply a negative `amount`; `status='completed'` should imply a high `completion_pct`), generate them *together*, not independently. Independent random generation lets nonsensical rows through (e.g. a `completed` event with 3% `completion_pct`) and produces gold-layer numbers that pass DQ checks but don't mean what they claim to.
- **Silent dedup tie-breaks**: don't invent a `QUALIFY ... ORDER BY <column>` tie-break rule without confirming intent. If duplicate rows can carry conflicting values in fields that feed different gold tables (e.g. one dup is `dropped`, another is `completed`), the tie-break silently decides which business fact survives — verify this against the actual generated data before trusting it, since none of the standard DQ checks catch a systematically-biased dedup.

## Conventions

- DuckDB in-memory connections (`duckdb.connect(":memory:")`), no persisted `.db` files.
- Parquet for silver/gold, CSV only for bronze (as-landed).
- Comment blocks use `# ====...====` section banners, matching the existing notebooks.
- No inline docstrings/comments beyond what clarifies a non-obvious choice (see root-level style guide in the coding agent's system prompt).
