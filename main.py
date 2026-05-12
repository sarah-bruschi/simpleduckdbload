import duckdb
from datetime import datetime

conn = duckdb.connect()

# load files 
def run_sql_file(conn, path, params=None):
    with open(path) as f:
        sql = f.read()

    if params:
        sql = sql.format(**params)

    conn.execute(sql)

run_sql_file(conn, "sql/load.sql", {
    "full_csv": "data/full_dataset.csv",
    "delta_csv": "data/delta.csv"
})



full_count = conn.execute("""
SELECT COUNT(*) FROM full_providers
""").fetchone()[0]

delta_count = conn.execute("""
SELECT COUNT(*) FROM delta_providers
""").fetchone()[0]

# debugging
print("Full providers count:", full_count)
print("Delta providers count:", delta_count)

# testing actual load
def inspect_table(conn, table_name):

    print(f"\n--- {table_name} SAMPLE ROWS ---")
    print(conn.execute(f"""
        SELECT * FROM {table_name} LIMIT 5
    """).fetchdf())

    print(f"\n--- {table_name} SCHEMA ---")
    print(conn.execute(f"""
        DESCRIBE {table_name}
    """).fetchdf())

    print(f"\n--- {table_name} COLUMN CHECK ---")

    expected = {
        "id",
        "first_name",
        "last_name",
        "effective_date",
        "termination_date",
        "primary_care_flag"
    }

    actual = set(
        row[1]
        for row in conn.execute(f"""
            PRAGMA table_info('{table_name}')
        """).fetchall()
    )

    missing = expected - actual

    if missing:
        raise Exception(f"{table_name} missing columns: {missing}")

    print("Schema OK")


inspect_table(conn, "full_providers")
inspect_table(conn, "delta_providers")


#validate delta
with open("sql/validate_delta.sql") as f:
    sql = f.read()

    results = conn.execute(sql).fetchall()

    print(f"Validation rows returned: {len(results)}")

    if len(results) > 0:
        print("Failures:")
        for r in results[:10]:
            print(r)
        raise Exception("Validation failed")

    else:
        print("Validation passed")


# snapshot full dataset

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
snapshot_table = f"providers_snapshot_{timestamp}"
run_sql_file(conn, "sql/snapshot.sql", {
    "snapshot_table": snapshot_table
})
print(conn.execute("SHOW TABLES").fetchall())
# create delta history table 
# merge delta with existing
# final validation 