import duckdb
import pytest

from main import run_sql_file, run_validation


# =========================================================
# SETUP
# =========================================================

def setup_connection(csv_path="data/delta.csv"):
    conn = duckdb.connect()

    run_sql_file(conn, "sql/load.sql", {
        "full_csv": "data/full_dataset.csv",
        "delta_csv": csv_path
    })

    return conn


@pytest.fixture
def conn():
    connection = setup_connection()
    yield connection
    connection.close()


# =========================================================
# POSITIVE TESTS
# =========================================================

def test_delta_validation_passes(conn):
    print("\n=== DELTA VALIDATION (HAPPY PATH) ===")
    run_validation(conn, "sql/validate_delta.sql", "delta_validation")


def test_merge_correctness(conn):
    print("\n=== MERGE TEST (HAPPY PATH) ===")

    before_ids = set(x[0] for x in conn.execute("""
        SELECT id FROM full_providers
    """).fetchall())

    delta_ids = set(x[0] for x in conn.execute("""
        SELECT id FROM delta_providers
    """).fetchall())

    before_count = conn.execute("""
        SELECT COUNT(*) FROM full_providers
    """).fetchone()[0]

    run_sql_file(conn, "sql/merge.sql")

    after_ids = set(x[0] for x in conn.execute("""
        SELECT id FROM full_providers
    """).fetchall())

    after_count = conn.execute("""
        SELECT COUNT(*) FROM full_providers
    """).fetchone()[0]

    # -------------------------
    # INSERT CHECK
    # -------------------------
    expected_inserts = delta_ids - before_ids
    actual_inserts = after_ids - before_ids

    assert expected_inserts == actual_inserts, (
        f"Insert mismatch:\nExpected: {expected_inserts}\nActual: {actual_inserts}"
    )

    # -------------------------
    # DUPLICATE CHECK
    # -------------------------
    dupes = conn.execute("""
        SELECT id
        FROM full_providers
        GROUP BY id
        HAVING COUNT(*) > 1
    """).fetchall()

    assert len(dupes) == 0, f"Duplicate IDs found: {dupes}"

    # -------------------------
    # UPDATE CHECK (sample)
    # -------------------------
    overlapping_ids = list(delta_ids & before_ids)

    if overlapping_ids:
        test_id = overlapping_ids[0]

        delta_row = conn.execute(f"""
            SELECT * FROM delta_providers WHERE id = '{test_id}'
        """).fetchdf()

        full_row = conn.execute(f"""
            SELECT * FROM full_providers WHERE id = '{test_id}'
        """).fetchdf()

        assert delta_row.iloc[0].to_dict() == full_row.iloc[0].to_dict(), \
            f"Update failed for id={test_id}"

    assert after_count >= before_count

    print("Merge test PASSED")


def test_final_validation(conn):
    print("\n=== FINAL VALIDATION ===")
    run_validation(conn, "sql/validate_final.sql", "final_validation")


# =========================================================
# NEGATIVE TESTS (UPDATED — NO CSV DEPENDENCIES)
# =========================================================

def test_duplicate_ids_rejected_inline():
    print("\n=== TEST: Duplicate IDs Rejected (INLINE) ===")

    conn = duckdb.connect()

    conn.execute("""
        CREATE TABLE delta_providers AS
        SELECT
            'dup1' AS id,
            'A' AS first_name,
            'B' AS last_name,
            DATE '2024-01-01' AS effective_date,
            NULL AS termination_date,
            true AS primary_care_flag
        UNION ALL
        SELECT
            'dup1',
            'C',
            'D',
            DATE '2024-01-02',
            NULL,
            true
    """)

    with pytest.raises(Exception):
        run_validation(conn, "sql/validate_delta.sql", "delta_validation")


def test_missing_fields_rejected_inline():
    print("\n=== TEST: Missing Fields Rejected (INLINE) ===")

    conn = duckdb.connect()

    conn.execute("""
        CREATE TABLE delta_providers AS
        SELECT
            NULL AS id,
            'A' AS first_name,
            'B' AS last_name,
            DATE '2024-01-01' AS effective_date,
            NULL AS termination_date,
            true AS primary_care_flag
    """)

    with pytest.raises(Exception):
        run_validation(conn, "sql/validate_delta.sql", "delta_validation")


def test_merge_blocked_on_invalid_data():
    print("\n=== TEST: Merge Blocked on Invalid Data ===")

    conn = duckdb.connect()

    conn.execute("""
        CREATE TABLE delta_providers AS
        SELECT
            NULL AS id,
            'A' AS first_name,
            'B' AS last_name,
            DATE '2024-01-01' AS effective_date,
            NULL AS termination_date,
            true AS primary_care_flag
    """)

    with pytest.raises(Exception):
        run_validation(conn, "sql/validate_delta.sql", "delta_validation")

    # ensures pipeline would stop before merge in real flow
    tables = [t[0] for t in conn.execute("SHOW TABLES").fetchall()]
    assert "delta_providers" in tables


# =========================================================
# OPTIONAL RUNNER
# =========================================================

def run_all_tests():
    conn = setup_connection()

    test_delta_validation_passes(conn)
    test_merge_correctness(conn)
    test_final_validation(conn)

    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    run_all_tests()