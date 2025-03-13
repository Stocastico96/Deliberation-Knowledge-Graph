/**
 * Deliberation Knowledge Graph - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Mermaid diagrams
    if (typeof mermaid !== 'undefined') {
        mermaid.initialize({
            startOnLoad: true,
            theme: 'neutral',
            securityLevel: 'loose',
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            }
        });
    }

    // Add animation classes to elements as they scroll into view
    const fadeElements = document.querySelectorAll('.dataset-card, .ontology-category, .authors, .documentation-container, .visualization-container');
    
    const fadeInOnScroll = () => {
        fadeElements.forEach(element => {
            const elementTop = element.getBoundingClientRect().top;
            const elementBottom = element.getBoundingClientRect().bottom;
            const isVisible = (elementTop < window.innerHeight - 100) && (elementBottom > 0);
            
            if (isVisible) {
                element.classList.add('fade-in');
            }
        });
    };
    
    // Initial check on page load
    fadeInOnScroll();
    
    // Check on scroll
    window.addEventListener('scroll', fadeInOnScroll);

    // Smooth scrolling for navigation links
    document.querySelectorAll('nav a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 70,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Knowledge Graph Visualization
    const visualizationContainer = document.getElementById('knowledge-graph-visualization');
    if (visualizationContainer && typeof d3 !== 'undefined') {
        // Sample data for the knowledge graph visualization
        const graphData = {
            nodes: [
                { id: "DKG", label: "Deliberation Knowledge Graph", group: "main" },
                
                { id: "AO", label: "Argumentation Ontologies", group: "category" },
                { id: "DO", label: "Deliberation Ontologies", group: "category" },
                { id: "LO", label: "Legal Ontologies", group: "category" },
                
                { id: "AIF", label: "AIF", group: "ontology" },
                { id: "AMO", label: "Argument Ontology", group: "ontology" },
                { id: "SIOC", label: "SIOC", group: "ontology" },
                { id: "IBIS", label: "IBIS", group: "ontology" },
                
                { id: "DELIB", label: "DELIB", group: "ontology" },
                { id: "DelibO", label: "Deliberation Ontology", group: "ontology" },
                { id: "PartO", label: "Participation Ontology", group: "ontology" },
                { id: "ConsO", label: "Consensus Ontology", group: "ontology" },
                
                { id: "LKIF", label: "LKIF-Core", group: "ontology" },
                { id: "OGD", label: "OGD Ontology", group: "ontology" },
                
                { id: "DS1", label: "Decide Madrid", group: "dataset" },
                { id: "DS2", label: "DeliData", group: "dataset" },
                { id: "DS3", label: "EU Have Your Say", group: "dataset" },
                { id: "DS4", label: "Habermas Machine", group: "dataset" },
                { id: "DS5", label: "Decidim Barcelona", group: "dataset" },
                { id: "DS6", label: "US Supreme Court", group: "dataset" }
            ],
            links: [
                { source: "DKG", target: "AO", value: 3 },
                { source: "DKG", target: "DO", value: 3 },
                { source: "DKG", target: "LO", value: 3 },
                
                { source: "AO", target: "AIF", value: 2 },
                { source: "AO", target: "AMO", value: 2 },
                { source: "AO", target: "SIOC", value: 2 },
                { source: "AO", target: "IBIS", value: 2 },
                
                { source: "DO", target: "DELIB", value: 2 },
                { source: "DO", target: "DelibO", value: 2 },
                { source: "DO", target: "PartO", value: 2 },
                { source: "DO", target: "ConsO", value: 2 },
                
                { source: "LO", target: "LKIF", value: 2 },
                { source: "LO", target: "OGD", value: 2 },
                
                { source: "DS1", target: "DKG", value: 2 },
                { source: "DS2", target: "DKG", value: 2 },
                { source: "DS3", target: "DKG", value: 2 },
                { source: "DS4", target: "DKG", value: 2 },
                { source: "DS5", target: "DKG", value: 2 },
                { source: "DS6", target: "DKG", value: 2 },
                
                { source: "DS1", target: "DELIB", value: 1 },
                { source: "DS1", target: "SIOC", value: 1 },
                
                { source: "DS2", target: "AIF", value: 1 },
                { source: "DS2", target: "IBIS", value: 1 },
                
                { source: "DS3", target: "OGD", value: 1 },
                { source: "DS3", target: "LKIF", value: 1 },
                
                { source: "DS4", target: "AMO", value: 1 },
                { source: "DS4", target: "ConsO", value: 1 },
                
                { source: "DS5", target: "PartO", value: 1 },
                { source: "DS5", target: "DELIB", value: 1 },
                
                { source: "DS6", target: "LKIF", value: 1 },
                { source: "DS6", target: "AIF", value: 1 }
            ]
        };

        // Set up the force simulation
        const width = visualizationContainer.clientWidth;
        const height = 500;

        // Create SVG element
        const svg = d3.select(visualizationContainer)
            .append("svg")
            .attr("width", width)
            .attr("height", height)
            .attr("viewBox", [0, 0, width, height])
            .attr("style", "max-width: 100%; height: auto;");

        // Define color scale for node groups
        const color = d3.scaleOrdinal()
            .domain(["main", "category", "ontology", "dataset"])
            .range(["#6366f1", "#f97316", "#0ea5e9", "#10b981"]);

        // Create a tooltip div
        const tooltip = d3.select("body").append("div")
            .attr("class", "tooltip")
            .style("opacity", 0)
            .style("position", "absolute")
            .style("background-color", "white")
            .style("border", "1px solid #ddd")
            .style("border-radius", "4px")
            .style("padding", "10px")
            .style("box-shadow", "0 2px 4px rgba(0,0,0,0.1)")
            .style("pointer-events", "none")
            .style("font-size", "14px")
            .style("z-index", 1000);

        // Create the force simulation
        const simulation = d3.forceSimulation(graphData.nodes)
            .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(50));

        // Create the links
        const link = svg.append("g")
            .selectAll("line")
            .data(graphData.links)
            .join("line")
            .attr("stroke", "#999")
            .attr("stroke-opacity", 0.6)
            .attr("stroke-width", d => Math.sqrt(d.value));

        // Create the nodes
        const node = svg.append("g")
            .selectAll("g")
            .data(graphData.nodes)
            .join("g")
            .call(drag(simulation));

        // Add circles to nodes
        node.append("circle")
            .attr("r", d => d.group === "main" ? 20 : d.group === "category" ? 15 : 10)
            .attr("fill", d => color(d.group))
            .attr("stroke", "#fff")
            .attr("stroke-width", 1.5)
            .on("mouseover", function(event, d) {
                tooltip.transition()
                    .duration(200)
                    .style("opacity", .9);
                tooltip.html(`<strong>${d.label}</strong><br/>${getGroupLabel(d.group)}`)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            })
            .on("mouseout", function() {
                tooltip.transition()
                    .duration(500)
                    .style("opacity", 0);
            });

        // Add labels to nodes
        node.append("text")
            .attr("dx", 12)
            .attr("dy", ".35em")
            .text(d => d.label)
            .style("font-size", d => d.group === "main" ? "14px" : "12px")
            .style("font-weight", d => d.group === "main" || d.group === "category" ? "bold" : "normal")
            .attr("fill", d => d.group === "main" ? "#6366f1" : "#333");

        // Set up the simulation tick function
        simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node
                .attr("transform", d => `translate(${d.x},${d.y})`);
        });

        // Helper function to get group label
        function getGroupLabel(group) {
            switch(group) {
                case "main": return "Knowledge Graph";
                case "category": return "Ontology Category";
                case "ontology": return "Ontology";
                case "dataset": return "Dataset";
                default: return "";
            }
        }

        // Drag functions
        function drag(simulation) {
            function dragstarted(event) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }
            
            function dragged(event) {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            }
            
            function dragended(event) {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }
            
            return d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended);
        }

        // Add zoom capabilities
        const zoom = d3.zoom()
            .scaleExtent([0.5, 3])
            .on("zoom", (event) => {
                svg.selectAll("g").attr("transform", event.transform);
            });

        svg.call(zoom);

        // Add visualization controls
        const controls = document.querySelector('.visualization-controls');
        if (controls) {
            // Reset zoom button
            const resetButton = document.getElementById('reset-zoom');
            if (resetButton) {
                resetButton.addEventListener('click', function() {
                    svg.transition().duration(750).call(
                        zoom.transform,
                        d3.zoomIdentity,
                        d3.zoomTransform(svg.node()).invert([width / 2, height / 2])
                    );
                });
            }

            // Filter buttons
            const filterButtons = document.querySelectorAll('.filter-button');
            filterButtons.forEach(button => {
                button.addEventListener('click', function() {
                    const filter = this.getAttribute('data-filter');
                    
                    // Toggle active class
                    filterButtons.forEach(btn => btn.classList.remove('active'));
                    this.classList.add('active');
                    
                    // Filter nodes and links
                    if (filter === 'all') {
                        node.style("display", "block");
                        link.style("display", "block");
                    } else {
                        node.style("display", d => {
                            if (d.group === filter || d.group === "main") {
                                return "block";
                            }
                            
                            // For category nodes, check if they're connected to the filter
                            if (d.group === "category") {
                                const hasConnection = graphData.links.some(link => 
                                    (link.source.id === d.id && link.target.group === filter) || 
                                    (link.target.id === d.id && link.source.group === filter)
                                );
                                return hasConnection ? "block" : "none";
                            }
                            
                            return "none";
                        });
                        
                        link.style("display", d => {
                            const sourceGroup = typeof d.source === 'object' ? d.source.group : graphData.nodes.find(n => n.id === d.source).group;
                            const targetGroup = typeof d.target === 'object' ? d.target.group : graphData.nodes.find(n => n.id === d.target).group;
                            
                            return (sourceGroup === filter || targetGroup === filter || 
                                   sourceGroup === "main" || targetGroup === "main") ? "block" : "none";
                        });
                    }
                });
            });
        }
    }

    // Convert Markdown content to HTML
    function renderMarkdown(markdownText) {
        if (!markdownText) return '';
        
        // Process headings
        let html = markdownText
            .replace(/^# (.*)/gm, '<h1>$1</h1>')
            .replace(/^## (.*)/gm, '<h2>$1</h2>')
            .replace(/^### (.*)/gm, '<h3>$1</h3>')
            .replace(/^#### (.*)/gm, '<h4>$1</h4>')
            .replace(/^##### (.*)/gm, '<h5>$1</h5>')
            .replace(/^###### (.*)/gm, '<h6>$1</h6>');
        
        // Process emphasis and strong
        html = html
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/__(.*?)__/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/_(.*?)_/g, '<em>$1</em>');
        
        // Process links
        html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
        
        // Process lists
        html = html.replace(/^\s*[\-\*] (.*)/gm, '<li>$1</li>');
        html = html.replace(/(<\/li>\s*<li>)/g, '$1');
        html = html.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
        
        // Process numbered lists
        html = html.replace(/^\s*\d+\. (.*)/gm, '<li>$1</li>');
        html = html.replace(/(<\/li>\s*<li>)/g, '$1');
        html = html.replace(/(<li>.*?<\/li>)/gs, '<ol>$1</ol>');
        
        // Process code blocks
        html = html.replace(/```([^`]*?)```/gs, '<pre><code>$1</code></pre>');
        
        // Process inline code
        html = html.replace(/`([^`]*?)`/g, '<code>$1</code>');
        
        // Process blockquotes
        html = html.replace(/^> (.*)/gm, '<blockquote>$1</blockquote>');
        
        // Process horizontal rules
        html = html.replace(/^---$/gm, '<hr>');
        
        // Process paragraphs (must be last)
        html = html.replace(/^([^<].*)/gm, '<p>$1</p>');
        html = html.replace(/<p>\s*<\/p>/g, '');
        
        return html;
    }

    // Load and display documentation
    function loadDocumentation(url, targetElementId) {
        const targetElement = document.getElementById(targetElementId);
        if (!targetElement) return;
        
        // Show loading indicator
        targetElement.innerHTML = '<div class="loading">Loading documentation...</div>';
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.text();
            })
            .then(markdown => {
                const html = renderMarkdown(markdown);
                targetElement.innerHTML = html;
                
                // Add syntax highlighting if Prism is available
                if (typeof Prism !== 'undefined') {
                    Prism.highlightAllUnder(targetElement);
                }
            })
            .catch(error => {
                console.error('Error loading documentation:', error);
                targetElement.innerHTML = `
                    <div class="error">
                        <h3>Error Loading Documentation</h3>
                        <p>There was a problem loading the documentation. Please try again later.</p>
                        <p>Error details: ${error.message}</p>
                    </div>
                `;
            });
    }

    // Initialize dataset filtering
    function initializeDatasetFiltering() {
        const filterButtons = document.querySelectorAll('.dataset-filter');
        const datasetCards = document.querySelectorAll('.dataset-card');
        
        if (filterButtons.length === 0 || datasetCards.length === 0) return;
        
        filterButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Remove active class from all buttons
                filterButtons.forEach(btn => btn.classList.remove('active'));
                
                // Add active class to clicked button
                this.classList.add('active');
                
                const filter = this.getAttribute('data-filter');
                
                // Show/hide dataset cards based on filter
                datasetCards.forEach(card => {
                    if (filter === 'all') {
                        card.style.display = 'block';
                    } else {
                        const category = card.getAttribute('data-category');
                        card.style.display = category === filter ? 'block' : 'none';
                    }
                });
            });
        });
    }

    // Initialize ontology browser
    function initializeOntologyBrowser() {
        const ontologyTabs = document.querySelectorAll('.ontology-tab');
        const ontologyContents = document.querySelectorAll('.ontology-content');
        
        if (ontologyTabs.length === 0 || ontologyContents.length === 0) return;
        
        ontologyTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                // Remove active class from all tabs
                ontologyTabs.forEach(t => t.classList.remove('active'));
                
                // Add active class to clicked tab
                this.classList.add('active');
                
                // Hide all content
                ontologyContents.forEach(content => {
                    content.style.display = 'none';
                });
                
                // Show selected content
                const target = this.getAttribute('data-target');
                document.getElementById(target).style.display = 'block';
            });
        });
    }

    // Initialize dark mode toggle
    function initializeDarkModeToggle() {
        const darkModeToggle = document.getElementById('dark-mode-toggle');
        if (!darkModeToggle) return;
        
        // Check for saved user preference
        const darkMode = localStorage.getItem('darkMode') === 'enabled';
        
        // Set initial state
        if (darkMode) {
            document.body.classList.add('dark-mode');
            darkModeToggle.checked = true;
        }
        
        // Toggle dark mode
        darkModeToggle.addEventListener('change', function() {
            if (this.checked) {
                document.body.classList.add('dark-mode');
                localStorage.setItem('darkMode', 'enabled');
            } else {
                document.body.classList.remove('dark-mode');
                localStorage.setItem('darkMode', null);
            }
        });
    }

    // Initialize search functionality
    function initializeSearch() {
        const searchInput = document.getElementById('search-input');
        const searchResults = document.getElementById('search-results');
        
        if (!searchInput || !searchResults) return;
        
        searchInput.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            
            if (query.length < 2) {
                searchResults.innerHTML = '';
                searchResults.style.display = 'none';
                return;
            }
            
            // Perform search (simplified example)
            const results = performSearch(query);
            
            // Display results
            if (results.length === 0) {
                searchResults.innerHTML = '<p>No results found</p>';
            } else {
                const resultsList = results.map(result => 
                    `<li><a href="${result.url}">${result.title}</a><p>${result.excerpt}</p></li>`
                ).join('');
                
                searchResults.innerHTML = `<ul>${resultsList}</ul>`;
            }
            
            searchResults.style.display = 'block';
        });
        
        // Simple search function (would be replaced with actual search implementation)
        function performSearch(query) {
            // This is just a placeholder
            const searchableContent = [
                { title: 'Deliberation Knowledge Graph', url: '#about', content: 'The Deliberation Knowledge Graph project aims to connect various deliberative process datasets and ontologies.' },
                { title: 'Decide Madrid Dataset', url: '#datasets', content: 'Citizen proposals and comments from Madrid\'s participatory democracy platform.' },
                { title: 'DeliData Dataset', url: '#datasets', content: 'A dataset for deliberation in multi-party problem solving.' },
                { title: 'Argumentation Ontologies', url: '#ontologies', content: 'Ontologies for representing argument structure and relations.' }
            ];
            
            return searchableContent
                .filter(item => 
                    item.title.toLowerCase().includes(query) || 
                    item.content.toLowerCase().includes(query)
                )
                .map(item => ({
                    title: item.title,
                    url: item.url,
                    excerpt: item.content.substring(0, 100) + '...'
                }));
        }
    }

    // Initialize all components
    initializeDatasetFiltering();
    initializeOntologyBrowser();
    initializeDarkModeToggle();
    initializeSearch();

    // Log that the script has loaded successfully
    console.log('Deliberation Knowledge Graph - JavaScript initialized');
});
