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

    // --- Preprocessing: Normalize problematic newline splits (applied to the *current* contentStr) ---
    // This happens here, ensuring fixes are applied to the single patent entry's content.
    let processedContentStr = contentStr;
    processedContentStr = processedContentStr.replace(/Electrical & Manufacturing\/Information and\nCommunications Technology/g, 'Electrical & Manufacturing/Information and Communications Technology');
    processedContentStr = processedContentStr.replace(/LIU, Shun-\nyee Michael/g, 'LIU, Shun-yee Michael');
    processedContentStr = processedContentStr.replace(/TSE, Chi Kong\nMichael/g, 'TSE, Chi Kong Michael');
    processedContentStr = processedContentStr.replace(/HU,\nJunyan/g, 'HU, Junyan');
    processedContentStr = processedContentStr.replace(/WONG, Lai Wa\nHelen/g, 'WONG, Lai Wa Helen');
    processedContentStr = processedContentStr.replace(/CHENG, Norbert C./g, 'CHENG, Norbert C.');
    processedContentStr = processedContentStr.replace(/LAU, Chung Ming;/g, 'LAU, Chung Ming;');
    processedContentStr = processedContentStr.replace(/TSE, Chi Kong\nMichael/g, 'TSE, Chi Kong Michael');
    processedContentStr = processedContentStr.replace(/TONG, Kai-yu Raymond;/g, 'TONG, Kai-yu Raymond;');
    processedContentStr = processedContentStr.replace(/SONG, Rong\n/g, 'SONG, Rong ');
    processedContentStr = processedContentStr.replace(/ZHANG, Dapeng David;/g, 'ZHANG, Dapeng David;');
    processedContentStr = processedContentStr.replace(/LUO, Nan;/g, 'LUO, Nan;');
    processedContentStr = processedContentStr.replace(/LI, Wei;/g, 'LI, Wei;');
    processedContentStr = processedContentStr.replace(/ZHANG, Lei;/g, 'ZHANG, Lei;');
    processedContentStr = processedContentStr.replace(/KANHANGAD, Vivek/g, 'KANHANGAD, Vivek');
    processedContentStr = processedContentStr.replace(/CHENG, Ka Wai Eric;/g, 'CHENG, Ka Wai Eric;');
    processedContentStr = processedContentStr.replace(/XUE, Xiangdang;/g, 'XUE, Xiangdang;');
    processedContentStr = processedContentStr.replace(/NGAI, Wing Kit;/g, 'NGAI, Wing Kit;');
    processedContentStr = processedContentStr.replace(/WA, Honwah;/g, 'WA, Honwah;');
    processedContentStr = processedContentStr.replace(/HO, Sze Kit\nNewmen;/g, 'HO, Sze Kit Newmen;');
    processedContentStr = processedContentStr.replace(/CHAN, Tai Wai David;/g, 'CHAN, Tai Wai David;');
    processedContentStr = processedContentStr.replace(/PANG, Man Kit\nPeter/g, 'PANG, Man Kit Peter');
    processedContentStr = processedContentStr.replace(/LEUNG, Woon Fong\nWallace/g, 'LEUNG, Woon Fong Wallace');
    processedContentStr = processedContentStr.replace(/KIn-\nwing;/g, 'KIn-wing;');
    processedContentStr = processedContentStr.replace(/LAM, Tin-yan;/g, 'LAM, Tin-yan;');
    processedContentStr = processedContentStr.replace(/LI, Yi;/g, 'LI, Yi;');
    processedContentStr = processedContentStr.replace(/LO, Lok-yuen Cherry;/g, 'LO, Lok-yuen Cherry;');
    processedContentStr = processedContentStr.replace(/CHOW, Hoi\nLam Martin;/g, 'CHOW, Hoi Lam Martin;');
    processedContentStr = processedContentStr.replace(/SIU, Kam-wah/g, 'SIU, Kam-wah');
    processedContentStr = processedContentStr.replace(/LI, Jianqing;/g, 'LI, Jianqing;');
    processedContentStr = processedContentStr.replace(/DAOUD, Walid A.;/g, 'DAOUD, Walid A;');
    processedContentStr = processedContentStr.replace(/XIN, Haozhong John;/g, 'XIN, Haozhong John;');
    processedContentStr = processedContentStr.replace(/QI, Kai Hong/g, 'QI, Kai Hong');
    processedContentStr = processedContentStr.replace(/HU, Junyan\nTAO, Xiao-ming; XU, Bingang/g, 'HU, Junyan; TAO, Xiao-ming; XU, Bingang');
    processedContentStr = processedContentStr.replace(/CHENG, Ka Wai Eric; XUE, Xiangdang;\nCHEUNG, Norbert C./g, 'CHENG, Ka Wai Eric; XUE, Xiangdang; CHEUNG, Norbert C.');
    processedContentStr = processedContentStr.replace(/LEUNG, Woon Fong Wallace; KWOK,\nKing Lun Alan; CHAN, Mau Wah Andy;\nSZE, So-Lam/g, 'LEUNG, Woon Fong Wallace; KWOK, King Lun Alan; CHAN, Mau Wah Andy; SZE, So-Lam');
    processedContentStr = processedContentStr.replace(/PANG, Man Kit\nPeter/g, 'PANG, Man Kit Peter');
    processedContentStr = processedContentStr.replace(/LI, Yi; LO, Lok-yuen Cherry; HU, Junyan/g, 'LI, Yi; LO, Lok-yuen Cherry; HU, Junyan');
    processedContentStr = processedContentStr.replace(/LO, Chun Lap Samuel; OR, Siu-wing\nDerek/g, 'LO, Chun Lap Samuel; OR, Siu-wing Derek');
    processedContentStr = processedContentStr.replace(/FONG, Bernard Cheuk Mun; SIU\n, Wan/g, 'FONG, Bernard Cheuk Mun; SIU Wan');
    processedContentStr = processedContentStr.replace(/DAOUD, Walid A.; XIN, Haozhong John;\nQI, Kai Hong/g, 'DAOUD, Walid A.; XIN, Haozhong John; QI, Kai Hong');
    processedContentStr = processedContentStr.replace(/SIU\n, Wan Chi/g, 'SIU, Wan Chi'); // Additional fix from PDF review
    processedContentStr = processedContentStr.replace(/TAM, Hwa-yaw; HO, Siu Lau; LIU, Shun-\nyee Michael/g, 'TAM, Hwa-yaw; HO, Siu Lau; LIU, Shun-yee Michael'); // Fix for record 3
    processedContentStr = processedContentStr.replace(/LAU, Chung Ming; TSE, Chi Kong\nMichael/g, 'LAU, Chung Ming; TSE, Chi Kong Michael'); // Fix for record 4


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
    // Only characters within postTechSectorContent will be marked/used for these fields.
    if (postTechSectorContent) {
        const charUsedPostZone = new Array(postTechSectorContent.length).fill(false); // New charUsed for this zone

        // Helper for this zone
        const markCharsUsedInPostZone = (startIndex, endIndex) => {
            for (let i = startIndex; i < endIndex; i++) {
                if (i >= 0 && i < postTechSectorContent.length) {
                    charUsedPostZone[i] = true;
                }
            }
        };

        let postZoneSegments = [];

        // Add the primary tech sector as a segment in the post-zone to mark its characters
        if (primaryTechSectorMatch) {
            // Start index relative to postTechSectorContent (which begins at primaryTechSectorMatch.index)
            postZoneSegments.push({
                text: primaryTechSectorMatch[0],
                startIndex: 0,
                endIndex: primaryTechSectorMatch[0].length,
                type: 'techSector',
                canonical: data.techSector
            });
        }

        // Identify Departments within postTechSectorContent
        const sortedDepartments = [...knownDepartments].sort((a, b) => b.length - a.length);
        for (const kd of sortedDepartments) {
            const deptRegex = new RegExp(`\\b${kd.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
            let match;
            const currentDeptRegex = new RegExp(deptRegex.source, 'gi');
            while ((match = currentDeptRegex.exec(postTechSectorContent)) !== null) {
                postZoneSegments.push({
                    text: match[0],
                    startIndex: match.index,
                    endIndex: match.index + match[0].length,
                    type: 'department',
                    canonical: kd
                });
            }
        }

        // Identify Inventors within postTechSectorContent - Removed isExcludedWord check
        // English name pattern: more robust for complex names including those with middle initials or multiple parts.
        // It now ensures full capture of "Last, First Middle" or "First Middle Last" and handles hyphens/periods.
        // It's also adjusted to be more robust with spacing and newlines within names.
        const englishNamePattern = /\b(?:[A-Z][a-zA-Z\.'\-]+(?:[\s\n]*[A-Z][a-zA-Z\.'\-]+){0,3}|[A-Z][a-zA-Z\.'\-]+,\s*(?:[A-Z][a-zA-Z\.'\-]+\s*){1,3})\b/g;

        // Chinese name pattern: targets 2-4 Chinese characters, now without consuming trailing delimiters
        const chineseNamePattern = /([\u4e00-\u9fa5]{2,4})/g;


        let inventorMatch;
        // Process English names
        const currentEnglishNamePattern = new RegExp(englishNamePattern.source, 'g');
        while ((inventorMatch = currentEnglishNamePattern.exec(postTechSectorContent)) !== null) {
            const potentialInventor = inventorMatch[0].trim(); // Use full match as per new logic
            // No isExcludedWord(potentialInventor) check as per user's golden rule for post-tech-sector content
            if (potentialInventor.length > 2 &&
                !knownDepartments.some(kd => potentialInventor.includes(kd)) &&
                !knownTechSectors.some(ts => potentialInventor.includes(ts)) &&
                !/^\d+[\s\S]*$/.test(potentialInventor) && // Does not start with numbers
                !/^[A-Z0-9]{2,}\d+$/.test(potentialInventor) && // Not just an ID (e.g., patent numbers)
                potentialInventor.trim() !== '' // Ensure it's not empty after trim
            ) {
                postZoneSegments.push({
                    text: inventorMatch[0], // Mark full matched text
                    startIndex: inventorMatch.index,
                    endIndex: inventorMatch.index + inventorMatch[0].length,
                    type: 'inventor',
                    canonical: potentialInventor
                });
            }
        }

        // Process Chinese names
        const currentChineseNamePattern = new RegExp(chineseNamePattern.source, 'g');
        while ((inventorMatch = currentChineseNamePattern.exec(postTechSectorContent)) !== null) {
            const potentialInventor = inventorMatch[1].trim(); // Use group 1 for actual name
            // No isExcludedWord(potentialInventor) check as per user's golden rule for post-tech-sector content
            if (potentialInventor.length >= 2 && potentialInventor.length <= 4 &&
                !knownDepartments.some(kd => potentialInventor.includes(kd)) &&
                !knownTechSectors.some(ts => potentialInventor.includes(ts)) &&
                potentialInventor.trim() !== '' // Ensure it's not empty after trim
            ) {
                postZoneSegments.push({
                    text: inventorMatch[1], // Text to mark
                    startIndex: inventorMatch.index,
                    endIndex: inventorMatch.index + inventorMatch[1].length, // Length of captured group
                    type: 'inventor',
                    canonical: potentialInventor
                });
            }
        }

        // Identify Countries within postTechSectorContent
        const sortedCountries = [...knownCountries].sort((a, b) => b.length - a.length); // Longest first for greedy matching
        for (const kc of sortedCountries) {
            const countryRegex = new RegExp(`\\b${kc.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
            let match;
            const currentCountryRegex = new RegExp(countryRegex.source, 'gi');
            while ((match = currentCountryRegex.exec(postTechSectorContent)) !== null) {
                postZoneSegments.push({
                    text: match[0],
                    startIndex: match.index,
                    endIndex: match.index + match[0].length,
                    type: 'country',
                    canonical: kc
                });
            }
        }

        console.log('Post-Tech Sector Zone Raw Segments:', postZoneSegments);

        // Sort segments within post-tech sector zone by position and priority
        // Tech Sector (3) > Department (2) > Inventor (1) > Country (0)
        postZoneSegments.sort((a, b) => {
            if (a.startIndex !== b.startIndex) return a.startIndex - b.startIndex;
            const typePriority = { 'techSector': 3, 'department': 2, 'inventor': 1, 'country': 0 };
            return typePriority[b.type] - typePriority[a.type];
        });

        // Process segments in sorted order and mark used characters in post-zone
        const tempInventors = new Set();
        const tempDepartments = new Set();
        let finalCountry = ''; // To hold the single country found

        for (const segment of postZoneSegments) {
            let isOverlappingAlreadyMarked = false;
            for (let i = segment.startIndex; i < segment.endIndex; i++) {
                if (i < charUsedPostZone.length && charUsedPostZone[i]) {
                    isOverlappingAlreadyMarked = true;
                    break;
                }
            }

            if (!isOverlappingAlreadyMarked) {
                markCharsUsedInPostZone(segment.startIndex, segment.endIndex);

                if (segment.type === 'department') {
                    tempDepartments.add(segment.canonical);
                } else if (segment.type === 'inventor') {
                    tempInventors.add(segment.canonical);
                } else if (segment.type === 'country') {
                    // Capture the first country found and stop looking for more
                    if (!finalCountry) {
                        finalCountry = segment.canonical;
                    }
                }
                // techSector is already handled
            } else {
                console.log(`Post-Zone Segment "${segment.text}" (Type: ${segment.type}) at [${segment.startIndex}, ${segment.endIndex}] skipped due to overlap.`);
            }
        }

        // Finalize data fields from temp sets for this zone
        data.inventors = [...tempInventors].join('; ').replace(/;+/g, ';').replace(/;\s*$/, '').trim();
        data.department = [...tempDepartments].join('; ').replace(/;+/g, ';').replace(/;\s*$/, '').trim();
        data.countryRegion = finalCountry; // Assign the extracted country

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
