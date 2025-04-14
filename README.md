News Knowledge Graph Builder
===========================

A complete pipeline that scrapes news articles, extracts entities and relationships using NLP, and visualizes them in an interactive Neo4j knowledge graph with Flask.

Quick Start
-----------

Prerequisites:
- Docker Desktop (https://www.docker.com/products/docker-desktop/)
- Python 3.8+
- OpenAI API key

Installation:
1. Set up Docker:
   - Download and install Docker Desktop
   - Ensure Docker engine is running

2. Configure environment:
   - Run the setup script: run-neo4j.bat
   - Will prompt for:
     * Neo4j username (default: neo4j)
     * Neo4j password (min 8 characters)
     * Your OpenAI API key

3. Install dependencies:
   pip install -r requirements.txt

Pipeline Execution
-----------------

Run these steps in order:

1. Scrape news articles:
   python news_scraper.py
   - Outputs to data/serbian_news_articles.json
   - Configure sources in sources.json
   - Configure scraping rules in scraping_rules.json

2. Process articles with NLP:
   python nlp.py
   - Uses OpenAI for NER and RE
   - Saves processed data to data/entities_and_relations.json

3. Build knowledge graph:
   python populate_graph.py
   - Creates nodes and relationships in Neo4j
   - Auto-connects using .env credentials

4. Launch visualization:
   python app.py
   - Access at: http://localhost:5000
   - Interactive graph explorer using Sigma.js
