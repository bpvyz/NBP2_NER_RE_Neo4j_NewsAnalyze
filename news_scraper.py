import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv
import time
from scraping_rules import SCRAPING_RULES
from sources import SOURCES
import os

# Configure user-agent to mimic a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_page(url):
    """Fetch a page with error handling and encoding support."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'  # Force UTF-8 for Serbian text
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"🚨 Failed to fetch {url}: {str(e)}")
        return None


def extract_article_body(article_url, site_rules):
    """Scrape the full text of an individual article."""
    html = fetch_page(article_url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')

    text_parts = []

    # Extract paragraphs from the main content container
    if "full_text_container" in site_rules:
        body = soup.select_one(site_rules["full_text_container"])
        if body:
            for unwanted in body.find_all("div"):
                unwanted.decompose()
            for unwanted in body.find_all("figure"):
                unwanted.decompose()
            if not site_rules["scrape_all_p"]: # Informer
                for p in body.find('p'):
                    paragraph = p.get_text(separator=' ', strip=True).replace("Ostavite komentar", "")
                    if paragraph and paragraph not in text_parts:
                        text_parts.append(paragraph)
            else: # Nova S
                for p in body.find_all('p'):
                    paragraph = p.get_text(separator=' ', strip=True)
                    if paragraph and paragraph not in text_parts:
                        text_parts.append(paragraph)
    return " ".join(text_parts) if text_parts else None


def scrape_news_site(base_url, site_name, bias):
    """Scrape a single news site for headlines and full article text."""
    domain = base_url.split("//")[-1].split("/")[0]
    rules = SCRAPING_RULES.get(domain, {})

    if not rules:
        print(f"⚠️ No scraping rules defined for {domain}. Skipping.")
        return []

    print(f"🔍 Scraping {site_name} ({base_url})...")
    html = fetch_page(base_url)
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    articles = []

    for item in soup.select(rules["container"], limit=5):
        try:
            link = item.select_one(rules["link"])["href"] if item.select_one(rules["link"]) else None
            title = item.select_one(rules["title"]).get_text(strip=True) if item.select_one(
                rules["title"]) else None
            print(link, title)
            if not link or not title:
                continue

            full_url = urljoin(base_url, link)
            body = extract_article_body(full_url, rules)
            print(body)
            if body:
                articles.append({
                    "source": site_name,
                    "bias": bias,
                    "title": title,
                    "url": full_url,
                    "text": body
                })
                print(f"  ✔️ Scraped: {title[:50]}...")
            time.sleep(1)  # Be polite between requests

        except Exception as e:
            print(f"❌ Error processing article: {str(e)}")
            continue

    return articles


def save_to_csv(data, filename="example_output/serbian_news_articles.csv"):
    """Save scraped data to a CSV file."""
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["source", "bias", "title", "url", "text"])
        writer.writeheader()
        writer.writerows(data)
    print(f"✅ Saved {len(data)} articles to {filename}")

if __name__ == "__main__":
    all_articles = []

    for source in SOURCES:
        articles = scrape_news_site(source["url"], source["name"], source["bias"])
        all_articles.extend(articles)
        print(f"Found {len(articles)} articles from {source['name']}")
        time.sleep(2)  # Delay between sites

    if all_articles:
        save_to_csv(all_articles)
    else:
        print("No articles were scraped. Check your selectors.")