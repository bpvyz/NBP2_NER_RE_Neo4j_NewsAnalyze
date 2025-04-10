import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import time
import os
import re
from scraping_rules import SCRAPING_RULES
from sources import SOURCES
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_page(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"🚨 Failed to fetch {url}: {str(e)}")
        return None

def clean_paragraphs(body, scrape_all_p):
    text_parts = []
    for tag in body.find_all(["div", "figure"]):
        tag.decompose()

    paragraphs = body.find_all("p") if scrape_all_p else body.find("p")
    if not paragraphs:
        return []

    if not isinstance(paragraphs, list):  # Single paragraph
        paragraphs = [paragraphs]

    for p in paragraphs:
        text = p.get_text(separator=' ', strip=True)
        text = re.sub(r'Ostavite komentar|Autor:.*', '', text)
        if text and text not in text_parts:
            text_parts.append(text)

    return text_parts


def extract_article_body(article_url, rules):
    html = fetch_page(article_url)
    if not html:
        return None
    soup = BeautifulSoup(html, 'html.parser')
    container = soup.select_one(rules.get("full_text_container", ""))
    if container:
        paragraphs = clean_paragraphs(container, rules.get("scrape_all_p", False))
        return " ".join(paragraphs) if paragraphs else None
    return None

def scrape_news_site(base_url, site_name, bias):
    domain = base_url.split("//")[-1].split("/")[0]
    sections = SCRAPING_RULES.get(domain, {})

    if not sections:
        print(f"⚠️ No scraping sections defined for {domain}. Skipping.")
        return []

    print(f"🔍 Scraping {site_name} ({base_url})...")
    html = fetch_page(base_url)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    articles = []
    tasks = []

    def process_article(item, rules):
        try:
            link_tag = item.select_one(rules["link"])
            title_tag = item.select_one(rules["title"])
            if not link_tag or not title_tag:
                return None
            link = link_tag["href"]
            title = title_tag.get_text(strip=True)
            full_url = urljoin(base_url, link)
            body = extract_article_body(full_url, rules)
            if body:
                print(f"  ✔️ Scraped: {title[:50]}...")
                return {
                    "source": site_name,
                    "bias": bias,
                    "title": title,
                    "url": full_url,
                    "text": body
                }
        except Exception as e:
            print(f"❌ Error processing article: {str(e)}")
            return None

    with ThreadPoolExecutor(max_workers=10) as executor:
        for section in sections:
            rules = sections.get(section, {})
            if site_name == "Informer" and rules.get("subsections"):
                subsection = soup.find_all(attrs={"data-category": "#e6272a"})
                if not subsection:
                    continue
                for item in subsection[-1].select(rules["container"]):
                    tasks.append(executor.submit(process_article, item, rules))
            elif site_name == "Informer":
                for main_news in soup.select(rules["main_container"]):
                    for item in main_news.select(rules["container"]):
                        tasks.append(executor.submit(process_article, item, rules))
            else:
                for item in soup.select(rules["container"]):
                    tasks.append(executor.submit(process_article, item, rules))

        for task in tasks:
            result = task.result()
            if result:
                articles.append(result)

    return articles

def save_to_json(data, filename="example_output/serbian_news_articles.json"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved {len(data)} articles to {filename}")

if __name__ == "__main__":
    start_time = time.time()
    all_articles = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(scrape_news_site, source["url"], source["name"], source["bias"]): source
            for source in SOURCES
        }

        for future in as_completed(futures):
            source = futures[future]
            try:
                articles = future.result()
                all_articles.extend(articles)
                print(f"✅ Found {len(articles)} articles from {source['name']}")
            except Exception as e:
                print(f"❌ Error scraping {source['name']}: {e}")

    if all_articles:
        save_to_json(all_articles)
    else:
        print("No articles were scraped. Check your selectors.")

    elapsed_time = time.time() - start_time
    print(f"⏱ Total scraping time: {elapsed_time:.2f} seconds")
