import duckdb
import os

con = duckdb.connect(database=":memory:")

SILVER_PARQUET = "silver/titanic_clean.parquet"
GOLD_DIR       = "gold"
GOLD_SURVIVAL  = os.path.join(GOLD_DIR, "survival_rate_by_class_sex.parquet")

os.makedirs(GOLD_DIR, exist_ok=True)

# ============================================================
# Quick look at the silver source
# ============================================================
src = con.execute(f"""
    SELECT
        COUNT(*)                    AS total_rows,
        COUNT(DISTINCT passenger_id) AS unique_passengers,
        COUNT(DISTINCT pclass)      AS classes,
        COUNT(DISTINCT sex)         AS sexes
    FROM '{SILVER_PARQUET}'
""").fetchone()

print("=== SILVER SOURCE ===")
print(f"  Rows               : {src[0]}")
print(f"  Unique passengers  : {src[1]}")
print(f"  Classes            : {src[2]}")
print(f"  Sexes              : {src[3]}")

# ============================================================
# GOLD TABLE: survival_rate_by_class_sex
#
# Grain : one row per (pclass, sex)
# Scope : all silver passengers (survived is never null in silver)
#
# Logic :
#   - survival_rate_pct = AVG(survived) * 100, rounded to 2dp
#   - passenger_count    = COUNT(*)
# ============================================================
gold_query = f"""
    SELECT
        pclass,
        sex,
        ROUND(AVG(survived) * 100, 2) AS survival_rate_pct,
        COUNT(*)                      AS passenger_count
    FROM   '{SILVER_PARQUET}'
    GROUP  BY pclass, sex
    ORDER  BY pclass, sex
"""

con.execute(f"COPY ({gold_query}) TO '{GOLD_SURVIVAL}' (FORMAT PARQUET)")
print(f"\n[OK] Written: {GOLD_SURVIVAL}")

# ============================================================
# VERIFICATION: grain uniqueness, row count, coverage reconciliation
# ============================================================
grain_check = con.execute(f"""
    SELECT COUNT(*) FROM (
        SELECT pclass, sex FROM '{GOLD_SURVIVAL}'
        GROUP BY pclass, sex HAVING COUNT(*) > 1
    )
""").fetchone()[0]

gold_rows = con.execute(f"SELECT COUNT(*) FROM '{GOLD_SURVIVAL}'").fetchone()[0]

coverage = con.execute(f"""
    SELECT
        (SELECT SUM(passenger_count) FROM '{GOLD_SURVIVAL}') AS gold_total,
        (SELECT COUNT(*) FROM '{SILVER_PARQUET}')             AS silver_total
""").fetchone()

rate_stats = con.execute(f"""
    SELECT MIN(survival_rate_pct), MAX(survival_rate_pct), AVG(survival_rate_pct)
    FROM '{GOLD_SURVIVAL}'
""").fetchone()

print(f"\n=== GOLD TABLE: survival_rate_by_class_sex ===")
print(f"  Row count               : {gold_rows}  (expected {src[2]} classes x {src[3]} sexes = {src[2]*src[3]})")
print(f"  Grain duplicates        : {grain_check}  {'OK' if grain_check == 0 else 'FAIL'}")
print(f"  Coverage (gold sum vs silver total) : {coverage[0]} vs {coverage[1]}  {'OK' if coverage[0] == coverage[1] else 'FAIL'}")
print(f"  survival_rate_pct range : {rate_stats[0]}% to {rate_stats[1]}%  (avg {rate_stats[2]:.2f}%)")

print(f"\n--- survival_rate_by_class_sex (all rows) ---")
print(con.execute(f"SELECT * FROM '{GOLD_SURVIVAL}'").fetchdf().to_string(index=False))

print(f"\n=== PIPELINE SUMMARY ===")
print(f"  Silver rows                        : {src[0]}")
print(f"  Gold survival_rate_by_class_sex     : {gold_rows} rows")
print(f"  Grain check passed                 : {'YES' if grain_check == 0 else 'NO'}")
print(f"  Coverage reconciled                : {'YES' if coverage[0] == coverage[1] else 'NO'}")
print(f"\n[OK] Silver -> Gold pipeline complete.")
