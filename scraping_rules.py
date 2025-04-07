SCRAPING_RULES = {
    "informer.rs": {
        "container": "article.news-item",  # Update based on actual HTML inspection
        "link": "a[href]",
        "title": "h2.news-item-title",
        "full_text_container": "div.single-news-content",  # Container for article body
        "scrape_all_p": False
    },
    "nova.rs": {
        "container": "div.uc-post-title",
        "link": "a[href]",
        "title": "a",
        "full_text_container": "div.post",  # Container for article body
        "scrape_all_p": True
    },
    # TODO
    "n1info.rs": {
        "container": "div.article-item",
        "link": "a.article-title",
        "title": "h3",
        "full_text_container": "div.entry-content"  # Container for article body
    },
    "pink.rs": {
        "container": "div.news-container",  # Placeholder (Pink TV often uses JS)
        "link": "a.news-link",
        "title": "h2.news-title",
        "full_text_container": "div.entry-content"
    }
}