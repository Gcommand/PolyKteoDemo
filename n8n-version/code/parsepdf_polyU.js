// This code element processes text extracted from a PDF to structure patent information.
// It skips the initial title row and parses each patent entry into a separate item.

// The input to this node is expected to be an item with a 'json' property containing a 'text' field.
// Example Input: [{ json: { text: "Official Title Tech Sector Inventor Department Country / Region\nGoogle Patent Link\n..." } }]

const originalText = $input.first().json.text;
console.log('Original Text Input:', originalText);

// Define known entities for robust parsing.
// These lists help in identifying and categorizing parts of the text.
const knownCountries = [
    'China', 'United States Of America', 'Hong Kong', 'Europe', 'Germany',
    'France', 'Italy', 'Netherlands', 'Romania', 'Serbia', 'Sweden',
    'Switzerland', 'Turkey', 'United Kingdom', 'Hungary', 'Japan', 'Taiwan',
    'India', 'Australia', 'Spain', 'Canada', 'Belgium', 'Macao', 'Malaysia',
    'Singapore', 'Nepal', 'South Korea / Republic of Korea', 'Mexico',
    'Ireland', 'Thailand', 'International Procedure', 'European Procedure (Patents)', 'Korea', 'United States'
]


const knownDepartments = [
    'FENG/BME', 'ASO/IC', 'FAST/ITC', 'FENG/EE', 'FENG/ISE', 'FENG/EIE',
    'FHSS/HTI', 'FHSS/SO', 'FENG/COMP', 'FAST/AP', 'RIIPT/RIIPT',
    'FENG/ME', 'FAST/ABCT', 'FCE/CEE', 'FCE/BSE', 'FCE/LSGI', 'SD/SD',
    'FB/MM', 'LGT/LGT', 'FHSS/RS', 'FHSS/SN', 'PDO/PDO', 'DP/DP', 'OR/OR',
    '(ITDO)', 'FENG/AAE', 'FCE/BRE', 'FB/LMS', 'FAST/AMA',
    'ASO/CDO', 'SFT/SFT', 'Inno/AiDLab', '(Inno/AiDLab)', 'Inno/CAiRS', 'Inno/CEVR',
    'FHSS/FHSS', 'FENG/EEE', 'FCE/BEEE', 'HKCC', 'FENG/FENG', 'FSN/FSN', 'FB/AF', 'Innovation and Technology Development Office - PolyU (ITDO)', 'Research Institute for Future Food (Rifood)'
];


const knownTechSectors = [
    'Healthcare/Textile',
    'Textile',
    'Textiles',
    'Electrical & Manufacturing',
    'Information and Communications Technology',
    'Material Science',
    'Foodtech/Biotech/Pharmaceutical',
    'Construction',
    'Positioning/Navigation/Timing',
    'Other',
    'Electrical & Manufacturing/Information and Communications Technology',
    'Healthcare',
    'Construction/Positioning/Navigation/Timing',
    'Foodtech/Biotech/Pharmaceutical/Textile',
    'Construction Foodtech/Biotech/Pharmaceutical',
    'Green Tech',
    'Food Tech',
    'Material Tech',
    'Manufacturing Tech',
    'Bio Tech / Pharmaceutical',
    'Health Tech',
    'Smart Hardware',
    'ICT',
    'Energy Tech',
    'Fashion & Textile',
    'Property Tech',
    'Robotics',
    'Social / Ed Tech',
    'FinTech',
    'Precision Manufacturing Techniques'
]


/**
 * Parses a single patent entry, which now receives already separated content and link.
 * It extracts country and then uses parseRemainingContentLineByLine for other fields.
 *
 * @param {string} contentPart The text containing title, tech sector, inventors, department, country.
 * @param {string} googlePatentLink The extracted and cleaned Google Patent Link.
 * @returns {object} An object containing the parsed patent fields.
 */
function parsePatentEntry(contentPart, googlePatentLink) {
    console.log('\n--- Parsing new patent entry ---');
    console.log('Content Part to Parse:', `\n---\n${contentPart}\n---`);
    console.log('Google Patent Link:', googlePatentLink);

    const patent = {
        officialTitle: '',
        techSector: '',
        inventors: '',
        department: '',
        countryRegion: '',
        googlePatentLink: googlePatentLink // Link is already clean
    };

    const parsedData = parseRemainingContentLineByLine(contentPart);
    Object.assign(patent, parsedData);

    console.log('Final Parsed Patent Data for this entry:', patent);
    return patent;
}

/**
 * Parses the content for Title, Tech Sector, Inventors, Departments, and Country.
 * This version strictly adheres to the sequential order: Title -> Tech Sector -> Inventors/Departments/Country.
 *
 * @param {string} contentStr The string containing the title, tech sector, inventors, department, and country information.
 * @returns {object} An object with officialTitle, techSector, inventors, department, and countryRegion properties.
 * @throws {Error} If a tech sector cannot be identified.
 */
function parseRemainingContentLineByLine(contentStr) {
    console.log('\n--- Starting parseRemainingContentLineByLine ---');
    console.log('Content String for remaining parsing:', `\n---\n${contentStr}\n---`);

    let data = {
        officialTitle: '',
        techSector: '',
        inventors: [],
        department: [],
        countryRegion: '' // Initialize country here
    };

    // --- Preprocessing: Aggressive newline and whitespace normalization ---
    let processedContentStr = contentStr;

    // 1. Replace specific known multi-line phrases first (ensure exact matches for these long terms)
    processedContentStr = processedContentStr.replace(/Electrical & Manufacturing\/Information and\s*Comunications Technology/g, 'Electrical & Manufacturing/Information and Communications Technology');
    processedContentStr = processedContentStr.replace(/Construction\/Positioning\/Navigation\/Timing/g, 'Construction/Positioning/Navigation/Timing');
    processedContentStr = processedContentStr.replace(/Foodtech\/Biotech\/Pharmaceutical\/Textile/g, 'Foodtech/Biotech/Pharmaceutical/Textile');

    // 2. Specific handling for 'Pharmaceutical' to consolidate internal spaces/newlines.
    processedContentStr = processedContentStr.replace(/P\s*h\s*a\s*r\s*m\s*a\s*c\s*e\s*u\s*t\s*i\s*c\s*a\s*l/gi, 'Pharmaceutical');


    // 3. Remove newlines that split *Chinese characters* (already there, ensuring no space)
    processedContentStr = processedContentStr.replace(/([\u4e00-\u9fa5])\s*\n\s*([\u4e00-\u9fa5])/g, '$1$2');

    // 4. Replace newlines that might be splitting a word from a *capitalized* word, intended as a space
    //    This handles cases like "InventorName\nDepartmentAbbr" or "word\nNextWord"
    processedContentStr = processedContentStr.replace(/([a-zA-Z0-9\.'\-,;])\s*\n\s*([A-Z\u4e00-\u9fa5\(\)])/g, '$1 $2');

    // 5. Replace any *remaining* newlines with a single space. This catches other general line breaks.
    processedContentStr = processedContentStr.replace(/\n/g, ' ');

    // 6. Consolidate all types of whitespace (multiple spaces, tabs, etc.) into a single space.
    processedContentStr = processedContentStr.replace(/\s+/g, ' ');
    processedContentStr = processedContentStr.trim();

    // 7. Remove noise patterns like (D84), (D30), etc. - parentheses with D followed by 1-3 digits
    processedContentStr = processedContentStr.replace(/\s*\(D\d{1,3}\)\s*/g, ' ');
    
    // 8. Clean up any extra spaces created by the noise removal
    processedContentStr = processedContentStr.replace(/\s+/g, ' ').trim();

    console.log('Content String after aggressive preprocessing and noise removal:', `\n---\n${processedContentStr}\n---`);

    let bestTechSectorMatch = null;
    let potentialTechSectorMatches = [];

    // --- Normalize and deduplicate tech sectors ---
    // Create a map of normalized tech sectors to their canonical forms
    const normalizedTechSectors = new Map();
    
    for (const ts of knownTechSectors) {
        // Normalize by: 1) trimming, 2) single spaces around slashes/semicolons, 3) single spaces between words
        const normalized = ts.trim()
            .replace(/\s*\/\s*/g, ' / ')  // Normalize slash spacing to " / "
            .replace(/\s*;\s*/g, ' ; ')   // Normalize semicolon spacing to " ; "
            .replace(/\s+/g, ' ');        // Multiple spaces become single space
        
        // If we haven't seen this normalized form, or if current entry is "preferred" (shorter/cleaner)
        if (!normalizedTechSectors.has(normalized) || ts.length < normalizedTechSectors.get(normalized).length) {
            normalizedTechSectors.set(normalized, ts);
        }
    }
    
    // --- Generate comprehensive list of all possible tech sector regex patterns ---
    // Sorted by their "length" (number of characters, which correlates to regex complexity/specificity)
    const allPossibleTechSectorRegexes = [];
    for (const [normalized, canonical] of normalizedTechSectors.entries()) {
        // Create a regex pattern that allows for flexible spacing around separators
        let pattern = normalized.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // Escape regex special chars

        // Allow flexible spacing around slashes and semicolons (e.g., Foodtech / Biotech, Foodtech/ Biotech, Foodtech /Biotech)
        pattern = pattern.replace(/\s*\/\s*/g, '\\s*\/\\s*');
        pattern = pattern.replace(/\s*;\s*/g, '\\s*;\\s*');

        // Allow flexible spacing where there's an actual space (e.g., Material Science)
        pattern = pattern.replace(/(\s+)/g, '\\s+'); // Use \\s+ to match one or more spaces

        allPossibleTechSectorRegexes.push({
            original: canonical, // Use the canonical form for output
            normalized: normalized,
            // Use word boundaries for the overall pattern to ensure it doesn't match partial words
            regex: new RegExp(`\\b${pattern}\\b`, 'gi')
        });

        // Also add a variant where slashes and semicolons are treated as just spaces in the regex pattern,
        // allowing for matching cases where the '/' or ';' might be missing or replaced by space.
        let spaceSeparatedPattern = normalized.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        spaceSeparatedPattern = spaceSeparatedPattern.replace(/\s*\/\s*/g, '\\s+'); // Slashes become one or more spaces
        spaceSeparatedPattern = spaceSeparatedPattern.replace(/\s*;\s*/g, '\\s+'); // Semicolons become one or more spaces
        spaceSeparatedPattern = spaceSeparatedPattern.replace(/(\s+)/g, '\\s+'); // Ensure spaces are \s+

        allPossibleTechSectorRegexes.push({
            original: canonical,
            normalized: normalized,
            regex: new RegExp(`\\b${spaceSeparatedPattern}\\b`, 'gi')
        });
    }
    // Sort by normalized length (longest pattern first) for greedy matching of the 'canonical' form
    allPossibleTechSectorRegexes.sort((a, b) => b.normalized.length - a.normalized.length);


    // --- Collect ALL potential tech sector matches with their start and end indices using RegExp.exec ---
    for (const tsCandidate of allPossibleTechSectorRegexes) {
        const currentRegex = new RegExp(tsCandidate.regex.source, 'gi'); // Create new regex instance for exec
        let match;
        while ((match = currentRegex.exec(processedContentStr)) !== null) {
            // Check if character before is non-word or start of string (already part of \b)
            // Check if character after is non-word or end of string (already part of \b)

            // Further check for common immediate delimiters after the tech sector
            const charAfterMatch = processedContentStr[match.index + match[0].length];
            const isFollowedByDelimiter = (match.index + match[0].length === processedContentStr.length) ||
                /\s/.test(charAfterMatch) || charAfterMatch === ';' || charAfterMatch === ',' ||
                knownDepartments.some(kd => processedContentStr.substring(match.index + match[0].length).trim().startsWith(kd)) ||
                knownCountries.some(kc => processedContentStr.substring(match.index + match[0].length).trim().startsWith(kc));

            if (isFollowedByDelimiter) { // Check only the end boundary here, as \b handles start
                potentialTechSectorMatches.push({
                    ts: tsCandidate.original, // Store the original clean string for output
                    index: match.index,
                    length: match[0].length, // Length of the *actual matched text*
                    matchedText: match[0] // The text that was actually matched
                });
            }
        }
    }

    // --- Select ALL non-overlapping tech sector matches ---
    // Sort potential matches by start index to process them in order
    potentialTechSectorMatches.sort((a, b) => a.index - b.index);
    
    let selectedTechSectorMatches = [];
    let lastEndIndex = -1;
    
    if (potentialTechSectorMatches.length > 0) {
        for (const match of potentialTechSectorMatches) {
            // Only include non-overlapping matches
            if (match.index >= lastEndIndex) {
                selectedTechSectorMatches.push(match);
                lastEndIndex = match.index + match.length;
            }
        }
        
        // Apply custom preferences within the selected matches
        // Prefer 'Textile' over 'Textiles' if both are present
        const hasTextile = selectedTechSectorMatches.some(m => m.ts === 'Textile');
        const hasTextiles = selectedTechSectorMatches.some(m => m.ts === 'Textiles');
        
        if (hasTextile && hasTextiles) {
            // Remove 'Textiles' in favor of 'Textile'
            selectedTechSectorMatches = selectedTechSectorMatches.filter(m => m.ts !== 'Textiles');
        }
        
        // For backward compatibility, set bestTechSectorMatch to the first one for split logic
        bestTechSectorMatch = selectedTechSectorMatches[0];
    }

    let preTechSectorContent = '';
    let postTechSectorContent = '';

    if (selectedTechSectorMatches.length > 0) {
        // Combine all selected tech sectors
        data.techSector = selectedTechSectorMatches.map(match => match.ts).join('/');
        
        // Remove all tech sector matches from the content by replacing them with spaces
        let contentWithoutTechSectors = processedContentStr;
        
        // Sort matches by index in reverse order to avoid index shifting when removing
        const sortedMatches = [...selectedTechSectorMatches].sort((a, b) => b.index - a.index);
        
        for (const match of sortedMatches) {
            contentWithoutTechSectors = contentWithoutTechSectors.substring(0, match.index) + 
                ' ' + contentWithoutTechSectors.substring(match.index + match.length);
        }
        
        // Clean up extra spaces
        contentWithoutTechSectors = contentWithoutTechSectors.replace(/\s+/g, ' ').trim();
        
        // For splitting into title and post-tech content, use the first tech sector position as reference
        const firstTechSectorMatch = selectedTechSectorMatches[0];
        preTechSectorContent = processedContentStr.substring(0, firstTechSectorMatch.index).trim();
        
        // For post-tech content, use the cleaned content (with all tech sectors removed)
        // Find where the title ends in the cleaned content and use the rest as post-tech content
        postTechSectorContent = contentWithoutTechSectors.substring(preTechSectorContent.length).trim();

        console.log(`Optimal Partition:`);
        console.log(`  Official Title: "${preTechSectorContent}"`);
        console.log(`  Tech Sectors (${selectedTechSectorMatches.length}): "${data.techSector}"`);
        console.log(`  Post-Tech Sector Content: "${postTechSectorContent}"`);
    } else {
        // ERROR: Tech Sector not identified - this will now halt the n8n workflow for this item
        console.error('ERROR: Tech Sector not identified for content:', contentStr);
        throw new Error('Tech Sector not found in patent entry.' + contentStr);
    }

    data.officialTitle = preTechSectorContent.replace(/[\s;]+/g, ' ').replace(/\s+/g, ' ').trim();
    data.officialTitle = data.officialTitle.replace(/([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])/g, '$1$2');


    // --- Extract Department(s) and Country from Post-Tech Sector Content ---
    let remainingContent = postTechSectorContent;
    
    // --- Preprocessing: Handle common typos in department names ---
    // Fix typo: "Innovation; Technology" should be "Innovation and Technology"
    remainingContent = remainingContent.replace(/Innovation\s*;\s*Technology\s+Development\s+Office\s*-\s*PolyU\s*\(\s*ITDO\s*\)/gi, 
        'Innovation and Technology Development Office - PolyU (ITDO)');
    
    let extractedDepartments = new Set();
    let extractedCountry = '';

    // Step 1: Try to extract country first (often at the very end of the structured part)
    // The country is usually at the very end of the line.
    const sortedCountriesByLengthRev = [...knownCountries].sort((a,b) => b.length - a.length);
    for (const kc of sortedCountriesByLengthRev) {
        // Escape regex special chars and create flexible pattern for parentheses
        let escapedCountry = kc.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        
        // For entries with parentheses, make them more flexible with optional spaces
        escapedCountry = escapedCountry.replace(/\\\(/g, '\\s*\\(\\s*');
        escapedCountry = escapedCountry.replace(/\\\)/g, '\\s*\\)\\s*');
        
        // Use a more flexible pattern: look for the country at the end, but allow for trailing spaces/punctuation
        const countryRegex = new RegExp(`(?:^|\\s)${escapedCountry}\\s*$`, 'i');
        const match = remainingContent.match(countryRegex);
        if (match) {
            extractedCountry = kc;
            remainingContent = remainingContent.substring(0, match.index).trim(); // Remove country from remaining
            console.log(`Found country "${extractedCountry}", remainingContent after country: "${remainingContent}"`);
            break;
        }
    }
    data.countryRegion = extractedCountry;

    // Step 2: Identify the split point between Inventors and Departments
    let departmentOrDelimiterStartIndex = -1;

    // First, scan for the earliest occurrence of any known department using regex.
    const sortedDepartmentsByLength = [...knownDepartments].sort((a, b) => b.length - a.length);
    for (const kd of sortedDepartmentsByLength) {
        // Simplified regex pattern - just escape special chars and handle basic spacing
        let escapedDept = kd.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        
        // Handle parentheses with flexible spacing
        escapedDept = escapedDept.replace(/\\\(/g, '\\s*\\(\\s*');
        escapedDept = escapedDept.replace(/\\\)/g, '\\s*\\)\\s*');
        
        // Handle slashes with flexible spacing  
        escapedDept = escapedDept.replace(/\\\//g, '\\s*\/\\s*');
        
        // Handle hyphens with flexible spacing
        escapedDept = escapedDept.replace(/\\-/g, '\\s*-\\s*');
        
        // Allow flexible spacing where there are actual spaces
        escapedDept = escapedDept.replace(/\s+/g, '\\s+');
        
        const deptRegex = new RegExp(`(?:^|\\s|;)${escapedDept}(?=\\s|;|,|$)`, 'gi');
        let match = deptRegex.exec(remainingContent); // Use exec to get index

        if (match) {
            if (departmentOrDelimiterStartIndex === -1 || match.index < departmentOrDelimiterStartIndex) {
                departmentOrDelimiterStartIndex = match.index;
            }
        }
        // Reset regex lastIndex for next iteration (important for global regexes)
        if (deptRegex.global) deptRegex.lastIndex = 0;
    }

    let inventorsRaw = '';
    let departmentsRawCandidate = ''; // This will hold the block that should contain departments

    if (departmentOrDelimiterStartIndex !== -1) {
        inventorsRaw = remainingContent.substring(0, departmentOrDelimiterStartIndex).trim();
        departmentsRawCandidate = remainingContent.substring(departmentOrDelimiterStartIndex).trim();

        // Remove any leading delimiters (semicolon, colon, comma) from departmentsRawCandidate
        // This ensures the department parsing starts with the department text, not leading punctuation.
        departmentsRawCandidate = departmentsRawCandidate.replace(/^[:;,\s]+/, '').trim();

    } else {
        // If no clear department is found, assume everything left is inventors
        inventorsRaw = remainingContent;
    }

    console.log(`Inventors Raw before final split: "${inventorsRaw}"`);
    console.log(`Departments Raw Candidate: "${departmentsRawCandidate}"`);

    // Step 3: Extract Departments from the departmentsRawCandidate
    let tempExtractedDepartments = new Set();
    let remainingAfterDepartmentExtraction = departmentsRawCandidate;

    for (const kd of sortedDepartmentsByLength) {
        // Simplified regex pattern - just escape special chars and handle basic spacing
        let escapedDept = kd.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        
        // Handle parentheses with flexible spacing
        escapedDept = escapedDept.replace(/\\\(/g, '\\s*\\(\\s*');
        escapedDept = escapedDept.replace(/\\\)/g, '\\s*\\)\\s*');
        
        // Handle slashes with flexible spacing  
        escapedDept = escapedDept.replace(/\\\//g, '\\s*\/\\s*');
        
        // Handle hyphens with flexible spacing
        escapedDept = escapedDept.replace(/\\-/g, '\\s*-\\s*');
        
        // Allow flexible spacing where there are actual spaces
        escapedDept = escapedDept.replace(/\s+/g, '\\s+');
        
        const deptRegex = new RegExp(`(?:^|\\s|;)${escapedDept}(?=\\s|;|,|$)`, 'gi');
        let match;
        const currentDeptRegex = new RegExp(deptRegex.source, 'gi'); // New instance for .exec

        while ((match = currentDeptRegex.exec(remainingAfterDepartmentExtraction)) !== null) {
            tempExtractedDepartments.add(kd); // Add the canonical name
            // Remove the matched department from `remainingAfterDepartmentExtraction`
            remainingAfterDepartmentExtraction = remainingAfterDepartmentExtraction.substring(0, match.index) + remainingAfterDepartmentExtraction.substring(match.index + match[0].length);
            remainingAfterDepartmentExtraction = remainingAfterDepartmentExtraction.replace(/\s+/g, ' ').trim();
            currentDeptRegex.lastIndex = 0; // Reset lastIndex because string was modified
        }
    }
    data.department = [...tempExtractedDepartments].join('; ').replace(/;+/g, ';').replace(/;\s*$/, '').trim();


    // The inventors should be the raw inventors content, plus anything left over from departmentsRawCandidate
    // that wasn't recognized as a department. This handles cases where department extraction fails,
    // or extraneous text exists in that zone.
    let finalInventors = [];
    let initialInventorParts = inventorsRaw.split(/;\s*|,\s*and\s*|\s+and\s+/);
    for (let part of initialInventorParts) {
        part = part.trim();
        if (part && part !== '(ITDO)' && part !== 'ITDO') { // Explicitly filter out '(ITDO)' and 'ITDO'
            finalInventors.push(part);
        }
    }

    // Add any remaining text from the department candidate area to inventors if it's not a department.
    // This is a last resort to avoid data loss, but ideally, this should be empty if all departments are caught.
    if (remainingAfterDepartmentExtraction.length > 0) {
        let remainingParts = remainingAfterDepartmentExtraction.split(/;\s*|,\s*and\s*|\s+and\s+/);
        for (let part of remainingParts) {
            part = part.trim();
            if (part && !extractedDepartments.has(part) && part !== '(ITDO)' && part !== 'ITDO') { // Don't re-add extracted departments or ITDO variants
                finalInventors.push(part);
            }
        }
    }

    // --- FAIL-SAFE for '(ITDO)' / 'ITDO' ---
    // This runs LAST to catch it if it somehow slipped through all other department detection
    // and was about to be misclassified as an inventor.
    let itdoFailSafeIndex = -1;
    let itdoFoundString = ''; // Store the exact string found ('(ITDO)' or 'ITDO')

    // Prioritize checking for '(ITDO)' first (as requested)
    const itdoWithParensIndex = remainingAfterDepartmentExtraction.indexOf('(ITDO)');
    if (itdoWithParensIndex !== -1) {
        itdoFailSafeIndex = itdoWithParensIndex;
        itdoFoundString = '(ITDO)';
        console.log(`FINAL FAIL-SAFE: Found literal '(ITDO)' in remaining after department extraction.`);
    } else {
        // Fallback to 'ITDO' if '(ITDO)' not found
        const itdoWithoutParensIndex = remainingAfterDepartmentExtraction.indexOf('ITDO');
        if (itdoWithoutParensIndex !== -1) {
            itdoFailSafeIndex = itdoWithoutParensIndex;
            itdoFoundString = 'ITDO';
            console.log(`FINAL FAIL-SAFE: Found literal 'ITDO' (all caps) in remaining after department extraction.`);
        }
    }

    if (itdoFailSafeIndex !== -1) {
        // Calculate the actual start index by backtracking to include leading punctuation/whitespace
        let actualSegmentStartIndex = itdoFailSafeIndex;
        while (actualSegmentStartIndex > 0) {
            const char = remainingAfterDepartmentExtraction[actualSegmentStartIndex - 1];
            if (/\s/.test(char) || char === ';' || char === ':' || char === ',') {
                actualSegmentStartIndex--;
            } else {
                break;
            }
        }

        // Add the canonical form '(ITDO)' if it's not already present
        if (!tempExtractedDepartments.has('(ITDO)')) {
            tempExtractedDepartments.add('(ITDO)');
            console.log(`FINAL FAIL-SAFE: Added canonical '(ITDO)' to departments.`);
        }

        // Remove the entire segment (including leading punctuation/whitespace) that was detected
        remainingAfterDepartmentExtraction = remainingAfterDepartmentExtraction.substring(0, actualSegmentStartIndex) +
            remainingAfterDepartmentExtraction.substring(itdoFailSafeIndex + itdoFoundString.length);
        remainingAfterDepartmentExtraction = remainingAfterDepartmentExtraction.replace(/\s+/g, ' ').trim();
        console.log(`FINAL FAIL-SAFE: Removed detected ITDO segment from remaining.`);

        data.department = [...tempExtractedDepartments].join('; ').replace(/;+/g, ';').replace(/;\s*$/, '').trim();
    }


    data.inventors = [...new Set(finalInventors)].join('; ');
    data.inventors = data.inventors.replace(/([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])/g, '$1$2');


    console.log('Final combined data after all processing:', data);
    return data;
}

// 1. Remove the known header lines from the original text.
const headerPattern = /Official Title Tech Sector Inventor(?:\(s\))? Department Country(?:\s*\/\s*Region)?\s*\n?Google\s+[Pp]atent\s+[Ll]inks?\s*/g; // Global flag added
const cleanText = originalText.replace(headerPattern, '').trim();
console.log('\nText after header removal:', `\n---\n${cleanText}\n---`);

// 2. Split the cleaned text into individual patent entry objects {content, link} using a precise two-pass strategy.
const linkOnlyRegex = /(https:\/\/patents\.google\.\n?com\/patent\/[A-Za-z0-9\._\/]+?\d+[A-Za-z0-9]*(?:\n[A-Za-z0-9\._\/]+?\d+[A-Za-z0-9]*)*(?:B\d*|A\d*|C\d*)?)/g;
const allLinkInfos = [];
let linkMatch;
while ((linkMatch = linkOnlyRegex.exec(cleanText)) !== null) {
    allLinkInfos.push({
        fullMatch: linkMatch[0],
        cleanedLink: linkMatch[0].replace(/\s+/g, '').trim(),
        startIndex: linkMatch.index,
        endIndex: linkMatch.index + linkMatch[0].length
    });
}

const individualPatentEntries = [];
let currentSegmentStart = 0;

for (let i = 0; i < allLinkInfos.length; i++) {
    const currentLinkInfo = allLinkInfos[i];

    // The content for the current patent is from the end of the previous segment
    // up to the start of the current patent's link.
    const content = cleanText.substring(currentSegmentStart, currentLinkInfo.startIndex).trim();

    individualPatentEntries.push({
        content: content,
        link: currentLinkInfo.cleanedLink
    });

    // The start of the next segment is immediately after the current link ends.
    currentSegmentStart = currentLinkInfo.endIndex;
}

// Check if there's any remaining content after the last link (should ideally be empty)
if (currentSegmentStart < cleanText.length) {
    console.warn('Warning: Residual content found after the last patent link. This might indicate an unparsed record or extraneous text.');
    // You might want to log this or handle it based on expected input behavior.
}

console.log('\nIndividual Patent Entries detected (count: %d):', individualPatentEntries.length);
individualPatentEntries.forEach((entry, index) => {
    console.log(`Entry ${index + 1}:`);
    console.log(`  Content:\n---\n${entry.content}\n---`);
    console.log(`  Link: ${entry.link}`);
});


// 3. Process each individual patent entry to extract structured data.
const outputItems = [];
for (const entry of individualPatentEntries) {
    const patentData = parsePatentEntry(entry.content, entry.link);
    if (patentData) { // Only add if parsing was successful
        outputItems.push({ json: patentData });
    }
}

// Return the array of structured items.
console.log('\n--- Final Output Items (count: %d) ---', outputItems.length);
console.log(JSON.stringify(outputItems, null, 2));
return outputItems;
