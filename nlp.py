import json
from openai import OpenAI
import os
import re

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Učitajte JSON podatke (pretpostavljamo da su u fajlu)
with open("example_output/serbian_news_articles.json", "r", encoding="utf-8") as f:
    news_data = json.load(f)

def extract_entities_and_relations(text):
    prompt = f"""
    Izvuci entitete (osobe, organizacije, lokacije, grupe, aktivnosti, itd.) i deskriptivne relacije (događaji, akcije, interakcije) iz sledećeg teksta vesti, koristeći odgovarajuće tipove za Neo4j. Relacije treba da budu konkretne, jasno definisane između entiteta, dok entiteti treba da budu označeni sa odgovarajućim labelama (npr. Politician, Location, Group, Activity, itd.).


    Tekst vesti:
    {text}

    Odgovor u sledećem formatu:
    Entiteti: [entitet1:label, entitet2:label, entitet3:label]
    Relacije: [entitet1 -[:relation]-> entitet2, entitet3 -[:relation]> entitet4]
    
    Bez uvodnih fraza, samo entiteti i relacije, tačno u ovom formatu.
    Za svaki entitet formirati odgovarajucu relaciju.
    """

    response = client.responses.create(
        model = "gpt-4o-mini",
        input = prompt
    )

    return response.output_text

# Prođite kroz svaku vest i izvucite entitete i relacije
with open('entities_and_relations.json', 'w', encoding='utf-8') as outfile:
    # Kreiranje liste za čuvanje svih rezultata
    results = []

    #for article in news_data:
    text = news_data[0].get('text', '') # replace news_data[0] with article
    if text:
        entities_and_relations = extract_entities_and_relations(text)
        entities = re.search(r'Entiteti: \[(.*?)\]', entities_and_relations).group(1)
        relations = re.search(r'Relacije: \[(.*]?)\]', entities_and_relations).group(1)

        results.append({
            'article_source': news_data[0].get('source', ''),
            'article_bias': news_data[0].get('bias', ''),
            'article_title': news_data[0].get('title', ''),  # Možete dodati id vesti ako je dostupan
            'article_url': news_data[0].get('url', ''),
            'article_text': news_data[0].get('text', ''),
            'entities_and_relations': entities_and_relations,
            'entities': entities,
            'relations': relations
        }) # replace news_data[0] with article

    # Snimi sve rezultate u JSON fajl
    json.dump(results, outfile, ensure_ascii=False, indent=4)