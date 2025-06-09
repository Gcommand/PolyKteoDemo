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
    'Singapore', 'Nepal'
];

const knownDepartments = [
    'FENG/BME', 'ASO/IC', 'FAST/ITC', 'FENG/EE', 'FENG/ISE', 'FENG/EIE',
    'FHSS/HTI', 'FENG', 'ASO', 'FAST', 'FHSS', 'IC', 'ITC', 'BME', 'EE',
    'EIE', 'ISE', 'HTI', 'FHSS/SO', 'FENG/COMP', 'FAST/AP', 'RIIPT/RIIPT',
    'FENG/ME', 'FAST/ABCT', 'FCE/CEE', 'FCE/BSE', 'FCE/LSGI', 'SD/SD',
    'FB/MM', 'LGT/LGT', 'FHSS/RS', 'FHSS/SN', 'PDO/PDO', 'DP/DP', 'OR/OR'
];

const knownTechSectors = [
    'Healthcare/Textile',
    'Textile',
    'Electrical & Manufacturing',
    'Information and Communications Technology',
    'Material Science',
    'Foodtech/Biotech/Pharmaceutical',
    'Construction',
    'Positioning/Navigation/Timing',
    'Other',
    // Added the combined tech sector phrase as identified in the issue
    'Electrical & Manufacturing/Information and Communications Technology',
    'Healthcare' // Added 'Healthcare' as a standalone tech sector
];

// The excludeWordsSet and isExcludedWord function are no longer needed
// because the parsing logic now strictly adheres to the input's positional
// guarantee that only relevant fields appear after the tech sector.


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

    // All parsing of title, tech sector, inventors, departments, and country
    // will now happen inside parseRemainingContentLineByLine.
    // This ensures strict adherence to the "after tech sector" rule for content.
    const parsedData = parseRemainingContentLineByLine(contentPart);
    Object.assign(patent, parsedData); // Merge the parsed fields into the patent object

    console.log('Final Parsed Patent Data for this entry:', patent);
    return patent;
}

/**
 * Parses the remaining content (after link and country extraction) for Title, Tech Sector, Inventors, and Department.
 * This version strictly adheres to the sequential order: Title -> Tech Sector -> Inventors/Departments/Country.
 * It ensures all content is accounted for and placed correctly using a character-by-character marking system.
 *
 * @param {string} contentStr The string containing the title, tech sector, inventors, department, and country information.
 * @returns {object} An object with officialTitle, techSector, inventors, department, and countryRegion properties.
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

    // --- Preprocessing: Normalize problematic newline splits and consolidate whitespace ---
    // This happens here, ensuring fixes are applied to the single patent entry's content.
    let processedContentStr = contentStr;
    processedContentStr = processedContentStr.replace(/Electrical & Manufacturing\/Information and\nCommunications Technology/g, 'Electrical & Manufacturing/Information and Communications Technology');

    // General replacement of newlines in names and general text
    // Replace newline that is preceded by a non-whitespace character and followed by a capitalized letter or a character that looks like a name part
    processedContentStr = processedContentStr.replace(/([a-zA-Z\.'\-,\/])\s*\n([A-Z\u4e00-\u9fa5])/g, '$1 $2');
    processedContentStr = processedContentStr.replace(/([a-zA-Z])\n([a-zA-Z])/g, '$1 $2'); // Catches simple word splits
    processedContentStr = processedContentStr.replace(/\s+/g, ' '); // Consolidate multiple spaces
    processedContentStr = processedContentStr.trim();


    console.log('Content String after preprocessing (newlines for known phrases):', `\n---\n${processedContentStr}\n---`);

    let primaryTechSectorMatch = null;
    let techSectorStartIndex = -1;
    let techSectorEndIndex = -1;

    // --- 1. Identify Primary Tech Sector from the entire processed string (HIGHEST PRIORITY) ---
    // This will determine the hard boundary for splitting the content.
    const sortedTechSectors = [...knownTechSectors].sort((a, b) => b.length - a.length); // Longest first for greedy matching
    for (const ts of sortedTechSectors) {
        // Use a word boundary (\b) for the start and a negative lookahead (?!\\w) for the end.
        // This allows matching "Healthcare" even if it's immediately followed by a space and a name.
        const tsRegex = new RegExp(`\\b${ts.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?!\\w)`, 'gi'); // Using (?!\\w) again for robustness
        let match;
        const currentTsRegex = new RegExp(tsRegex.source, 'gi'); // New instance for .exec
        while ((match = currentTsRegex.exec(processedContentStr)) !== null) {
            // We want the *first* one encountered as the primary divider, globally.
            // If multiple of the same length, earlier occurrence wins.
            if (!primaryTechSectorMatch || match.index < primaryTechSectorMatch.index) {
                primaryTechSectorMatch = match;
                data.techSector = ts; // Assign to final data.techSector
                techSectorStartIndex = match.index;
                techSectorEndIndex = match.index + match[0].length;
            }
        }
    }

    let preTechSectorContent = '';
    let postTechSectorContent = '';

    if (primaryTechSectorMatch) {
        preTechSectorContent = processedContentStr.substring(0, techSectorStartIndex).trim();
        postTechSectorContent = processedContentStr.substring(techSectorStartIndex).trim();
        console.log(`Hard Partitioned:`);
        console.log(`  Pre-Tech Sector Content (for title): "${preTechSectorContent}"`);
        console.log(`  Post-Tech Sector Content (for other fields): "${postTechSectorContent}"`);
    } else {
        // If no tech sector is found, the entire content becomes the "pre" part (title),
        // and "post" part is empty. Other fields will remain empty unless found in title.
        // This is a fallback to ensure no data loss, but indicates a parsing issue.
        preTechSectorContent = processedContentStr;
        console.warn('No known Tech Sector found. Treating entire content as pre-tech sector (title).');
    }

    // --- Assign Official Title from Pre-Tech Sector Content ---
    data.officialTitle = preTechSectorContent.replace(/[\s;]+/g, ' ').replace(/\s+/g, ' ').trim();


    // --- Now, Process Post-Tech Sector Content for Departments, Inventors, and Country ---
    // Strict sequential parsing based on the golden rule
    if (postTechSectorContent) {
        let contentAfterTechSector = postTechSectorContent;
        // Remove the tech sector itself from the front of this content
        if (primaryTechSectorMatch) {
            contentAfterTechSector = contentAfterTechSector.substring(primaryTechSectorMatch[0].length).trim();
        }

        let firstDeptStart = Infinity;
        let firstCountryStart = Infinity;

        // Find the earliest department
        for (const kd of knownDepartments) {
            const match = contentAfterTechSector.match(new RegExp(`\\b${kd.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i'));
            if (match && match.index < firstDeptStart) {
                firstDeptStart = match.index;
            }
        }

        // Find the earliest country
        for (const kc of knownCountries) {
            const match = contentAfterTechSector.match(new RegExp(`\\b${kc.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i'));
            if (match && match.index < firstCountryStart) {
                firstCountryStart = match.index;
            }
        }

        const inventorsEndIndex = Math.min(firstDeptStart, firstCountryStart, contentAfterTechSector.length);

        let inventorsRaw = contentAfterTechSector.substring(0, inventorsEndIndex).trim();
        let remainingContentAfterInventors = contentAfterTechSector.substring(inventorsEndIndex).trim();

        // Process inventorsRaw: simply split by common list separators
        if (inventorsRaw) {
            // Split by semicolons, then further split by commas or "and" if they are used as separators within a name string
            let tempInventors = [];
            let primaryParts = inventorsRaw.split(/;\s*/);
            for (let part of primaryParts) {
                // Split sub-parts by commas or " and "
                let subParts = part.split(/,\s*|\s+and\s+/);
                tempInventors.push(...subParts.map(s => s.trim()).filter(Boolean));
            }
            data.inventors = [...new Set(tempInventors)].join('; '); // Remove duplicates and join
        }

        // Process remainingContentAfterInventors for departments and country
        let currentContentForDeptCountry = remainingContentAfterInventors;
        let tempDepartments = new Set();
        let finalCountry = '';

        // Extract departments from the remaining content
        for (const kd of knownDepartments) {
            const deptRegex = new RegExp(`\\b${kd.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
            let match;
            const currentDeptRegex = new RegExp(deptRegex.source, 'gi');
            while ((match = currentDeptRegex.exec(currentContentForDeptCountry)) !== null) {
                tempDepartments.add(kd);
                // Remove the found department to avoid re-matching and clean string for country
                currentContentForDeptCountry = currentContentForDeptCountry.replace(match[0], '').trim();
                // Consolidate any new multiple spaces after removal
                currentContentForDeptCountry = currentContentForDeptCountry.replace(/\s+/g, ' ').trim();
            }
        }
        data.department = [...tempDepartments].join('; ').replace(/;+/g, ';').replace(/;\s*$/, '').trim();

        // Extract country from the now further reduced content
        for (const kc of knownCountries) {
            const countryRegex = new RegExp(`\\b${kc.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
            if (countryRegex.test(currentContentForDeptCountry)) {
                finalCountry = kc;
                break; // Assuming only one country
            }
        }
        data.countryRegion = finalCountry;

    } // End if (postTechSectorContent) block

    console.log('Final combined data after all processing:', data);
    return data;
}

// 1. Remove the known header lines from the original text.
const headerPattern = /Official Title Tech Sector Inventor Department Country \/ Region\s*\nGoogle Patent Link\s*/g; // Global flag added
const cleanText = originalText.replace(headerPattern, '').trim();
console.log('\nText after header removal:', `\n---\n${cleanText}\n---`);

// 2. Split the cleaned text into individual patent entry objects {content, link} using a precise regex.
// This regex captures the content (group 1) and the full multi-line link (group 2).
// It now ensures the link ID is consumed greedily, and the lookahead is stricter for the next title's start.
const entryPattern = /([\s\S]*?)(https:\/\/patents\.google\.\n?com\/patent\/[A-Za-z0-9\._\/]+?\d+[A-Za-z0-9]*(?:\n[A-Za-z0-9\._\/]+?\d+[A-Za-z0-9]*)*(?:B\d*|A\d*|C\d*)?)(?=\n*(?:[A-Z\u4e00-\u9fa5][a-zA-Z\s]*|[A-Z\u4e00-\u9fa5]|https:\/\/patents\.google\.)|$)/gs;
// Regex breakdown:
// ([\s\S]*?)        : Group 1, non-greedy match for any characters (the patent's content).
// (                : Start Group 2 (the entire Google Patent Link).
//   https:\/\/patents\.google\. : Literal match for the domain start.
//   \n?com\/patent\/ : Optional newline before "com/patent/", then literal match.
//   [A-Za-z0-9\._\/]+? : Non-greedy match for patent ID characters (alphanumeric, dot, underscore, slash), allowing internal newlines.
//   \d+[A-Za-z0-9]* : MUST contain at least one digit and end with alphanumeric (key for ID termination).
//   (?:\n[A-Za-z0-9\._\/]+?\d+[A-Za-z0-9]*)* : Optional repeating segments of the ID on newlines, must follow the digit-ending pattern.
//   (?:B\d*|A\d*|C\d*)?: Optional suffixes like "B2", "A1", "C9".
// )                : End Group 2.
// (?=              : Positive Lookahead (ensures the following pattern exists but doesn't consume it).
//   \n* : Optional multiple newlines before the next pattern.
//   (?:            : Non-capturing group for the next pattern options.
//     [A-Z\u4e00-\u9fa5][a-zA-Z\s]* : An uppercase English letter or Chinese character followed by letters/spaces (strong hint of a title).
//     | [A-Z\u4e00-\u9fa5] : OR just an uppercase English letter or Chinese character (simpler title start).
//     | https:\/\/patents\.google\. : OR the literal start of another patent link (very strong delimiter).
//   )
//   | \s*$         : OR optional whitespace then end of string (for the very last entry).
// )
// /gs              : Global and Dotall flags.

const individualPatentEntries = [];
let match;
while ((match = entryPattern.exec(cleanText)) !== null) {
    const content = match[1].trim();
    const link = match[2].replace(/\s+/g, '').trim(); // Clean link immediately after extraction
    individualPatentEntries.push({ content, link });
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
