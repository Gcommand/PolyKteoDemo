-- Create a temporary list of the department mappings you want to verify
WITH departments_to_check (irregular_name_to_check, abbreviation_to_check) AS (
    VALUES
        ('Department of Aeronautical and Aviation Engineering', 'AAE'),
        ('Department of Applied Biology and Chemical Technology', 'ABCT'),
        ('Department of Applied Physics', 'AP'),
        ('Department of Building and Real Estate', 'BRE'),
        ('Department of Building Environment and Energy Engineering', 'BEEE'),
        ('Department of Civil and Environmental Engineering', 'CEE'),
        ('Department of Computer', 'COMP'),
        ('Department of Electrical and Electronic Engineering', 'EEE'),
        ('Department of Food Science and Nutrition', 'FSN'),
        ('Department of Health Technology and Informatics', 'HTI'),
        ('Department of Industrial and Systems Engineering', 'ISE'),
        ('Department of Industrial & Systems Engineering', 'ISE'),
        ('Department of Land Surveying and Geo-informatics', 'LSGI'),
        ('Department of Land Surveying and Geo-Informatics', 'LSGI'),
        ('Department of Mechanical Engineering', 'ME'),
        ('FCE/BEEE', 'BEEE'),
        ('FENG/EEE', 'EEE'),
        ('FSN/FSN', 'FSN'),
        ('Graduate School', 'GS'),
        ('Industrial Centre', 'IC'),
        ('(Inno/AiDLab)', 'Inno/AiDLab'),
        ('Inno/AiDLab', 'Inno/AiDLab'),
        ('Inno/CAiRS', 'Inno/CAiRS'),
        ('Inno/CEVR', 'Inno/CEVR'),
        ('Innovation and Technology Development Office - PolyU (ITDO)', 'ITDO'),
        ('(ITDO)', 'ITDO'),
        ('School of Design', 'SD'),
        ('School of Fashion and Textiles', 'SFT'),
        ('School of Fashion & Textiles', 'SFT'),
        ('School of Optometry', 'SO'),
        ('SFT/SFT', 'SFT')
)
-- Compare the list with the dictionary and departments tables
SELECT
    c.irregular_name_to_check,
    c.abbreviation_to_check,
    CASE
        -- Case 1: Everything is perfect. The irregular name is found and maps to the correct abbreviation.
        WHEN d.abbreviation IS NOT NULL AND d.abbreviation = c.abbreviation_to_check THEN '✅ Correctly mapped'
        -- Case 2: The irregular name is not in the dictionary at all.
        WHEN d_dict.irregular_name IS NULL THEN '❌ Not found in dictionary'
        -- Case 3: The irregular name is in the dictionary, but it points to a department_id that doesn't exist in the departments table.
        WHEN d.abbreviation IS NULL THEN '⚠️ In dictionary, but linked to an invalid department_id'
        -- Case 4: The irregular name is in the dictionary, but it points to the WRONG department/abbreviation.
        ELSE '❌ Mapped to wrong abbreviation (' || d.abbreviation || ')'
        END AS status
FROM
    departments_to_check c
        LEFT JOIN
    -- Join dictionary on the raw name (case-insensitive, ignoring whitespace)
        public.department_dictionary d_dict ON TRIM(LOWER(c.irregular_name_to_check)) = TRIM(LOWER(d_dict.irregular_name))
        LEFT JOIN
    -- Join departments table to get the abbreviation for the found mapping
        public.departments d ON d_dict.department_id = d.department_id
ORDER BY
    status, c.irregular_name_to_check;



-- This script inserts missing mappings from a predefined list into the department_dictionary.

-- CTE with the full list of desired mappings
WITH desired_mappings (irregular_name, abbreviation) AS (
    VALUES
        ('Department of Aeronautical and Aviation Engineering', 'AAE'),
        ('Department of Applied Biology and Chemical Technology', 'ABCT'),
        ('Department of Applied Physics', 'AP'),
        ('Department of Building and Real Estate', 'BRE'),
        ('Department of Building Environment and Energy Engineering', 'BEEE'),
        ('Department of Civil and Environmental Engineering', 'CEE'),
        ('Department of Computer', 'COMP'),
        ('Department of Electrical and Electronic Engineering', 'EEE'),
        ('Department of Food Science and Nutrition', 'FSN'),
        ('Department of Health Technology and Informatics', 'HTI'),
        ('Department of Industrial and Systems Engineering', 'ISE'),
        ('Department of Industrial & Systems Engineering', 'ISE'),
        ('Department of Land Surveying and Geo-informatics', 'LSGI'),
        ('Department of Land Surveying and Geo-Informatics', 'LSGI'),
        ('Department of Mechanical Engineering', 'ME'),
        ('FCE/BEEE', 'BEEE'),
        ('FENG/EEE', 'EEE'),
        ('FSN/FSN', 'FSN'),
        ('Graduate School', 'GS'),
        ('Industrial Centre', 'IC'),
        ('(Inno/AiDLab)', 'Inno/AiDLab'),
        ('Inno/AiDLab', 'Inno/AiDLab'),
        ('Inno/CAiRS', 'Inno/CAiRS'),
        ('Inno/CEVR', 'Inno/CEVR'),
        ('Innovation and Technology Development Office - PolyU (ITDO)', 'ITDO'),
        ('(ITDO)', 'ITDO'),
        ('School of Design', 'SD'),
        ('School of Fashion and Textiles', 'SFT'),
        ('School of Fashion & Textiles', 'SFT'),
        ('School of Optometry', 'SO'),
        ('SFT/SFT', 'SFT')
),
-- Find the correct department_id for each desired mapping by looking up the abbreviation
     mappings_with_ids AS (
         SELECT
             dm.irregular_name,
             d.department_id
         FROM
             desired_mappings dm
                 JOIN
             public.departments d ON dm.abbreviation = d.abbreviation
     )
-- Insert only the mappings that do not already exist in the dictionary
INSERT INTO public.department_dictionary (irregular_name, department_id)
SELECT
    m.irregular_name,
    m.department_id
FROM
    mappings_with_ids m
WHERE NOT EXISTS (
    -- This check prevents inserting duplicates
    SELECT 1
    FROM public.department_dictionary dd
    WHERE TRIM(LOWER(dd.irregular_name)) = TRIM(LOWER(m.irregular_name))
);