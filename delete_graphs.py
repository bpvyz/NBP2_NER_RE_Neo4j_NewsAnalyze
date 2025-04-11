from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = os.getenv("NEO4J_KEY")


def delete_all_data(uri, user, password):
    driver = GraphDatabase.driver(uri, auth=(user, password))

    try:
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("All nodes and relationships have been deleted.")

            try:
                result = session.run("SHOW CONSTRAINTS")
                constraints = [record["name"] for record in result]
                for constraint in constraints:
                    session.run(f"DROP CONSTRAINT {constraint}")

                result = session.run("SHOW INDEXES")
                indexes = [record["name"] for record in result if
                           record["type"] == "RANGE"]
                for index in indexes:
                    session.run(f"DROP INDEX {index}")

                print("All constraints and indexes have been dropped.")
            except Exception as schema_error:
                print(f"Couldn't drop constraints/indexes: {schema_error}")
                print("You may need to manually drop them or install APOC library.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.close()


if __name__ == "__main__":
    confirmation = input("WARNING: This will delete ALL data in your Neo4j database. Continue? (y/n): ")
    if confirmation.lower() == 'y':
        delete_all_data(URI, USER, PASSWORD)
    else:
        print("Operation cancelled.")