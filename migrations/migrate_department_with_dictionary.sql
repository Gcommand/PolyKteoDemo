-- This SQL assumes:
-- 1. Your 'public.departments' table is populated with abbreviations and their corresponding department_id (the SERIAL PK).
-- 2. Your 'public.department_dictionary' table is populated with exact distinct 'irregular_name' values
--    (from patents_list.department parts) and their corresponding integer 'department_id'.
--    Example: If patents_list.department contains 'FENG/BME ; ASO/IC', then department_dictionary
--    should have 'feng/bme' and 'aso/ic' as 'irregular_name' entries.
-- 3. Your 'public.patent_departments' table is created as per your DDL, linking patent_id (int) to department_id (int PK from departments).

-- Step 1: Explode the multi-valued 'department' column in 'patents_list'.
--         First, standardize delimiters by replacing all commas with semicolons.
--         Then, split the string by semicolons into individual raw department name strings.
--         Trim whitespace from each part.
WITH exploded_patent_raw_parts AS (
    SELECT
        pl.sys_id AS patent_id,
        TRIM(UNNEST(STRING_TO_ARRAY(REPLACE(pl.department, ',', ';'), ';'))) AS department_name_raw_part
    FROM
        public.patents_list pl
    WHERE
        pl.department IS NOT NULL AND pl.department != ''
),
-- Step 2: Clean each individual department name part only by trimming and lowercasing.
--         Since the dictionary is generated from distinct values, no further text replacement
--         is needed here, as the dictionary itself should contain the exact (case-insensitive)
--         form of these raw parts.
cleaned_department_parts AS (
    SELECT
        eprp.patent_id,
        TRIM(LOWER(eprp.department_name_raw_part)) AS cleaned_department_part
    FROM
        exploded_patent_raw_parts eprp
    WHERE
        TRIM(eprp.department_name_raw_part) != '' -- Filter out empty strings that might result from multiple delimiters
),
-- Step 3: Join the cleaned individual department name parts with department_dictionary
--         to get the final integer 'department_id'.
--         INNER JOIN ensures we only consider parts that have a direct mapping in the dictionary.
mapped_department_ids AS (
    SELECT DISTINCT -- Use DISTINCT to ensure unique (patent_id, department_id) pairs
        cdp.patent_id,
        dd.department_id
    FROM
        cleaned_department_parts cdp
    INNER JOIN
        public.department_dictionary dd ON cdp.cleaned_department_part = TRIM(LOWER(dd.irregular_name))
)
-- Step 4: Insert the processed data into the public.patent_departments table.
INSERT INTO public.patent_departments (patent_id, department_id)
SELECT
    md.patent_id,
    md.department_id
FROM
    mapped_department_ids md
ON CONFLICT (patent_id, department_id) DO NOTHING; -- Prevents errors on re-run if primary key exists

-- Optional: After you have successfully migrated all data and verified its correctness,
-- you can remove the original 'department' column from the 'patents_list' table.
-- ALTER TABLE public.patents_list DROP COLUMN department;