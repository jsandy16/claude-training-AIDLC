Build a new bronze → silver → gold → DQ → serve pipeline notebook for the
dataset described in $ARGUMENTS, following the established pattern in this
repository (see CLAUDE.md for the full spec).

Steps:

1. Read `notebooks/course-completions-pipeline.ipynb` and
   `notebooks/700-wide-katas.ipynb` as reference templates — reuse their
   structure (generator → silver SQL → gold SQL → DQ checks → charts), not
   just their prose.
2. Ask the user (if not already specified) for: the raw columns and types,
   the intentional data-quality issues to inject (null rate, duplicate
   rate, mixed formats, etc.), and the gold-table definitions (grain +
   metrics) they want.
3. **Before writing the generator**: check whether any pair of columns has
   an implied business relationship (e.g. a status/outcome column and a
   magnitude/percentage column). If so, generate them together so the
   relationship holds — do not generate them as independent random draws.
   This is a known pitfall documented in CLAUDE.md.
4. Write the generator, silver SQL, gold SQL, and 6+ DQ checks (nulls,
   ranges, grain, rate bounds/coverage) as separate notebook cells, mirroring
   the section-banner comment style (`# ====...====`) used in the existing
   notebooks.
5. Before finalizing any dedup tie-break rule (`QUALIFY ROW_NUMBER() OVER
   (PARTITION BY ... ORDER BY ...)`), check the actual generated bronze
   data for duplicate IDs with conflicting business-relevant fields (e.g.
   different status values) and confirm the tie-break doesn't silently
   bias a downstream gold metric.
6. For Plotly charts, set `pio.renderers.default = "notebook"` before
   calling `fig.show()`.
7. Execute the notebook end-to-end with `jupyter nbconvert --to notebook
   --execute --inplace <notebook>.ipynb` and verify: row counts at each
   layer, all DQ checks (report pass/fail honestly, don't hide failures),
   and that chart cells produced `text/html` output (not
   `application/vnd.plotly.v1+json`).
8. Write bronze/silver/gold outputs to `notebooks/bronze/`,
   `notebooks/silver/`, `notebooks/gold/` alongside the existing pipeline's
   files — do not overwrite them.
9. Report a summary: row counts per layer, DQ check results, and any
   business-logic assumptions made that the user should confirm.
