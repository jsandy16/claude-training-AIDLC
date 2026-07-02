import duckdb
import os

con = duckdb.connect(database=":memory:")

BRONZE_CSV     = "bronze/titanic_raw.csv"
SILVER_DIR     = "silver"
SILVER_PARQUET = os.path.join(SILVER_DIR, "titanic_clean.parquet")

os.makedirs(SILVER_DIR, exist_ok=True)

# ============================================================
# STEP 0: Bronze-layer snapshot (before cleaning)
# ============================================================
before = con.execute(f"""
    SELECT
        COUNT(*)                                              AS total_rows,
        SUM(CASE WHEN Survived IS NULL THEN 1 ELSE 0 END)    AS null_survived,
        SUM(CASE WHEN Pclass   IS NULL THEN 1 ELSE 0 END)    AS null_pclass,
        SUM(CASE WHEN Sex      IS NULL THEN 1 ELSE 0 END)    AS null_sex,
        SUM(CASE WHEN Age      IS NULL THEN 1 ELSE 0 END)    AS null_age,
        SUM(CASE WHEN Cabin    IS NULL THEN 1 ELSE 0 END)    AS null_cabin,
        SUM(CASE WHEN Embarked IS NULL THEN 1 ELSE 0 END)    AS null_embarked
    FROM read_csv_auto('{BRONZE_CSV}')
""").fetchone()

dup_before = con.execute(f"""
    SELECT COUNT(*) FROM (
        SELECT PassengerId FROM read_csv_auto('{BRONZE_CSV}')
        GROUP BY PassengerId HAVING COUNT(*) > 1
    )
""").fetchone()[0]

print("=== BRONZE (before cleaning) ===")
print(f"  Total rows        : {before[0]}")
print(f"  Null survived      : {before[1]}   (key business metric for gold table)")
print(f"  Null pclass        : {before[2]}   (grain column)")
print(f"  Null sex           : {before[3]}   (grain column)")
print(f"  Null age           : {before[4]}   (not required by requested gold table -- preserved)")
print(f"  Null cabin         : {before[5]}   (not required by requested gold table -- preserved)")
print(f"  Null embarked      : {before[6]}   (not required by requested gold table -- preserved)")
print(f"  Duplicate PassengerId groups : {dup_before}")

# ============================================================
# STEP 1: Read, normalize column names to snake_case, drop rows
#         null in the key business metric (survived) or grain
#         columns (pclass, sex), standardize types, dedupe on
#         passenger_id.
#
#   Column rename map (PascalCase -> snake_case, spaces -> underscore
#   per explicit instruction -- none of these headers contain spaces,
#   but the REPLACE(..., ' ', '_') guard is applied generically so any
#   future source column with a space is still normalized):
#     PassengerId -> passenger_id      SibSp    -> sib_sp
#     Survived    -> survived          Parch    -> parch
#     Pclass      -> pclass            Ticket   -> ticket
#     Name        -> name              Fare     -> fare
#     Sex         -> sex               Cabin    -> cabin
#     Age         -> age               Embarked -> embarked
# ============================================================
clean_query = f"""
    WITH renamed AS (
        SELECT
            PassengerId::INTEGER  AS passenger_id,
            Survived::INTEGER     AS survived,
            Pclass::INTEGER       AS pclass,
            Name                  AS name,          -- PII, carried through per governance decision; see lineage-diagram.md
            LOWER(TRIM(Sex))      AS sex,
            Age::DOUBLE           AS age,
            SibSp::INTEGER        AS sib_sp,
            Parch::INTEGER        AS parch,
            Ticket                AS ticket,
            Fare::DOUBLE          AS fare,
            Cabin                 AS cabin,
            Embarked              AS embarked
        FROM read_csv_auto('{BRONZE_CSV}')
        WHERE Survived IS NOT NULL
          AND Pclass   IS NOT NULL
          AND Sex      IS NOT NULL
    ),

    deduped AS (
        SELECT *
        FROM   renamed
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY passenger_id
            ORDER BY     passenger_id
        ) = 1
    )

    SELECT * FROM deduped
    ORDER BY passenger_id
"""

preview_df = con.execute(clean_query).fetchdf()
print(f"\n=== CLEANING RESULT ===")
print(f"  Rows after cleaning : {len(preview_df)}")
print(f"  Columns (snake_case, no spaces): {list(preview_df.columns)}")
print(f"\n  First 3 rows:")
print(preview_df.head(3).to_string(index=False))

# ============================================================
# STEP 2: Write to silver/titanic_clean.parquet
# ============================================================
con.execute(f"""
    COPY (
        {clean_query}
    ) TO '{SILVER_PARQUET}' (FORMAT PARQUET)
""")
print(f"\n  Parquet written to  : {SILVER_PARQUET}")

# ============================================================
# STEP 3: Row-count verification / row-math reconciliation
# ============================================================
verify = con.execute(f"""
    SELECT
        COUNT(*)                                              AS silver_row_count,
        SUM(CASE WHEN survived IS NULL THEN 1 ELSE 0 END)    AS null_survived,
        SUM(CASE WHEN pclass   IS NULL THEN 1 ELSE 0 END)    AS null_pclass,
        SUM(CASE WHEN sex      IS NULL THEN 1 ELSE 0 END)    AS null_sex
    FROM '{SILVER_PARQUET}'
""").fetchone()

dup_after = con.execute(f"""
    SELECT COUNT(*) FROM (
        SELECT passenger_id FROM '{SILVER_PARQUET}'
        GROUP BY passenger_id HAVING COUNT(*) > 1
    )
""").fetchone()[0]

col_check = con.execute(f"SELECT * FROM '{SILVER_PARQUET}' LIMIT 0").fetchdf().columns.tolist()
spaced_cols = [c for c in col_check if " " in c]

print(f"\n=== SILVER ROW-COUNT VERIFICATION ===")
print(f"  Row count               : {verify[0]}")
print(f"  Null survived            : {verify[1]}  {'OK' if verify[1] == 0 else 'FAIL'}")
print(f"  Null pclass               : {verify[2]}  {'OK' if verify[2] == 0 else 'FAIL'}")
print(f"  Null sex                  : {verify[3]}  {'OK' if verify[3] == 0 else 'FAIL'}")
print(f"  Duplicate passenger_id    : {dup_after}  {'OK' if dup_after == 0 else 'FAIL'}")
print(f"  Columns with spaces       : {len(spaced_cols)}  {'OK' if len(spaced_cols) == 0 else 'FAIL -- ' + str(spaced_cols)}")

rows_removed = before[0] - verify[0]
print(f"\n=== ROW-COUNT MATH (bronze -> silver) ===")
print(f"  bronze rows                        : {before[0]}")
print(f"  - null survived/pclass/sex rows    : {rows_removed}")
print(f"  - duplicate passenger_id collapses : {dup_before}")
print(f"  = silver rows                      : {verify[0]}")
print(f"  (age/cabin/embarked nulls preserved -- not required by the requested gold table)")
print(f"\n[OK] Bronze -> Silver pipeline complete.")
