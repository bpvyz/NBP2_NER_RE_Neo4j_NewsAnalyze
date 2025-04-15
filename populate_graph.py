from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
import json
from rapidfuzz import fuzz

load_dotenv()

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")


class ArticleGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.entity_mapping = {}
        self.entity_labels = {}
        self.label_usage_count = {}
        self.label_variants = {}
        self.all_labels = []
        self.relationship_types = set()

    def close(self):
        self.driver.close()

    def sanitize_label(self, label):
        """Sanitize label names for Neo4j"""
        safe_label = ''.join(c for c in label if c.isalnum() or c == '_')
        if safe_label and safe_label[0].isdigit():
            safe_label = f"Label_{safe_label}"
        return safe_label

    def fuzzy_match_entity(self, entity_name):
        """Fuzzy match entity name to canonical names"""
        best_match = None
        highest_score = 0
        threshold = 80

        for known_entity, label in self.entity_labels.items():
            if label in set(self.entity_labels.values()):
                score = fuzz.ratio(entity_name.lower(), known_entity.lower())
                if score > highest_score and score >= threshold:
                    best_match = known_entity
                    highest_score = score

        return best_match if best_match else entity_name

    def normalize_entity(self, entity_name):
        """Normalize entity names to handle variations"""
        if entity_name in self.entity_mapping:
            return self.entity_mapping[entity_name]

        # Last name rule matching
        for known_entity in self.entity_labels.keys():
            if known_entity == entity_name:
                continue
            if known_entity.endswith(entity_name) and len(known_entity.split()) > 1:
                self.entity_mapping[entity_name] = known_entity
                return known_entity

        # Fuzzy matching fallback
        best_match = self.fuzzy_match_entity(entity_name)
        if best_match != entity_name:
            self.entity_mapping[entity_name] = best_match
            return best_match

        self.entity_mapping[entity_name] = entity_name
        return entity_name

    def process_relationship_string(self, relation_str):
        """
        Parse relationship string into components with directionality
        Expected format: "Entity1 -[:REL_TYPE]-> Entity2"
        Returns: (from_entity, rel_type, to_entity, direction)
        """
        relation_str = relation_str.strip()

        # Split into parts
        parts = relation_str.split("-[:")
        if len(parts) != 2:
            return None, None, None, None

        from_entity = parts[0].strip()

        # Split the remaining part
        remaining = parts[1].split("]->")
        if len(remaining) != 2:
            return None, None, None, None

        rel_type = remaining[0].strip()
        to_entity = remaining[1].strip()

        return from_entity, rel_type, to_entity, "->"

    def create_directed_relationship(self, tx, from_entity, rel_type, to_entity, direction, article_title):
        """Create a directed relationship between entities"""
        # Get labels for entities
        from_label = self.entity_labels.get(from_entity, "Entity")
        to_label = self.entity_labels.get(to_entity, "Entity")

        # Sanitize labels and relationship type
        safe_from_label = self.sanitize_label(from_label)
        safe_to_label = self.sanitize_label(to_label)
        safe_rel_type = rel_type.upper().replace(" ", "_")
        safe_rel_type = ''.join(c for c in safe_rel_type if c.isalnum() or c == '_')

        # Track relationship type
        self.relationship_types.add(safe_rel_type)

        # Create the relationship with directionality
        query = f"""
            MATCH (from:{safe_from_label} {{name: $from_name}})
            MATCH (to:{safe_to_label} {{name: $to_name}})
            CREATE (from)-[r:{safe_rel_type} {{article: $article_title}}]->(to)
            RETURN r
        """

        result = tx.run(query,
                        from_name=from_entity,
                        to_name=to_entity,
                        article_title=article_title)

        return result.single()

    def process_all_articles(self, articles):
        """Pre-process articles to build entity mappings"""
        print("Pre-processing articles to build entity mappings...")

        # First pass: collect all entity labels and variants
        for article in articles:
            if "entities" in article and article["entities"]:
                entities = article["entities"].split(", ")
                for entity in entities:
                    if ":" in entity:
                        name, label = entity.split(":", 1)
                        name = name.strip()
                        label = label.strip()

                        # Track label usage
                        if label not in self.label_usage_count:
                            self.label_usage_count[label] = 0
                        self.label_usage_count[label] += 1

                        # Track label variants
                        if name not in self.label_variants:
                            self.label_variants[name] = []
                        self.label_variants[name].append(label)

                        # Store entity label
                        self.entity_labels[name] = label
                        self.all_labels.append(label)

        # Process articles with entities and relationships
        print(f"Processing {len(articles)} articles...")
        for i, article in enumerate(articles):
            print(f"\nProcessing article {i + 1}/{len(articles)}: {article['article_title']}")
            self.create_article_with_entities_and_relations(article)

    def create_article_with_entities_and_relations(self, article_data):
        with self.driver.session() as session:
            session.execute_write(self._create_article_graph, article_data)

    def _create_article_graph(self, tx, article):
        # Create article node
        tx.run("""
            MERGE (a:Article {
                title: $title,
                url: $url,
                source: $source,
                bias: $bias,
                text: $text
            })
        """, title=article["article_title"],
               url=article["article_url"],
               source=article["article_source"],
               bias=article["article_bias"],
               text=article["article_text"])

        # Process entities
        if "entities" in article and article["entities"]:
            entities = article["entities"].split(", ")
            for entity in entities:
                if ":" in entity:
                    name, label = entity.split(":", 1)
                    name = name.strip()
                    label = label.strip()

                    # Get preferred label
                    preferred_label = self.get_preferred_label(name)
                    safe_label = self.sanitize_label(preferred_label if preferred_label else label)

                    # Create entity node and relationship to article
                    tx.run(f"""
                        MATCH (a:Article {{title: $title}})
                        MERGE (e:{safe_label} {{name: $name}})
                        MERGE (a)-[:MENTIONS]->(e)
                    """, title=article["article_title"], name=name)

        # Process relationships with directionality
        if "relations" in article and article["relations"]:
            relations = article["relations"].split(", ")
            for relation in relations:
                relation = relation.strip()
                if not relation:
                    continue

                from_entity, rel_type, to_entity, direction = self.process_relationship_string(relation)

                if None in [from_entity, rel_type, to_entity, direction]:
                    print(f"Skipping malformed relation: {relation}")
                    continue

                # Normalize entity names
                canonical_from = self.normalize_entity(from_entity)
                canonical_to = self.normalize_entity(to_entity)

                # Create the directed relationship
                try:
                    self.create_directed_relationship(
                        tx,
                        canonical_from,
                        rel_type,
                        canonical_to,
                        direction,
                        article["article_title"]
                    )
                except Exception as e:
                    print(f"Failed to create relationship {relation}: {str(e)}")

    def get_preferred_label(self, name):
        """Get most frequently used label for an entity"""
        if name not in self.label_variants:
            return None

        variant_counts = {}
        for variant in self.label_variants[name]:
            variant_counts[variant] = variant_counts.get(variant, 0) + 1

        return max(variant_counts, key=variant_counts.get)


# Load data and process
try:
    with open("data/entities_and_relations.json", encoding="utf-8") as f:
        article_data = json.load(f)

    graph = ArticleGraph(URI, USER, PASSWORD)
    graph.process_all_articles(article_data)
    graph.close()
    print("\nProcessing complete!")
except Exception as e:
    print(f"An error occurred: {str(e)}")