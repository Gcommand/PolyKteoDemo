// This code processes the output from the "n8n Patent Text Parser"
// to consolidate duplicate patent records.
// Duplicates are identified by the 'googlePatentLink' field.
// For duplicate records, the 'countryRegion' fields are merged into a single,
// comma-separated string, ensuring uniqueness of country names.
// This version also processes and consolidates tech sectors to prepare for
// insertion into a patent_tech_sectors join table.

// Expected input: An array of patent objects, where each object has a 'json' property
// containing fields like 'officialTitle', 'techSector', 'inventors', 'department',
// 'countryRegion', and 'googlePatentLink'.
// Example Input: [{ json: { /* patent data */ } }, { json: { /* another patent data */ } }]

const patentRecords = $input.all().map(item => item.json);
console.log('Input Patent Records:', patentRecords);

// Hardcoded tech sector mapping from your DDL for quick ID lookup
const techSectorNameToIdMap = new Map([
    ["Foodtech", 1],
    ["Biotech", 2],
    ["Pharmaceutical", 3],
    ["Other", 4],
    ["Information and Communications Technology", 5],
    ["Electrical & Manufacturing", 6],
    ["Healthcare", 7],
    ["Construction", 8],
    ["Material Science", 9],
    ["Textile", 10],
    ["Positioning", 11], // Fixed typo from "Positioniing"
    ["Navigation", 12],
    ["Timing", 13],
    ["Textiles", 14],
    ["Green Tech", 15],
    ["Food Tech", 16],
    ["Material Tech", 17],
    ["Manufacturing Tech", 18],
    ["Bio Tech", 19], // Split from "Bio Tech / Pharmaceutical"
    ["Health Tech", 20],
    ["Smart Hardware", 21],
    ["ICT", 22],
    ["Energy Tech", 23],
    ["Fashion & Textile", 24],
    ["Property Tech", 25],
    ["Robotics", 26],
    ["Social", 27], // Split from "Social / Ed Tech"
    ["Ed Tech", 28], // Split from "Social / Ed Tech"
    ["FinTech", 29],
    ["Precision Manufacturing Techniques", 30]
]);

/**
 * Helper function to parse a tech sector string (e.g., "Healthcare/Textile")
 * into an array of unique names and their corresponding IDs.
 * @param {string} techSectorString - The combined tech sector string from a patent record.
 * @returns {object} An object containing 'ids' (array of unique tech sector IDs) and 'names' (string of unique sorted tech sector names).
 */
function getTechSectorData(techSectorString) {
    const names = techSectorString.split('/').map(s => s.trim()).filter(Boolean);
    const ids = new Set();
    const uniqueNames = new Set();

    for (const name of names) {
        if (techSectorNameToIdMap.has(name)) {
            ids.add(techSectorNameToIdMap.get(name));
            uniqueNames.add(name);
        }
    }
    return {
        ids: Array.from(ids).sort((a, b) => a - b), // Sort IDs numerically
        // Rejoin with '/' to maintain consistency with the original format
        // or use ', ' if comma-separated is preferred for consolidated output.
        // For consistency in the consolidated record's 'techSector' field, let's keep '/'
        // and sort names alphabetically.
        names: Array.from(uniqueNames).sort().join('/')
    };
}

const uniquePatentsMap = new Map();

for (const record of patentRecords) {
    const link = record.googlePatentLink;

    // Process current record's tech sectors
    const currentTechSectorData = getTechSectorData(record.techSector);

    if (uniquePatentsMap.has(link)) {
        // Duplicate found: Merge countryRegion AND techSector(s)
        const existingRecord = uniquePatentsMap.get(link);

        // Merge countries
        const existingCountries = existingRecord.countryRegion
            .split(',')
            .map(c => c.trim())
            .filter(Boolean);
        const newCountries = record.countryRegion
            .split(',')
            .map(c => c.trim())
            .filter(Boolean);
        const allCountries = new Set([...existingCountries, ...newCountries]);
        existingRecord.countryRegion = Array.from(allCountries).sort().join(', ');

        // Merge tech sectors (names and IDs)
        const existingTechSectorNames = existingRecord.techSector
            .split('/') // Assuming original tech_sector comes as "Name1/Name2"
            .map(s => s.trim())
            .filter(Boolean);
        const allTechSectorNames = new Set([...existingTechSectorNames, ...currentTechSectorData.names.split('/')]); // Add names from current record
        existingRecord.techSector = Array.from(allTechSectorNames).sort().join('/'); // Update techSector string in the record

        const existingTechSectorIds = existingRecord.techSectorIds || []; // Handle initial case where it might not exist
        const allTechSectorIds = new Set([...existingTechSectorIds, ...currentTechSectorData.ids]);
        existingRecord.techSectorIds = Array.from(allTechSectorIds).sort((a, b) => a - b); // Update techSectorIds array

        uniquePatentsMap.set(link, existingRecord);
        console.log(`Merged duplicate link: ${link}. New countryRegion: ${existingRecord.countryRegion}, New techSector: ${existingRecord.techSector}, New techSectorIds: ${existingRecord.techSectorIds}`);

    } else {
        // Not a duplicate: Add to map with initial techSectorIds
        uniquePatentsMap.set(link, {
            ...record,
            techSector: currentTechSectorData.names, // Ensure techSector is consistent (sorted, / separated)
            techSectorIds: currentTechSectorData.ids // Add the new techSectorIds array
        });
        console.log(`Added unique record for link: ${link} with techSectorIds: ${currentTechSectorData.ids}`);
    }
}

// Convert the Map values back to an array of objects for output
const outputRecords = Array.from(uniquePatentsMap.values()).map(record => ({ json: record }));

console.log('\n--- Unique and Consolidated Patent Records ---');
console.log(JSON.stringify(outputRecords, null, 2));

return outputRecords;
