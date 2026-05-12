-- duplicate ids
SELECT 
    'duplicate_ids' AS rule
    ,id
FROM delta_providers
Where id IS NOT NULL --added to prevent grouping NULLS together
GROUP BY id
HAVING COUNT(*) > 1

UNION ALL
-- missing required
SELECT 
    'missing_required_fields' AS rule
    ,COALESCE(id, 'NULL_ID') AS id --this makes it easier to read in logs
FROM delta_providers
WHERE id IS NULL
   OR first_name IS NULL
   OR last_name IS NULL
   OR effective_date IS NULL

UNION ALL
-- date check
SELECT 
    'invalid_dates' AS rule
    ,id
FROM delta_providers
WHERE termination_date IS NOT NULL
  AND termination_date < effective_date

UNION ALL

SELECT 'invalid_type_cast' AS rule, id
FROM delta_providers
WHERE
    TRY_CAST(id AS VARCHAR) IS NULL
    OR TRY_CAST(first_name AS VARCHAR) IS NULL
    OR TRY_CAST(last_name AS VARCHAR) IS NULL
    OR TRY_CAST(effective_date AS DATE) IS NULL
    OR TRY_CAST(termination_date AS DATE) IS NULL
    OR TRY_CAST(primary_care_flag AS BOOLEAN) IS NULL;
 