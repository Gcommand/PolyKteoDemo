const outputItems = [];

for (const item of $input.all()) {
  const linkedProjectTitles = item.json.linkedProjectTitles || [];
  const linkedProjectHrefs = item.json.linkedProjectHrefs || [];
  const projectMainDivs = item.json.projectMainDivs || [];
  const projectId = item.json.projectId || [];
  const richTextHtmls = item.json.richTextHtmls || [];

  // Get original event context from previous nodes
  const originalEventUrl = $('Cache Tech Event').item.json.eventPageUrl;
  const originalEventTitle = $('Cache Tech Event').item.json.eventTitle;
  const originalEventDateText = $('Cache Tech Event').item.json.eventDateText;

  // DEBUG: Log array lengths to identify mismatches
  console.log('=== ARRAY LENGTH DEBUGGING ===');
  console.log(`linkedProjectTitles.length: ${linkedProjectTitles.length}`);
  console.log(`linkedProjectHrefs.length: ${linkedProjectHrefs.length}`);
  console.log(`projectMainDivs.length: ${projectMainDivs.length}`);
  console.log(`projectId.length: ${projectId.length}`);
  console.log(`richTextHtmls.length: ${richTextHtmls.length}`);
  console.log('=== END ARRAY LENGTH DEBUG ===');

  // Use the maximum length to ensure we don't miss any projects
  const maxLength = Math.max(
    projectMainDivs.length,
    projectId.length,
    richTextHtmls.length
  );
  
  console.log(`Processing ${maxLength} projects (using max array length)`);

  // Process each project
  for (let i = 0; i < maxLength; i++) {
    console.log(`\n=== PROCESSING PROJECT ${i + 1}/${maxLength} ===`);
    
    // Safely get array elements with detailed logging
    const projectMainDivHtml = projectMainDivs[i] || '';
    const currentRichTextHtml = richTextHtmls[i] || '';
    const currentProjectId = projectId[i] || null;

    // Log what we have for this project
    console.log(`Project ${i + 1} data availability:`);
    console.log(`- projectMainDivHtml: ${projectMainDivHtml ? projectMainDivHtml.length + ' chars' : 'MISSING'}`);
    console.log(`- richTextHtml: ${currentRichTextHtml ? currentRichTextHtml.length + ' chars' : 'MISSING'}`);
    console.log(`- projectId: ${currentProjectId || 'MISSING'}`);

    // Skip if we don't have essential data
    if (!projectMainDivHtml && !currentRichTextHtml) {
      console.log(`⚠️ SKIPPING Project ${i + 1}: No main content available`);
      continue;
    }

    let projectData = {
        parentEventTitle: originalEventTitle,
        parentEventDateText: originalEventDateText,
        parentEventUrl: originalEventUrl,
        projectId: currentProjectId,
        combinedProjectHtml: `
          ${projectMainDivHtml}
          ${currentRichTextHtml}
        `.trim()
    };

    // Link handling
    if (projectData.projectId) {
      const correspondingLinkIndex = linkedProjectHrefs.findIndex(href => href.endsWith('#'+projectData.projectId));
      if (correspondingLinkIndex !== -1) {
          projectData.linkedFromTopTitle = linkedProjectTitles[correspondingLinkIndex];
          projectData.linkedFromTopUrl = 'https://www.polyu.edu.hk' + linkedProjectHrefs[correspondingLinkIndex];
          console.log(`✅ Found link for Project ${i + 1}: ${projectData.linkedFromTopTitle}`);
      } else {
          projectData.linkedFromTopTitle = null;
          projectData.linkedFromTopUrl = null;
          console.log(`❌ No link found for Project ${i + 1} with ID: ${projectData.projectId}`);
      }
    } else {
      projectData.linkedFromTopTitle = null;
      projectData.linkedFromTopUrl = null;
      console.log(`❌ No project ID for Project ${i + 1}, skipping link lookup`);
    }

    // --- IMPROVED EXTRACTION FUNCTIONS ---

    function logDebug(message) {
        console.log(`DEBUG: ${message}`);
    }

    // --- MALFORMED URL HANDLER ---
    function handleMalformedUrl(url, extractionType) {
        logDebug(`Handling malformed URL for ${extractionType}: "${url}"`);
        
        // Extract anchor/fragment identifier which often contains project info
        const anchorMatch = url.match(/#([^?]+)/);
        if (anchorMatch && anchorMatch[1]) {
            const anchor = anchorMatch[1];
            logDebug(`Found anchor: "${anchor}"`);
            
            if (extractionType === 'title') {
                // Convert anchor to readable project title
                const titleFromAnchor = convertAnchorToTitle(anchor);
                if (titleFromAnchor) {
                    logDebug(`SUCCESS (URL Anchor): Converted "${anchor}" to title: "${titleFromAnchor}"`);
                    return titleFromAnchor;
                }
            } else if (extractionType === 'pi') {
                // For PI extraction, we can't reliably get PI info from URL
                logDebug(`Cannot extract PI from URL anchor: "${anchor}"`);
                return null;
            }
        }
        
        // Try to extract page context from URL path
        const pathMatch = url.match(/\/([^\/]+)(?:#|$)/);
        if (pathMatch && pathMatch[1] && extractionType === 'title') {
            const pageContext = pathMatch[1];
            logDebug(`Found page context: "${pageContext}"`);
            
            // Convert common page contexts to meaningful titles
            const contextTitles = {
                'geneva2023': 'Geneva International Exhibition of Inventions 2023',
                'geneva2024': 'Geneva International Exhibition of Inventions 2024', 
                'aeii-2024': 'Asia Exhibition of Innovations and Inventions 2024',
                'aeii-2023': 'Asia Exhibition of Innovations and Inventions 2023'
            };
            
            if (contextTitles[pageContext.toLowerCase()]) {
                const contextTitle = contextTitles[pageContext.toLowerCase()];
                logDebug(`SUCCESS (URL Context): Using context title: "${contextTitle}"`);
                return contextTitle;
            }
        }
        
        // Extract any recognizable project identifier from the URL for logging
        const projectIdMatch = url.match(/#([a-zA-Z0-9_-]+)/);
        if (projectIdMatch) {
            logDebug(`Project identifier found in URL: "${projectIdMatch[1]}"`);
            // Store this for potential future use or debugging
            if (extractionType === 'title') {
                logDebug(`PARTIAL SUCCESS: At least identified project: "${projectIdMatch[1]}"`);
            }
        }
        
        logDebug(`FALLBACK: No useful ${extractionType} info extracted from malformed URL`);
        return null;
    }
    
    function convertAnchorToTitle(anchor) {
        // Common anchor to title conversions
        const anchorTitleMap = {
            'PolyPi': 'PolyPi: Edge-AI Empowered Robot for Autonomous In-pipe Inspection',
            'goodvision': 'Good Vision Technology Project',
            'smartmanufacturing': 'Smart Manufacturing System',
            'dronedelivery': 'Last-Centimeter Drone Delivery System',
            'prosthetichand': 'ProRuka Novel Prosthetic Hand',
            'solarcooling': 'Synergistic Integration of Terrestrial Radiative Cooling and Bifacial Solar Photovoltaics'
        };
        
        // Direct mapping
        if (anchorTitleMap[anchor]) {
            return anchorTitleMap[anchor];
        }
        
        // Convert camelCase or hyphenated anchors to readable titles
        let title = anchor
            .replace(/([a-z])([A-Z])/g, '$1 $2')  // camelCase to spaces
            .replace(/[-_]/g, ' ')                // hyphens/underscores to spaces
            .replace(/\b\w/g, l => l.toUpperCase()) // capitalize words
            .trim();
        
        // Add context if title seems too short or generic
        if (title.length < 10) {
            title = `${title} Technology Project`;
        }
        
        return title;
    }

    // --- FIXED PROJECT TITLE EXTRACTION ---
    function extractProjectTitleFixed(html) {
        if (!html || html.trim().length === 0) {
            logDebug('ERROR: No HTML provided for project title extraction');
            return null;
        }

        logDebug(`Starting project title extraction... HTML length: ${html.length}`);
        
        // Check if content is a malformed URL and try to extract useful info
        const urlPattern = /^https?:\/\//i;
        if (urlPattern.test(html.trim())) {
            logDebug('DETECTED: Content appears to be a malformed URL');
            return handleMalformedUrl(html.trim(), 'title');
        }

        // Helper function to clean extracted content
        function cleanTitleText(text) {
            if (!text) return null;
            return text
                .replace(/<[^>]*>/g, '')           // Remove all HTML tags
                .replace(/&nbsp;/gi, ' ')          // Replace &nbsp; with space
                .replace(/&amp;/gi, '&')          // Replace &amp; with &
                .replace(/&lt;/gi, '<')           // Replace &lt; with <
                .replace(/&gt;/gi, '>')           // Replace &gt; with >
                .replace(/&quot;/gi, '"')         // Replace &quot; with "
                .replace(/&#39;/gi, "'")          // Replace &#39; with '
                .replace(/\s+/g, ' ')             // Normalize whitespace
                .trim();
        }

        // Helper function to validate if content looks like a project title
        function isValidProjectTitle(text) {
            if (!text || text.length < 5) return false;
            
            const lowerText = text.toLowerCase();
            
            // Reject if it's clearly a person name or academic title
            const personIndicators = [
                /^(prof\.|professor|dr\.|doctor|mr\.|ms\.|mrs\.|ir prof\.)\s/i,
                /^[A-Z][a-z]+\s+[A-Z][A-Z\s]*,/,  // "John SMITH," pattern
                /, (professor|director|head|chair|associate|deputy|founder|co-founder|ceo|cto)/i,
                /\b(co-founder|founder|ceo|cto|director|president)\b/i,  // Business roles anywhere
                /professor\s*$/i,
                /\b(alumnus|alumni|engineer|graduate)\b/i,
                /\(a polyu.*startup\)/i,  // Startup descriptions
                /academic-led startup/i
            ];
            
            if (personIndicators.some(pattern => pattern.test(text))) {
                logDebug(`REJECTED as person name: "${text}"`);
                return false;
            }

            // Reject if it's clearly not a project title
            const nonTitleIndicators = [
                /^(principal investigator|investigator|pi):/i,
                /^research project$/i,
                /^project title$/i,
                /^award$/i,
                /^department of/i,
                /^school of/i,
                /^faculty of/i
            ];
            
            if (nonTitleIndicators.some(pattern => pattern.test(text))) {
                logDebug(`REJECTED as non-title: "${text}"`);
                return false;
            }

            return true;
        }

        // Strategy 1: Look for structured heading tags (h1, h2, h3) with content
        const headingPatterns = [
            /<h1[^>]*>(.*?)<\/h1>/gsi,
            /<h2[^>]*>(.*?)<\/h2>/gsi,
            /<h3[^>]*>(.*?)<\/h3>/gsi,
            /<h4[^>]*>(.*?)<\/h4>/gsi
        ];

        for (let pattern of headingPatterns) {
            const headingMatches = html.match(pattern);
            if (headingMatches && headingMatches.length > 0) {
                for (let match of headingMatches) {
                    const content = match.replace(/<\/?h[1-6][^>]*>/gi, '');
                    
                    // Check for strong tags within heading
                    const strongMatch = content.match(/<strong[^>]*>(.*?)<\/strong>/si);
                    if (strongMatch) {
                        const titleCandidate = cleanTitleText(strongMatch[1]);
                        if (isValidProjectTitle(titleCandidate)) {
                            logDebug(`SUCCESS (Heading+Strong): "${titleCandidate}"`);
                            return titleCandidate;
                        }
                    }
                    
                    // Check for markdown bold within heading
                    const markdownMatch = content.match(/\*\*(.*?)\*\*/si);
                    if (markdownMatch) {
                        const titleCandidate = cleanTitleText(markdownMatch[1]);
                        if (isValidProjectTitle(titleCandidate)) {
                            logDebug(`SUCCESS (Heading+Markdown): "${titleCandidate}"`);
                            return titleCandidate;
                        }
                    }
                    
                    // Check heading content directly
                    const titleCandidate = cleanTitleText(content);
                    if (isValidProjectTitle(titleCandidate) && titleCandidate.length > 10) {
                        logDebug(`SUCCESS (Heading Direct): "${titleCandidate}"`);
                        return titleCandidate;
                    }
                }
            }
        }

        // Strategy 2: Look for the first meaningful strong tag that isn't a person name
        const strongPattern = /<strong[^>]*>(.*?)<\/strong>/gsi;
        const strongMatches = html.match(strongPattern);
        
        if (strongMatches && strongMatches.length > 0) {
            for (let match of strongMatches) {
                const titleCandidate = cleanTitleText(match.replace(/<\/?strong[^>]*>/gi, ''));
                
                if (isValidProjectTitle(titleCandidate)) {
                    // Additional validation for project titles in strong tags
                    const lowerCandidate = titleCandidate.toLowerCase();
                    
                    // Prefer content that has technology/research keywords
                    const techKeywords = [
                        'system', 'technology', 'method', 'algorithm', 'application',
                        'development', 'design', 'framework', 'platform', 'solution',
                        'analysis', 'model', 'software', 'hardware', 'device', 'smart',
                        'intelligent', 'automated', 'digital', 'innovation', 'prototype'
                    ];
                    
                    const hasTechKeywords = techKeywords.some(keyword => 
                        lowerCandidate.includes(keyword)
                    );
                    
                    // Accept if it has tech keywords OR is substantial content without person indicators
                    if (hasTechKeywords || titleCandidate.length > 25) {
                        logDebug(`SUCCESS (Strong Tag): "${titleCandidate}"`);
                        return titleCandidate;
                    }
                }
            }
        }

        // Strategy 3: Look for first substantial paragraph content
        const paragraphPattern = /<p[^>]*>(.*?)<\/p>/gsi;
        const paragraphMatches = html.match(paragraphPattern);
        
        if (paragraphMatches && paragraphMatches.length > 0) {
            for (let match of paragraphMatches) {
                const content = match.replace(/<\/?p[^>]*>/gi, '');
                
                // Skip if it contains investigator labels
                if (content.toLowerCase().includes('investigator')) continue;
                
                const strongMatch = content.match(/<strong[^>]*>(.*?)<\/strong>/si);
                if (strongMatch) {
                    const titleCandidate = cleanTitleText(strongMatch[1]);
                    if (isValidProjectTitle(titleCandidate) && titleCandidate.length > 20) {
                        logDebug(`SUCCESS (Paragraph Strong): "${titleCandidate}"`);
                        return titleCandidate;
                    }
                }
                
                // Also check for markdown bold in paragraphs
                const markdownMatch = content.match(/\*\*(.*?)\*\*/si);
                if (markdownMatch) {
                    const titleCandidate = cleanTitleText(markdownMatch[1]);
                    if (isValidProjectTitle(titleCandidate) && titleCandidate.length > 15) {
                        logDebug(`SUCCESS (Paragraph Markdown): "${titleCandidate}"`);
                        return titleCandidate;
                    }
                }
            }
        }

        // Strategy 4: Look for any prominent bold text near the beginning that could be a title
        logDebug('Trying strategy 4: Any bold text near beginning');
        const firstPartHtml = html.substring(0, 2000); // First 2000 characters
        
        // Find all bold content in the beginning
        const boldPatterns = [
            /\*\*(.*?)\*\*/g,
            /<strong[^>]*>(.*?)<\/strong>/g,
            /<b[^>]*>(.*?)<\/b>/g
        ];
        
        for (let pattern of boldPatterns) {
            let match;
            while ((match = pattern.exec(firstPartHtml)) !== null) {
                const titleCandidate = cleanTitleText(match[1]);
                if (isValidProjectTitle(titleCandidate) && 
                    titleCandidate.length > 8 && 
                    titleCandidate.length < 150) {
                    logDebug(`SUCCESS (Strategy 4 - Early Bold): "${titleCandidate}"`);
                    return titleCandidate;
                }
            }
        }

        logDebug('ERROR: No valid project title found');
        return null;
    }

    // --- FIXED PRINCIPAL INVESTIGATOR EXTRACTION ---
    function extractPrincipleInvestigatorFixed(html) {
        if (!html || html.trim().length === 0) {
            logDebug('ERROR: No HTML provided for PI extraction');
            return null;
        }

        logDebug(`Starting improved PI extraction... HTML length: ${html.length}`);
        
        // Check if content is a malformed URL
        const urlPattern = /^https?:\/\//i;
        if (urlPattern.test(html.trim())) {
            logDebug('DETECTED: Content appears to be a malformed URL for PI extraction');
            return handleMalformedUrl(html.trim(), 'pi');
        }

        // Helper function to score PI candidates (higher score = more likely to be a person's name)
        function scorePI(candidate) {
            if (!candidate) return 0;
            
            let score = 0;
            const lowerCandidate = candidate.toLowerCase();
            
            // Strong positive indicators (academic titles)
            if (candidate.includes('Dr.') || candidate.includes('Dr ')) score += 50;
            if (candidate.includes('Prof.') || candidate.includes('Prof ')) score += 50;
            if (candidate.includes('Ir Prof.') || candidate.includes('Ir Dr.')) score += 60;
            
            // Positive indicators (name patterns)
            if (/^[A-Z][a-z]+ [A-Z][A-Z\s]*$/.test(candidate)) score += 30; // "John SMITH" pattern
            if (/[A-Z][a-z]+ [A-Z][a-z]+/.test(candidate)) score += 20; // "John Smith" pattern
            if (candidate.split(' ').length >= 2 && candidate.split(' ').length <= 6) score += 10; // 2-6 words
            
            // Negative indicators (department/organization names)
            const departmentKeywords = [
                'department', 'university', 'school', 'faculty', 'centre', 'center', 
                'institute', 'laboratory', 'lab', 'division', 'office', 'bureau',
                'technology', 'engineering', 'research', 'studies', 'sciences',
                'company', 'limited', 'ltd', 'corporation', 'corp', 'inc'
            ];
            
            for (let keyword of departmentKeywords) {
                if (lowerCandidate.includes(keyword)) {
                    score -= 30;
                    break; // Only penalize once for department-like content
                }
            }
            
            // Penalty for very long text (likely descriptions)
            if (candidate.length > 80) score -= 20;
            if (candidate.length > 120) score -= 30;
            
            // Bonus for appropriate length (typical name length)
            if (candidate.length >= 10 && candidate.length <= 40) score += 10;
            
            logDebug(`Scoring "${candidate}": ${score} points`);
            return score;
        }

        // Helper function to clean extracted content (enhanced for nested HTML)
        function cleanPIContent(text) {
            if (!text) return null;
            
            logDebug(`cleanPIContent input: "${text}"`);
            
            let cleaned = text
                .replace(/<[^>]*>/g, '')           // Remove all HTML tags (including nested ones)
                .replace(/&nbsp;/gi, ' ')          // Replace &nbsp; with space
                .replace(/&amp;/gi, '&')          // Replace &amp; with &
                .replace(/&lt;/gi, '<')           // Replace &lt; with <
                .replace(/&gt;/gi, '>')           // Replace &gt; with >
                .replace(/&quot;/gi, '"')         // Replace &quot; with "
                .replace(/&#39;/gi, "'")          // Replace &#39; with '
                .replace(/\*\*/g, '')             // Remove markdown bold markers
                .replace(/\s+/g, ' ')             // Normalize whitespace
                .trim();
            
            logDebug(`cleanPIContent output: "${cleaned}"`);
            
            // Additional validation for meaningful content
            if (!cleaned || cleaned.length < 2) {
                logDebug(`cleanPIContent rejected: too short (${cleaned ? cleaned.length : 'null'})`);
                return null;
            }
            
            // Reject if it's just whitespace or special characters
            if (/^[\s\-_.:;,]*$/.test(cleaned)) {
                logDebug(`cleanPIContent rejected: only whitespace/punctuation "${cleaned}"`);
                return null;
            }
            
            return cleaned;
        }

        // N8N-compatible bold content detection using string methods
        function findAllBoldContent(htmlContent, startIndex = 0) {
            const searchArea = htmlContent.substring(startIndex);
            const boldContent = [];
            
            logDebug(`Searching for bold content in: "${searchArea.substring(0, 200)}..."`);
            
            // Method 1: Find markdown bold **text** using string splitting (n8n-safe)
            logDebug('Trying markdown bold extraction with string methods...');
            const markdownItems = extractMarkdownBold(searchArea, 0); // Use 0 offset for searchArea
            // Adjust positions to original text
            markdownItems.forEach(item => item.position += startIndex);
            boldContent.push(...markdownItems);
            
            // Method 2: Find HTML strong tags using string methods
            logDebug('Trying strong tag extraction with string methods...');
            const strongItems = extractStrongTags(searchArea, 0); // Use 0 offset for searchArea
            // Adjust positions to original text
            strongItems.forEach(item => item.position += startIndex);
            boldContent.push(...strongItems);
            
            // Method 3: Find HTML b tags using string methods  
            logDebug('Trying b tag extraction with string methods...');
            const bItems = extractBTags(searchArea, 0); // Use 0 offset for searchArea
            // Adjust positions to original text
            bItems.forEach(item => item.position += startIndex);
            boldContent.push(...bItems);
            
            // Sort by position and remove duplicates
            const sorted = boldContent.sort((a, b) => a.position - b.position);
            const unique = [];
            const seen = new Set();
            
            for (let item of sorted) {
                const key = item.content.toLowerCase().trim();
                if (!seen.has(key) && key.length > 0) {
                    seen.add(key);
                    unique.push(item);
                }
            }
            
            logDebug(`Final unique bold items: ${unique.length}`);
            return unique;
        }
        
        // Robust markdown bold extraction using line-by-line processing (n8n compatible)
        function extractMarkdownBold(text, offset = 0) {
            const items = [];
            
            logDebug(`Starting robust markdown extraction from: "${text.substring(0, 100)}..."`);
            
            // Split by lines and find complete **content** patterns
            const lines = text.split('\n');
            
            for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                logDebug(`Processing line ${i}: "${line.substring(0, 80)}..."`);
                
                // Look for lines that start and end with **
                if (line.startsWith('**') && line.endsWith('**') && line.length > 4) {
                    const content = line.substring(2, line.length - 2);
                    const cleanContent = cleanPIContent(content);
                    
                    logDebug(`Found complete bold line: "${content}" -> clean: "${cleanContent}"`);
                    
                    if (cleanContent && cleanContent.length > 5) {
                        const lowerContent = cleanContent.toLowerCase();
                        
                        // Skip labels but keep actual PI names
                        if (!lowerContent.includes('investigator') && !lowerContent.includes('pi:')) {
                            items.push({
                                content: cleanContent,
                                position: offset + i * 50, // Approximate position
                                fullMatch: line,
                                type: 'markdown_line'
                            });
                            logDebug(`✅ Added robust markdown: "${cleanContent}"`);
                        } else {
                            logDebug(`❌ Skipped label line: "${cleanContent}"`);
                        }
                    }
                }
            }
            
            logDebug(`Robust markdown extraction complete: ${items.length} items found`);
            return items;
        }
        
        // Extract strong tags using string methods (n8n compatible) - Enhanced for nested HTML
        function extractStrongTags(text, offset = 0) {
            const items = [];
            let searchPos = 0;
            
            while (true) {
                const startTag = text.indexOf('<strong', searchPos);
                if (startTag === -1) break;
                
                const startContent = text.indexOf('>', startTag);
                if (startContent === -1) break;
                
                const endTag = text.indexOf('</strong>', startContent);
                if (endTag === -1) break;
                
                const rawContent = text.substring(startContent + 1, endTag);
                
                logDebug(`Raw strong content before cleaning: "${rawContent}"`);
                
                // Enhanced cleaning to handle nested HTML like <span> inside <strong>
                const cleanContent = cleanPIContent(rawContent);
                
                logDebug(`Cleaned strong content: "${cleanContent}"`);
                
                if (cleanContent && cleanContent.length > 2) {
                    items.push({
                        content: cleanContent,
                        position: offset + startTag,
                        fullMatch: text.substring(startTag, endTag + 9),
                        type: 'strong',
                        rawContent: rawContent  // Keep raw content for debugging
                    });
                    logDebug(`✅ Found strong tag: "${cleanContent}" (from raw: "${rawContent.substring(0, 100)}...")`);
                } else {
                    logDebug(`❌ Skipped strong tag: cleaned="${cleanContent}", length=${cleanContent ? cleanContent.length : 'null'}`);
                }
                
                searchPos = endTag + 9;
            }
            
            logDebug(`Total strong tags found: ${items.length}`);
            return items;
        }
        
        // Extract b tags using string methods (n8n compatible)
        function extractBTags(text, offset = 0) {
            const items = [];
            let searchPos = 0;
            
            while (true) {
                const startTag = text.indexOf('<b', searchPos);
                if (startTag === -1) break;
                
                const startContent = text.indexOf('>', startTag);
                if (startContent === -1) break;
                
                const endTag = text.indexOf('</b>', startContent);
                if (endTag === -1) break;
                
                const content = text.substring(startContent + 1, endTag);
                const cleanContent = cleanPIContent(content);
                
                if (cleanContent && cleanContent.length > 2) {
                    items.push({
                        content: cleanContent,
                        position: offset + startTag,
                        fullMatch: text.substring(startTag, endTag + 4),
                        type: 'b'
                    });
                    logDebug(`Found b tag: "${cleanContent}"`);
                }
                
                searchPos = endTag + 4;
            }
            
            return items;
        }

        // STRATEGY 1: Find PI label and extract ALL subsequent bold content
        const piLabelPatterns = [
            'Principle Investigator',
            'Principal Investigator', 
            'Principle Investigators',
            'Principal Investigators',
            'PI:',
            'Investigator:',
            'Lead Investigator',
            'Project Leader'
        ];
        
        for (let label of piLabelPatterns) {
            logDebug(`Trying pattern: "${label}"`);
            
            // Use simple case-insensitive indexOf instead of regex
            const labelMatch = html.toLowerCase().indexOf(label.toLowerCase());
            
            if (labelMatch !== -1) {
                logDebug(`✅ Found PI label "${label}" at position ${labelMatch}`);
                
                            // Show context around the label for debugging
            const contextStart = Math.max(0, labelMatch - 50);
            const contextEnd = Math.min(html.length, labelMatch + label.length + 200);
            const context = html.substring(contextStart, contextEnd);
            logDebug(`Context around label: "${context}"`);
            
            // PRIORITY CHECK: Look for font-weight: bolder spans anywhere in extended context
            const extendedContext = html.substring(Math.max(0, labelMatch - 200), Math.min(html.length, labelMatch + 800));
            const allBolderSpans = [...extendedContext.matchAll(/<span[^>]*font-weight:\s*bolder[^>]*>([^<]+)<\/span>/gi)];
            if (allBolderSpans.length > 0) {
                // Score each candidate and pick the best one
                const candidates = [];
                for (let bolderMatch of allBolderSpans) {
                    const candidate = cleanPIContent(bolderMatch[1]);
                    if (candidate && candidate.length > 5 && !candidate.toLowerCase().includes('investigator')) {
                        const score = scorePI(candidate);
                        
                        // Try to find additional affiliation info immediately after this span
                        const spanEndIndex = extendedContext.indexOf(bolderMatch[0]) + bolderMatch[0].length;
                        const afterSpanText = extendedContext.substring(spanEndIndex, spanEndIndex + 500);
                        
                        // Look for strong tag immediately following the span (handle nested spans)
                        const followingStrongPattern = /^\s*<strong[^>]*>(.*?)<\/strong>/i;
                        const followingStrongMatch = afterSpanText.match(followingStrongPattern);
                        
                        let fullPI = candidate;
                        if (followingStrongMatch && followingStrongMatch[1]) {
                            const rawAffiliation = followingStrongMatch[1];
                            logDebug(`Raw affiliation HTML: "${rawAffiliation}"`);
                            
                            // Handle nested span within strong tag
                            let affiliation = cleanPIContent(rawAffiliation);
                            
                            // If the affiliation is very short, it might be just punctuation - try extracting from nested span
                            if (!affiliation || affiliation.length <= 5) {
                                const nestedSpanPattern = /<span[^>]*>([^<]+)<\/span>/i;
                                const nestedSpanMatch = rawAffiliation.match(nestedSpanPattern);
                                if (nestedSpanMatch && nestedSpanMatch[1]) {
                                    const nestedContent = cleanPIContent(nestedSpanMatch[1]);
                                    if (nestedContent && nestedContent.length > 10) {
                                        affiliation = `, ${nestedContent}`;
                                        logDebug(`Found nested span affiliation: "${affiliation}"`);
                                    }
                                }
                            }
                            
                            if (affiliation && affiliation.length > 5) {
                                fullPI = `${candidate}${affiliation}`;
                                logDebug(`Found affiliation info: "${affiliation}"`);
                                logDebug(`Combined full PI: "${fullPI}"`);
                            } else {
                                logDebug(`Affiliation too short or invalid: "${affiliation}"`);
                            }
                        }
                        
                        candidates.push({ candidate: fullPI, score, originalName: candidate });
                        logDebug(`Bolder span candidate: "${fullPI}" (score: ${score})`);
                    }
                }
                
                // Sort by score and return the best candidate
                if (candidates.length > 0) {
                    candidates.sort((a, b) => b.score - a.score);
                    const bestCandidate = candidates[0];
                    if (bestCandidate.score > 0) {
                        logDebug(`🎉 SUCCESS (Priority Check - Bolder Span): Found PI with full info: "${bestCandidate.candidate}" (score: ${bestCandidate.score})`);
                        return bestCandidate.candidate;
                    }
                }
            } else {
                // FALLBACK: Look for multiple consecutive spans near PI label (when no bolder spans)
                const multipleSpansPattern = /<span[^>]*>([^<]+)<\/span>\s*,\s*<span[^>]*>([^<]+)<\/span>/gi;
                const multipleSpansMatches = [...extendedContext.matchAll(multipleSpansPattern)];
                if (multipleSpansMatches.length > 0) {
                    logDebug(`Found ${multipleSpansMatches.length} multiple consecutive span patterns (no bolder spans)`);
                    
                    for (let spanPair of multipleSpansMatches) {
                        const firstSpan = cleanPIContent(spanPair[1]);
                        const secondSpan = cleanPIContent(spanPair[2]);
                        
                        logDebug(`Multiple spans found (no bolder):`);
                        logDebug(`  First span: "${firstSpan}"`);
                        logDebug(`  Second span: "${secondSpan}"`);
                        
                        if (firstSpan && secondSpan && !firstSpan.toLowerCase().includes('investigator')) {
                            const score = scorePI(firstSpan);
                            
                            // Check if first span looks like a name and second like affiliation
                            if (score > 0 && secondSpan.length > 10) {
                                const combinedPI = `${firstSpan}, ${secondSpan}`;
                                logDebug(`🎉 SUCCESS (Multiple Spans No-Bolder Strategy): Found combined PI: "${combinedPI}" (score: ${score})`);
                                return combinedPI;
                            }
                        }
                    }
                }
                
                // SVIIF2024 CHECK: Look for strong tag with br-separated content (no bolder spans)
                const brSeparatedStrongPattern = /<strong[^>]*>.*?<br\s*\/?>\s*([^<]+?)<br\s*\/?>\s*([^<]+?)<\/strong>/gi;
                const brSeparatedMatches = [...extendedContext.matchAll(brSeparatedStrongPattern)];
                if (brSeparatedMatches.length > 0) {
                    logDebug(`Found ${brSeparatedMatches.length} br-separated strong patterns (no bolder, SVIIF2024 case)`);
                    
                    for (let brMatch of brSeparatedMatches) {
                        const nameContent = cleanPIContent(brMatch[1]);
                        const affiliationContent = cleanPIContent(brMatch[2]);
                        
                        logDebug(`BR-separated content found (no bolder):`);
                        logDebug(`  Name content: "${nameContent}"`);
                        logDebug(`  Affiliation content: "${affiliationContent}"`);
                        
                        if (nameContent && affiliationContent && !nameContent.toLowerCase().includes('investigator')) {
                            const score = scorePI(nameContent);
                            
                            // Check if first line looks like a name and second like affiliation
                            if (score > 0 && affiliationContent.length > 10) {
                                const combinedPI = `${nameContent}, ${affiliationContent}`;
                                logDebug(`🎉 SUCCESS (BR-Separated Strong No-Bolder Strategy): Found combined PI: "${combinedPI}" (score: ${score})`);
                                return combinedPI;
                            }
                        }
                    }
                }
                
                // GENEVA2024 CHECK: Manual strong tag extraction (no bolder spans)
                const allStrongTags = [];
                let pos = 0;
                while ((pos = extendedContext.indexOf('<strong', pos)) !== -1) {
                    const startPos = pos;
                    const tagClosePos = extendedContext.indexOf('>', startPos);
                    if (tagClosePos === -1) break;
                    
                    // Find matching closing tag by counting nesting levels
                    let currentPos = tagClosePos + 1;
                    let depth = 1;
                    let strongContent = '';
                    
                    while (currentPos < extendedContext.length && depth > 0) {
                        const nextStrongStart = extendedContext.indexOf('<strong', currentPos);
                        const nextStrongEnd = extendedContext.indexOf('</strong>', currentPos);
                        
                        if (nextStrongEnd === -1) break;
                        
                        if (nextStrongStart !== -1 && nextStrongStart < nextStrongEnd) {
                            // Found nested strong tag
                            depth++;
                            currentPos = nextStrongStart + 7; // Move past '<strong'
                        } else {
                            // Found closing tag
                            if (depth === 1) {
                                // This is our closing tag
                                strongContent = extendedContext.substring(tagClosePos + 1, nextStrongEnd);
                                allStrongTags.push(strongContent);
                            }
                            depth--;
                            currentPos = nextStrongEnd + 9; // Move past '</strong>'
                        }
                    }
                    
                    pos = startPos + 1; // Move to next potential strong tag
                }
                
                if (allStrongTags.length > 0) {
                    logDebug(`Found ${allStrongTags.length} strong tags via manual extraction (no bolder, Geneva2024 case)`);
                    
                    const allPIs = [];
                    
                    // Process all manually extracted strong tags
                    for (let strongContent of allStrongTags) {
                        const cleanContent = cleanPIContent(strongContent);
                        
                        // Skip the label tag but include PI content
                        if (cleanContent && cleanContent.length > 20) {
                            // Skip if it's just the label
                            if (cleanContent.toLowerCase().includes('investigator') && cleanContent.length < 50) {
                                logDebug(`Skipping label tag (no bolder): "${cleanContent}"`);
                                continue;
                            }
                            
                            // Check if it contains PI information (has Dr/Prof/Mr and substantial content)
                            // CRITICAL FIX: Check for both "Dr " and "Dr." patterns
                            if (cleanContent.includes('Dr ') || cleanContent.includes('Dr.') || 
                                cleanContent.includes('Prof ') || cleanContent.includes('Prof.') || 
                                cleanContent.includes('Mr ') || cleanContent.includes('Mr.')) {
                                // Relax scoring for Geneva2024 structures
                                let score = scorePI(cleanContent);
                                // CRITICAL FIX: Boost score more aggressively for clear PI names
                                if (score <= 0 && (cleanContent.includes('Dr ') || cleanContent.includes('Dr.') || 
                                                  cleanContent.includes('Prof ') || cleanContent.includes('Prof.') || 
                                                  cleanContent.includes('Mr ') || cleanContent.includes('Mr.'))) {
                                    score = 50; // Force positive score for titles even with dept keywords
                                }
                                logDebug(`Strong tag content (no bolder): "${cleanContent}" (score: ${score})`);
                                if (score > 0) allPIs.push(cleanContent);
                            }
                        }
                        
                        // Also check for nested spans within this strong tag (Solarcell case)
                        const spansInStrong = [...strongContent.matchAll(/<span[^>]*>([^<]*)<\/span>/gi)];
                        if (spansInStrong.length >= 2) {
                            const nameSpan = cleanPIContent(spansInStrong[0][1]);
                            const affiliationSpan = cleanPIContent(spansInStrong[1][1]);
                            
                            if (nameSpan && affiliationSpan && !nameSpan.toLowerCase().includes('investigator')) {
                                const score = scorePI(nameSpan);
                                
                                if (score > 0 && affiliationSpan.length > 10) {
                                    const combinedPI = `${nameSpan}${affiliationSpan}`;
                                    logDebug(`🎉 SUCCESS (Strong Nested Spans No-Bolder Strategy): Found combined PI: "${combinedPI}" (score: ${score})`);
                                    return combinedPI;
                                }
                            }
                        }
                    }
                    
                    if (allPIs.length > 0) {
                        // CRITICAL FIX: Remove duplicates and filter out pure organization names
                        const uniquePIs = [];
                        const seen = new Set();
                        
                        for (let pi of allPIs) {
                            // Skip pure organization/company names without person titles
                            if (!pi.includes('Dr ') && !pi.includes('Dr.') && 
                                !pi.includes('Prof ') && !pi.includes('Prof.') && 
                                !pi.includes('Mr ') && !pi.includes('Mr.') &&
                                (pi.includes('Limited') || pi.includes('Technology') || pi.includes('start-up'))) {
                                logDebug(`Filtering out organization name (no bolder): "${pi}"`);
                                continue;
                            }
                            
                            // Check for duplicates (fuzzy matching by first 50 chars)
                            const piKey = pi.substring(0, 50).toLowerCase();
                            if (!seen.has(piKey)) {
                                seen.add(piKey);
                                uniquePIs.push(pi);
                            } else {
                                logDebug(`Removing duplicate PI (no bolder): "${pi}"`);
                            }
                        }
                        
                        if (uniquePIs.length > 0) {
                            const combinedPIs = uniquePIs.join('; ');
                            logDebug(`🎉 SUCCESS (Manual Strong Extraction No-Bolder Strategy): Found combined PIs: "${combinedPIs}"`);
                            return combinedPIs;
                        }
                    }
                }
                
                // GENEVA2024 CHECK: Look for strong with nested spans (no bolder spans, Solarcell case)
                const strongNestedSpansPattern = /<strong[^>]*>.*?<span[^>]*>([^<]+)<\/span>\s*<span[^>]*>([^<]+)<\/span>.*?<\/strong>/gi;
                const strongNestedSpansMatches = [...extendedContext.matchAll(strongNestedSpansPattern)];
                if (strongNestedSpansMatches.length > 0) {
                    logDebug(`Found ${strongNestedSpansMatches.length} strong with nested spans patterns (no bolder, Geneva2024 Solarcell case)`);
                    
                    for (let spanMatch of strongNestedSpansMatches) {
                        const nameSpan = cleanPIContent(spanMatch[1]);
                        const affiliationSpan = cleanPIContent(spanMatch[2]);
                        
                        logDebug(`Strong with nested spans found (no bolder):`);
                        logDebug(`  Name span: "${nameSpan}"`);
                        logDebug(`  Affiliation span: "${affiliationSpan}"`);
                        
                        if (nameSpan && affiliationSpan && !nameSpan.toLowerCase().includes('investigator')) {
                            const score = scorePI(nameSpan);
                            
                            if (score > 0 && affiliationSpan.length > 10) {
                                const combinedPI = `${nameSpan}${affiliationSpan}`;
                                logDebug(`🎉 SUCCESS (Strong Nested Spans No-Bolder Strategy): Found combined PI: "${combinedPI}" (score: ${score})`);
                                return combinedPI;
                            }
                        }
                    }
                }
            }
            
            // SPECIAL CHECK: Look for span inside strong pattern around the PI label area
            // Look for all strong tags that contain spans (more precise matching)
            const strongTagsWithSpans = [...extendedContext.matchAll(/<strong[^>]*>([^<]*<span[^>]*>([^<]+)<\/span>[^<]*)<\/strong>/gi)];
            if (strongTagsWithSpans.length > 0) {
                logDebug(`Found ${strongTagsWithSpans.length} strong tags with nested spans`);
                
                for (let strongMatch of strongTagsWithSpans) {
                    const fullStrongContent = strongMatch[1]; // Full content inside this specific strong tag
                    const spanContent = strongMatch[2]; // Content inside the nested span
                    
                    logDebug(`Analyzing strong tag with nested span:`);
                    logDebug(`  Span content: "${spanContent}"`);
                    logDebug(`  Full strong content: "${fullStrongContent}"`);
                    
                    const spanCandidate = cleanPIContent(spanContent);
                    if (spanCandidate && spanCandidate.length > 5 && !spanCandidate.toLowerCase().includes('investigator')) {
                        const score = scorePI(spanCandidate);
                        
                        // Try to extract the full content from this specific strong tag
                        const fullContent = cleanPIContent(fullStrongContent);
                        if (fullContent && fullContent.length > spanCandidate.length + 10 && !fullContent.toLowerCase().includes('principal investigator')) {
                            // Full content is significantly longer and doesn't include the label, likely includes affiliation
                            logDebug(`🎉 SUCCESS (Strategy 1 Span-in-Strong FULL): Found full PI: "${fullContent}" (score: ${score})`);
                            return fullContent;
                        } else if (spanCandidate) {
                            // Fall back to just the span content if full content includes unwanted text
                            logDebug(`🎉 SUCCESS (Strategy 1 Span-in-Strong NAME): Found PI name: "${spanCandidate}" (score: ${score})`);
                            return spanCandidate;
                        }
                    }
                }
            }
            
            // FALLBACK CHECK: Look for multiple consecutive spans near PI label (Pipelines case)
            const multipleSpansPattern = /<span[^>]*>([^<]+)<\/span>\s*,\s*<span[^>]*>([^<]+)<\/span>/gi;
            const multipleSpansMatches = [...extendedContext.matchAll(multipleSpansPattern)];
            if (multipleSpansMatches.length > 0) {
                logDebug(`Found ${multipleSpansMatches.length} multiple consecutive span patterns`);
                
                for (let spanPair of multipleSpansMatches) {
                    const firstSpan = cleanPIContent(spanPair[1]);
                    const secondSpan = cleanPIContent(spanPair[2]);
                    
                    logDebug(`Multiple spans found:`);
                    logDebug(`  First span: "${firstSpan}"`);
                    logDebug(`  Second span: "${secondSpan}"`);
                    
                    if (firstSpan && secondSpan && !firstSpan.toLowerCase().includes('investigator')) {
                        const score = scorePI(firstSpan);
                        
                        // Check if first span looks like a name and second like affiliation
                        if (score > 0 && secondSpan.length > 10) {
                            const combinedPI = `${firstSpan}, ${secondSpan}`;
                            logDebug(`🎉 SUCCESS (Multiple Spans Strategy): Found combined PI: "${combinedPI}" (score: ${score})`);
                            return combinedPI;
                        }
                    }
                }
            }
            
            // SVIIF2024 CHECK: Look for strong tag with br-separated content (SVIIF2024 case)
            const brSeparatedStrongPattern = /<strong[^>]*>.*?<br\s*\/?>\s*([^<]+?)<br\s*\/?>\s*([^<]+?)<\/strong>/gi;
            const brSeparatedMatches = [...extendedContext.matchAll(brSeparatedStrongPattern)];
            if (brSeparatedMatches.length > 0) {
                logDebug(`Found ${brSeparatedMatches.length} br-separated strong patterns (SVIIF2024 case)`);
                
                for (let brMatch of brSeparatedMatches) {
                    const nameContent = cleanPIContent(brMatch[1]);
                    const affiliationContent = cleanPIContent(brMatch[2]);
                    
                    logDebug(`BR-separated content found:`);
                    logDebug(`  Name content: "${nameContent}"`);
                    logDebug(`  Affiliation content: "${affiliationContent}"`);
                    
                    if (nameContent && affiliationContent && !nameContent.toLowerCase().includes('investigator')) {
                        const score = scorePI(nameContent);
                        
                        // Check if first line looks like a name and second like affiliation
                        if (score > 0 && affiliationContent.length > 10) {
                            const combinedPI = `${nameContent}, ${affiliationContent}`;
                            logDebug(`🎉 SUCCESS (BR-Separated Strong Strategy): Found combined PI: "${combinedPI}" (score: ${score})`);
                            return combinedPI;
                        }
                    }
                }
            }
            
            // GENEVA2024 CHECK: Manual strong tag extraction for complex nested structures
            const allStrongTags = [];
            let pos = 0;
            while ((pos = extendedContext.indexOf('<strong', pos)) !== -1) {
                const startPos = pos;
                const tagClosePos = extendedContext.indexOf('>', startPos);
                if (tagClosePos === -1) break;
                
                // Find matching closing tag by counting nesting levels
                let currentPos = tagClosePos + 1;
                let depth = 1;
                let strongContent = '';
                
                while (currentPos < extendedContext.length && depth > 0) {
                    const nextStrongStart = extendedContext.indexOf('<strong', currentPos);
                    const nextStrongEnd = extendedContext.indexOf('</strong>', currentPos);
                    
                    if (nextStrongEnd === -1) break;
                    
                    if (nextStrongStart !== -1 && nextStrongStart < nextStrongEnd) {
                        // Found nested strong tag
                        depth++;
                        currentPos = nextStrongStart + 7; // Move past '<strong'
                    } else {
                        // Found closing tag
                        if (depth === 1) {
                            // This is our closing tag
                            strongContent = extendedContext.substring(tagClosePos + 1, nextStrongEnd);
                            allStrongTags.push(strongContent);
                        }
                        depth--;
                        currentPos = nextStrongEnd + 9; // Move past '</strong>'
                    }
                }
                
                pos = startPos + 1; // Move to next potential strong tag
            }
            
            if (allStrongTags.length > 0) {
                logDebug(`Found ${allStrongTags.length} strong tags via manual extraction (Geneva2024 case)`);
                
                const allPIs = [];
                
                // Process all manually extracted strong tags
                for (let strongContent of allStrongTags) {
                    const cleanContent = cleanPIContent(strongContent);
                    
                    // Skip the label tag but include PI content
                    if (cleanContent && cleanContent.length > 20) {
                        // Skip if it's just the label
                        if (cleanContent.toLowerCase().includes('investigator') && cleanContent.length < 50) {
                            logDebug(`Skipping label tag: "${cleanContent}"`);
                            continue;
                        }
                        
                        // Check if it contains PI information (has Dr/Prof/Mr and substantial content)
                        // CRITICAL FIX: Check for both "Dr " and "Dr." patterns
                        if (cleanContent.includes('Dr ') || cleanContent.includes('Dr.') || 
                            cleanContent.includes('Prof ') || cleanContent.includes('Prof.') || 
                            cleanContent.includes('Mr ') || cleanContent.includes('Mr.')) {
                            // Relax scoring for Geneva2024 structures
                            let score = scorePI(cleanContent);
                            // CRITICAL FIX: Boost score more aggressively for clear PI names
                            if (score <= 0 && (cleanContent.includes('Dr ') || cleanContent.includes('Dr.') || 
                                              cleanContent.includes('Prof ') || cleanContent.includes('Prof.') || 
                                              cleanContent.includes('Mr ') || cleanContent.includes('Mr.'))) {
                                score = 50; // Force positive score for titles even with dept keywords
                            }
                            logDebug(`Strong tag content: "${cleanContent}" (score: ${score})`);
                            if (score > 0) allPIs.push(cleanContent);
                        }
                    }
                    
                    // Also check for nested spans within this strong tag (Solarcell case)
                    const spansInStrong = [...strongContent.matchAll(/<span[^>]*>([^<]*)<\/span>/gi)];
                    if (spansInStrong.length >= 2) {
                        const nameSpan = cleanPIContent(spansInStrong[0][1]);
                        const affiliationSpan = cleanPIContent(spansInStrong[1][1]);
                        
                        if (nameSpan && affiliationSpan && !nameSpan.toLowerCase().includes('investigator')) {
                            const score = scorePI(nameSpan);
                            
                            if (score > 0 && affiliationSpan.length > 10) {
                                const combinedPI = `${nameSpan}${affiliationSpan}`;
                                logDebug(`🎉 SUCCESS (Strong Nested Spans Strategy): Found combined PI: "${combinedPI}" (score: ${score})`);
                                return combinedPI;
                            }
                        }
                    }
                }
                
                if (allPIs.length > 0) {
                    // CRITICAL FIX: Remove duplicates and filter out pure organization names
                    const uniquePIs = [];
                    const seen = new Set();
                    
                    for (let pi of allPIs) {
                        // Skip pure organization/company names without person titles
                        if (!pi.includes('Dr ') && !pi.includes('Dr.') && 
                            !pi.includes('Prof ') && !pi.includes('Prof.') && 
                            !pi.includes('Mr ') && !pi.includes('Mr.') &&
                            (pi.includes('Limited') || pi.includes('Technology') || pi.includes('start-up'))) {
                            logDebug(`Filtering out organization name: "${pi}"`);
                            continue;
                        }
                        
                        // Check for duplicates (fuzzy matching by first 50 chars)
                        const piKey = pi.substring(0, 50).toLowerCase();
                        if (!seen.has(piKey)) {
                            seen.add(piKey);
                            uniquePIs.push(pi);
                        } else {
                            logDebug(`Removing duplicate PI: "${pi}"`);
                        }
                    }
                    
                    if (uniquePIs.length > 0) {
                        const combinedPIs = uniquePIs.join('; ');
                        logDebug(`🎉 SUCCESS (Manual Strong Extraction Strategy): Found combined PIs: "${combinedPIs}"`);
                        return combinedPIs;
                    }
                }
            }
            
            // GENEVA2024 CHECK: Look for strong with nested spans (Solarcell case)
            const strongNestedSpansPattern = /<strong[^>]*>.*?<span[^>]*>([^<]+)<\/span>\s*<span[^>]*>([^<]+)<\/span>.*?<\/strong>/gi;
            const strongNestedSpansMatches = [...extendedContext.matchAll(strongNestedSpansPattern)];
            if (strongNestedSpansMatches.length > 0) {
                logDebug(`Found ${strongNestedSpansMatches.length} strong with nested spans patterns (Geneva2024 Solarcell case)`);
                
                for (let spanMatch of strongNestedSpansMatches) {
                    const nameSpan = cleanPIContent(spanMatch[1]);
                    const affiliationSpan = cleanPIContent(spanMatch[2]);
                    
                    logDebug(`Strong with nested spans found:`);
                    logDebug(`  Name span: "${nameSpan}"`);
                    logDebug(`  Affiliation span: "${affiliationSpan}"`);
                    
                    if (nameSpan && affiliationSpan && !nameSpan.toLowerCase().includes('investigator')) {
                        const score = scorePI(nameSpan);
                        
                        if (score > 0 && affiliationSpan.length > 10) {
                            const combinedPI = `${nameSpan}${affiliationSpan}`;
                            logDebug(`🎉 SUCCESS (Strong Nested Spans Strategy): Found combined PI: "${combinedPI}" (score: ${score})`);
                            return combinedPI;
                        }
                    }
                }
            }
                
                // Get all bold content after the label
                const boldContent = findAllBoldContent(html, labelMatch + label.length);
                logDebug(`Found ${boldContent.length} bold items after label`);
                
                // Log what we found for debugging with more detail
                boldContent.forEach((item, index) => {
                    logDebug(`Bold item ${index + 1} (${item.type}): "${item.content}" | Raw: "${item.rawContent ? item.rawContent.substring(0, 100) + '...' : 'N/A'}"`);
                });
                
                if (boldContent.length > 0) {
                    // Filter out content that's clearly not PI (but be liberal)
                    const validPIContent = boldContent.filter(item => {
                        const content = item.content.toLowerCase();
                        // Only exclude if it's clearly non-PI content
                        const isLabel = content.includes('principle investigator') ||
                                       content.includes('principal investigator') ||
                                       content.includes('investigator:') ||
                                       content.includes('pi:');
                        const tooShort = content.length <= 3;
                        
                        const isValid = !isLabel && !tooShort;
                        logDebug(`Filtering "${item.content}": isLabel=${isLabel}, tooShort=${tooShort}, isValid=${isValid}`);
                        return isValid;
                    });
                    
                    logDebug(`After filtering: ${validPIContent.length} valid PI items`);
                    
                    if (validPIContent.length > 0) {
                        // Combine all valid PI content with spaces
                        const combinedPI = validPIContent.map(item => item.content).join(' ').trim();
                        
                        logDebug(`Combined PI result: "${combinedPI}" (length: ${combinedPI.length})`);
                        
                        if (combinedPI.length > 5) {
                            logDebug(`🎉 SUCCESS (Strategy 1): Found PI with bold content after label: "${combinedPI}"`);
                            return combinedPI;
                        } else {
                            logDebug(`❌ Combined PI too short: "${combinedPI}" (${combinedPI.length} chars)`);
                        }
                    }
                }
                
                // Additional strategy: Look for content in the next 500 characters that looks like PI
                logDebug('No valid bold content found, trying text-based search after label');
                const afterLabelText = html.substring(labelMatch + label.length, labelMatch + label.length + 500);
                logDebug(`Searching in text after label: "${afterLabelText.substring(0, 200)}..."`);
                
                // SPECIAL CASE 1: Look for span with font-weight: bolder (Geneva2023 specific)
                const bolderSpanPattern = /<span[^>]*font-weight:\s*bolder[^>]*>([^<]+)<\/span>/i;
                const bolderSpanMatch = afterLabelText.match(bolderSpanPattern);
                if (bolderSpanMatch && bolderSpanMatch[1]) {
                    logDebug(`Found font-weight: bolder span pattern: "${bolderSpanMatch[1]}"`);
                    const candidate = cleanPIContent(bolderSpanMatch[1]);
                    if (candidate && candidate.length > 5) {
                        // Try to find additional affiliation info immediately after this span
                        const spanEndIndex = afterLabelText.indexOf(bolderSpanMatch[0]) + bolderSpanMatch[0].length;
                        const afterSpanText = afterLabelText.substring(spanEndIndex, spanEndIndex + 400);
                        
                        // Look for strong tag immediately following the span (handle nested spans)
                        const followingStrongPattern = /^\s*<strong[^>]*>(.*?)<\/strong>/i;
                        const followingStrongMatch = afterSpanText.match(followingStrongPattern);
                        
                        let fullPI = candidate;
                        if (followingStrongMatch && followingStrongMatch[1]) {
                            const rawAffiliation = followingStrongMatch[1];
                            logDebug(`Raw affiliation HTML: "${rawAffiliation}"`);
                            
                            // Handle nested span within strong tag
                            let affiliation = cleanPIContent(rawAffiliation);
                            
                            // If the affiliation is very short, it might be just punctuation - try extracting from nested span
                            if (!affiliation || affiliation.length <= 5) {
                                const nestedSpanPattern = /<span[^>]*>([^<]+)<\/span>/i;
                                const nestedSpanMatch = rawAffiliation.match(nestedSpanPattern);
                                if (nestedSpanMatch && nestedSpanMatch[1]) {
                                    const nestedContent = cleanPIContent(nestedSpanMatch[1]);
                                    if (nestedContent && nestedContent.length > 10) {
                                        affiliation = `, ${nestedContent}`;
                                        logDebug(`Found nested span affiliation: "${affiliation}"`);
                                    }
                                }
                            }
                            
                            if (affiliation && affiliation.length > 5) {
                                fullPI = `${candidate}${affiliation}`;
                                logDebug(`Found affiliation info: "${affiliation}"`);
                                logDebug(`Combined full PI: "${fullPI}"`);
                            }
                        }
                        
                        logDebug(`🎉 SUCCESS (Strategy 1 Bolder Span): Found PI with full info: "${fullPI}"`);
                        return fullPI;
                    }
                }
                
                // SPECIAL CASE 2: Look for span tags directly after PI label (Geneva2023 structure)
                const spanAfterLabelPattern = /<\/strong>\s*<span[^>]*>([^<]+)<\/span>/i;
                const spanAfterLabelMatch = afterLabelText.match(spanAfterLabelPattern);
                if (spanAfterLabelMatch && spanAfterLabelMatch[1]) {
                    logDebug(`Found span after label pattern: "${spanAfterLabelMatch[1]}"`);
                    const candidate = cleanPIContent(spanAfterLabelMatch[1]);
                    if (candidate && candidate.length > 5) {
                        logDebug(`🎉 SUCCESS (Strategy 1 Span After Label): Found PI in span after label: "${candidate}"`);
                        return candidate;
                    }
                }
                
                // SPECIAL CASE 2: Look for nested HTML patterns like <strong>PI:</strong> <span>Name</span>
                const nestedPattern = /<\/strong>\s*<[^>]*>([^<]+)<\/[^>]*>/i;
                const nestedMatch = afterLabelText.match(nestedPattern);
                if (nestedMatch && nestedMatch[1]) {
                    logDebug(`Found nested element pattern: "${nestedMatch[1]}"`);
                    const candidate = cleanPIContent(nestedMatch[1]);
                    if (candidate && candidate.length > 5) {
                        logDebug(`🎉 SUCCESS (Strategy 1 Nested): Found PI in nested element: "${candidate}"`);
                        return candidate;
                    }
                }
                
                // Look for academic titles in the subsequent text
                const academicTitleMatch = afterLabelText.match(/(?:\s|[:\*])+([^<\n]*(?:Prof\.|Dr\.|Ir Prof\.|Mr\.|Ms\.)[^<\n]*?)(?:\n|\*\*|<|$)/i);
                if (academicTitleMatch && academicTitleMatch[1]) {
                    logDebug(`Found academic title match: "${academicTitleMatch[1]}"`);
                    const candidate = cleanPIContent(academicTitleMatch[1]);
                    if (candidate && candidate.length > 10) {
                        logDebug(`🎉 SUCCESS (Strategy 1 Text Search): Found PI with academic title: "${candidate}"`);
                        return candidate;
                    }
                }
                
                // Final fallback: Look for any name-like content after the label
                const nameMatch = afterLabelText.match(/(?:\s|[:\*])+([A-Z][^<\n]*[A-Z][^<\n]*?)(?:\n|\*\*|<|$)/);
                if (nameMatch && nameMatch[1]) {
                    logDebug(`Found name pattern match: "${nameMatch[1]}"`);
                    const candidate = cleanPIContent(nameMatch[1]);
                    if (candidate && candidate.length > 8 && candidate.length < 200) {
                        logDebug(`🎉 SUCCESS (Strategy 1 Name Fallback): Found PI with name pattern: "${candidate}"`);
                        return candidate;
                    }
                }
            } else {
                logDebug(`❌ PI label "${label}" not found in HTML`);
            }
        }
        
        // STRATEGY 2: Look for academic titles in bold content (when no label found)
        logDebug('PI label methods failed, trying academic title patterns');
        
        const allBoldContent = findAllBoldContent(html);
        
        for (let boldItem of allBoldContent) {
            const content = boldItem.content;
            
            // Check if it contains academic titles
            if (content.match(/(?:Prof\.|Dr\.|Ir Prof\.|Mr\.|Ms\.|Mrs\.)/i) && 
                content.length > 10 && content.length < 500) {
                
                // Make sure it's not clearly project title or other non-PI content
                const lowerContent = content.toLowerCase();
                if (!lowerContent.includes('project') &&
                    !lowerContent.includes('system') &&
                    !lowerContent.includes('research center') &&
                    !lowerContent.includes('university') &&
                    !lowerContent.includes('department of') &&
                    !lowerContent.includes('school of')) {
                    
                    logDebug(`SUCCESS (Strategy 2): Found PI with academic title in bold: "${content}"`);
                    return content;
                }
            }
        }
        
        // STRATEGY 3: Last resort - look for any person name pattern in bold
        logDebug('Academic title patterns failed, trying any person name in bold');
        
        for (let boldItem of allBoldContent) {
            const content = boldItem.content;
            
            // Very basic person name pattern
            if (content.length > 5 && content.length < 200 &&
                /^[A-Z]/i.test(content) &&
                content.includes(' ') &&
                !content.toLowerCase().includes('investigator') &&
                !content.toLowerCase().includes('project') &&
                !content.toLowerCase().includes('title') &&
                !content.toLowerCase().includes('system') &&
                !content.toLowerCase().includes('method') &&
                !content.toLowerCase().includes('algorithm') &&
                !content.toLowerCase().includes('technology') &&
                !content.toLowerCase().includes('innovation') &&
                !content.toLowerCase().includes('startup') &&
                !content.toLowerCase().includes('company') &&
                !content.toLowerCase().includes('university') &&
                !content.toLowerCase().includes('department')) {
                
                logDebug(`SUCCESS (Strategy 3): Found PI with person name pattern: "${content}"`);
                return content;
            }
        }
        
        // FINAL FALLBACK: If we found any PI label anywhere, search entire HTML for font-weight: bolder spans
        const hasAnyPILabel = piLabelPatterns.some(label => html.toLowerCase().includes(label.toLowerCase()));
        if (hasAnyPILabel) {
            logDebug('Found PI label somewhere, trying global font-weight: bolder search as fallback...');
            const globalBolderSpans = [...html.matchAll(/<span[^>]*font-weight:\s*bolder[^>]*>([^<]+)<\/span>/gi)];
            if (globalBolderSpans.length > 0) {
                for (let bolderMatch of globalBolderSpans) {
                    const candidate = cleanPIContent(bolderMatch[1]);
                    // More strict validation for global search
                    if (candidate && candidate.length > 8 && candidate.length < 150 && 
                        !candidate.toLowerCase().includes('investigator') &&
                        (candidate.includes('Dr.') || candidate.includes('Prof.') || candidate.includes('Dr ') || candidate.includes('Prof '))) {
                        
                        // Try to find additional affiliation info immediately after this span
                        const spanEndIndex = html.indexOf(bolderMatch[0]) + bolderMatch[0].length;
                        const afterSpanText = html.substring(spanEndIndex, spanEndIndex + 400);
                        
                        // Look for strong tag immediately following the span (handle nested spans)
                        const followingStrongPattern = /^\s*<strong[^>]*>(.*?)<\/strong>/i;
                        const followingStrongMatch = afterSpanText.match(followingStrongPattern);
                        
                        let fullPI = candidate;
                        if (followingStrongMatch && followingStrongMatch[1]) {
                            const rawAffiliation = followingStrongMatch[1];
                            logDebug(`Raw affiliation HTML in global search: "${rawAffiliation}"`);
                            
                            // Handle nested span within strong tag
                            let affiliation = cleanPIContent(rawAffiliation);
                            
                            // If the affiliation is very short, it might be just punctuation - try extracting from nested span
                            if (!affiliation || affiliation.length <= 5) {
                                const nestedSpanPattern = /<span[^>]*>([^<]+)<\/span>/i;
                                const nestedSpanMatch = rawAffiliation.match(nestedSpanPattern);
                                if (nestedSpanMatch && nestedSpanMatch[1]) {
                                    const nestedContent = cleanPIContent(nestedSpanMatch[1]);
                                    if (nestedContent && nestedContent.length > 10) {
                                        affiliation = `, ${nestedContent}`;
                                        logDebug(`Found nested span affiliation in global search: "${affiliation}"`);
                                    }
                                }
                            }
                            
                            if (affiliation && affiliation.length > 5) {
                                fullPI = `${candidate}${affiliation}`;
                                logDebug(`Found affiliation info in global search: "${affiliation}"`);
                                logDebug(`Combined full PI in global search: "${fullPI}"`);
                            }
                        }
                        
                        logDebug(`🎉 SUCCESS (Global Fallback - Bolder Span): Found PI in global font-weight: bolder search: "${fullPI}"`);
                        return fullPI;
                    }
                }
            }
        }
        
        logDebug('ERROR: No principal investigator found with any strategy');
        return null;
    }

    // --- APPLY IMPROVED EXTRACTION ---
    // Debug logging for n8n environment
    logDebug('=== EXTRACTION DEBUG INFO ===');
    logDebug(`Project ID: ${projectData.projectId}`);
    logDebug(`ProjectMainDiv length: ${projectMainDivHtml.length}`);
    logDebug(`RichTextHtml length: ${currentRichTextHtml.length}`);
    
    // Log a snippet of the actual HTML content for debugging
    if (currentRichTextHtml && currentRichTextHtml.length > 0) {
        logDebug(`RichTextHtml snippet: "${currentRichTextHtml.substring(0, 300)}..."`);
        
        // Check if it contains PI patterns
        if (currentRichTextHtml.includes('Principle Investigator') || currentRichTextHtml.includes('Principal Investigator')) {
            logDebug('✅ HTML contains PI label patterns');
        } else {
            logDebug('❌ HTML does NOT contain PI label patterns');
        }
        
        // Check if it contains markdown bold patterns
        const markdownCount = (currentRichTextHtml.match(/\*\*/g) || []).length;
        logDebug(`Found ${markdownCount} markdown bold markers in HTML`);
        
        // Check for strong tags
        const strongCount = (currentRichTextHtml.match(/<strong>/g) || []).length;
        logDebug(`Found ${strongCount} strong tags in HTML`);
    } else {
        logDebug('❌ RichTextHtml is empty or null');
    }
    
    // Search across ALL HTML content for project title (heading might be in main div)
    const allProjectHtml = `${projectMainDivHtml}\n${currentRichTextHtml}`;
    
    logDebug('--- STARTING TITLE EXTRACTION ---');
    const extractedTitle = extractProjectTitleFixed(allProjectHtml);
    logDebug(`✅ Title Result: "${extractedTitle}"`);
    
    logDebug('--- STARTING PI EXTRACTION ---');
    const extractedPI = extractPrincipleInvestigatorFixed(currentRichTextHtml);
    logDebug(`✅ PI Result: "${extractedPI}"`);
    
    logDebug('=== END EXTRACTION DEBUG ===');
    
    projectData.projectTitle = extractedTitle;
    projectData.principleInvestigator = extractedPI;

    // --- EXISTING LOGIC FOR OTHER FIELDS ---
    
    // Project Description
    const descriptionMatches = [...currentRichTextHtml.matchAll(/<p[^>]*>(?!.*(Principle Investigator|Principal Investigator))(.+?)<\/p>/gsi)];
    projectData.projectDescription = descriptionMatches.map(match => match[2].trim()).join('\n\n');
    if (projectData.projectDescription === "") {
        projectData.projectDescription = null;
    }
    


    // Image URL
    const imgMatch = projectMainDivHtml.match(/<img[^>]*src="([^"]+)"/i);
    let imageUrl = imgMatch ? imgMatch[1] : null;
    if (imageUrl && imageUrl.startsWith('/')) {
        imageUrl = 'https://www.polyu.edu.hk' + imageUrl;
    }
    projectData.projectImageUrl = imageUrl;

    outputItems.push({ json: projectData });
    console.log(`✅ Successfully processed Project ${i + 1}`);
  }
  
  // Final summary
  console.log('\n=== FINAL PROCESSING SUMMARY ===');
  console.log(`Total projects attempted: ${maxLength}`);
  console.log(`Successfully processed: ${outputItems.length}`);
  console.log(`Skipped/Failed: ${maxLength - outputItems.length}`);
  console.log('=== END SUMMARY ===');
}

return outputItems; 