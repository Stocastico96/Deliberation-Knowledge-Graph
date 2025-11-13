// Arguments Page JavaScript
const API_BASE = '/api';

let allArguments = [];
let filteredArguments = [];
let allPlatforms = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadArgumentsData();
    loadPlatforms();
});

// Load platforms for filter
async function loadPlatforms() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();

        if (data.platforms && Array.isArray(data.platforms)) {
            allPlatforms = data.platforms.filter(p => p && typeof p === 'string').sort();

            const platformFilter = document.getElementById('platformFilterArgs');
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

// Load arguments data - for now show sample/placeholder
async function loadArgumentsData() {
    try {
        showLoading();

        // For now, create sample arguments from contributions
        // In future, this would come from argument mining analysis
        const response = await fetch(`${API_BASE}/stats`);
        const data = await response.json();

        // Generate placeholder data
        allArguments = generateSampleArguments(data);
        filteredArguments = allArguments;

        updateStatistics();
        renderArgumentNetwork();
        renderQualityChart();
        renderArgumentsList();
    } catch (error) {
        console.error('Error loading arguments:', error);
        showPlaceholder();
    }
}

// Generate sample arguments (placeholder until argument mining is implemented)
function generateSampleArguments(stats) {
    const sampleArguments = [];
    const topics = [
        'Climate Change Policy',
        'Digital Rights',
        'Healthcare Reform',
        'Education System',
        'Economic Policy',
        'Immigration',
        'Data Protection',
        'Environmental Protection'
    ];

    const argumentTypes = ['pro', 'con', 'neutral'];
    const platforms = stats.platforms || ['European Parliament', 'Decidim Barcelona'];

    // Generate 50 sample arguments
    for (let i = 0; i < 50; i++) {
        const topic = topics[Math.floor(Math.random() * topics.length)];
        const type = argumentTypes[Math.floor(Math.random() * argumentTypes.length)];
        const platform = platforms[Math.floor(Math.random() * platforms.length)];

        sampleArguments.push({
            id: `arg_${i}`,
            text: `This is a sample ${type} argument about ${topic}. In a real scenario, this would contain actual argumentative content extracted from deliberation contributions through argument mining techniques.`,
            type: type,
            topic: topic,
            platform: platform,
            strength: Math.random(),
            fallacies: Math.random() > 0.7 ? ['Ad Hominem', 'Straw Man'][Math.floor(Math.random() * 2)] : null,
            supports: Math.random() > 0.5 ? `arg_${Math.floor(Math.random() * i)}` : null,
            opposes: Math.random() > 0.7 ? `arg_${Math.floor(Math.random() * i)}` : null
        });
    }

    return sampleArguments;
}

// Update statistics
function updateStatistics() {
    const totalArgs = filteredArguments.length;
    const proArgs = filteredArguments.filter(a => a.type === 'pro').length;
    const conArgs = filteredArguments.filter(a => a.type === 'con').length;
    const fallacies = filteredArguments.filter(a => a.fallacies).length;

    document.getElementById('totalArguments').textContent = totalArgs;
    document.getElementById('proArguments').textContent = proArgs;
    document.getElementById('conArguments').textContent = conArgs;
    document.getElementById('fallaciesCount').textContent = fallacies;
}

// Render argument network using D3
function renderArgumentNetwork() {
    const container = document.getElementById('argumentNetwork');
    container.innerHTML = '';

    if (!filteredArguments || filteredArguments.length === 0) {
        container.innerHTML = '<p style="text-align: center; padding: 3rem; color: #6b7280;">No arguments to display</p>';
        return;
    }

    // Prepare network data (sample first 30 arguments for readability)
    const sampleArgs = filteredArguments.slice(0, 30);

    const nodes = sampleArgs.map(arg => ({
        id: arg.id,
        label: arg.topic,
        type: arg.type,
        strength: arg.strength
    }));

    const links = [];
    sampleArgs.forEach(arg => {
        if (arg.supports && sampleArgs.find(a => a.id === arg.supports)) {
            links.push({
                source: arg.id,
                target: arg.supports,
                type: 'supports'
            });
        }
        if (arg.opposes && sampleArgs.find(a => a.id === arg.opposes)) {
            links.push({
                source: arg.id,
                target: arg.opposes,
                type: 'opposes'
            });
        }
    });

    const width = container.offsetWidth;
    const height = 600;

    const svg = d3.select('#argumentNetwork')
        .append('svg')
        .attr('width', width)
        .attr('height', height);

    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-200))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(30));

    const link = svg.append('g')
        .selectAll('line')
        .data(links)
        .enter().append('line')
        .attr('stroke', d => d.type === 'supports' ? '#10b981' : '#ef4444')
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', d => d.type === 'opposes' ? '5,5' : '0');

    const node = svg.append('g')
        .selectAll('circle')
        .data(nodes)
        .enter().append('circle')
        .attr('r', d => 8 + d.strength * 12)
        .attr('fill', d => {
            if (d.type === 'pro') return '#10b981';
            if (d.type === 'con') return '#ef4444';
            return '#6b7280';
        })
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .style('cursor', 'pointer')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    const label = svg.append('g')
        .selectAll('text')
        .data(nodes)
        .enter().append('text')
        .text(d => d.label.length > 20 ? d.label.substr(0, 20) + '...' : d.label)
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

// Render quality metrics chart
function renderQualityChart() {
    if (!filteredArguments || filteredArguments.length === 0) {
        document.getElementById('qualityChart').innerHTML = '<p style="text-align: center; color: #6b7280;">No data to display</p>';
        return;
    }

    // Calculate quality metrics per platform
    const platformMetrics = {};

    filteredArguments.forEach(arg => {
        if (!platformMetrics[arg.platform]) {
            platformMetrics[arg.platform] = {
                total: 0,
                avgStrength: 0,
                withFallacies: 0,
                diversity: 0
            };
        }

        platformMetrics[arg.platform].total++;
        platformMetrics[arg.platform].avgStrength += arg.strength;
        if (arg.fallacies) platformMetrics[arg.platform].withFallacies++;
    });

    const platforms = Object.keys(platformMetrics);
    const avgStrengths = platforms.map(p =>
        ((platformMetrics[p].avgStrength / platformMetrics[p].total) * 100).toFixed(1)
    );
    const fallacyRates = platforms.map(p =>
        ((platformMetrics[p].withFallacies / platformMetrics[p].total) * 100).toFixed(1)
    );

    const trace1 = {
        x: platforms,
        y: avgStrengths,
        name: 'Argument Strength',
        type: 'bar',
        marker: { color: '#2563eb' }
    };

    const trace2 = {
        x: platforms,
        y: fallacyRates,
        name: 'Fallacy Rate',
        type: 'bar',
        marker: { color: '#ef4444' }
    };

    const data = [trace1, trace2];

    const layout = {
        title: 'Deliberative Quality by Platform',
        barmode: 'group',
        xaxis: { title: 'Platform' },
        yaxis: { title: 'Percentage (%)' },
        plot_bgcolor: '#fafafa',
        paper_bgcolor: 'white'
    };

    Plotly.newPlot('qualityChart', data, layout, { responsive: true, displaylogo: false });
}

// Render arguments list
function renderArgumentsList() {
    const container = document.getElementById('argumentsList');

    if (!filteredArguments || filteredArguments.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: #6b7280;">
                <i class="fas fa-inbox" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                <h3>No arguments found</h3>
                <p>Try adjusting your filters</p>
            </div>
        `;
        return;
    }

    const html = filteredArguments.map(arg => `
        <div class="argument-card">
            <div class="argument-header">
                <div>
                    <span class="argument-type ${arg.type}">${arg.type.toUpperCase()}</span>
                    <h3 style="margin: 0.5rem 0; color: #1f2937;">${escapeHtml(arg.topic)}</h3>
                </div>
                ${arg.fallacies ? `<span class="fallacy-badge"><i class="fas fa-exclamation-triangle"></i> ${escapeHtml(arg.fallacies)}</span>` : ''}
            </div>

            <div class="argument-text">${escapeHtml(arg.text)}</div>

            <div class="argument-meta">
                <span><i class="fas fa-globe"></i> ${escapeHtml(arg.platform)}</span>
                <span><i class="fas fa-chart-line"></i> Strength: ${(arg.strength * 100).toFixed(0)}%</span>
                ${arg.supports ? '<span><i class="fas fa-arrow-up"></i> Supports other argument</span>' : ''}
                ${arg.opposes ? '<span><i class="fas fa-arrow-down"></i> Opposes other argument</span>' : ''}
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

// Apply filters
function applyFilters() {
    const platformFilter = document.getElementById('platformFilterArgs').value;
    const typeFilter = document.getElementById('argumentTypeFilter').value;
    const searchQuery = document.getElementById('argumentSearch').value.toLowerCase().trim();

    filteredArguments = allArguments.filter(arg => {
        if (platformFilter && arg.platform !== platformFilter) return false;
        if (typeFilter && arg.type !== typeFilter) return false;
        if (searchQuery) {
            const text = arg.text.toLowerCase();
            const topic = arg.topic.toLowerCase();
            if (!text.includes(searchQuery) && !topic.includes(searchQuery)) return false;
        }
        return true;
    });

    updateStatistics();
    renderArgumentNetwork();
    renderQualityChart();
    renderArgumentsList();
}

// Show loading state
function showLoading() {
    document.getElementById('argumentsList').innerHTML = `
        <div style="text-align: center; padding: 3rem;">
            <div class="spinner" style="margin: 0 auto 1rem auto;"></div>
            <p style="color: #6b7280;">Loading arguments...</p>
        </div>
    `;
}

// Show placeholder
function showPlaceholder() {
    document.getElementById('argStats').innerHTML = `
        <div class="stat-box" style="grid-column: 1 / -1;">
            <div class="stat-box-label">
                <i class="fas fa-info-circle"></i> Argument analysis results not yet available
            </div>
        </div>
    `;

    document.getElementById('argumentNetwork').innerHTML = `
        <div style="text-align: center; padding: 3rem; color: #6b7280;">
            <i class="fas fa-comments" style="font-size: 4rem; margin-bottom: 1.5rem; opacity: 0.3;"></i>
            <h3>Argument Mining In Progress</h3>
            <p>We're analyzing the deliberations to extract and structure arguments.</p>
            <p style="margin-top: 1rem;"><strong>Note:</strong> Currently showing sample data for demonstration purposes.</p>
        </div>
    `;
}

// Utility function
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
