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
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Učitaj vesti iz JSON fajla
with open("data/serbian_news_articles.json", "r", encoding="utf-8") as f:
    news_data = json.load(f)

async def extract_entities_and_relations(text):
    prompt = f"""
    Izvuci entitete (Osoba, Organizacija, Lokacija, Vreme, Aktivnost, AktivnostDogađaj, Događaj, Grupa, Vozilo, Proizvod, Umetničko delo, Dokument, Biljka, Broj, Hrana, Piće, Institucija, Simbol, HranaPiće, Životinja, Tehnologija) i deskriptivne relacije (događaji, akcije, interakcije) iz sledećeg teksta vesti, 
    koristeći odgovarajuće tipove za Neo4j. Relacije treba da budu konkretne, jasno definisane između entiteta, dok entiteti treba da budu označeni sa odgovarajućim labelama 
    (npr. Osoba, Organizacija, Lokacija, Vreme, Aktivnost/Događaj, Vozilo, Proizvod, Umetničko delo, Dokument, Hrana/Piće, Životinja, Biljka, Tehnologija, itd.).

    Tekst vesti:
    {text}

    Odgovor u sledećem formatu:
    Entiteti: [entitet1:label, entitet2:label, entitet3:label]
    Relacije: [entitet1 -[:relation]-> entitet2, entitet3 -[:relation]-> entitet4]

    Bez uvodnih fraza, samo entiteti i relacije, tačno u ovom formatu.
    Za svaki entitet formirati odgovarajuću relaciju.
    Za svaki entitet koji učestvuje u relaciji formirati odgovarajući label.
    Svi entiteti i sve relacije moraju biti isključivo na srpskom jeziku. Nije dozvoljeno koristiti engleske, hrvatske ili strane nazive.
    Na primer, 'European Union' treba biti 'Evropska unija', 'Germany' treba biti 'Nemačka', 'Croatian police' treba biti 'hrvatska policija'.
    Nije dozvoljeno koristiti generičku labelu "Entity". Svaki entitet mora imati konkretnu i tačnu labelu iz gore navedene liste.
    """

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
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
        total=len(subset)
    )

    results = [r for r in results if r]

    with open("data/entities_and_relations.json", "w", encoding="utf-8") as outfile:
        json.dump(results, outfile, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(process_articles())
    elapsed_time = time.time() - start_time
    print(Fore.YELLOW + f"\n⏱ Total analyzing time: {elapsed_time:.2f} seconds")
