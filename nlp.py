import os
import re
import json
import time
import asyncio
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm_asyncio
from colorama import Fore, init

# Inicijalizacija okruženja
load_dotenv()
init(autoreset=True)

# Inicijalizacija asinhronog OpenAI klijenta
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Konstantna putanja do podataka
DATA_PATH = "data/serbian_news_articles.json"
OUTPUT_PATH = "data/entities_and_relations.json"
AI_MODEL = "google/gemini-2.0-flash-001"

# Učitaj vesti
def load_articles(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_prompt(title, text: str) -> str:
    return f"""
Izvuci entitete (Osoba, Organizacija, Lokacija, Vreme, Aktivnost, AktivnostDogađaj, Događaj, Grupa, Vozilo, Proizvod, Umetničko delo, Dokument, Biljka, Broj, Hrana, Piće, Institucija, Simbol, HranaPiće, Životinja, Tehnologija) 
i deskriptivne relacije (događaji, akcije, interakcije) iz sledećeg teksta vesti, koristeći odgovarajuće tipove za Neo4j.

Relacije moraju biti konkretne, jasno definisane između entiteta. Svaki entitet mora biti označen jednom od dozvoljenih labela.

**Zatim dodatno:**

1. Sažmi najvažnije proverljive informacije iz teksta.  
   Zatim za svaku proceni njenu verodostojnost koristeći sledeće kriterijume:
   - **tačno** — u skladu sa poznatim činjenicama ili jasno potkrepljeno izvorima u tekstu,
   - **verovatno tačno** — deluje tačno i logično na osnovu informacija u tekstu, ali bez dodatnih dokaza,
   - **sumnjivo** — neobično, nejasno, bez izvora ili sa mogućim manipulativnim jezikom,
   - **nepotkrepljeno** — tvrdnja bez ikakvih naznaka dokaza ili konteksta.

   Ako je moguće, daj **kratak dodatni kontekst** koji uključuje:
   - istorijski, pravni, društveni ili institucionalni okvir,
   - poznate činjenice u javnosti (npr. poznate presude, zakoni, prethodni slučajevi, izjave relevantnih institucija).

2. Opiši **ton** teksta — uzimajući u obzir rečnik, stil pisanja i emocije koje prenosi (neutralan, informativan, pristrasan, senzacionalistički, emotivan, manipulativan, pozitivan, negativan)

Tekst vesti:
{title}

{text}

Odgovor u tačno sledećem formatu:
Entiteti: [entitet1:label, entitet2:label, entitet3:label]
Relacije: [entitet1 -[:relacija]-> entitet2, entitet3 -[:relacija]-> entitet4]
FactCheck: 
- Tvrdnja 1: "<iz teksta>"
  Ocena: tačno / verovatno tačno / sumnjivo / nepotkrepljeno
  Kontekst: <kratko objašnjenje ili referenca na poznate činjenice>

- Tvrdnja 2: "..."
  ...

Ton: <kratka analiza tona>
"""

async def extract_entities_and_relations(title, text: str) -> str:

    response = await client.chat.completions.create(
        model=AI_MODEL,
        messages=[{"role": "user", "content": build_prompt(title, text)}],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()

def extract_matches(text: str) -> tuple[str, str]:
    entities_match = re.search(r'Entiteti: \[(.*?)\]', text)
    relations_match = re.search(r'Relacije: \[(.*]?)\]', text)

    entities = entities_match.group(1).strip() if entities_match else ""
    relations = relations_match.group(1).strip() if relations_match else ""

    return entities, relations

async def process_article(article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    title = article.get("title", "")
    text = article.get("text", "")
    if not text:
        return None

    try:
        result = await extract_entities_and_relations(title, text)
        entities, relations = extract_matches(result)

        factcheck_match = re.search(r'(?s)FactCheck:\s*(.*?)Ton:', result)
        tone_match = re.search(r'Ton:\s*(.*)', result)

        factcheck = factcheck_match.group(1).strip() if factcheck_match else ""
        tone = tone_match.group(1).strip() if tone_match else ""

        return {
            "article_source": article.get("source"),
            "article_bias": article.get("bias"),
            "article_title": article.get("title"),
            "article_url": article.get("url"),
            "article_text": text,
            "entities_and_relations": result,
            "entities": entities,
            "entity_count": len(entities.split(", ")) if entities else 0,
            "relations": relations,
            "relations_count": len(relations.split(", ")) if relations else 0,
            "fact_check": factcheck,
            "tone_analysis": tone
        }


    except Exception as e:
        print(Fore.RED + f"[✖] Greška za članak '{article.get('title', 'N/A')}': {e}")
        return None

async def process_articles():
    articles = load_articles(DATA_PATH)

    print(Fore.CYAN + f"🔎 Analiza {len(articles)} članaka...\n")
    results = await tqdm_asyncio.gather(
        *(process_article(article) for article in articles),
        desc="🔍 Obrada vesti",
        total=len(articles),
        colour='blue',
        leave=False,
        unit="article",
        unit_scale=True,
        smoothing=0.1,
        miniters=1,
        bar_format="{l_bar}{bar}| {n}/{total} [{elapsed}<{remaining}, {rate_fmt}]",
    )

    cleaned_results = [r for r in results if r]
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(cleaned_results, f, ensure_ascii=False, indent=4)

    print(Fore.GREEN + f"\n✔ Sačuvano {len(cleaned_results)} članaka u '{OUTPUT_PATH}'")

if __name__ == "__main__":
    start = time.time()
    print(Fore.MAGENTA + f"\nKoristim {AI_MODEL} model za analizu!\n")
    asyncio.run(process_articles())
    print(Fore.YELLOW + f"\n⏱ Ukupno vreme: {time.time() - start:.2f} sekundi")