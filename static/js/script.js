// ===== Constants =====
const COLLAPSED_CLASS = 'collapsed';
const VISIBLE_CLASS = 'visible';
const ACTIVE_CLASS = 'active';

// ===== Global State =====
let currentState = {
    openArticleId: null,
    articlesCache: {},
    graphCache: {},
    graphInstance: null
};

// ===== DOM Elements =====
const elements = {
    appContainer: document.getElementById('appContainer'),
    mainContent: document.getElementById('mainContent'),
    articleWindow: document.getElementById('articleWindow'),
    articleWindowTitle: document.getElementById('articleWindowTitle'),
    articleWindowSource: document.getElementById('articleSourceValue'),
    articleWindowContent: document.getElementById('articleWindowContent'),
    closeBtn: document.getElementById('closeBtn'),
    graphContainer: document.getElementById('sigma-container'),
    articleItems: document.querySelectorAll('.article-item'),
    biasGroupHeaders: document.querySelectorAll('.bias-group-header'),
    sourceGroupHeaders: document.querySelectorAll('.source-group-header'),
    biasGroups: document.querySelectorAll('.bias-group-content'),
    sourceGroups: document.querySelectorAll('.source-group-content'),
    collapseIcons: document.querySelectorAll('.collapse-icon')
};

// ===== Utility Functions =====
function debounce(func, wait) {
    let timeout;
    return function () {
        const context = this, args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

function toggleGroup(header) {
    const targetId = header.getAttribute('data-target');
    const content = document.getElementById(targetId);
    const icon = header.querySelector('.collapse-icon');

    const isCollapsed = content.classList.contains(COLLAPSED_CLASS);

    if (isCollapsed) {
        content.classList.remove(COLLAPSED_CLASS);
        const height = content.scrollHeight;
        content.style.maxHeight = height + 'px';
        setTimeout(() => content.style.maxHeight = 'none', 300);
        icon.textContent = '-';
    } else {
        const height = content.scrollHeight;
        content.style.maxHeight = height + 'px';
        void content.offsetHeight;
        content.classList.add(COLLAPSED_CLASS);
        content.style.maxHeight = '0';
        icon.textContent = '+';
    }
}

// ===== Article Functions =====
async function openArticle(articleId) {
    if (currentState.openArticleId === articleId) return;

    try {
        elements.articleWindowContent.innerHTML = '<div class="loading-spinner"></div><p>Loading article...</p>';
        showArticleWindow(articleId);

        const [articleData, graphData] = await Promise.all([
            fetchArticleById(articleId),
            fetchGraphData(articleId)
        ]);

        renderArticle(articleData);
        renderGraph(graphData);

        currentState.openArticleId = articleId;
        updateActiveArticleItem(articleId);
    } catch (error) {
        console.error("Error opening article:", error);
        elements.articleWindowContent.innerHTML = `<p class="error">Error loading article: ${error.message}</p>`;
    }
}

async function fetchArticleById(articleId) {
    if (currentState.articlesCache[articleId]) {
        return currentState.articlesCache[articleId];
    }

    const response = await fetch(`/api/article/${articleId}`);
    if (!response.ok) throw new Error('Article not found');

    const data = await response.json();
    currentState.articlesCache[articleId] = data;
    return data;
}

async function fetchGraphData(articleId) {
    if (currentState.graphCache[articleId]) return currentState.graphCache[articleId];

    const response = await fetch(`/api/graph/${articleId}`);
    if (!response.ok) throw new Error('Graph data not available');

    const data = await response.json();
    currentState.graphCache[articleId] = data;
    return data;
}

function renderArticle(articleData) {
    elements.articleWindowTitle.textContent = articleData.title;
    elements.articleWindowSource.textContent = articleData.source;
    elements.articleWindowSource.href = articleData.url;

    elements.articleWindowContent.innerHTML = `
        <div class="article-meta">
            <span class="article-date">${articleData.date}</span>
            <span class="article-read-time">${articleData.readTime}</span>
        </div>
        <div class="article-text">${articleData.content}</div>
    `;
}

function updateActiveArticleItem(articleId) {
    elements.articleItems.forEach(item => {
        item.classList.toggle(ACTIVE_CLASS, item.dataset.articleId === articleId);
    });
}

// ===== Graph Functions with Sigma.js =====
function renderGraph(graphData) {
    // Clean up previous graph instance if it exists
    if (currentState.graphInstance) {
        currentState.graphInstance.kill();
        currentState.graphInstance = null;
    }

    // Hide loading elements
    document.querySelector('.loading-spinner').style.display = 'none';
    document.querySelector('.loading-text').style.display = 'none';

    if (!graphData.nodes || !graphData.nodes.length) {
        document.querySelector('.loading-text').textContent = 'No graph data available for this article';
        document.querySelector('.loading-text').style.display = 'block';
        return;
    }


    elements.graphContainer.innerHTML = '';

    if (!graphData.nodes || !graphData.nodes.length) {
        elements.graphContainer.innerHTML = '<p>No graph data available for this article</p>';
        return;
    }

    try {
        // Format data for Sigma.js
        const sigmaGraph = {
            nodes: [],
            edges: []
        };

        // Process nodes
        graphData.nodes.forEach(node => {
            sigmaGraph.nodes.push({
                id: node.id.toString(),
                label: node.label || `Node ${node.id}`,
                x: Math.random(), // Random initial position
                y: Math.random(),
                size: node.group === 'article' ? 8 : 5,
                color: getNodeColor(node.group || 'default'),
                originalData: node.properties || {}
            });
        });

        // Process edges - ensure each edge has a label property
        graphData.edges.forEach((edge, i) => {
            sigmaGraph.edges.push({
                id: `e${i}`,
                source: edge.from.toString(),
                target: edge.to.toString(),
                label: edge.label || '', // Ensure label exists even if empty
                color: '#ccc',
                size: 1,
                type: 'arrow'
            });
        });

        // Initialize Sigma.js with proper settings for edge labels
        currentState.graphInstance = new sigma({
            graph: sigmaGraph,
            container: 'sigma-container',
            renderer: {
                container: document.getElementById('sigma-container'),
                type: sigma.renderers.canvas
            },
            settings: {
                defaultNodeColor: '#3388AA',
                defaultEdgeColor: '#ccc',
                edgeColor: 'default',
                labelThreshold: 7,
                minNodeSize: 3,
                maxNodeSize: 10,
                minEdgeSize: 1,
                maxEdgeSize: 2,
                enableEdgeHovering: true,
                edgeHoverColor: 'edge',
                defaultEdgeHoverColor: '#393939',
                edgeHoverSizeRatio: 2,

                // Edge label specific settings
                drawEdgeLabels: true, // This must be true
                edgeLabelSize: 'proportional',
                edgeLabelSizeRatio: 0.5,
                edgeLabelColor: {
                    color: '#393939' // Black edge labels
                },
                defaultEdgeLabelColor: '#393939',
                edgeLabelActiveColor: '#393939',

                // Other settings
                drawEdges: true,
                drawNodes: true,
                labelSize: 'proportional',
                labelSizeRatio: 1,
                minArrowSize: 5
            }
        });

        // Register edge label renderers
        sigma.canvas.edges.labels.def = sigma.canvas.edges.labels.def;
        sigma.canvas.edges.labels.curve = sigma.canvas.edges.labels.curve;

        // Initialize dragNodes plugin
        const dragListener = sigma.plugins.dragNodes(currentState.graphInstance, currentState.graphInstance.renderers[0]);

        // Create a simpler tooltip system using DOM
        createTooltipSystem(currentState.graphInstance);

        // Apply ForceAtlas2 layout algorithm
        currentState.graphInstance.startForceAtlas2({
            worker: true,
            barnesHutOptimize: true,
            slowDown: 10,
            gravity: 1,
            scalingRatio: 10
        });

        // Stop layout algorithm after a few seconds for better performance
        setTimeout(() => {
            if (currentState.graphInstance) {
                currentState.graphInstance.stopForceAtlas2();
            }
        }, 3000);

    } catch (error) {
        console.error("Error rendering graph:", error);
        elements.graphContainer.innerHTML = `<p class="error">Error rendering graph: ${error.message}</p>`;
    }

    if (currentState.graphInstance) {
        // Bring fullscreen button to front
        const fullscreenBtn = document.getElementById('fullscreenBtn');
        if (fullscreenBtn) {
            fullscreenBtn.style.zIndex = '1000';
        }

        // Handle graph refresh on fullscreen change
        window.addEventListener('resize', debounce(() => {
            if (currentState.graphInstance) {
                currentState.graphInstance.refresh();
            }
        }, 100));
    }
}

function createTooltipSystem(sigmaInstance) {
    // Create tooltip element if it doesn't exist
    let tooltip = document.getElementById('sigma-tooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'sigma-tooltip';
        tooltip.className = 'sigma-tooltip';
        tooltip.style.display = 'none';
        tooltip.style.position = 'absolute';
        tooltip.style.padding = '10px';
        tooltip.style.backgroundColor = 'white';
        tooltip.style.borderRadius = '4px';
        tooltip.style.boxShadow = '0 2px 6px rgba(0,0,0,0.3)';
        tooltip.style.zIndex = '999';
        document.body.appendChild(tooltip);
    }

    // Node hover event
    sigmaInstance.bind('hovers', function(e) {
        if (!e.data.enter.nodes || e.data.enter.nodes.length === 0) {
            tooltip.style.display = 'none';
            return;
        }

        const node = e.data.enter.nodes[0];
        const nodeData = sigmaInstance.graph.nodes(node);

        // Create tooltip content
        let content = `<strong>${nodeData.label}</strong><br>`;

        // Add additional properties from originalData if available
        if (nodeData.originalData) {
            for (const key in nodeData.originalData) {
                if (key !== 'title' && key !== 'label' && key !== 'name') {
                    content += `${key}: ${nodeData.originalData[key]}<br>`;
                }
            }
        }

        tooltip.innerHTML = content;
        tooltip.style.display = 'block';

        // Position tooltip near the mouse
        const renderer = sigmaInstance.renderers[0];
        const x = renderer.getDisplayX(nodeData.x);
        const y = renderer.getDisplayY(nodeData.y);

        tooltip.style.left = (x + 15) + 'px';
        tooltip.style.top = (y + 15) + 'px';
    });

    // Stage double-click event to reset view
    sigmaInstance.bind('doubleClickStage', function() {
        sigma.misc.animation.camera(
            sigmaInstance.camera,
            { x: 0.5, y: 0.5, ratio: 1 },
            { duration: 300 }
        );
    });
}

function getNodeColor(group) {
    const colorMap = {
        'article': '#ff0000',
        'osoba': '#1f77b4',          // Person (Blue)
        'organizacija': '#ff7f0e',   // Organization (Orange)
        'lokacija': '#2ca02c',       // Location (Green)
        'vreme': '#d62728',          // Time (Red)
        'aktivnost': '#9467bd',      // Activity (Purple)
        'aktivnostdogadjaj': '#8c564b', // Activity Event (Brown)
        'dogadjaj': '#e377c2',       // Event (Pink)
        'grupa': '#7f7f7f',          // Group (Grey)
        'vozilo': '#17becf',         // Vehicle (Cyan)
        'proizvod': '#bcbd22',       // Product (Yellow-green)
        'umetnicko_delo': '#ffb6c1', // Artwork (Light Pink)
        'dokument': '#7f7f7f',       // Document (Dark Grey)
        'biljka': '#2ca02c',         // Plant (Green)
        'broj': '#8c564b',           // Number (Brown)
        'hrana': '#32a852',          // Food (Dark Green)
        'pice': '#9c27b0',           // Drink (Purple)
        'institucija': '#20b2aa',    // Institution (Light Sea Green)
        'simbol': '#ff6347',         // Symbol (Tomato)
        'hranapice': '#ff4500',      // Food & Drink (Orange-red)
        'zivotinja': '#f39c12',      // Animal (Yellow)
        'tehnologija': '#34495e',    // Technology (Charcoal)
        'entity': '#999999',         // Default Entity (Gray)
        'default': '#999999'         // Default color for unknown types
    };

    return colorMap[group.toLowerCase()] || colorMap.default;
}

// ===== Window Management =====
function showArticleWindow(articleId) {
    if (window.innerWidth >= 768) {
        const articleWidth = elements.articleWindow.offsetWidth;
        const sidebarWidth = document.querySelector('.article-list').offsetWidth;
        const availableWidth = window.innerWidth - articleWidth - sidebarWidth;

        elements.mainContent.style.transition = 'all var(--transition-normal) ease-out';
        elements.mainContent.style.width = `${availableWidth}px`;
        elements.mainContent.style.marginRight = `${articleWidth}px`;
    } else {
        elements.mainContent.style.transform = 'scale(0.85)';
        elements.mainContent.style.transformOrigin = 'left center';
        elements.mainContent.style.filter = 'brightness(0.8)';
    }

    elements.articleWindow.classList.add(VISIBLE_CLASS);
    elements.appContainer.classList.add('article-visible');
}

function closeArticle() {
    if (!currentState.openArticleId) return;

    elements.mainContent.style.transition = 'all var(--transition-normal) ease-out';
    elements.mainContent.style.width = '';
    elements.mainContent.style.marginRight = '';
    elements.mainContent.style.transform = '';
    elements.mainContent.style.filter = '';

    elements.articleWindow.classList.remove(VISIBLE_CLASS);
    elements.appContainer.classList.remove('article-visible');
    currentState.openArticleId = null;
    updateActiveArticleItem(null);
}

// ===== Event Listeners =====
function setupEventListeners() {
    // Close button
    elements.closeBtn.addEventListener('click', closeArticle);

    // Escape key to close article
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeArticle();
    });

    // Article item click
    elements.articleItems.forEach(item => {
        item.addEventListener('click', () => openArticle(item.dataset.articleId));
    });

    // Window resize
    window.addEventListener('resize', debounce(() => {
        if (currentState.openArticleId) {
            if (window.innerWidth >= 768) {
                elements.mainContent.style.filter = '';
            } else {
                elements.mainContent.style.filter = 'brightness(0.8)';
            }
            resizeGraphContainer();
        }
    }, 100));

    // Group toggle
    elements.biasGroupHeaders.forEach(header => header.addEventListener('click', () => toggleGroup(header)));
    elements.sourceGroupHeaders.forEach(header => header.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleGroup(header);
    }));


    // Fullscreen button
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', toggleFullscreen);
    }

    // Fullscreen change events
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);
}

function resizeGraphContainer() {
    if (currentState.graphInstance) {
        currentState.graphInstance.refresh();
    }
}

// Fullscreen button functionality
const fullscreenBtn = document.getElementById('fullscreenBtn');
if (fullscreenBtn) {
    fullscreenBtn.addEventListener('click', toggleFullscreen);
}

function toggleFullscreen() {
    const container = document.querySelector('.graph-container');

    if (!document.fullscreenElement) {
        // Enter fullscreen
        if (container.requestFullscreen) {
            container.requestFullscreen().catch(err => {
                console.error(`Error attempting to enable fullscreen: ${err.message}`);
            });
        } else if (container.webkitRequestFullscreen) {
            container.webkitRequestFullscreen();
        } else if (container.msRequestFullscreen) {
            container.msRequestFullscreen();
        }
    } else {
        // Exit fullscreen
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
    }
}

function handleFullscreenChange() {
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    if (!fullscreenBtn) return;

    if (document.fullscreenElement) {
        // Update to "exit fullscreen" icon
        fullscreenBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="24" height="24">
                <path fill="currentColor" d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/>
            </svg>`;
    } else {
        // Update to "enter fullscreen" icon
        fullscreenBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="24" height="24">
                <path fill="currentColor" d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
            </svg>`;
    }

    // Refresh graph when fullscreen changes
    if (currentState.graphInstance) {
        setTimeout(() => {
            currentState.graphInstance.refresh();
        }, 300);
    }
}

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    console.log("Article Browser initialized");

    // Initialize groups as collapsed
    elements.biasGroups.forEach(group => {
        group.classList.add(COLLAPSED_CLASS);
        group.style.maxHeight = '0';
    });

    elements.sourceGroups.forEach(group => {
        group.classList.add(COLLAPSED_CLASS);
        group.style.maxHeight = '0';
    });

    elements.collapseIcons.forEach(icon => {
        icon.textContent = '+';
    });
});