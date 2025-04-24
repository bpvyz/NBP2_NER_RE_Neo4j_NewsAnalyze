import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase
from tqdm import tqdm
from colorama import Fore
# from rapidfuzz import fuzz  # Removed: no fuzzy matching

load_dotenv()

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")


class ArticleGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        # self.entity_mapping = {}  # Removed: not using normalization
        # self.entity_labels = {}   # Removed: not using label tracking
        # self.label_usage_count = {}  # Removed
        # self.label_variants = {}     # Removed
        # self.all_labels = []         # Removed
        self.relationship_types = set()

    def close(self):
        self.driver.close()

    def sanitize_label(self, label):
        safe_label = ''.join(c for c in label if c.isalnum() or c == '_')
        return f"Label_{safe_label}" if safe_label and safe_label[0].isdigit() else safe_label

    def process_relationship_string(self, relation_str):
        parts = relation_str.strip().split("-[:")
        if len(parts) != 2:
            return None, None, None, None

        from_entity = parts[0].strip()
        remaining = parts[1].split("]->")
        if len(remaining) != 2:
            return None, None, None, None

        rel_type = remaining[0].strip()
        to_entity = remaining[1].strip()

        return from_entity, rel_type, to_entity, "->"

    def create_directed_relationship(self, tx, from_entity, rel_type, to_entity, article_title):
        query = f"""
            MATCH (from {{name: $from_name}})
            MATCH (to {{name: $to_name}})
            CREATE (from)-[r:{rel_type} {{article: $article_title}}]->(to)
            RETURN r
        """
        return tx.run(query, from_name=from_entity, to_name=to_entity, article_title=article_title).single()

    def process_all_articles(self, articles):
        print(Fore.CYAN + "🚀 Starting article processing...\n")

        # Removed first pass for collecting entity labels and variants
        # for article in articles:
        #     if "entities" in article and article["entities"]:
        #         entities = article["entities"].split(", ")
        #         for entity in entities:
        #             if ":" in entity:
        #                 name, label = entity.split(":", 1)
        #                 name = name.strip()
        #                 label = label.strip()
        #                 self.entity_labels[name] = label
        #                 self.label_variants.setdefault(name, []).append(label)
        #                 self.label_usage_count[label] = self.label_usage_count.get(label, 0) + 1
        #                 self.all_labels.append(label)

        with tqdm(
                total=len(articles),
                desc="Processing Articles",
                bar_format="{l_bar}{bar}| {n}/{total} [{elapsed}<{remaining}, {rate_fmt}]",
                colour='blue',
                leave=False,
                unit="article",
                unit_scale=True,
                smoothing=0.1,
                miniters=1
        ) as pbar:
            for article in articles:
                self.create_article_with_entities_and_relations(article)
                pbar.update(1)

        # Replace the progress bar with a completion message
        print(f"\r{Fore.GREEN}✔ All {len(articles)} articles processed successfully{' ' * 20}")

    def create_article_with_entities_and_relations(self, article_data):
        with self.driver.session() as session:
            session.execute_write(self._create_article_graph, article_data)

    def _create_article_graph(self, tx, article):
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

        # Map entity name to label from article['entities']
        entity_labels_map = {}
        if "entities" in article and article["entities"]:
            entities = article["entities"].split(", ")
            for entity in entities:
                if ":" not in entity:
                    continue
                name, label = map(str.strip, entity.split(":", 1))
                safe_label = self.sanitize_label(label)
                entity_labels_map[name] = safe_label

                tx.run(f"""
                    MERGE (e:{safe_label} {{name: $name}})
                """, name=name)

                tx.run(f"""
                    MATCH (a:Article {{title: $title}})
                    MATCH (e:{safe_label} {{name: $name}})
                    MERGE (a)-[:MENTIONS]->(e)
                """, title=article["article_title"], name=name)

        if "relations" in article and article["relations"]:
            relations = article["relations"].split(", ")
            for relation in relations:
                relation = relation.strip()
                if not relation:
                    continue

                from_entity, rel_type, to_entity, direction = self.process_relationship_string(relation)
                if None in [from_entity, rel_type, to_entity, direction]:
                    continue

                rel_type_clean = ''.join(c for c in rel_type.upper().replace(" ", "_") if c.isalnum() or c == '_')
                self.relationship_types.add(rel_type_clean)

                # Determine label for from/to entities if known from entities section
                from_label = entity_labels_map.get(from_entity, "Entity")
                to_label = entity_labels_map.get(to_entity, "Entity")

                # Ensure both entities exist
                tx.run(f"MERGE (e:{from_label} {{name: $name}})", name=from_entity)
                tx.run(f"MERGE (e:{to_label} {{name: $name}})", name=to_entity)

                try:
                    # Create relationship only once
                    tx.run(f"""
                        MATCH (from:{from_label} {{name: $from_name}})
                        MATCH (to:{to_label} {{name: $to_name}})
                        MERGE (from)-[r:{rel_type_clean} {{article: $article_title}}]->(to)
                    """, from_name=from_entity, to_name=to_entity, article_title=article["article_title"])
                except Exception as e:
                    print(f"Failed to create relationship {relation}: {e}")

    # Removed fuzzy matching and label preference
    # def fuzzy_match_entity(self, entity_name): ...
    # def normalize_entity(self, entity_name): ...
    # def get_preferred_label(self, name): ...


if __name__ == "__main__":
    try:
        with open("data/entities_and_relations.json", encoding="utf-8") as f:
            article_data = json.load(f)

        graph = ArticleGraph(URI, USER, PASSWORD)
        graph.process_all_articles(article_data)
        graph.close()
        print("\nProcessing complete!")

    except Exception as e:
        print(f"An error occurred: {e}")
