from flask import Flask, render_template, jsonify
from flask_assets import Environment, Bundle
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
from functools import wraps

load_dotenv()

app = Flask(__name__)

assets = Environment(app)

scss_bundle = Bundle(
    'scss/main.scss',
    filters='libsass,cssmin',
    output='css/main.min.css',
    depends='scss/**/*.scss'
)

assets.register('scss_all', scss_bundle)

# Configuration
class Config:
    NEO4J_URI = os.getenv("NEO4J_URI")
    NEO4J_USER = os.getenv("NEO4J_USER")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
    NEO4J_MAX_CONNECTION_LIFETIME = 3600  # 1 hour

app.config.from_object(Config)

# Neo4j connection pool
driver = GraphDatabase.driver(
    app.config["NEO4J_URI"],
    auth=(app.config["NEO4J_USER"], app.config["NEO4J_PASSWORD"]),
    max_connection_lifetime=app.config["NEO4J_MAX_CONNECTION_LIFETIME"]
)

# Constants
ENTITY_LABELS = [
    "Osoba", "Organizacija", "Lokacija", "Vreme", "Aktivnost",
    "AktivnostDogađaj", "Događaj", "Grupa", "Vozilo", "Proizvod",
    "Umetničko delo", "Dokument", "Biljka", "Broj", "Hrana", "Piće",
    "Institucija", "Simbol", "HranaPiće", "Životinja", "Tehnologija", "Entity"
]

# Decorators
def handle_neo4j_exceptions(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            app.logger.error(f"Neo4j error: {str(e)}")
            return jsonify({"error": "Database error occurred"}), 500
    return decorated_function

# Routes
@app.route("/")
def index():
    try:
        with driver.session() as session:
            # Query to get all articles grouped by bias and then by source
            result = session.run("""
                MATCH (a:Article)
                WITH a.bias AS bias, a.source AS source, collect(a) AS articles
                RETURN bias, source, articles
                ORDER BY bias, source
            """)

            # Create a nested dictionary structure: {bias: {source: [articles]}}
            bias_groups = {}

            for record in result:
                bias = record["bias"] or "Nepoznat bias"
                source = record["source"] or "Nepoznat izvor"
                articles = []

                for article in record["articles"]:
                    articles.append({
                        "id": article.element_id,
                        "title": article.get("title", f"Article {article.element_id}"),
                        "source": source,
                        "bias": bias,
                        "url": article.get("url", "#"),
                        "content": article.get("content", "<p>Sadržaj članka nije dostupan.</p>"),
                        "date": article.get("date", ""),
                        "read_time": article.get("read_time", "")
                    })

                if bias not in bias_groups:
                    bias_groups[bias] = {}

                bias_groups[bias][source] = articles

            # Convert the nested dictionary to a template-friendly structure
            groups = []
            for bias, sources in bias_groups.items():
                source_list = []
                for source_name, articles in sources.items():
                    source_list.append({
                        "id": source_name.lower().replace(" ", "-"),
                        "name": source_name,
                        "articles": articles
                    })

                groups.append({
                    "id": bias.lower().replace(" ", "-"),
                    "name": bias,
                    "sources": source_list
                })

            return render_template("index.html", groups=groups)

    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        return render_template("error.html", message="Error loading articles"), 500


@app.route("/api/graph/<article_id>")
@handle_neo4j_exceptions
def get_article_graph(article_id):
    if not article_id or not isinstance(article_id, str):
        return jsonify({"error": "Invalid article ID"}), 400

    with driver.session() as session:
        query = """
        MATCH (a:Article)
        WHERE elementId(a) = $article_id
        
        // Nađi sve čvorove povezane sa člankom kroz usmerene veze
        OPTIONAL MATCH (a)-[r]->(connected)
        
        // Dodatno, nađi sve usmerene veze između povezanih čvorova
        OPTIONAL MATCH (connected)-[r2]->(other_connected)
        WHERE r2.article = a.title
        
        RETURN a, r, connected, r2, other_connected
        """
        result = session.run(query, article_id=article_id)

        nodes = []
        edges = []
        node_ids = set()



        for record in result:
            # Add article node
            a = record["a"]
            if a.element_id not in node_ids:
                nodes.append({
                    "id": a.element_id,
                    "label": a.get("title", f"Article {a.element_id}"),
                    "group": "article",
                    "properties": dict(a)
                })
                node_ids.add(a.element_id)

            connected = record["connected"]
            if connected and connected.element_id not in node_ids:
                node_type = next(iter(connected.labels), "Entity").lower()
                nodes.append({
                    "id": connected.element_id,
                    "label": connected.get("name", connected.get("title", f"{node_type} {connected.element_id}")),
                    "group": node_type,
                    "properties": dict(connected)
                })
                node_ids.add(connected.element_id)

            rel = record["r"]
            if rel.type:
                edges.append({
                    "from": a.element_id,
                    "to": connected.element_id,
                    "label": rel.type,
                    "properties": dict(rel)
                })

            # Additional logic for edges between connected nodes
            connected2 = record["other_connected"]
            rel2 = record["r2"]
            if connected2 and connected2.element_id not in node_ids:
                nodes.append({
                    "id": connected2.element_id,
                    "label": connected2.get("name", connected2.get("title", f"{connected2.element_id}")),
                    "group": next(iter(connected2.labels), "Entity").lower(),
                    "properties": dict(connected2)
                })
                node_ids.add(connected2.element_id)

            if rel2:
                edges.append({
                    "from": connected.element_id,
                    "to": connected2.element_id,
                    "label": rel2.type,
                    "properties": dict(rel2)
                })
        # for rel in edges:
        #     print(rel["from"], rel["to"], rel["label"], rel["properties"])
        return jsonify({"nodes": nodes, "edges": edges})


@app.route("/api/article/<article_id>")
@handle_neo4j_exceptions
def get_article_content(article_id):
    if not article_id or not isinstance(article_id, str):
        return jsonify({"error": "Invalid article ID"}), 400

    with driver.session() as session:
        query = """
        MATCH (a:Article)
        WHERE elementId(a) = $article_id OR elementId(a) = toInteger($article_id)
        RETURN a
        """
        result = session.run(query, article_id=article_id).single()

        if not result:
            return jsonify({"error": "Article not found"}), 404

        article = result["a"]
        return jsonify({
            "id": article.element_id,
            "title": article.get("title", f"Article {article.element_id}"),
            "date": article.get("date", ""),
            "readTime": article.get("read_time", ""),
            "content": article.get("text", "Sadržaj članka nije dostupan."),
            "source": article.get("source", ""),
            "bias": article.get("bias", "#"),
            "url": article.get("url", "#"),
        })

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="Page not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', message="Internal server error"), 500

if __name__ == "__main__":
    app.run(debug=True)