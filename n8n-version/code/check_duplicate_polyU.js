// This code processes the output from the "n8n Patent Text Parser"
// to consolidate duplicate patent records.
// Duplicates are identified by the 'googlePatentLink' field.
// For duplicate records, the 'countryRegion' fields are merged into a single,
// comma-separated string, ensuring uniqueness of country names.

// Expected input: An array of patent objects, where each object has a 'json' property
// containing fields like 'officialTitle', 'techSector', 'inventors', 'department',
// 'countryRegion', and 'googlePatentLink'.
// Example Input: [{ json: { /* patent data */ } }, { json: { /* another patent data */ } }]

const patentRecords = $input.all().map(item => item.json);
console.log('Input Patent Records:', patentRecords);

const uniquePatentsMap = new Map();

for (const record of patentRecords) {
    const link = record.googlePatentLink;

    if (uniquePatentsMap.has(link)) {
        // Duplicate found: Merge countryRegion
        const existingRecord = uniquePatentsMap.get(link);

        const existingCountries = existingRecord.countryRegion
            .split(',')
            .map(c => c.trim())
            .filter(Boolean); // Filter out empty strings

        const newCountries = record.countryRegion
            .split(',')
            .map(c => c.trim())
            .filter(Boolean); // Filter out empty strings

        // Create a Set to ensure unique countries
        const allCountries = new Set([...existingCountries, ...newCountries]);

        // Sort for consistent output, then join with comma
        existingRecord.countryRegion = Array.from(allCountries).sort().join(', ');

        uniquePatentsMap.set(link, existingRecord); // Update the map
        console.log(`Merged countries for duplicate link: ${link}. New countryRegion: ${existingRecord.countryRegion}`);

    } else {
        // Not a duplicate: Add to map
        uniquePatentsMap.set(link, { ...record }); // Store a copy to avoid modifying original input
        console.log(`Added unique record for link: ${link}`);
    }
}

// Convert the Map values back to an array of objects for output
const outputRecords = Array.from(uniquePatentsMap.values()).map(record => ({ json: record }));

console.log('\n--- Unique and Consolidated Patent Records ---');
console.log(JSON.stringify(outputRecords, null, 2));

return outputRecords;
