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
    ,id 
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
 