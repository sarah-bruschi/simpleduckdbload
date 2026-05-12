# Provider ETL Pipeline (DuckDB + Python)

## Overview

This project implements a lightweight, production-style ETL pipeline using Python and DuckDB to process daily provider delta files and maintain a continuously updated provider dataset.

The pipeline simulates a real-world ingestion workflow:

**load → schema validation → delta validation → snapshot → merge → final validation**

Each stage is implemented as modular SQL files executed via a Python orchestration layer.

The focus is on correctness, data integrity, and pipeline reliability—not framework complexity.

---

## Key Design Principles

- **Separation of concerns**
  - Python handles orchestration only
  - SQL handles all transformations and validations

- **Reproducibility**
  - Entire pipeline runs in-memory using DuckDB
  - Deterministic execution from raw CSV inputs

- **Data safety first**
  - Validation gates prevent invalid data from reaching merge stage
  - Snapshotting preserves pre-merge state for debugging and rollback

---

## Architecture

- **Python**: orchestration and pipeline control flow
- **DuckDB**: in-memory analytical engine
- **SQL files**: transformation + validation logic
- **CSV inputs**: full dataset + daily delta files

---

## Data Model

Each provider record contains:

- `id` (primary key)
- `first_name`
- `last_name`
- `effective_date`
- `termination_date` (nullable)
- `primary_care_flag`

Delta files represent:
- new provider inserts
- updates to existing providers (matched on `id`)

---

## Pipeline Stages

### 1. Load
CSV files are loaded into DuckDB tables:
- `full_providers`
- `delta_providers`

No transformations are applied.

---

### 2. Schema Validation
Ensures required columns exist before processing continues.

---

### 3. Delta Validation (Pre-Merge Gate)
Validates incoming data:

- Duplicate IDs
- Missing required fields
- Invalid date ranges

**Note**: DuckDB’s typed CSV ingestion already rejects invalid primitive types during load, so explicit type validation primarily serves as a secondary schema contract layer.

If validation fails, the pipeline stops execution.

---

### 4. Snapshot
The full dataset is snapshotted before mutation to enable:

- debugging
- rollback analysis
- data lineage tracking

---

### 5. Merge (Upsert Logic)
Applies delta updates:

- Inserts new provider records
- Updates existing providers based on `id`

---

### 6. Final Validation
Ensures post-merge integrity:

- No duplicate IDs
- Required fields remain valid
- No corrupted data introduced

---

## Testing Strategy

The project includes integration tests covering:

### Positive Cases
- Valid delta files process successfully
- Merge correctly applies inserts and updates
- Final dataset remains consistent

### Negative Cases
- Duplicate IDs are rejected
- Missing fields fail validation
- Invalid data blocks merge execution

### Approach
- Fully self-contained tests
- Bad data generated inline using DuckDB SQL
- End-to-end pipeline validation

---

## Production Readiness Considerations

If productionized, the system would require:

### 1. Persistent Storage
- Replace in-memory DuckDB tables with S3 / warehouse / Parquet storage
- Introduce versioned snapshots

### 2. Observability
- Structured logging per pipeline stage
- Metrics for:
  - inserts
  - updates
  - validation failures

### 3. Data Quality Framework
- Configurable validation rules engine
- Severity levels (WARN / FAIL)
- Historical tracking of data quality issues

### 4. Orchestration
- Replace manual execution with Airflow / Dagster / Prefect
- Add retries and failure recovery

### 5. CI/CD Integration
- Automated pipeline tests in CI
- Regression testing for new delta patterns

---

## Operational Concerns — Daily Execution

Running this pipeline daily in production surfaces several classes of issues that require architectural decisions:

### 1. Snapshot Bloat
Each run creates a timestamped backup table (`providers_snapshot_20260512_143022`). Over a year, this accumulates 365+ tables consuming disk space and complicating metadata queries.

**Mitigation**: Implement retention policy (e.g., keep last 30 days), automated cleanup of old snapshots, or use single "current_snapshot" table with metadata instead of per-run tables.

### 2. Delta File Lifecycle Management
No tracking of which delta files have been consumed. Repeated pipeline runs against the same delta file can cause double-merging of updates or create inconsistent state.

**Mitigation**: Move processed deltas to archive, log delta fingerprints (filename + checksum), maintain consumption audit trail in metadata table.

### 3. Idempotency Gaps
If pipeline crashes mid-merge, partial data remains in `full_providers` while snapshot is already created. Re-running creates risk of duplicate inserts or inconsistent state.

**Mitigation**: Wrap merge in database transaction, add run_id tracking throughout pipeline, implement idempotent upsert logic that survives partial executions.

### 4. Performance Degradation Over Time
- No indexes on `id` column; MERGE performance degrades as `full_providers` grows to millions of rows
- Validation (especially TRY_CAST checks) runs on every row even after initial load succeeds
- Query plans may become inefficient after weeks of data accumulation

**Mitigation**: Add PRIMARY KEY constraint on id, create indexes for join performance, optimize validation to only run on new/changed rows.

### 5. Observability Blind Spots
- No metrics: inserts/updates/deletes per run
- No structured logging tied to run_id
- No alerting on validation failures or slow runs
- Cannot correlate pipeline failures to data quality issues

**Mitigation**: Add run metadata table (run_id, start_time, delta_file, inserts, updates, status), implement structured logging per stage, expose Prometheus metrics for monitoring.

### 6. Schema Evolution
If provider schema changes (new columns, type changes), old snapshots become incompatible and validation rules may drift.

**Mitigation**: Version validation rules, maintain schema migration playbooks, pin schema version to each run, archive old snapshots separately.

### 7. Concurrent Execution Risk
If orchestrator triggers pipeline before previous run completes:
- Race condition on delta file consumption
- Snapshot table name collisions
- Delta table gets modified mid-read

**Mitigation**: Implement file-based or database lock, ensure sequential execution, add run_id to all temporary objects.

### 8. Data Lineage Loss
After merge, no way to know when a record last changed, what previous values were, or which delta introduced a change. This makes debugging and compliance difficult.

**Mitigation**: Add `modified_at`, `modified_by_run_id` columns, maintain full change history table, keep immutable event log of all transformations.

### 9. Terminated Provider Accumulation
Over time, terminated providers accumulate in `full_providers`. No strategy for archiving inactive records or handling re-activations.

**Mitigation**: Implement archival policy for terminated providers older than threshold, handle re-activation edge cases in merge logic, report on churn metrics separately.

### 10. Validation Rule Stagnation
Validation rules are static SQL. New edge cases discovered post-production cannot be selectively applied to historical data.

**Mitigation**: Implement validation versioning, allow selective re-validation with new rules, maintain audit trail of rule changes.

---

## Recommended Production Additions

1. **Metadata tracking table**: `(run_id, start_time, delta_file, inserts, updates, validation_status, end_time, error_message)`
2. **Delta consumption log**: Prevents re-processing of the same delta file
3. **Idempotency keys**: Delta file checksum + content hash for deduplication
4. **Change audit table**: Full history of all changes per provider ID
5. **SLA monitoring**: Alert if daily run exceeds threshold (time or record volume)
6. **Snapshot retention policy**: Automated cleanup (e.g., keep only last 30 days)
7. **Database transactions**: Wrap merge in transaction; rollback on validation failure
8. **Primary key constraint**: Enforce uniqueness at DB layer, not just validation
9. **Run-scoped locking**: File or database lock prevents concurrent execution
10. **Data lineage columns**: `modified_at`, `modified_by_run_id` on all records

---

## Running the Pipeline

Install dependencies:
`make install`

To run the pipeline and merge delta's from the csv provided in the data folder:
`make run`

To run tests:
`make test`

To run the data generator:
`make run-generator`

## AI Usage

AI was used as a collaborative engineering tool to accelerate design and implementation of this project. It was used for structuring, test design, and documentation clarity—not for generating final system logic end-to-end.

### Documentation & System Design

- **Generate README.md structure**
  - Prompt Given:  
    “Help me write a clear, hiring-manager-friendly README for a Python + DuckDB ETL pipeline. The pipeline processes daily provider delta files, applies validations, snapshots state before merge, and performs upserts into a full dataset.

    The README should be structured like a production data engineering project with sections for: Overview, Architecture, Data Model, Pipeline Stages, Validation Strategy, Testing Strategy, Production Considerations, and AI Usage.

    Write it so it is easy to scan in under 2 minutes, avoids unnecessary detail, and emphasizes design decisions, data integrity, and reliability.

    The tone should be professional and engineering-focused, not tutorial-like.*

  - Usage:
    AI was used to help organize an initial set of loosely defined ideas into a structured ETL pipeline narrative, including stages, validation flow, and architecture breakdown.

---

### Test Framework Design

- **Generate pytest / integration test structure**
  - Prompt Given:  
    *“Help me design tests for a DuckDB-based ETL pipeline that validate both merge correctness and failure cases”*

  - Usage:
    AI assisted in shaping a full integration testing strategy, including:
    - separation of positive vs negative test cases
    - validation of merge semantics (insert vs update behavior)
    - design of failure scenarios using inline dataset construction
    - structuring end-to-end pipeline validation in a reproducible way

---

### Data Observability & Debugging Enhancements

- **Build a real change-diff report for ETL debugging**
  - Prompt Given:  
    *"Build a real change-diff report that shows exactly what columns changed per ID (before vs after)"*

  - Usage:
    AI was used to design a row-level data diffing approach to improve pipeline observability. This included:
    - comparing snapshot vs post-merge state at the row level
    - identifying field-level changes per provider ID
    - distinguishing between inserts and true updates
    - improving debugging visibility for ETL transformations

    This enhanced the pipeline from basic validation checks into a more production-like data auditing workflow.

---

### Data Generation Support

- **Synthetic dataset generation**
  - Prompt Given:  
    “Generate a realistic synthetic dataset for a provider ETL pipeline.

    The dataset represents a healthcare provider table with the following schema:

    id (string, unique identifier)
    first_name (string)
    last_name (string)
    effective_date (date)
    termination_date (nullable date)
    primary_care_flag (boolean)

    Create two CSV datasets:

    full_dataset.csv (1000 baseline records)
    delta_dataset.csv (30–50 records containing a mix of inserts and updates keyed on id)

    Ensure the delta file includes:

    new provider inserts (new ids)
    updates to existing providers (same id, modified fields)

    Make the data realistic (proper names, valid dates, logical relationships).”

  - Usage:
    AI was used to generate realistic sample datasets for testing incremental updates and validating pipeline behavior under changing inputs.

