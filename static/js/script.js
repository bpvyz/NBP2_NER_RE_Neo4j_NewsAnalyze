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
    graphContainer: document.getElementById('graphContainer'),
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

// ===== Graph Functions =====
function renderGraph(graphData) {
    if (currentState.graphInstance) {
        currentState.graphInstance.destroy();
    }

    elements.graphContainer.innerHTML = '';

    if (!graphData.nodes.length) {
        elements.graphContainer.innerHTML = '<p>No graph data available for this article</p>';
        return;
    }

    try {
        const config = {
            containerId: "graphContainer",
            nodes: graphData.nodes,
            relationships: graphData.edges,
            options: {
                physics: { stabilization: { iterations: 100 } },
                nodes: { shape: 'dot', size: 16, font: { size: 12, face: 'Tahoma' } },
                edges: { width: 0.5, color: { inherit: 'both' }, smooth: { type: 'continuous' } },
                interaction: { tooltipDelay: 200, hideEdgesOnDrag: true }
            }
        };

        currentState.graphInstance = new NeoVis.default(config);
        currentState.graphInstance.render();
    } catch (error) {
        console.error("Error rendering graph:", error);
        elements.graphContainer.innerHTML = `<p class="error">Error rendering graph: ${error.message}</p>`;
    }
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
    elements.closeBtn.addEventListener('click', closeArticle);

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeArticle();
    });

    elements.articleItems.forEach(item => {
        item.addEventListener('click', () => openArticle(item.dataset.articleId));
    });

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

    elements.biasGroupHeaders.forEach(header => header.addEventListener('click', () => toggleGroup(header)));
    elements.sourceGroupHeaders.forEach(header => header.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleGroup(header);
    }));
}

function resizeGraphContainer() {
    if (currentState.graphInstance) {
        requestAnimationFrame(() => currentState.graphInstance.redraw());
    }
}

// ===== Initialization =====
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    console.log("Article Browser initialized");

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