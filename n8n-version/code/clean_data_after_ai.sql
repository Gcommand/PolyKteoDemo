UPDATE patents_list
SET
    ai_summary =
        -- The chain of nested functions applies each rule sequentially
        REPLACE(
                REPLACE(
                        REPLACE(
                                REPLACE(
                                        REPLACE(
                                                REPLACE(
                                                        REPLACE(
                                                            -- 1. Remove trailing commas
                                                                regexp_replace(ai_summary, ',\s*(\n|$)', E'\\1', 'g'),
                                                            -- 2. Remove '---' separators
                                                                '---', ''
                                                        ),
                                                    -- 3. Standardize field names
                                                        'official_title', 'Official Title'
                                                ),
                                                'tech_sector', 'Tech Sector'
                                        ),
                                        'inventor', 'Inventor'
                                ),
                                'department', 'Department'
                        ),
                        'country_region', 'Country Region'
                ),
            -- 4. Standardize a specific field value
                'Navigation/Timing', 'Positioning/Navigation/Timing'
        )
WHERE
  -- This comprehensive WHERE clause is now idempotent for the tech sector change.
  -- It will only select rows that need at least one of the specified fixes.
    (
        ai_summary ~ '---'
            OR ai_summary ~ ',\s*(\n|$)'
            OR ai_summary ~ '(official_title|tech_sector|inventor|department|country_region)'
            OR (ai_summary LIKE '%Navigation/Timing%' AND ai_summary NOT LIKE '%Positioning/Navigation/Timing%')
        ) AND is_tech = false
;
UPDATE patents_list
SET
    ai_summary = regexp_replace(
            ai_summary,
        -- Match group 1: Start of string or a newline
        -- Match group 2: Any leading whitespace
        -- Match group 3: One of the target keywords
            '(^|\n)(\s*)(Official Title|Tech Sector|Inventor|Department|Country Region)',
        -- Reconstruct the line: \1(newline) \2(whitespace) - \3(keyword)
            E'\\1\\2- \\3',
            'g'
                 )
WHERE
    -- This WHERE clause efficiently finds only the rows that need updating,
    -- ignoring rows where the change has already been made.
    ai_summary ~ '(^|\n)\s*(Official Title|Tech Sector|Inventor|Department|Country Region)';