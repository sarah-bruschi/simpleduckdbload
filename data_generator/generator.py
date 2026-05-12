import csv
import random
from pathlib import Path
from datetime import date
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

COLUMNS = ["id", "first_name", "last_name", "effective_date",
           "termination_date", "primary_care_flag"]


def random_provider(provider_id: int) -> dict:
    effective_date = fake.date_between(start_date="-2y", end_date="today")
    termination_date = random.choice(["", fake.date_between(start_date=effective_date, end_date="today")])

    return {
        "id":                str(provider_id),
        "first_name":        fake.first_name(),
        "last_name":         fake.last_name(),
        "effective_date":    effective_date,
        "termination_date":  termination_date,
        "primary_care_flag": random.choice(["true", "false"]),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {len(rows):,} rows → {path}")


# ── Generate full dataset ──────────────────────────────────────────────────────

def generate_full_dataset(n: int = 1000) -> list[dict]:
    print(f"\nGenerating full dataset ({n} providers)...")
    rows = [random_provider(i) for i in range(1, n + 1)]
    write_csv(DATA_DIR / "full_dataset.csv", rows)
    return rows


# ── Generate delta file ──────────────────────────────────────────────────────

def generate_delta(full_rows: list[dict],
                   n_updates: int = 20,
                   n_inserts: int = 10) -> None:
    print(f"\nGenerating delta ({n_updates} updates, {n_inserts} new providers)...")

    existing_ids = [r["id"] for r in full_rows]
    next_id = max(int(i) for i in existing_ids) + 1

    update_ids = random.sample(existing_ids, n_updates)
    updates = []
    for uid in update_ids:
        original = next(r for r in full_rows if r["id"] == uid)
        changed = original.copy()
        fields_to_change = random.sample(["first_name", "last_name", "primary_care_flag"], k=random.randint(1, 2))
        for field in fields_to_change:
            if field == "first_name":
                changed["first_name"] = fake.first_name()
            elif field == "last_name":
                changed["last_name"] = fake.last_name()
            elif field == "primary_care_flag":
                changed["primary_care_flag"] = random.choice(["true", "false"])

        changed["effective_date"] = date.today()
        changed["termination_date"] = random.choice(["", fake.date_between(start_date=changed["effective_date"], end_date="today")])
        updates.append(changed)

    inserts = [random_provider(next_id + i) for i in range(n_inserts)]

    delta_rows = updates + inserts
    random.shuffle(delta_rows)
    write_csv(DATA_DIR / "delta.csv", delta_rows)


# ── Bad delta variants (for testing validation failures) ──────────────────────

def generate_bad_delta_duplicate_ids(full_rows: list[dict]) -> None:
    """Delta where the same provider_id appears twice — should fail step 1."""
    print("\nGenerating bad delta (duplicate IDs)...")
    rows = [random_provider(9001), random_provider(9001)]
    write_csv(DATA_DIR / "delta_bad_duplicate_ids.csv", rows)


def generate_bad_delta_missing_column(full_rows: list[dict]) -> None:
    """Delta missing the first_name column — should fail step 1."""
    print("\nGenerating bad delta (missing column)...")
    rows = [random_provider(9002)]
    bad_rows = [{k: v for k, v in r.items() if k != "first_name"} for r in rows]
    path = DATA_DIR / "delta_bad_missing_column.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[c for c in COLUMNS if c != "first_name"])
        writer.writeheader()
        writer.writerows(bad_rows)
    print(f"  wrote {len(bad_rows)} rows → {path}")


def generate_bad_delta_null_required(full_rows: list[dict]) -> None:
    """Delta with null first_name — should fail step 1."""
    print("\nGenerating bad delta (null required field)...")
    row = random_provider(9003)
    row["first_name"] = ""
    write_csv(DATA_DIR / "delta_bad_null_first_name.csv", [row])


def generate_bad_delta_invalid_date(full_rows: list[dict]) -> None:
    """Delta with a garbage effective_date — should fail step 1."""
    print("\nGenerating bad delta (invalid date)...")
    row = random_provider(9004)
    row["effective_date"] = "not-a-date"
    write_csv(DATA_DIR / "delta_bad_invalid_date.csv", [row])


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    full = generate_full_dataset(n=1000)

    generate_delta(full, n_updates=20, n_inserts=10)
    generate_bad_delta_duplicate_ids(full)
    generate_bad_delta_missing_column(full)
    generate_bad_delta_null_required(full)
    generate_bad_delta_invalid_date(full)

    print("\nDone. Test runs:")
    print("  python pipeline.py --full data/full_dataset.csv --delta data_generator/data/delta.csv")
    print("  python pipeline.py --full data/full_dataset.csv --delta data_generator/data/delta_bad_duplicate_ids.csv")
    print("  python pipeline.py --full data/full_dataset.csv --delta data_generator/data/delta_bad_missing_column.csv")
    print("  python pipeline.py --full data/full_dataset.csv --delta data_generator/data/delta_bad_null_first_name.csv")
    print("  python pipeline.py --full data/full_dataset.csv --delta data_generator/data/delta_bad_invalid_date.csv")
