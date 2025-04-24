import json
import os
import re
import asyncio
import aiohttp
from tqdm.asyncio import tqdm
from colorama import Fore, init
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

init(autoreset=True)

# Load configuration files
with open('sources.json', 'r', encoding='utf-8') as f:
    SOURCES = json.load(f)

with open('scraping_rules.json', 'r', encoding='utf-8') as f:
    SCRAPING_RULES = json.load(f)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


async def fetch_page(session, url):
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            return await response.text(encoding='utf-8')
    except Exception as e:
        print(Fore.RED + f"🚨 Failed to fetch {url}: {str(e)}")
        return None


def clean_paragraphs(body, scrape_all_p):
    text_parts = []
    for tag in body.find_all(["div", "figure"]):
        tag.decompose()

    paragraphs = body.find_all("p") if scrape_all_p else body.find("p")
    if not paragraphs:
        return []

    if not isinstance(paragraphs, list):
        paragraphs = [paragraphs]

    for p in paragraphs:
        text = p.get_text(separator=' ', strip=True)
        text = re.sub(r'Ostavite komentar|Autor:.*', '', text)
        if text and text not in text_parts:
            text_parts.append(text)

    return text_parts


async def extract_article_body(session, article_url, rules):
    html = await fetch_page(session, article_url)
    if not html:
        return None

    soup = BeautifulSoup(html, 'html.parser')
    container = soup.select_one(rules.get("full_text_container", ""))
    if container:
        paragraphs = clean_paragraphs(container, rules.get("scrape_all_p", False))
        return " ".join(paragraphs) if paragraphs else None
    return None


def is_politics_url(url):
    politics_keywords = ['/politika/', '/politics/', '/vesti/', '/news/']
    return any(kw in url.lower() for kw in politics_keywords)


async def process_article(session, item, rules, base_url, site_name, bias, article_pbar):
    try:
        link_tag = item.select_one(rules["link"])
        title_tag = item.select_one(rules["title"])
        if not link_tag or not title_tag:
            return None

        link = link_tag["href"]
        if not is_politics_url(link):
            return None

        title = title_tag.get_text(strip=True)
        full_url = urljoin(base_url, link)
        body = await extract_article_body(session, full_url, rules)

        if body:
            article_pbar.set_postfix_str(f"📰 {title[:30]}...", refresh=True)
            article_pbar.update(1)
            return {
                "source": site_name,
                "bias": bias,
                "title": title,
                "url": full_url,
                "text": body
            }
    except Exception as e:
        print(Fore.RED + f"❌ Error processing article: {str(e)}")
        return None

async def scrape_site(session, source, position):
    base_url = source["url"]
    site_name = source["name"]
    bias = source["bias"]
    domain = base_url.split("//")[-1].split("/")[0]
    sections = SCRAPING_RULES.get(domain, {})

    if not sections:
        tqdm.write(f"{Fore.YELLOW}⚠️ {site_name[:15]:<15} | No scraping rules")
        return []

    html = await fetch_page(session, base_url)
    if not html:
        tqdm.write(f"{Fore.RED}⚠️ {site_name[:15]:<15} | Failed to fetch")
        return []

    soup = BeautifulSoup(html, 'html.parser')
    article_items = []

    for section in sections:
        rules = sections.get(section, {})
        if site_name == "Informer" and rules.get("subsections"):
            subsection = soup.find_all(attrs={"data-category": "#e6272a"})
            if subsection:
                article_items.extend(subsection[-1].select(rules["container"]))
        elif site_name == "Informer":
            for main_news in soup.select(rules["main_container"]):
                article_items.extend(main_news.select(rules["container"]))
        else:
            article_items.extend(soup.select(rules["container"]))

    article_items = [item for item in article_items
                     if is_politics_url(item.select_one(rules["link"])["href"])]

    # Lokalni progress bar za ovaj sajt
    article_pbar = tqdm(
        total=len(article_items),
        desc=f"{site_name[:15]:<15}",
        bar_format="{l_bar}{bar}| {n}/{total} [{elapsed}<{remaining}, {rate_fmt}]",
        colour='blue',
        leave=False,
        unit="article",
        unit_scale=True,
        miniters=1,
        position=position
    )

    results = []
    semaphore = asyncio.Semaphore(5)

    async def process_with_semaphore(item):
        async with semaphore:
            result = await process_article(session, item, rules, base_url, site_name, bias, article_pbar)
            return result

    tasks = [process_with_semaphore(item) for item in article_items]
    results = await asyncio.gather(*tasks)

    article_pbar.close()

    successful_articles = len([r for r in results if r is not None])
    tqdm.write(f"{Fore.GREEN}✔ {site_name[:15]:<15} | {successful_articles} articles saved")

    return [result for result in results if result]


async def save_results(results):
    all_articles = [article for sublist in results for article in sublist]

    if not all_articles:
        print(Fore.RED + "No articles were scraped")
        return

    os.makedirs("data", exist_ok=True)
    with open("data/serbian_news_articles.json", "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    print(Fore.GREEN + f"\n✅ Total {len(all_articles)} articles saved to data/serbian_news_articles.json")


async def main():
    start_time = time.time()
    print(Fore.CYAN + "🚀 Starting news scraping...\n")

    async with aiohttp.ClientSession() as session:
        tasks = []
        for idx, source in enumerate(SOURCES):
            tasks.append(scrape_site(session, source, idx))  # pozicija po indeksu

        results = await asyncio.gather(*tasks)

        await save_results(results)

    elapsed_time = time.time() - start_time
    print(Fore.YELLOW + f"\n⏱ Completed in {elapsed_time:.2f} seconds\n")


if __name__ == "__main__":
    asyncio.run(main())