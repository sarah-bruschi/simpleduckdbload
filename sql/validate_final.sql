SELECT 
    'duplicate_ids' AS rule
    ,id
FROM full_providers
Where id IS NOT NULL
GROUP BY id 
HAVING COUNT(*) > 1

UNION ALL 

SELECT 
    'missing_required_fields' AS rule
    ,id
FROM full_providers
WHERE id IS NULL 
    OR first_name IS NULL 
    OR last_name IS NULL 
    OR effective_date IS NULL 
    OR primary_care_flag IS NULL 

UNION ALL 

SELECT 
    'invalid_dates' AS rule
    ,id
FROM full_providers
WHERE termination_date IS NOT NULL 
    AND termination_date < effective_date;