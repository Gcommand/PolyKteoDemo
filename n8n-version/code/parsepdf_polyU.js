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
    'Singapore', 'Nepal', 'South Korea / Republic of Korea', 'Mexico'
];

const knownDepartments = [
    'FENG/BME', 'ASO/IC', 'FAST/ITC', 'FENG/EE', 'FENG/ISE', 'FENG/EIE',
    'FHSS/HTI', 'FHSS/SO', 'FENG/COMP', 'FAST/AP', 'RIIPT/RIIPT',
    'FENG/ME', 'FAST/ABCT', 'FCE/CEE', 'FCE/BSE', 'FCE/LSGI', 'SD/SD',
    'FB/MM', 'LGT/LGT', 'FHSS/RS', 'FHSS/SN', 'PDO/PDO', 'DP/DP', 'OR/OR',
    '(ITDO)',
    'FENG/AAE', 'FCE/BRE', 'FB/LMS', 'FAST/AMA'
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
    'Foodtech/Biotech/Pharmaceutical/Textile'
];

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
 */
function parseRemainingContentLineByLine(contentStr) {
    console.log('\n--- Starting parseRemainingContentLineByLine ---');
    console.log('Content String for remaining parsing:', `\n---\n${contentStr}\n---`);

    let data = {
        officialTitle: '',
        techSector: '',
        inventors: '',
        department: '',
        countryRegion: ''
    };

    // --- Preprocessing: Aggressive newline and whitespace normalization ---
    let processedContentStr = contentStr;
    // Replace known multi-line phrases first (ensure order of replacement for overlaps)
    processedContentStr = processedContentStr.replace(/Electrical & Manufacturing\/Information and\nCommunications Technology/g, 'Electrical & Manufacturing/Information and Communications Technology');
    processedContentStr = processedContentStr.replace(/Construction\/Positioning\/Navigation\/Timing/g, 'Construction/Positioning/Navigation/Timing');
    processedContentStr = processedContentStr.replace(/Foodtech\/Biotech\/Pharmaceutical\/Textile/g, 'Foodtech/Biotech/Pharmaceutical/Textile');

    // Replace newlines followed by capitalized letters or Chinese chars with a space, to preserve names/words
    processedContentStr = processedContentStr.replace(/([a-zA-Z\.'\-,])\s*\n([A-Z\u4e00-\u9fa5])/g, '$1 $2');
    // Replace newlines between Chinese characters with no space
    processedContentStr = processedContentStr.replace(/([\u4e00-\u9fa5])\s*\n\s*([\u4e00-\u9fa5])/g, '$1$2');
    // Replace any remaining newlines with a single space
    processedContentStr = processedContentStr.replace(/\n/g, ' ');
    // Consolidate multiple spaces
    processedContentStr = processedContentStr.replace(/\s+/g, ' ');
    processedContentStr = processedContentStr.trim();

    console.log('Content String after aggressive preprocessing:', `\n---\n${processedContentStr}\n---`);

    let bestTechSectorMatch = null;
    let potentialTechSectorMatches = [];

    // --- Generate comprehensive list of all possible tech sector matches (sorted longest first) ---
    const allPossibleTechSectorMatches = new Set();
    for (const ts of knownTechSectors) {
        allPossibleTechSectorMatches.add(ts);
        if (ts.includes('/')) {
            ts.split('/').forEach(part => allPossibleTechSectorMatches.add(part.trim()));
        }
    }
    const sortedAllPossibleTechSectors = Array.from(allPossibleTechSectorMatches).sort((a, b) => b.length - a.length);

    // --- Collect ALL potential tech sector matches with their start and end indices ---
    for (const tsCandidate of sortedAllPossibleTechSectors) {
        const lowerProcessedContent = processedContentStr.toLowerCase();
        const lowerTsCandidate = tsCandidate.toLowerCase();
        let currentMatchIndex = -1;
        let lastSearchIndex = 0;

        while ((currentMatchIndex = lowerProcessedContent.indexOf(lowerTsCandidate, lastSearchIndex)) !== -1) {
            // Refined end boundary check for tech sector: allow it to be followed by space, semicolon, or start of known department/country/inventor pattern
            const charAfter = processedContentStr[currentMatchIndex + tsCandidate.length];
            const isEndBoundaryLax = (currentMatchIndex + tsCandidate.length === processedContentStr.length) ||
                                     /\s/.test(charAfter) || // Followed by whitespace
                                     charAfter === ';' || // Followed by semicolon
                                     // Check if followed by known department or country pattern (start of next field)
                                     knownDepartments.some(kd => processedContentStr.substring(currentMatchIndex + tsCandidate.length).trim().startsWith(kd)) ||
                                     knownCountries.some(kc => processedContentStr.substring(currentMatchIndex + tsCandidate.length).trim().startsWith(kc));

            const isCharBeforeWord = (currentMatchIndex > 0) && /\w/.test(processedContentStr[currentMatchIndex - 1]);
            const isStartBoundary = (currentMatchIndex === 0) || !isCharBeforeWord;

            if (isStartBoundary && isEndBoundaryLax) {
                potentialTechSectorMatches.push({
                    ts: tsCandidate,
                    index: currentMatchIndex,
                    length: tsCandidate.length
                });
            }
            lastSearchIndex = currentMatchIndex + tsCandidate.length;
        }
    }

    // --- Select the best tech sector match ---
    // Criteria: Prioritize longest match, then earliest index.
    if (potentialTechSectorMatches.length > 0) {
        bestTechSectorMatch = potentialTechSectorMatches.reduce((best, current) => {
            if (!best) return current;
            // Prioritize by length (longer is better)
            if (current.length > best.length) return current;
            if (current.length < best.length) return best;
            // If lengths are equal, prioritize by earliest index
            if (current.index < best.index) return current;
            return best;
        }, null);
    }

    let preTechSectorContent = '';
    let postTechSectorContent = '';

    if (bestTechSectorMatch) {
        // The title is everything before the best tech sector match
        preTechSectorContent = processedContentStr.substring(0, bestTechSectorMatch.index).trim();
        // Post tech sector content is everything after the best tech sector match
        postTechSectorContent = processedContentStr.substring(bestTechSectorMatch.index + bestTechSectorMatch.length).trim();
        data.techSector = bestTechSectorMatch.ts; // Assign the actual tech sector found

        console.log(`Optimal Partition:`);
        console.log(`  Official Title: "${preTechSectorContent}"`);
        console.log(`  Tech Sector: "${data.techSector}"`);
        console.log(`  Post-Tech Sector Content: "${postTechSectorContent}"`);
    } else {
        // Fallback: If no tech sector could be identified at all, assume whole string is title
        preTechSectorContent = processedContentStr;
        console.warn('No known Tech Sector found. Treating entire content as officialTitle.');
    }

    data.officialTitle = preTechSectorContent.replace(/[\s;]+/g, ' ').replace(/\s+/g, ' ').trim();
    data.officialTitle = data.officialTitle.replace(/([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])/g, '$1$2');


    // --- Extract Department(s) and Country from Post-Tech Sector Content ---
    let remainingContent = postTechSectorContent;
    let extractedDepartments = new Set();
    let extractedCountry = '';

    // Step 1: Try to extract country first (often at the very end of the structured part)
    const sortedCountriesByLengthRev = [...knownCountries].sort((a,b) => b.length - a.length);
    for (const kc of sortedCountriesByLengthRev) {
        const countryRegex = new RegExp(`\\b${kc.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b$`, 'i');
        const match = remainingContent.match(countryRegex);
        if (match) {
            extractedCountry = kc;
            remainingContent = remainingContent.substring(0, match.index).trim();
            console.log(`Found country "${extractedCountry}", remainingContent after country: "${remainingContent}"`);
            break;
        }
    }
    data.countryRegion = extractedCountry;

    // Step 2: Extract Departments from the now remaining content (after tech sector, before potential country)
    const sortedDepartmentsByLength = [...knownDepartments].sort((a, b) => b.length - a.length);
    let tempRemainingForInventors = remainingContent; // Make a copy to extract departments without affecting inventor area

    for (const kd of sortedDepartmentsByLength) {
        const escapedKd = kd.replace(/[\-\[\]\{\}\(\)\*\+\?\.\\\^\$\|\`]/g, "\\$&");
        const deptRegex = new RegExp(`\\b${escapedKd}\\b`, 'gi');
        let match;
        const currentDeptRegex = new RegExp(deptRegex.source, 'gi');

        while ((match = currentDeptRegex.exec(tempRemainingForInventors)) !== null) {
            extractedDepartments.add(kd);
            tempRemainingForInventors = tempRemainingForInventors.substring(0, match.index) + tempRemainingForInventors.substring(match.index + match[0].length);
            tempRemainingForInventors = tempRemainingForInventors.replace(/\s+/g, ' ').trim();
            currentDeptRegex.lastIndex = 0;
        }
    }
    data.department = [...extractedDepartments].join('; ').replace(/;+/g, ';').replace(/;\s*$/, '').trim();

    // Step 3: What's left in `tempRemainingForInventors` is assumed to be the inventors (golden rule)
    let inventorsRaw = tempRemainingForInventors;
    if (inventorsRaw) {
        let tempInventors = [];
        let primaryParts = inventorsRaw.split(/;\s*|,\s*and\s*|\s+and\s+/);
        for (let part of primaryParts) {
            part = part.trim();
            if (part) {
                tempInventors.push(part);
            }
        }
        data.inventors = [...new Set(tempInventors)].join('; ');
        data.inventors = data.inventors.replace(/([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])/g, '$1$2');
    }

    console.log('Final combined data after all processing:', data);
    return data;
}

// 1. Remove the known header lines from the original text.
const headerPattern = /Official Title Tech Sector Inventor Department Country \/ Region\s*\nGoogle Patent Link\s*/g;
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

    const content = cleanText.substring(currentSegmentStart, currentLinkInfo.startIndex).trim();

    individualPatentEntries.push({
        content: content,
        link: currentLinkInfo.cleanedLink
    });

    currentSegmentStart = currentLinkInfo.endIndex;
}

if (currentSegmentStart < cleanText.length) {
    console.warn('Warning: Residual content found after the last patent link. This might indicate an unparsed record or extraneous text.');
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
    if (patentData) {
        outputItems.push({ json: patentData });
    }
}

console.log('\n--- Final Output Items (count: %d) ---', outputItems.length);
console.log(JSON.stringify(outputItems, null, 2));
return outputItems;
