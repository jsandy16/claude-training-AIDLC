# Lineage — titanic pipeline

```
[SOURCE]                       [BRONZE]                [SILVER]                       [GOLD]                                    [CONSUMER]
titanic.csv                    bronze/                 silver/                        gold/                                     Requester
(user-uploaded,       ---->    titanic_raw.csv --->    titanic_clean.parquet  ---->    survival_rate_by_class_sex.parquet  ---->  (survival-rate
this session)                  (landed as-is,          (891 rows; snake_case                (grain: pclass, sex;                  analysis by
                                zero transforms)        columns; nulls dropped in            metrics: survival_rate_pct,           class & sex)
                                                         key metric/grain cols only;          passenger_count)
                                                         deduped on passenger_id)
```

## Source

- **Name**: `titanic.csv` (uploaded by requester this session, as
  `titanic.csv.zip`)
- **Provenance**: no upstream system-of-record or contract.yaml provided;
  treated as a one-off user-supplied dataset, not a governed production
  source.
- **Row count**: 891

## Consumer

- **Who**: the requester, for survival-rate analysis cut by passenger
  class and sex (explicitly specified gold-table grain/metrics).
- **What they read**: `gold/survival_rate_by_class_sex.parquet` only.
  They do not have access to `bronze/` or `silver/` (which still carry
  the `name` column) through this lineage path.

## Columns carried end-to-end (bronze → silver)

| bronze column | silver column | classification | notes |
|---|---|---|---|
| PassengerId | passenger_id | none | primary key, unique, no nulls |
| Survived | survived | none | key business metric for gold table |
| Pclass | pclass | none | grain column |
| **Name** | **name** | **PII** | full passenger name; carried through per explicit requester decision (not a named governance approver); **excluded from all gold-table grains/metrics** |
| Sex | sex | none | grain column, lowercased |
| Age | age | none | 177 nulls preserved (not required downstream) |
| SibSp | sib_sp | none | |
| Parch | parch | none | |
| Ticket | ticket | none | free-text identifier, not validated as PII pattern but not a government ID either |
| Fare | fare | none | |
| Cabin | cabin | none | 687 nulls preserved (not required downstream) |
| Embarked | embarked | none | 2 nulls preserved (not required downstream) |

## Governance flags

- `name` is tagged **PII** in this record because it matches the skill's
  PII pattern (full person name) and no `contract.yaml` classification
  existed at build time. The requester approved carrying it through as-is
  — that approval is recorded here, not assumed silently. If this pipeline
  is ever promoted beyond this training/demo context, `name` needs a
  formal classification sign-off from a named governance approver before
  any consumer beyond this lineage path is granted access to `silver/` or
  `bronze/`.
- No other escalation triggers were hit: no schema-breaking change, no
  conflicting source values across systems, no DQ check failed on clean
  data, and the gold metric's grain/denominator was directly specified by
  the requester.
