// Topics Page JavaScript
const API_BASE = '/api';

let allTopics = [];
let filteredTopics = [];
let allPlatforms = [];

// Pagination variables
let currentPage = 1;
const TOPICS_PER_PAGE = 10;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadTopicsData();
    loadPlatforms();
});

// Load platforms for filter
async function loadPlatforms() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();

        if (data.platforms && Array.isArray(data.platforms)) {
            allPlatforms = data.platforms.filter(p => p && typeof p === 'string').sort();

            const platformFilter = document.getElementById('platformFilterTopics');
            platformFilter.innerHTML = '<option value="">All Platforms</option>';

            allPlatforms.forEach(platform => {
                const option = document.createElement('option');
                option.value = platform;
                option.textContent = platform;
                platformFilter.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading platforms:', error);
    }
}

// Load topics data from API
async function loadTopicsData() {
    try {
        showLoading();

        // Check if topic modeling results exist
        const response = await fetch(`${API_BASE}/topics`);

        if (response.status === 404) {
            showPlaceholder();
            return;
        }

        const data = await response.json();

        if (!data.topics || data.topics.length === 0) {
            showPlaceholder();
            return;
        }

        allTopics = data.topics;
        filteredTopics = allTopics;

        updateStatistics();
        renderTopicsChart();
        renderTopicsList();
    } catch (error) {
        console.error('Error loading topics:', error);
        showPlaceholder();
    }
}

// Update statistics
function updateStatistics() {
    const totalTopics = filteredTopics.length;
    const totalContributions = filteredTopics.reduce((sum, t) => sum + (t.contributions_count || 0), 0);
    const avgContribPerTopic = totalTopics > 0 ? (totalContributions / totalTopics).toFixed(1) : 0;

    document.getElementById('totalTopics').textContent = totalTopics;
    document.getElementById('totalContributions').textContent = totalContributions.toLocaleString();
    document.getElementById('avgContribPerTopic').textContent = avgContribPerTopic;
}

// Render topics chart using Plotly
function renderTopicsChart() {
    if (!filteredTopics || filteredTopics.length === 0) {
        document.getElementById('topicsChart').innerHTML = '<p style="text-align: center; color: #6b7280;">No topics to display</p>';
        return;
    }

    // Sort by contribution count and take top 20
    const topTopics = [...filteredTopics]
        .sort((a, b) => (b.contributions_count || 0) - (a.contributions_count || 0))
        .slice(0, 20);

    const labels = topTopics.map((t, i) => t.name || `Topic ${i + 1}`);
    const values = topTopics.map(t => t.contributions_count || 0);
    const colors = topTopics.map(() => `rgba(74, 157, 60, ${0.6 + Math.random() * 0.4})`);

    const data = [{
        type: 'bar',
        x: values,
        y: labels,
        orientation: 'h',
        marker: {
            color: colors,
            line: {
                color: '#2d6b2d',
                width: 1.5
            }
        },
        text: values.map(v => v.toLocaleString()),
        textposition: 'auto',
        hovertemplate: '<b>%{y}</b><br>Contributions: %{x}<extra></extra>'
    }];

    const layout = {
        title: {
            text: 'Top 20 Topics by Contribution Count',
            font: { size: 18, color: '#1f2937' }
        },
        xaxis: {
            title: 'Number of Contributions',
            titlefont: { size: 14, color: '#4b5563' },
            tickfont: { size: 12, color: '#6b7280' }
        },
        yaxis: {
            titlefont: { size: 14, color: '#4b5563' },
            tickfont: { size: 12, color: '#6b7280' },
            automargin: true
        },
        margin: { l: 200, r: 50, t: 80, b: 80 },
        plot_bgcolor: '#fafafa',
        paper_bgcolor: 'white',
        hoverlabel: {
            bgcolor: 'white',
            bordercolor: '#4a9d3c',
            font: { size: 13 }
        }
    };

    const config = {
        responsive: true,
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
    };

    Plotly.newPlot('topicsChart', data, layout, config);
}

// Render topics list with pagination
function renderTopicsList() {
    const container = document.getElementById('topicsList');

    if (!filteredTopics || filteredTopics.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: #6b7280;">
                <i class="fas fa-inbox" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                <h3>No topics found</h3>
                <p>Try adjusting your filters</p>
            </div>
        `;
        return;
    }

    // Sort topics by contribution count descending
    const sortedTopics = [...filteredTopics].sort((a, b) => (b.contributions_count || 0) - (a.contributions_count || 0));

    // Pagination
    const totalPages = Math.ceil(sortedTopics.length / TOPICS_PER_PAGE);
    const startIndex = (currentPage - 1) * TOPICS_PER_PAGE;
    const endIndex = startIndex + TOPICS_PER_PAGE;
    const pageTopics = sortedTopics.slice(startIndex, endIndex);

    const html = pageTopics.map((topic, index) => {
        const globalIndex = startIndex + index; // For showTopicDetails
        const keywords = topic.keywords || [];
        const platforms = topic.platforms || [];
        const topicLabel = topic.name || `Topic ${globalIndex + 1}`;

        return `
            <div class="topic-card" onclick="showTopicDetails(${globalIndex})">
                <div class="topic-header">
                    <div class="topic-title">
                        <i class="fas fa-lightbulb"></i> ${escapeHtml(topicLabel)}
                    </div>
                    <div class="topic-count">
                        ${(topic.contributions_count || 0).toLocaleString()} contributions
                    </div>
                </div>

                ${topic.description ? `
                    <p style="color: #4b5563; margin: 1rem 0;">${escapeHtml(topic.description)}</p>
                ` : ''}

                ${keywords.length > 0 ? `
                    <div class="topic-keywords">
                        <strong style="margin-right: 0.5rem;">Keywords:</strong>
                        ${keywords.slice(0, 8).map(kw => `
                            <span class="keyword-badge">${escapeHtml(kw)}</span>
                        `).join('')}
                        ${keywords.length > 8 ? `<span class="keyword-badge">+${keywords.length - 8} more</span>` : ''}
                    </div>
                ` : ''}

                ${platforms.length > 0 ? `
                    <div class="topic-platforms">
                        <strong style="margin-right: 0.5rem;"><i class="fas fa-globe"></i>
                            ${topic.dominant_platform ? 'Dominant:' : 'Platforms:'}
                        </strong>
                        ${topic.dominant_platform ? `
                            <span class="platform-badge" style="background: #4a9d3c; color: white; font-weight: 500;">
                                ${escapeHtml(topic.dominant_platform)}
                                ${topic.platform_distribution && topic.platform_distribution[topic.dominant_platform] ?
                                    ` (${topic.platform_distribution[topic.dominant_platform]}%)` : ''}
                            </span>
                            ${platforms.length > 1 ? `<span style="color: #6b7280; font-size: 0.9rem;">+${platforms.length - 1} more</span>` : ''}
                        ` : platforms.map(p => `
                            <span class="platform-badge">${escapeHtml(p)}</span>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');

    // Pagination controls
    const paginationHtml = `
        <div style="display: flex; justify-content: center; align-items: center; gap: 1rem; margin-top: 2rem; padding: 2rem;">
            <button onclick="changePage(${currentPage - 1})"
                    ${currentPage === 1 ? 'disabled' : ''}
                    style="padding: 0.5rem 1rem; background: #4a9d3c; color: white; border: none; border-radius: 4px; cursor: ${currentPage === 1 ? 'not-allowed' : 'pointer'}; opacity: ${currentPage === 1 ? '0.5' : '1'};">
                <i class="fas fa-chevron-left"></i> Previous
            </button>
            <span style="color: #4b5563;">
                Page ${currentPage} of ${totalPages} (${sortedTopics.length} topics)
            </span>
            <button onclick="changePage(${currentPage + 1})"
                    ${currentPage === totalPages ? 'disabled' : ''}
                    style="padding: 0.5rem 1rem; background: #4a9d3c; color: white; border: none; border-radius: 4px; cursor: ${currentPage === totalPages ? 'not-allowed' : 'pointer'}; opacity: ${currentPage === totalPages ? '0.5' : '1'};">
                Next <i class="fas fa-chevron-right"></i>
            </button>
        </div>
    `;

    container.innerHTML = html + paginationHtml;
}

// Change page
function changePage(newPage) {
    const sortedTopics = [...filteredTopics].sort((a, b) => (b.contributions_count || 0) - (a.contributions_count || 0));
    const totalPages = Math.ceil(sortedTopics.length / TOPICS_PER_PAGE);

    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        renderTopicsList();
        // Scroll to top of topics list
        document.getElementById('topicsList').scrollIntoView({ behavior: 'smooth' });
    }
}

// Apply filters
function applyFilters() {
    const platformFilter = document.getElementById('platformFilterTopics').value;
    const minContribs = parseInt(document.getElementById('minContributions').value) || 0;
    const searchQuery = document.getElementById('topicSearch').value.toLowerCase().trim();

    filteredTopics = allTopics.filter(topic => {
        // Platform filter
        if (platformFilter && (!topic.platforms || !topic.platforms.includes(platformFilter))) {
            return false;
        }

        // Min contributions filter
        if ((topic.contributions_count || 0) < minContribs) {
            return false;
        }

        // Search filter
        if (searchQuery) {
            const label = (topic.name || '').toLowerCase();
            const description = (topic.description || '').toLowerCase();
            const keywords = (topic.keywords || []).map(k => k.toLowerCase()).join(' ');

            if (!label.includes(searchQuery) && !description.includes(searchQuery) && !keywords.includes(searchQuery)) {
                return false;
            }
        }

        return true;
    });

    // Reset to first page when filters change
    currentPage = 1;

    updateStatistics();
    renderTopicsChart();
    renderTopicsList();
}

// Show topic details modal
function showTopicDetails(index) {
    const topic = filteredTopics[index];
    if (!topic) return;

    const modal = document.getElementById('topicModal');
    const content = document.getElementById('topicModalContent');

    const keywords = topic.keywords || [];
    const platforms = topic.platforms || [];
    const contributions = topic.sample_contributions || [];

    content.innerHTML = `
        <h2><i class="fas fa-lightbulb"></i> ${escapeHtml(topic.name || 'Topic Details')}</h2>

        ${topic.description ? `
            <p style="font-size: 1.1rem; color: #4b5563; margin: 1rem 0;">${escapeHtml(topic.description)}</p>
        ` : ''}

        <div style="background: #f3f4f6; padding: 1rem; border-radius: 8px; margin: 1.5rem 0;">
            <strong>Total Contributions:</strong> ${(topic.contributions_count || 0).toLocaleString()}<br>
            ${topic.coherence_score ? `<strong>Coherence Score:</strong> ${(topic.coherence_score * 100).toFixed(1)}%<br>` : ''}
            ${topic.diversity_score ? `<strong>Diversity Score:</strong> ${(topic.diversity_score * 100).toFixed(1)}%` : ''}
        </div>

        ${keywords.length > 0 ? `
            <h3 style="margin-top: 2rem;"><i class="fas fa-tags"></i> Keywords</h3>
            <div class="topic-keywords">
                ${keywords.map(kw => `<span class="keyword-badge">${escapeHtml(kw)}</span>`).join('')}
            </div>
        ` : ''}

        ${platforms.length > 0 ? `
            <h3 style="margin-top: 2rem;"><i class="fas fa-globe"></i> Platform Distribution</h3>
            ${topic.platform_distribution && Object.keys(topic.platform_distribution).length > 0 ? `
                <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 1px solid #e5e7eb; margin-top: 1rem;">
                    ${Object.entries(topic.platform_distribution)
                        .sort((a, b) => b[1] - a[1])
                        .map(([platform, percentage]) => `
                            <div style="margin-bottom: 1rem;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                                    <span style="font-weight: 500; color: #374151;">
                                        ${escapeHtml(platform)}
                                        ${topic.dominant_platform === platform ? '<span style="color: #4a9d3c; font-size: 0.8rem;"> ★ Dominant</span>' : ''}
                                    </span>
                                    <span style="color: #6b7280;">${percentage}%</span>
                                </div>
                                <div style="width: 100%; background: #e5e7eb; height: 8px; border-radius: 4px; overflow: hidden;">
                                    <div style="width: ${percentage}%; background: ${topic.dominant_platform === platform ? '#4a9d3c' : '#9ca3af'}; height: 100%; transition: width 0.3s ease;"></div>
                                </div>
                            </div>
                        `).join('')}
                </div>
            ` : `
                <div class="topic-platforms">
                    ${platforms.map(p => `<span class="platform-badge">${escapeHtml(p)}</span>`).join('')}
                </div>
            `}
        ` : ''}

        ${contributions.length > 0 ? `
            <h3 style="margin-top: 2rem;"><i class="fas fa-comments"></i> Sample Contributions</h3>
            <div class="contributions-sample">
                ${contributions.map((c, idx) => {
                    // Handle both string and object formats
                    const text = typeof c === 'string' ? c : (c.text || '');
                    const preview = text.length > 500 ? text.substring(0, 500) + '...' : text;
                    return `
                        <div class="contribution-item">
                            <p style="color: #6b7280; font-size: 0.9rem; margin-bottom: 0.5rem;">
                                <strong>Sample ${idx + 1}</strong>
                            </p>
                            <p style="margin-top: 0.5rem; white-space: pre-wrap;">${escapeHtml(preview)}</p>
                        </div>
                    `;
                }).join('')}
            </div>
        ` : ''}
    `;

    modal.style.display = 'block';
}

// Close topic modal
function closeTopicModal() {
    document.getElementById('topicModal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('topicModal');
    if (event.target === modal) {
        closeTopicModal();
    }
}

// Show loading state
function showLoading() {
    document.getElementById('topicsList').innerHTML = `
        <div style="text-align: center; padding: 3rem;">
            <div class="spinner" style="margin: 0 auto 1rem auto;"></div>
            <p style="color: #6b7280;">Loading topics...</p>
        </div>
    `;
}

// Show placeholder when no topic modeling data
function showPlaceholder() {
    document.getElementById('topicStats').innerHTML = `
        <div class="stat-box" style="grid-column: 1 / -1;">
            <div class="stat-box-label">
                <i class="fas fa-info-circle"></i> Topic modeling results not yet available
            </div>
        </div>
    `;

    document.getElementById('topicsChart').innerHTML = `
        <div style="text-align: center; padding: 3rem; color: #6b7280;">
            <i class="fas fa-brain" style="font-size: 4rem; margin-bottom: 1.5rem; opacity: 0.3;"></i>
            <h3>Topic Modeling In Progress</h3>
            <p>We're analyzing the deliberations to identify topics and patterns.</p>
            <p style="margin-top: 1rem;"><strong>Check back soon!</strong></p>
        </div>
    `;

    document.getElementById('topicsList').innerHTML = '';
}

// Utility function
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
