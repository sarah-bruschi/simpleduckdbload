import duckdb
from datetime import datetime



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

def generate_change_diff_report(conn, snapshot_table):
    print("\n==============================")
    print(" FIELD-LEVEL CHANGE REPORT")
    print("==============================")

    # -------------------------
    # Get delta IDs
    # -------------------------
    delta_ids = set(x[0] for x in conn.execute("""
        SELECT id FROM delta_providers
    """).fetchall())

    # -------------------------
    # Inserts (new IDs)
    # -------------------------
    snapshot_ids = set(x[0] for x in conn.execute(f"""
        SELECT id FROM {snapshot_table}
    """).fetchall())

    inserts = delta_ids - snapshot_ids

    print(f"\n--- INSERTS ({len(inserts)}) ---")
    print(list(inserts)[:10])

    # -------------------------
    # Updates (existing IDs)
    # -------------------------
    updates = delta_ids & snapshot_ids

    print(f"\n--- UPDATES WITH FIELD CHANGES ---")

    changed_rows = []

    for id_ in list(updates):

        before = conn.execute(f"""
            SELECT * FROM {snapshot_table}
            WHERE id = '{id_}'
        """).fetchdf()

        after = conn.execute(f"""
            SELECT * FROM full_providers
            WHERE id = '{id_}'
        """).fetchdf()

        if before.empty or after.empty:
            continue

        before_row = before.iloc[0]
        after_row = after.iloc[0]

        row_changes = {}

        for col in before.columns:
            before_val = before_row[col]
            after_val = after_row[col]

            if before_val != after_val:
                row_changes[col] = {
                    "before": before_val,
                    "after": after_val
                }

        if row_changes:
            changed_rows.append({
                "id": id_,
                "changes": row_changes
            })

    # -------------------------
    # Print diff
    # -------------------------
    for item in changed_rows[:10]:
        print(f"\nID: {item['id']}")
        for col, vals in item["changes"].items():
            print(f"  {col}: {vals['before']} → {vals['after']}")

    print(f"\nTotal updated rows with actual changes: {len(changed_rows)}")






def main():

    conn = duckdb.connect()
    # -------------
    # 1. LOAD
    # -------------
    run_sql_file(conn, "sql/load.sql", {
        "full_csv": "data/full_dataset.csv",
        "delta_csv": "data/delta.csv"
    })


    # ------------------
    # 2. VALIDATE DELTA
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
    # 3. SNAPSHOT FULL DATASET
    # ------------------

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_table = f"providers_snapshot_{timestamp}"
    run_sql_file(conn, "sql/snapshot.sql", {
        "snapshot_table": snapshot_table
    })


    # ------------------
    # 4.MERGE
    # ------------------

    run_sql_file(conn, "sql/merge.sql")


    # ------------------
    # 5.VALIDATE FINAL
    # ------------------
    run_validation(conn, "sql/validate_final.sql", "final_validation")


    # ------------------
    # 6.Show diff report
    # ------------------

    generate_change_diff_report(conn, snapshot_table)


if __name__ == "__main__":
    main()