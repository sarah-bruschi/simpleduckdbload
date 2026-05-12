MERGE INTO full_providers f
USING delta_providers d
ON f.id = d.id
WHEN MATCHED THEN UPDATE SET
    first_name = d.first_name,
    last_name = d.last_name,
    effective_date = d.effective_date,
    termination_date = d.termination_date,
    primary_care_flag = d.primary_care_flag
WHEN NOT MATCHED THEN
INSERT (
    id
    ,first_name
    ,last_name
    ,effective_date
    ,termination_date
    ,primary_care_flag
)
VALUES (
    d.id
    ,d.first_name
    ,d.last_name
    ,d.effective_date
    ,d.termination_date
    ,d.primary_care_flag
);