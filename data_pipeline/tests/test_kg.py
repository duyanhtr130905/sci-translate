import os
import pytest
from neo4j import GraphDatabase

MIN_NODES = 500
MIN_EDGES = 1000

def _require_driver():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    return GraphDatabase.driver(uri, auth=(user, password))

def _run_scalar(driver, query: str, **params):
    with driver.session() as session:
        record = session.run(query, params).single()
        return None if record is None else list(record.values())[0]

@pytest.mark.integration
def test_neo4j_node_count_at_least_500() -> None:
    driver = _require_driver()
    with driver:
        total_terms = _run_scalar(driver, "MATCH (t:Term) RETURN count(t) AS total_terms")
    assert isinstance(total_terms, int)
    assert total_terms >= MIN_NODES, f"Neo4j chỉ có {total_terms} Term nodes, cần >= {MIN_NODES}"

@pytest.mark.integration
def test_neo4j_edge_count_at_least_1000() -> None:
    driver = _require_driver()
    with driver:
        total_edges = _run_scalar(driver, "MATCH ()-[r]->() RETURN count(r) AS total_edges")
    assert isinstance(total_edges, int)
    assert total_edges >= MIN_EDGES, f"Neo4j chỉ có {total_edges} relationships, cần >= {MIN_EDGES}"

@pytest.mark.integration
def test_neo4j_contains_rag_term() -> None:
    driver = _require_driver()
    with driver:
        found = _run_scalar(
            driver,
            """
            MATCH (t:Term)
            WHERE toLower(replace(t.term, '"', '')) = 'rag'
            RETURN count(t) > 0 AS found
            """,
        )
    assert found is True, "Không tìm thấy term='RAG' trong Neo4j"