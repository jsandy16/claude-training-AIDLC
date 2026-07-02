# DQ Certificate — `gold/survival_rate_by_class_sex.parquet`

**Pipeline**: titanic (bronze → silver → gold)
**Certified**: 8/8 checks force-tested and passing
**Method**: every check below was run against a deliberately corrupted
copy of its target table first, to confirm it actually fires, before
being trusted against the real clean data. A check that doesn't fire on
an injected violation is not certified, regardless of whether it passes
clean.

| # | Check | Layer | Category | Force-test (injected violation) | Clean-data result | Status |
|---|-------|-------|----------|----------------------------------|--------------------|--------|
| 1 | No nulls in `passenger_id` / `pclass` / `sex` / `survived` | silver | nulls | FIRED (1 row) | PASS | CERTIFIED |
| 2 | `passenger_id` is unique | silver | grain | FIRED (1 row) | PASS | CERTIFIED |
| 3 | `pclass` in {1, 2, 3} | silver | domain | FIRED (1 row) | PASS | CERTIFIED |
| 4 | `survived` in {0, 1} | silver | domain | FIRED (1 row) | PASS | CERTIFIED |
| 5 | No nulls in `pclass` / `sex` / `survival_rate_pct` / `passenger_count` | gold | nulls | FIRED (1 row) | PASS | CERTIFIED |
| 6 | `survival_rate_pct` in [0, 100] | gold | range | FIRED (1 row) | PASS | CERTIFIED |
| 7 | Unique grain `(pclass, sex)` | gold | grain | FIRED (1 row) | PASS | CERTIFIED |
| 8 | Coverage: `SUM(passenger_count)` == silver row count | gold | coverage | FIRED (1 row) | PASS | CERTIFIED |

## Row-count math (bronze → silver)

```
bronze rows                        : 891
- null survived/pclass/sex rows    : 0
- duplicate passenger_id collapses : 0
= silver rows                      : 891
```

`age` (177 nulls), `cabin` (687 nulls), and `embarked` (2 nulls) are **not**
dropped — they aren't required by the requested gold table
(`survival_rate_by_class_sex`, which only depends on `pclass`, `sex`,
`survived`) and dropping rows on their account would discard valid
class/sex/survival data for no benefit to this gold table.

## Silver → gold coverage reconciliation

```
silver rows                                : 891
SUM(passenger_count) across gold table     : 891
match                                      : YES
```

Every silver passenger is represented in exactly one gold grain row — no
passengers were silently dropped by the aggregation.

## Gold table contents

| pclass | sex | survival_rate_pct | passenger_count |
|-------:|-----|-------------------:|-----------------:|
| 1 | female | 96.81 | 94 |
| 1 | male | 36.89 | 122 |
| 2 | female | 92.11 | 76 |
| 2 | male | 15.74 | 108 |
| 3 | female | 50.00 | 144 |
| 3 | male | 13.54 | 347 |

## Governance note — PII

`name` (full passenger name) is carried through silver and gold unchanged,
per an explicit decision from the requester. It is **not** used in any
gold-table grain or metric — `survival_rate_by_class_sex` never selects
it. See `lineage-diagram.md` for the PII classification tag.

**Escalations not raised**: no schema-breaking change, no conflicting
source values, no DQ check failed against clean data, and the gold
table's grain/metric definition (`(pclass, sex)` → `survival_rate_pct`,
`passenger_count`) was directly specified by the requester, so no
metric-definition sign-off was needed beyond that.
