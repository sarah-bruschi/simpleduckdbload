import duckdb

conn = duckdb.connect()


conn.execute("""
CREATE TABLE full_providers AS
SELECT * FROM read_csv_auto('data/full_dataset.csv');
""")

conn.execute("""
CREATE TABLE delta_providers AS
SELECT * FROM read_csv_auto('data/delta.csv');
""")

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