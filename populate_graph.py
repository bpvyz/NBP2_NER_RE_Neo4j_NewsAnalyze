from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
import json
from rapidfuzz import fuzz

load_dotenv()

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = os.getenv("NEO4J_KEY")


class ArticleGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        # Dictionary to store normalized entity names -> canonical entity names
        self.entity_mapping = {}
        # Dictionary to store entity -> label mappings
        self.entity_labels = {}
        self.label_usage_count = {}  # Track frequency of all labels for all entities
        self.label_variants = {}  # Track all variants for each entity
        self.all_labels = []

    def close(self):
        self.driver.close()

    def sanitize_label(self, label):
        """Sanitize label names for Neo4j"""
        # Remove special characters
        safe_label = ''.join(c for c in label if c.isalnum() or c == '_')

        # Neo4j labels cannot start with a number, add prefix if needed
        if safe_label and safe_label[0].isdigit():
            safe_label = f"Label_{safe_label}"

        return safe_label

    def normalize_entity(self, entity_name):
        """Normalize entity names to handle variations of names (not labels)"""
        # If already mapped, return it
        if entity_name in self.entity_mapping:
            return self.entity_mapping[entity_name]

        # Exact match: last name rule
        for known_entity in self.entity_labels.keys():
            if known_entity == entity_name:
                continue
            if known_entity.endswith(entity_name) and len(known_entity.split()) > 1:
                print(f"Mapping '{entity_name}' to '{known_entity}' (last name rule)")
                self.entity_mapping[entity_name] = known_entity
                return known_entity

        # Fallback: use as is
        self.entity_mapping[entity_name] = entity_name
        return entity_name

    def fuzzy_match_entity(self, entity_name):
        """Fuzzy match entity name to a canonical entity name."""
        best_match = None
        highest_score = 0
        threshold = 80  # Increase threshold to avoid false positives

        # Get only distinct labels
        distinct_labels = set(self.entity_labels.values())

        # Try fuzzy matching the entity name with the stored canonical labels
        for known_entity, label in self.entity_labels.items():
            if label in distinct_labels:  # Only match entities with distinct labels
                score = fuzz.ratio(entity_name.lower(), known_entity.lower())
                if score > highest_score and score >= threshold:
                    best_match = known_entity
                    highest_score = score

        return best_match if best_match else entity_name

    def fuzzy_match_label(self, entity_label):
        """Fuzzy match labels to canonical labels."""
        best_match = None
        highest_score = 0
        threshold = 80  # Increase threshold to avoid false positives

        # Get only distinct labels
        distinct_labels = set(self.entity_labels.values())

        # Try fuzzy matching the label with the stored canonical labels
        for known_label in distinct_labels:  # Now compare only distinct labels
            score = fuzz.ratio(entity_label.lower(), known_label.lower())
            print(f"Matching score between '{entity_label}' and '{known_label}': {score}")  # Debug output
            if score > highest_score and score >= threshold:
                best_match = known_label
                highest_score = score

        return best_match if best_match else entity_label

    def track_label_usage(self, label):
        """Track how frequently each label is used"""
        if label not in self.label_usage_count:
            self.label_usage_count[label] = 0
        self.label_usage_count[label] += 1
        print(f"Tracking label: {label} (count: {self.label_usage_count[label]})")

    def track_label_variants(self, name, label):
        """Track all variants of a label for an entity"""
        if name not in self.label_variants:
            self.label_variants[name] = []
        self.label_variants[name].append(label)

    def get_preferred_label(self, name):
        """Return the most frequently used label for an entity"""
        if name not in self.label_variants:
            return None  # If no variants, return None

        variants = self.label_variants[name]
        label_counts = {}

        for variant in variants:
            if variant not in label_counts:
                label_counts[variant] = 0
            label_counts[variant] += 1

        # Log label usage counts
        print(f"Label usage for '{name}': {label_counts}")

        # Find the most common label for this entity
        preferred_label = max(label_counts, key=label_counts.get)
        print(f"Preferred label for '{name}': {preferred_label}")
        return preferred_label

    def fuzzy_correct_labels(self):
        """Compare all labels with each other and replace if fuzzy score > 80"""
        threshold = 80  # Set fuzzy matching threshold
        corrected_labels = {}  # To store final corrected labels

        for label in self.all_labels:
            for other_label in self.all_labels:
                if label != other_label:  # No need to compare the label with itself
                    score = fuzz.ratio(label.lower(), other_label.lower())
                    if score > threshold:  # If the match is strong enough, consider replacing
                        # Use the more common label (or decide on a preferred one)
                        preferred_label = other_label if self.label_usage_count.get(other_label,
                                                                                    0) > self.label_usage_count.get(
                            label, 0) else label
                        corrected_labels[label] = preferred_label

        # Update the labels in the graph based on the fuzzy matches
        for old_label, new_label in corrected_labels.items():
            self.replace_label_in_entities(old_label, new_label)

    def replace_label_in_entities(self, old_label, new_label):
        """Replace the label for all entities that use the old label"""
        for entity, label in self.entity_labels.items():
            if label == old_label:
                self.entity_labels[entity] = new_label
                print(f"Replacing label '{old_label}' with '{new_label}' for entity '{entity}'")

    def process_all_articles(self, articles):
        """Pre-process all articles to build entity mappings first"""
        print("Pre-processing articles to build entity mappings...")

        # First pass: collect all entity labels and their variants
        for article in articles:
            if "entities" in article and article["entities"]:
                entities = article["entities"].split(", ")
                for entity in entities:
                    if ":" in entity:
                        name, label = entity.split(":", 1)
                        name = name.strip()
                        label = label.strip()

                        # Track label usage and variants
                        self.track_label_usage(label)
                        self.track_label_variants(name, label)

                        # Store the entity label
                        self.entity_labels[name] = label
                        self.all_labels.append(label)

        # Now perform fuzzy label correction
        self.fuzzy_correct_labels()

        # Now process the articles
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
                   bias: $bias
               })
               RETURN a
           """, title=article["article_title"], url=article["article_url"],
               source=article["article_source"], bias=article["article_bias"])

        print(f"Created/Found article node: '{article['article_title']}'")

        # Process entities
        if "entities" in article and article["entities"]:
            entities = article["entities"].split(", ")
            for entity in entities:
                if ":" in entity:
                    name, label = entity.split(":", 1)
                    name = name.strip()
                    label = label.strip()

                    # Fuzzy correct the label (already corrected in the process)
                    corrected_label = self.entity_labels.get(name, label)

                    # Clean label for Neo4j
                    safe_label = self.sanitize_label(corrected_label)

                    try:
                        # Create entity node and connect it to the article
                        tx.run(f"""
                               MATCH (a:Article {{title: $title, url: $url}})
                               MERGE (e:{safe_label} {{name: $canonical_name}})
                               MERGE (a)-[:MENTIONS]->(e)
                           """, title=article["article_title"], url=article["article_url"],
                           canonical_name=name)

                        print(f"Created/Found node: '{name}' with label '{safe_label}'")

                    except Exception as e:
                        print(f"Failed to create entity {entity}: {str(e)}")
                else:
                    print(f"Skipping entity without label: {entity}")

        # Process relations
        if "relations" in article and article["relations"]:
            relations = article["relations"].split(", ")
            for relation in relations:
                try:
                    # Expected format: "EntityName -[:RELATION_TYPE]-> EntityName"
                    parts = relation.split(" -[:")
                    if len(parts) != 2:
                        print(f"Skipping malformed relation (wrong format): {relation}")
                        continue

                    from_entity = parts[0].strip()

                    # Split the second part at the "]-> " marker
                    second_parts = parts[1].split("]-> ")
                    if len(second_parts) != 2:
                        print(f"Skipping malformed relation (wrong ending): {relation}")
                        continue

                    relation_type = second_parts[0].strip()
                    to_entity = second_parts[1].strip()

                    # Normalize entity names
                    canonical_from = self.normalize_entity(from_entity)
                    canonical_to = self.normalize_entity(to_entity)

                    # Find entity labels
                    from_label = self.entity_labels.get(canonical_from, self.entity_labels.get(from_entity, "Entity"))
                    to_label = self.entity_labels.get(canonical_to, self.entity_labels.get(to_entity, "Entity"))

                    # Clean labels and relation type for Neo4j
                    safe_from_label = self.sanitize_label(from_label)
                    safe_to_label = self.sanitize_label(to_label)

                    # For relation types, replace spaces with underscores and make uppercase
                    relation_type = relation_type.upper().replace(" ", "_")
                    safe_relation_type = ''.join(c for c in relation_type if c.isalnum() or c == '_')

                    # First ensure both entities exist
                    tx.run(f"""
                        MERGE (from:{safe_from_label} {{name: $from_name}})
                    """, from_name=canonical_from)

                    tx.run(f"""
                        MERGE (to:{safe_to_label} {{name: $to_name}})
                    """, to_name=canonical_to)

                    # Then create relationship
                    tx.run(f"""
                        MATCH (from:{safe_from_label} {{name: $from_name}})
                        MATCH (to:{safe_to_label} {{name: $to_name}})
                        MERGE (from)-[r:{safe_relation_type}]->(to)
                    """, from_name=canonical_from, to_name=canonical_to)

                    print(f"Created relation: {canonical_from} -[{safe_relation_type}]-> {canonical_to}")
                except Exception as e:
                    print(f"Failed to create relation {relation}: {str(e)}")


# Load data and process
try:
    with open("entities_and_relations.json", encoding="utf-8") as f:
        article_data = json.load(f)

    graph = ArticleGraph(URI, USER, PASSWORD)
    graph.process_all_articles(article_data)
    graph.close()
    print("\nProcessing complete!")
except Exception as e:
    print(f"An error occurred: {str(e)}")