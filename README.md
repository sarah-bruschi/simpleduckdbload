## Overview

This project implements a lightweight ETL pipeline using Python and DuckDB to process daily provider delta files and maintain a full provider dataset.

 ## Data Loading 
CSV files are loaded into DuckDB using `read_csv_auto` and persisted as in-memory tables:
- full_providers
- delta_providers
This step is intentionally minimal and performs no validation or transformation. Its sole responsibility is to materialize raw input data into queryable tables for downstream processing.

## Data Assumptions

The pipeline assumes:
- Consistent schema across daily files
- Required fields: id, first_name, last_name, effective_date
- Delta files contain inserts and updates keyed by `id`

## Delta Validation

Before applying updates, the delta file is validated for:

- Duplicate provider IDs
- Missing required fields
- Invalid date ranges

If validation fails, the pipeline stops execution to prevent corrupting the full dataset.


## To run
Create a python virtual enviornment by running: 
`make install`

To run the generator: 
`make run-generator`

## AI Usage:
I used AI to generate a method of creating sample data - 
Prompt given: Create fake data with this schema so that I can test daily delta file changes. The daily delta file contains: 
New providers to be added
Changes to existing providers (matched on id)
model used: Claude Sonnet 4.6
result:generator.py