// Citizen Interface JavaScript
// API base URL
const API_BASE = '/api';

// State
let currentResults = [];
let currentProcess = null;
let currentParticipants = [];
let currentParticipantsPage = 1;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('searchInput');

    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });

    // Autocomplete
    searchInput.addEventListener('input', handleAutocomplete);
}

// Load statistics and populate platform filter
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();

        const statsHTML = `
            <div class="stat-card">
                <div class="stat-number">${data.total_processes || 0}</div>
                <div class="stat-label">Deliberation Processes</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${data.total_contributions || 0}</div>
                <div class="stat-label">Contributions</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${data.total_fallacies || 0}</div>
                <div class="stat-label">Detected Fallacies</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${data.platforms ? data.platforms.length : 0}</div>
                <div class="stat-label">Platforms</div>
            </div>
        `;

        document.getElementById('stats').innerHTML = statsHTML;

        // Populate platform filter dropdown dynamically with guardrails
        if (data.platforms && Array.isArray(data.platforms)) {
            const platformFilter = document.getElementById('platformFilter');
            // Keep "All Platforms" option
            platformFilter.innerHTML = '<option value="">All Platforms</option>';

            // Add each platform from API (sorted alphabetically)
            data.platforms
                .filter(p => p && typeof p === 'string' && p.trim().length > 0) // Guardrail: validate platform names
                .sort()
                .forEach(platform => {
                    const option = document.createElement('option');
                    option.value = platform;
                    option.textContent = platform;
                    platformFilter.appendChild(option);
                });
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        // Guardrail: if stats fail, show error message
        document.getElementById('stats').innerHTML = `
            <div class="stat-card" style="grid-column: 1 / -1;">
                <div class="stat-label" style="color: var(--error-color);">
                    <i class="fas fa-exclamation-triangle"></i> Unable to load statistics. Please refresh the page.
                </div>
            </div>
        `;
    }
}

// Perform search
async function performSearch() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) return;

    // Force return to results view if in detail view
    backToResults();

    const topK = parseInt(document.getElementById('topK').value);
    const platformFilter = document.getElementById('platformFilter').value;

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/semantic-search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query,
                top_k: topK,
                platform: platformFilter || null
            })
        });

        const data = await response.json();
        const results = data.results || [];

        currentResults = results;
        displayResults(currentResults);
    } catch (error) {
        console.error('Search error:', error);
        showError('Search error. Please try again.');
    }
}

// Display search results
function displayResults(results) {
    const resultsContainer = document.getElementById('searchResults');

    if (!results || results.length === 0) {
        resultsContainer.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: var(--text-light);">
                <i class="fas fa-search" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                <h3>No results found</h3>
                <p>Try different keywords</p>
            </div>
        `;
        return;
    }

    const resultsHTML = results.map((result, index) => `
        <div class="result-card" onclick="viewProcess('${escapeHtml(result.uri)}')">
            <div class="result-header">
                <h3>${escapeHtml(result.title || 'Untitled Process')}</h3>
                <span class="relevance-score">
                    ${(result.relevance_score * 100).toFixed(1)}%
                </span>
            </div>
            <p class="description">${escapeHtml(truncate(result.description || '', 200))}</p>
            <div class="result-meta">
                <span>
                    <i class="fas fa-calendar"></i>
                    ${result.date || 'N/A'}
                </span>
                <span>
                    <i class="fas fa-globe"></i>
                    ${escapeHtml(result.platform || 'Unknown')}
                </span>
                <span>
                    <i class="fas fa-comments"></i>
                    ${result.contributions_count || 0} contributions
                </span>
                <span>
                    <i class="fas fa-exclamation-triangle"></i>
                    ${result.fallacies_count || 0} fallacies
                </span>
            </div>
        </div>
    `).join('');

    resultsContainer.innerHTML = resultsHTML;
}

// View process details
async function viewProcess(uri) {
    showLoading();

    try {
        // Use query parameter instead of path parameter (Apache-friendly)
        const encodedUri = encodeURIComponent(uri);
        const response = await fetch(`${API_BASE}/process?uri=${encodedUri}`);
        const process = await response.json();

        currentProcess = process;
        displayProcessDetails(process);
    } catch (error) {
        console.error('Error loading process:', error);
        showError('Error loading process details');
    }
}

// Display process details
function displayProcessDetails(process) {
    const resultsContainer = document.getElementById('searchResults');
    const detailsContainer = document.getElementById('processDetails');

    resultsContainer.style.display = 'none';
    detailsContainer.style.display = 'block';

    // Reset pagination state for participants
    currentParticipants = process.participants || [];
    currentParticipantsPage = 1;

    const detailsHTML = `
        <button class="back-button" onclick="backToResults()">
            <i class="fas fa-arrow-left"></i> Back to results
        </button>

        <h2>${escapeHtml(process.title || 'Untitled Process')}</h2>

        <div class="result-meta">
            <span><i class="fas fa-calendar"></i> ${formatDate(process.date)}</span>
            <span><i class="fas fa-globe"></i> ${escapeHtml(process.platform || 'Unknown')}</span>
            <span><i class="fas fa-link"></i> <a href="${process.uri}" target="_blank">URI</a></span>
        </div>

        <p style="margin-top: 1.5rem;">${escapeHtml(process.description || 'No description available')}</p>

        <!-- Contributions Section -->
        <div class="section">
            <h3>
                <i class="fas fa-comments"></i>
                Contributions (${process.contributions ? process.contributions.length : 0})
            </h3>
            <div id="contributions-container">
                <div class="contributions-grid" id="contributions-grid">
                    ${renderContributions(process.contributions || [], 1)}
                </div>
                <div id="contributions-pagination"></div>
            </div>
        </div>

        <!-- Fallacies Section -->
        <div class="section">
            <h3>
                <i class="fas fa-exclamation-triangle"></i>
                Detected Fallacies (${process.fallacies ? process.fallacies.length : 0})
            </h3>
            <div class="fallacies-grid">
                ${renderFallacies(process.fallacies || [])}
            </div>
        </div>

        <!-- Participants Section -->
        <div class="section">
            <h3>
                <i class="fas fa-users"></i>
                Participants (${process.participants ? process.participants.length : 0})
            </h3>
            <div id="participants-container">
                <div class="participants-grid" id="participants-grid">
                    ${renderParticipants(process.participants || [], 1)}
                </div>
                <div id="participants-pagination"></div>
            </div>
        </div>

        <!-- Graph Visualization -->
        <div class="section">
            <h3><i class="fas fa-project-diagram"></i> Graph Visualization</h3>
            <div id="graphViz"></div>
        </div>

        <!-- Download This Process -->
        <div class="section">
            <h3><i class="fas fa-download"></i> Download This Deliberation</h3>
            <div class="download-options">
                <button onclick="downloadProcess('${process.uri}', 'ttl')" class="btn-secondary">
                    <i class="fas fa-file-code"></i> RDF/Turtle
                </button>
                <button onclick="downloadProcess('${process.uri}', 'jsonld')" class="btn-secondary">
                    <i class="fas fa-file-code"></i> JSON-LD
                </button>
                <button onclick="downloadProcess('${process.uri}', 'json')" class="btn-secondary">
                    <i class="fas fa-file-alt"></i> JSON
                </button>
            </div>
        </div>
    `;

    detailsContainer.innerHTML = detailsHTML;

    // Initialize graph visualization
    if (process.contributions && process.contributions.length > 0) {
        visualizeGraph(process);
    }
}

// Global for current contributions page
let currentContributions = [];
let currentContributionsPage = 1;
const CONTRIBUTIONS_PER_PAGE = 10;
const PARTICIPANTS_PER_PAGE = 10;

// Render contributions with pagination and threading
function renderContributions(contributions, page = 1) {
    if (!contributions || contributions.length === 0) {
        return '<p style="color: var(--text-light);">No contributions available</p>';
    }

    currentContributions = contributions;
    currentContributionsPage = page;

    // Organize contributions by threading
    const mainContributions = [];
    const commentsByParent = new Map();

    // First pass: separate main contributions from comments
    contributions.forEach(c => {
        if (c.responseTo) {
            // This is a comment responding to another contribution
            if (!commentsByParent.has(c.responseTo)) {
                commentsByParent.set(c.responseTo, []);
            }
            commentsByParent.get(c.responseTo).push(c);
        } else {
            // This is a main contribution
            mainContributions.push(c);
        }
    });

    // Paginate only main contributions
    const start = (page - 1) * CONTRIBUTIONS_PER_PAGE;
    const end = start + CONTRIBUTIONS_PER_PAGE;
    const pageMainContributions = mainContributions.slice(start, end);

    const html = pageMainContributions.map(c => {
        const comments = commentsByParent.get(c.uri) || [];
        const commentsHtml = comments.length > 0 ? `
            <div style="margin-top: 1rem; padding-left: 1.5rem; border-left: 3px solid var(--primary-color);">
                <p style="font-size: 0.9rem; font-weight: bold; color: var(--primary-color); margin-bottom: 0.5rem;">
                    <i class="fas fa-reply"></i> ${comments.length} Response${comments.length > 1 ? 's' : ''}
                </p>
                ${comments.map(comment => `
                    <div class="contribution-comment" onclick="showResourceDetails('${comment.uri}')" style="margin-bottom: 0.75rem; padding: 0.75rem; background: rgba(74, 157, 60, 0.05); border-radius: 6px; cursor: pointer;">
                        <p style="margin: 0;"><strong>${escapeHtml(comment.author || 'Unknown')}</strong> ${comment.timestamp ? `<span style="color: var(--text-light); font-size: 0.85rem;">• ${formatDate(comment.timestamp)}</span>` : ''}</p>
                        <p style="margin: 0.5rem 0 0 0; font-size: 0.95rem;">${escapeHtml(truncate(comment.text || '', 200))}</p>
                    </div>
                `).join('')}
            </div>
        ` : '';

        return `
            <div class="contribution-card clickable-contribution" onclick="showResourceDetails('${c.uri}')">
                <p><strong>Author:</strong> ${escapeHtml(c.author || 'Unknown')} ${c.timestamp ? `<span style="color: var(--text-light); font-size: 0.85rem;">• ${formatDate(c.timestamp)}</span>` : ''}</p>
                <p>${escapeHtml(truncate(c.text || '', 500))}</p>
                <p style="font-size: 0.8rem; color: var(--text-light); margin-top: 0.5rem;">
                    <i class="fas fa-link"></i> Click to view full details
                </p>
                ${commentsHtml}
            </div>
        `;
    }).join('');

    // Render pagination after the grid is updated (paginate main contributions only)
    setTimeout(() => renderContributionsPagination(mainContributions.length, page), 0);

    return html;
}

// Render pagination controls
function renderContributionsPagination(totalContributions, currentPage) {
    const paginationContainer = document.getElementById('contributions-pagination');
    if (!paginationContainer) return;

    const totalPages = Math.ceil(totalContributions / CONTRIBUTIONS_PER_PAGE);

    if (totalPages <= 1) {
        paginationContainer.innerHTML = '';
        return;
    }

    let html = '<div class="pagination">';

    // Previous button
    if (currentPage > 1) {
        html += `<button class="pagination-btn" onclick="changeContributionsPage(${currentPage - 1})">
            <i class="fas fa-chevron-left"></i> Previous
        </button>`;
    }

    // Page numbers
    const maxButtons = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);

    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }

    if (startPage > 1) {
        html += `<button class="pagination-btn" onclick="changeContributionsPage(1)">1</button>`;
        if (startPage > 2) html += '<span class="pagination-ellipsis">...</span>';
    }

    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="pagination-btn ${i === currentPage ? 'active' : ''}"
                 onclick="changeContributionsPage(${i})">${i}</button>`;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) html += '<span class="pagination-ellipsis">...</span>';
        html += `<button class="pagination-btn" onclick="changeContributionsPage(${totalPages})">${totalPages}</button>`;
    }

    // Next button
    if (currentPage < totalPages) {
        html += `<button class="pagination-btn" onclick="changeContributionsPage(${currentPage + 1})">
            Next <i class="fas fa-chevron-right"></i>
        </button>`;
    }

    html += '</div>';
    paginationContainer.innerHTML = html;
}

// Change contributions page
function changeContributionsPage(page) {
    const grid = document.getElementById('contributions-grid');
    if (!grid) return;

    grid.innerHTML = renderContributions(currentContributions, page);

    // Scroll to contributions section
    document.getElementById('contributions-container').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Render fallacies
function renderFallacies(fallacies) {
    if (!fallacies || fallacies.length === 0) {
        return '<p style="color: var(--text-light);">No fallacies detected</p>';
    }

    return fallacies.map(f => `
        <div class="fallacy-card">
            <p><strong>Type:</strong> ${escapeHtml(getFallacyName(f.type))}</p>
            <p><strong>Location:</strong> ${escapeHtml(f.location || 'N/A')}</p>
        </div>
    `).join('');
}

// Render participants
function renderParticipants(participants, page = 1) {
    currentParticipantsPage = page;

    if (!participants || participants.length === 0) {
        setTimeout(() => renderParticipantsPagination(0, 1), 0);
        return '<p style="color: var(--text-light);">No participants available</p>';
    }

    const start = (page - 1) * PARTICIPANTS_PER_PAGE;
    const end = start + PARTICIPANTS_PER_PAGE;
    const pageParticipants = participants.slice(start, end);

    const html = pageParticipants.map(p => `
        <div class="participant-card" onclick="showResourceDetails('${p.uri}')" style="cursor: pointer;">
            <p><strong>${escapeHtml(p.name || 'Unknown')}</strong></p>
            ${p.party ? `<p>Party: ${escapeHtml(p.party)}</p>` : ''}
            <p style="font-size: 0.8rem; color: var(--text-light); margin-top: 0.5rem;">
                <i class="fas fa-link"></i> Click to view details
            </p>
        </div>
    `).join('');

    setTimeout(() => renderParticipantsPagination(participants.length, page), 0);

    return html;
}

function renderParticipantsPagination(totalParticipants, currentPage) {
    const paginationContainer = document.getElementById('participants-pagination');
    if (!paginationContainer) return;

    const totalPages = Math.ceil(totalParticipants / PARTICIPANTS_PER_PAGE);

    if (totalPages <= 1) {
        paginationContainer.innerHTML = '';
        return;
    }

    let html = '<div class="pagination">';

    if (currentPage > 1) {
        html += `<button class="pagination-btn" onclick="changeParticipantsPage(${currentPage - 1})">
            <i class="fas fa-chevron-left"></i> Previous
        </button>`;
    }

    const maxButtons = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);

    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }

    if (startPage > 1) {
        html += `<button class="pagination-btn" onclick="changeParticipantsPage(1)">1</button>`;
        if (startPage > 2) html += '<span class="pagination-ellipsis">...</span>';
    }

    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="pagination-btn ${i === currentPage ? 'active' : ''}"
                 onclick="changeParticipantsPage(${i})">${i}</button>`;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) html += '<span class="pagination-ellipsis">...</span>';
        html += `<button class="pagination-btn" onclick="changeParticipantsPage(${totalPages})">${totalPages}</button>`;
    }

    if (currentPage < totalPages) {
        html += `<button class="pagination-btn" onclick="changeParticipantsPage(${currentPage + 1})">
            Next <i class="fas fa-chevron-right"></i>
        </button>`;
    }

    html += '</div>';
    paginationContainer.innerHTML = html;
}

function changeParticipantsPage(page) {
    const grid = document.getElementById('participants-grid');
    if (!grid) return;

    grid.innerHTML = renderParticipants(currentParticipants, page);
    document.getElementById('participants-container').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Visualize graph with D3.js
function visualizeGraph(process) {
    const container = document.getElementById('graphViz');
    if (!container) return;

    // Clear previous visualization
    container.innerHTML = '';

    // Prepare graph data
    const nodes = [
        { id: process.uri, label: process.title, type: 'process', uri: process.uri }
    ];

    const links = [];

    // Track unique participants
    const participantsMap = new Map();
    const contributionUriToId = new Map();

    // Add contributions and extract participants/topics
    (process.contributions || []).forEach((c, i) => {
        const nodeId = `contribution_${i}`;
        contributionUriToId.set(c.uri, nodeId);

        const isComment = !!c.responseTo;

        nodes.push({
            id: nodeId,
            label: isComment ? `Comment ${i + 1}` : `Contribution ${i + 1}`,
            type: isComment ? 'comment' : 'contribution',
            uri: c.uri
        });

        // Link to process (only if not a comment)
        if (!isComment) {
            links.push({ source: process.uri, target: nodeId });
        }

        // Track participant (will be linked later)
        if (c.author && c.author !== 'Unknown') {
            participantsMap.set(c.author, nodeId);
        }
    });

    // Second pass: add responseTo links for comments
    (process.contributions || []).forEach((c, i) => {
        if (c.responseTo) {
            const commentId = contributionUriToId.get(c.uri);
            const parentId = contributionUriToId.get(c.responseTo);

            if (commentId && parentId) {
                links.push({
                    source: parentId,
                    target: commentId,
                    type: 'responseTo'
                });
            }
        }
    });

    // Add participants as nodes
    let participantIndex = 0;
    participantsMap.forEach((contributionId, participantName) => {
        const participantId = `participant_${participantIndex++}`;
        nodes.push({
            id: participantId,
            label: participantName.length > 30 ? participantName.substr(0, 30) + '...' : participantName,
            type: 'participant',
            uri: null // Will be set if available
        });
        links.push({ source: contributionId, target: participantId });
    });

    // Add fallacies
    (process.fallacies || []).forEach((f, i) => {
        const nodeId = `fallacy_${i}`;
        nodes.push({
            id: nodeId,
            label: getFallacyName(f.type),
            type: 'fallacy',
            uri: f.uri
        });
        links.push({ source: process.uri, target: nodeId });
    });

    // Add participants nodes if available
    (process.participants || []).forEach((p, i) => {
        const nodeId = `participant_${i}`;
        nodes.push({
            id: nodeId,
            label: p.name || `Participant ${i + 1}`,
            type: 'participant',
            uri: p.uri
        });
        links.push({ source: process.uri, target: nodeId });
    });

    // Create D3 visualization
    const width = container.offsetWidth;
    const height = 500;

    const svg = d3.select('#graphViz')
        .append('svg')
        .attr('width', width)
        .attr('height', height);

    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2));

    const link = svg.append('g')
        .selectAll('line')
        .data(links)
        .enter().append('line')
        .attr('stroke', d => d.type === 'responseTo' ? '#f59e0b' : '#999')
        .attr('stroke-width', d => d.type === 'responseTo' ? 2.5 : 2)
        .attr('stroke-dasharray', d => d.type === 'responseTo' ? '5,5' : '0');

    const node = svg.append('g')
        .selectAll('circle')
        .data(nodes)
        .enter().append('circle')
        .attr('r', d => {
            if (d.type === 'process') return 15;
            if (d.type === 'participant') return 10;
            return 8;
        })
        .attr('fill', d => {
            if (d.type === 'process') return '#4a9d3c'; // DKG green
            if (d.type === 'fallacy') return '#ef4444'; // Red
            if (d.type === 'participant') return '#ffd700'; // Gold
            if (d.type === 'comment') return '#f59e0b'; // Orange for comments
            return '#10b981'; // Contribution green
        })
        .style('cursor', 'pointer')
        .on('click', function(event, d) {
            event.stopPropagation();
            if (d.uri) {
                showResourceDetails(d.uri);
            }
        })
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    const label = svg.append('g')
        .selectAll('text')
        .data(nodes)
        .enter().append('text')
        .text(d => d.label)
        .attr('font-size', 10)
        .attr('dx', 12)
        .attr('dy', 4);

    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        node
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);

        label
            .attr('x', d => d.x)
            .attr('y', d => d.y);
    });

    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

// Back to results
function backToResults() {
    document.getElementById('searchResults').style.display = 'block';
    document.getElementById('processDetails').style.display = 'none';
}

// Autocomplete handler
let autocompleteTimeout;
async function handleAutocomplete() {
    clearTimeout(autocompleteTimeout);

    const query = document.getElementById('searchInput').value.trim();
    const autocompleteDiv = document.getElementById('autocomplete');

    if (query.length < 2) {
        autocompleteDiv.classList.remove('show');
        return;
    }

    autocompleteTimeout = setTimeout(async () => {
        try {
            const response = await fetch(`${API_BASE}/autocomplete?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (data.suggestions && data.suggestions.length > 0) {
                autocompleteDiv.innerHTML = data.suggestions.map(s =>
                    `<div class="autocomplete-item" onclick="selectSuggestion('${escapeHtml(s)}')">${escapeHtml(s)}</div>`
                ).join('');
                autocompleteDiv.classList.add('show');
            } else {
                autocompleteDiv.classList.remove('show');
            }
        } catch (error) {
            console.error('Autocomplete error:', error);
        }
    }, 300);
}

// Select autocomplete suggestion
function selectSuggestion(suggestion) {
    document.getElementById('searchInput').value = suggestion;
    document.getElementById('autocomplete').classList.remove('show');
    performSearch();
}

// Download data
async function downloadData(format) {
    try {
        const response = await fetch(`${API_BASE}/download/${format}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_dump: true })
        });

        if (format === 'json') {
            const data = await response.json();
            downloadJSON(data, `dkg_export_${new Date().toISOString().split('T')[0]}.json`);
        } else {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `dkg_export_${new Date().toISOString().split('T')[0]}.${format}`;
            a.click();
        }
    } catch (error) {
        console.error('Download error:', error);
        alert('Download error. Please try again.');
    }
}

// Download single process
async function downloadProcess(uri, format) {
    try {
        const encodedUri = encodeURIComponent(uri);
        const response = await fetch(`${API_BASE}/download/process/${format}?uri=${encodedUri}`);

        if (format === 'json') {
            const data = await response.json();
            const processId = uri.split('/').pop();
            downloadJSON(data, `process_${processId}_${new Date().toISOString().split('T')[0]}.json`);
        } else {
            const blob = await response.blob();
            const url_obj = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url_obj;
            const processId = uri.split('/').pop();
            a.download = `process_${processId}.${format}`;
            a.click();
            window.URL.revokeObjectURL(url_obj);
        }
    } catch (error) {
        console.error('Download error:', error);
        alert('Download error. Please try again.');
    }
}

// Download JSON helper
function downloadJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
}

// Show loading
function showLoading() {
    document.getElementById('searchResults').innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
        </div>
    `;
}

// Show error
function showError(message) {
    document.getElementById('searchResults').innerHTML = `
        <div style="text-align: center; padding: 3rem; color: var(--error-color);">
            <i class="fas fa-exclamation-circle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
            <h3>${message}</h3>
        </div>
    `;
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncate(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substr(0, maxLength) + '...';
}

function getFallacyName(uri) {
    if (!uri) return 'Unknown';
    const name = uri.split('#').pop().split('/').pop();
    return name.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1').trim();
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';

    try {
        // Handle different date formats
        let date;

        // ISO format with timezone: 2025-03-10T00:00:00+00:00
        if (dateString.includes('T')) {
            date = new Date(dateString);
        }
        // Simple date: 2025-03-10
        else if (dateString.match(/^\d{4}-\d{2}-\d{2}$/)) {
            date = new Date(dateString);
        }
        // Other formats with slashes: 2023/05/12
        else if (dateString.includes('/')) {
            const parts = dateString.split(/[\s\/]/);
            date = new Date(parts[0]);
        }
        else {
            return dateString; // Return as is if can't parse
        }

        // Check if date is valid
        if (isNaN(date.getTime())) {
            return dateString;
        }

        // Format as YYYY-MM-DD
        return date.toISOString().split('T')[0];
    } catch (e) {
        return dateString;
    }
}

// Resource modal functions
async function showResourceDetails(uri) {
    const modal = document.getElementById('resourceModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');

    modalBody.innerHTML = '<p>Loading...</p>';
    modal.style.display = 'flex';

    try {
        const encodedUri = encodeURIComponent(uri);
        const response = await fetch(`${API_BASE}/resource?uri=${encodedUri}`);
        const resource = await response.json();

        if (resource.error) {
            modalBody.innerHTML = `<p style="color: var(--error-color);">Error: ${resource.error}</p>`;
            return;
        }

        // Build title
        const typeName = resource.type ? resource.type.split('#').pop().split('/').pop() : 'Resource';
        modalTitle.textContent = typeName + ' Details';

        // Build properties display
        let html = `<div class="resource-property">
            <div class="resource-property-name">URI</div>
            <div class="resource-property-value">${escapeHtml(uri)}</div>
        </div>`;

        for (const [key, value] of Object.entries(resource.properties)) {
            if (key === 'type') continue; // Already shown in title

            html += `<div class="resource-property">
                <div class="resource-property-name">${escapeHtml(key)}</div>
                <div class="resource-property-value">`;

            if (Array.isArray(value)) {
                html += '<ul>';
                for (const v of value) {
                    if (v.startsWith('http://') || v.startsWith('https://')) {
                        html += `<li><span class="resource-uri-link" onclick="showResourceDetails('${v}')">🔗 ${escapeHtml(v)}</span></li>`;
                    } else {
                        html += `<li>${escapeHtml(v)}</li>`;
                    }
                }
                html += '</ul>';
            } else {
                if (value.startsWith('http://') || value.startsWith('https://')) {
                    const linkId = 'link-' + Math.random().toString(36).substr(2, 9);
                    html += `<div>
                        <span class="resource-uri-link" onclick="showResourceDetails('${value}')">🔗 Click to view resource</span>
                        <div id="${linkId}" style="margin: 0.5rem 0 0 1rem; padding: 0.75rem; background: #f8f9fa; border-left: 3px solid var(--primary-color); border-radius: 4px; font-size: 0.9em;">
                            <em>Loading resource information...</em>
                        </div>
                    </div>`;
                    // Queue this for async loading
                    setTimeout(() => loadLinkedResource(value, linkId), 100);
                } else {
                    html += escapeHtml(value);
                }
            }

            html += `</div></div>`;
        }

        modalBody.innerHTML = html;

        if (resource.contributions && resource.contributions.length > 0) {
            const contributionsList = resource.contributions.map((c, index) => `
                <div class="resource-contribution-card" onclick="showResourceDetails('${c.uri}')" style="cursor: pointer; padding: 0.75rem; border: 1px solid #e0e0e0; border-radius: 6px; margin-bottom: 0.75rem;">
                    <p style="margin: 0; font-weight: 600;">
                        Contribution ${index + 1}
                        ${c.timestamp ? `<span style="color: var(--text-light); font-size: 0.85rem;">• ${formatDate(c.timestamp)}</span>` : ''}
                    </p>
                    <p style="margin: 0.5rem 0 0 0;">${escapeHtml(truncate(c.text || '', 240))}</p>
                    <p style="font-size: 0.8rem; color: var(--text-light); margin-top: 0.5rem;">
                        <i class="fas fa-link"></i> Click to open contribution
                    </p>
                </div>
            `).join('');

            modalBody.innerHTML += `
                <div class="resource-section">
                    <h4 style="margin-top: 1.5rem; margin-bottom: 0.75rem;"><i class="fas fa-comments"></i> Contributions (${resource.contributions.length})</h4>
                    ${contributionsList}
                </div>
            `;
        }
    } catch (error) {
        modalBody.innerHTML = `<p style="color: var(--error-color);">Error loading resource: ${error.message}</p>`;
    }
}

function closeResourceModal() {
    document.getElementById('resourceModal').style.display = 'none';
}

// Load linked resource information inline
async function loadLinkedResource(uri, elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;

    try {
        const encodedUri = encodeURIComponent(uri);
        const response = await fetch(`${API_BASE}/resource?uri=${encodedUri}`);
        const resource = await response.json();

        if (resource.error) {
            element.innerHTML = `<em style="color: var(--error-color);">Could not load resource</em>`;
            return;
        }

        const typeName = resource.type ? resource.type.split('#').pop().split('/').pop() : 'Resource';
        let html = `<strong>${typeName}</strong><br>`;

        // Show main properties
        const importantProps = ['name', 'text', 'title', 'description', 'created', 'country'];
        for (const prop of importantProps) {
            if (resource.properties[prop]) {
                const value = resource.properties[prop];
                const shortValue = typeof value === 'string' && value.length > 150 ? value.substr(0, 150) + '...' : value;
                html += `<div style="margin-top: 0.25rem;"><strong>${prop}:</strong> ${escapeHtml(shortValue)}</div>`;
            }
        }

        element.innerHTML = html;
    } catch (error) {
        element.innerHTML = `<em style="color: var(--error-color);">Error loading resource</em>`;
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('resourceModal');
    if (event.target === modal) {
        closeResourceModal();
    }
}

// Check URL parameters on page load
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const showResourceUri = urlParams.get('show_resource');

    if (showResourceUri) {
        // Show resource modal automatically
        showResourceDetails(showResourceUri);

        // Remove the parameter from URL without reload
        const newUrl = window.location.pathname;
        window.history.replaceState({}, document.title, newUrl);
    }
});
