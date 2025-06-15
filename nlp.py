import json
import os
import re
import asyncio
from openai import AsyncOpenAI
import time
from tqdm.asyncio import tqdm_asyncio
from dotenv import load_dotenv
from colorama import Fore, init

load_dotenv()

init(autoreset=True)

# Inicijalizacija asinhronog klijenta
client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENAI_API_KEY"))

# Učitaj vesti iz JSON fajla
with open("data/serbian_news_articles.json", "r", encoding="utf-8") as f:
    news_data = json.load(f)

async def extract_entities_and_relations(text):
    prompt = f"""
Izvuci entitete (Osoba, Organizacija, Lokacija, Vreme, Aktivnost, AktivnostDogađaj, Događaj, Grupa, Vozilo, Proizvod, Umetničko delo, Dokument, Biljka, Broj, Hrana, Piće, Institucija, Simbol, HranaPiće, Životinja, Tehnologija) i deskriptivne relacije (događaji, akcije, interakcije) iz sledećeg teksta vesti, koristeći odgovarajuće tipove za Neo4j.

Relacije moraju biti konkretne, jasno definisane između entiteta. Svaki entitet mora biti označen jednom od dozvoljenih labela.

Tekst vesti:
{text}

Odgovor u tačno sledećem formatu:
Entiteti: [entitet1:label, entitet2:label, entitet3:label]
Relacije: [entitet1 -[:relacija]-> entitet2, entitet3 -[:relacija]-> entitet4]

**Pravila:**

1. **Svi entiteti navedeni u listi `Entiteti:` moraju učestvovati u najmanje jednoj relaciji.**
2. **Ne sme biti entiteta u listi `Entiteti:` koji se ne pojavljuju ni u jednoj relaciji.**
3. **Ne sme biti entiteta u `Relacije:` koji nisu prethodno navedeni u `Entiteti:`.**
4. Svi entiteti moraju imati tačnu labelu iz dozvoljene liste (npr. Osoba, Lokacija, Aktivnost itd.). Nije dozvoljena generička oznaka poput "Entity".
5. Svi nazivi entiteta i relacija moraju biti isključivo na srpskom jeziku. Strani izrazi nisu dozvoljeni. Primer: "Germany" → "Nemačka", "European Union" → "Evropska unija".
6. Nisu dozvoljeni opisni izrazi kao što su "grupa ljudi", "neki događaj", već samo eksplicitno navedeni entiteti iz teksta.
7. Sve relacije moraju biti precizno imenovane i povezivati samo entitete iz liste `Entiteti:`.

Napomena: Odgovor treba da sadrži **samo listu entiteta i relacija**, bez dodatnih objašnjenja, komentara ili uvodnih rečenica.
"""

    response = await client.chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content.strip()

async def process_article(article):
    text = article.get("text", "")
    if not text:
        return None

    try:
        entities_and_relations = await extract_entities_and_relations(text)

        entities_match = re.search(r'Entiteti: \[(.*?)\]', entities_and_relations)
        relations_match = re.search(r'Relacije: \[(.*]?)\]', entities_and_relations)

        entities = entities_match.group(1) if entities_match else ""
        relations = relations_match.group(1) if relations_match else ""

        return {
            "article_source": article.get("source", ""),
            "article_bias": article.get("bias", ""),
            "article_title": article.get("title", ""),
            "article_url": article.get("url", ""),
            "article_text": text,
            "entities_and_relations": entities_and_relations,
            "entities": entities,
            "entity_count": len(entities.split(", ")),
            "relations": relations,
            "relations_count": len(relations.split(", "))
        }

    except Exception as e:
        print(f"Greška za članak '{article.get('title', '')}': {e}")
        return None

async def process_articles():

    subset = news_data

    results = await tqdm_asyncio.gather(
        *(process_article(article) for article in subset),
        desc="🔍 Obrada vesti",
        total=len(subset),
        colour='blue',
        leave=False,
        unit="article",
        unit_scale=True,
        smoothing=0.1,
        miniters=1,
        bar_format="{l_bar}{bar}| {n}/{total} [{elapsed}<{remaining}, {rate_fmt}]",
    )

    print(f"\r{Fore.GREEN}✔ All {len(results)} articles analyzed successfully{' ' * 20}")

    results = [r for r in results if r]

    with open("data/entities_and_relations.json", "w", encoding="utf-8") as outfile:
        json.dump(results, outfile, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(process_articles())
    elapsed_time = time.time() - start_time
    print(Fore.YELLOW + f"\n⏱ Total analyzing time: {elapsed_time:.2f} seconds")
