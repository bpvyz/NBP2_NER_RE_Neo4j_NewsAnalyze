SCRAPING_RULES = {
    "informer.rs": {
        "section1": {
            "subsections": False,
            "main_container": "div.new-lead-box-news",
            "container": "article.news-item",  # Update based on actual HTML inspection
            "link": "a[href]",
            "title": "h2.news-item-title",
            "full_text_container": "div.single-news-content",  # Container for article body
            "scrape_all_p": False
        },
        "section2": {
            "subsections": True,
            "container": "article.news-item",  # Update based on actual HTML inspection
            "link": "a[href]",
            "title": "h2.news-item-title",
            "full_text_container": "div.single-news-content",  # Container for article body
            "scrape_all_p": False
        }
    },
    "nova.rs": {
        "section1": {
            "container": "div.uc-post-title",
            "link": "a[href]",
            "title": "a",
            "full_text_container": "div.post",  # Container for article body
            "scrape_all_p": True
        }
    },
    "n1info.rs": {
        "section1": {
            "container": "article.post",
            "link": "a[href]",
            "title": "a.uc-block-post-grid-title-link",
            "full_text_container": "div.entry-content",  # Container for article body
            "scrape_all_p": True
        }
    },
    "pink.rs": {
        "section1": {
            "container": "div.featured-news",
            "link": "a[href]",
            "title": "div.featured-title",
            "full_text_container": "div.news-single-content",
            "scrape_all_p": True
        },
        "section2": {
            "container": "div.news-double",
            "link": "a[href]",
            "title": "div.item-title > h2",
            "full_text_container": "div.news-single-content",
            "scrape_all_p": True
        },
        "section3": {
            "container": "div.news-item",
            "link": "a[href]",
            "title": "div.item-title > h2",
            "full_text_container": "div.news-single-content",
            "scrape_all_p": True
        }
    }
}