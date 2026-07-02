import duckdb
import pandas as pd

con = duckdb.connect(database=":memory:")

SILVER_PARQUET = "silver/titanic_clean.parquet"
GOLD_SURVIVAL  = "gold/survival_rate_by_class_sex.parquet"

silver_df = con.execute(f"SELECT * FROM '{SILVER_PARQUET}'").fetchdf()
gold_df   = con.execute(f"SELECT * FROM '{GOLD_SURVIVAL}'").fetchdf()


# ============================================================
# Helper: run a fail_query against a named in-memory table and
# return (passed: bool, fail_count: int, sample_df)
# ============================================================
def run_against(df, fail_sql, table_alias="t"):
    local_con = duckdb.connect(database=":memory:")
    local_con.register(table_alias, df)
    fail_df = local_con.execute(fail_sql).fetchdf()
    return len(fail_df) == 0, len(fail_df), fail_df.head(3)


# ============================================================
# Each check is defined as (name, fail_sql, clean_df, dirty_df_builder)
#   - fail_sql        : SQL returning ONLY failing rows, table alias "t"
#   - clean_df        : the real silver/gold table this check runs against
#   - dirty_df_builder: function that returns a corrupted copy of
#                       clean_df with exactly one violation injected,
#                       used to force-test the check fires correctly
# ============================================================
checks = []

# ---- SILVER CHECKS -------------------------------------------------

checks.append((
    "1. Silver: no nulls in passenger_id / pclass / sex / survived",
    "SELECT * FROM t WHERE passenger_id IS NULL OR pclass IS NULL OR sex IS NULL OR survived IS NULL",
    silver_df,
    lambda df: df.assign(sex=[None] + list(df["sex"][1:])),
))

checks.append((
    "2. Silver: passenger_id is unique",
    "SELECT passenger_id, COUNT(*) c FROM t GROUP BY passenger_id HAVING COUNT(*) > 1",
    silver_df,
    lambda df: pd.concat([df, df.iloc[[0]]], ignore_index=True),
))

checks.append((
    "3. Silver: pclass in {1, 2, 3}",
    "SELECT * FROM t WHERE pclass NOT IN (1, 2, 3)",
    silver_df,
    lambda df: df.assign(pclass=[9] + list(df["pclass"][1:])),
))

checks.append((
    "4. Silver: survived in {0, 1}",
    "SELECT * FROM t WHERE survived NOT IN (0, 1)",
    silver_df,
    lambda df: df.assign(survived=[2] + list(df["survived"][1:])),
))

# ---- GOLD CHECKS -----------------------------------------------------

checks.append((
    "5. Gold: no nulls in pclass / sex / survival_rate_pct / passenger_count",
    "SELECT * FROM t WHERE pclass IS NULL OR sex IS NULL OR survival_rate_pct IS NULL OR passenger_count IS NULL",
    gold_df,
    lambda df: df.assign(survival_rate_pct=[None] + list(df["survival_rate_pct"][1:])),
))

checks.append((
    "6. Gold: survival_rate_pct in [0, 100]",
    "SELECT * FROM t WHERE survival_rate_pct < 0.0 OR survival_rate_pct > 100.0",
    gold_df,
    lambda df: df.assign(survival_rate_pct=[150.0] + list(df["survival_rate_pct"][1:])),
))

checks.append((
    "7. Gold: unique grain (pclass, sex)",
    "SELECT pclass, sex, COUNT(*) c FROM t GROUP BY pclass, sex HAVING COUNT(*) > 1",
    gold_df,
    lambda df: pd.concat([df, df.iloc[[0]]], ignore_index=True),
))

checks.append((
    "8. Gold: coverage -- SUM(passenger_count) == silver row count",
    f"SELECT SUM(passenger_count) AS gold_total, {len(silver_df)} AS silver_total "
    "FROM t HAVING SUM(passenger_count) != " + str(len(silver_df)),
    gold_df,
    lambda df: df.assign(passenger_count=[df["passenger_count"].iloc[0] - 5] + list(df["passenger_count"][1:])),
))


# ============================================================
# Force-test each check: run against the injected-violation copy
# first (must FAIL / fire), then run against the real clean data
# (must PASS). A check that doesn't fire on the dirty copy is
# never trusted on the clean pass.
# ============================================================
results = []

print("=" * 78)
print("  DQ SUITE -- FORCE-TESTED (injected violation -> clean pass)")
print("=" * 78)

for name, fail_sql, clean_df, dirty_builder in checks:
    dirty_df = dirty_builder(clean_df)

    # On the dirty copy we WANT the fail_query to return rows (i.e. fire)
    _, dirty_fail_count, _ = run_against(dirty_df, fail_sql)
    force_test_fired = dirty_fail_count > 0

    clean_passed, clean_fail_count, clean_sample = run_against(clean_df, fail_sql)

    status = "CERTIFIED" if (force_test_fired and clean_passed) else "NOT CERTIFIED"
    results.append((name, force_test_fired, clean_passed, status))

    print(f"\n  {name}")
    print(f"    Force-test (injected violation) : {'FIRED (' + str(dirty_fail_count) + ' rows)' if force_test_fired else 'DID NOT FIRE -- CHECK IS BROKEN'}")
    print(f"    Clean-data pass                 : {'PASS' if clean_passed else 'FAIL (' + str(clean_fail_count) + ' rows)'}")
    if not clean_passed:
        print(f"      Examples:")
        for line in clean_sample.to_string(index=False).split("\n"):
            print(f"        {line}")
    print(f"    STATUS: {status}")

print("\n" + "=" * 78)
certified = sum(1 for r in results if r[3] == "CERTIFIED")
total = len(results)
print(f"  RESULT: {certified}/{total} checks force-tested and certified")
if certified < total:
    failed = [r[0] for r in results if r[3] != "CERTIFIED"]
    print(f"  NOT CERTIFIED: {failed}")
print("=" * 78)
