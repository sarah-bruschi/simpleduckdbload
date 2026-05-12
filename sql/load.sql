CREATE OR REPLACE TABLE full_providers AS
SELECT * FROM read_csv_auto('{full_csv}');

CREATE OR REPLACE TABLE delta_providers AS
SELECT * FROM read_csv_auto('{delta_csv}');