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

print("Full providers count:", full_count)
print("Delta providers count:", delta_count)