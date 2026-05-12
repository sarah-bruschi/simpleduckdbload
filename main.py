import duckdb
from datetime import datetime

conn = duckdb.connect()


def run_sql_file(conn, path, params=None):
    with open(path) as f:
        sql = f.read()

    if params:
        sql = sql.format(**params)

    conn.execute(sql)

def validate_schema(conn, table, expected_columns):
    actual = set(
        row[1]
        for row in conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    )

    missing = expected_columns - actual

    if missing:
        raise Exception(f"{table} missing columns: {missing}")

    print(f"{table} schema OK")

    

def run_validation(conn, path, name):
    with open(path) as f:
        sql = f.read()
    
    results = conn.execute(sql).fetchall()

    print(f"[{name}] violations: {len(results)}")

    if results:
        print(results[:10])
        raise Exception(f"{name} failed")
    print(f"{name} passed")

def inspect_table(conn, table_name):
    print(f"\n=={table_name} ===")
    print(conn.execute(f"SELECT * FROM {table_name} LIMIT 5").fetchdf())
    print(conn.execute(f"DESCRIBE {table_name}").fetchdf())







# -------------
# 1. LOAD
# -------------
run_sql_file(conn, "sql/load.sql", {
    "full_csv": "data/full_dataset.csv",
    "delta_csv": "data/delta.csv"
})
# debugging

print(conn.execute("SELECT COUNT(*) FROM full_providers").fetchone()[0],
      conn.execute("SELECT COUNT(*) FROM delta_providers").fetchone()[0])




# testing actual load
# ------------------
# 2. INSPECT
# ------------------
# inspect_table(conn, "full_providers")
# inspect_table(conn, "delta_providers")



# ------------------
# 3. VALIDATE DELTA
# ------------------
EXPECTED_COLUMNS = {
    "id",
    "first_name",
    "last_name",
    "effective_date",
    "termination_date",
    "primary_care_flag"
}

validate_schema(conn, "delta_providers", EXPECTED_COLUMNS)
run_validation(conn, "sql/validate_delta.sql", "delta_validation")

# ------------------
# 4. SNAPSHOT FULL DATASET
# ------------------

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
snapshot_table = f"providers_snapshot_{timestamp}"
run_sql_file(conn, "sql/snapshot.sql", {
    "snapshot_table": snapshot_table
})


# create delta history table if time 

# getting counts
before_count = conn.execute("""
SELECT COUNT(*) FROM full_providers
""").fetchone()[0]

print("Before merge:", before_count)

delta_ids = conn.execute("""
SELECT id FROM delta_providers
""").fetchall()

delta_ids = [x[0] for x in delta_ids]
print("Delta size:", len(delta_ids))

# ------------------
# 5.MERGE
# ------------------

run_sql_file(conn, "sql/merge.sql")


# ------------------
# 6.VALIDATE FINAL
# ------------------
run_validation(conn, "sql/validate_final.sql", "final_validation")


# ------------------
# 7.Export debug
# ------------------


# print(conn.execute("""
# SELECT * FROM full_providers
# WHERE id IN (SELECT id FROM delta_providers)
# LIMIT 10
# """).fetchdf())

applied = conn.execute(f"""
SELECT COUNT(*)
FROM full_providers
WHERE id IN ({','.join([repr(i) for i in delta_ids])})
""").fetchone()[0]

print("Delta IDs present in full:", applied)

after_count = conn.execute("""
SELECT COUNT(*) FROM full_providers
""").fetchone()[0]

print("After merge:", after_count)