import os
import logging
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Neo4jClient:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "")
        self.password = os.getenv("NEO4J_PASSWORD", "")
        self.driver = None

        try:
            if not self.user or self.user == "none":
                self.driver = GraphDatabase.driver(self.uri)
            else:
                self.driver = GraphDatabase.driver(
                    self.uri, auth=(self.user, self.password)
                )
            self.driver.verify_connectivity()
            logger.info("Neo4j connected successfully")
        except Exception as e:
            logger.warning(f"Neo4j not available: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()
            self.driver = None

    def query(self, query, parameters=None):
        if not self.driver:
            logger.warning("Neo4j driver is not available")
            return []
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Cypher execution error: {e}")
            return []

    def get_health(self):
        if not self.driver:
            return "Down"
        try:
            self.driver.verify_connectivity()
            return "Ready"
        except Exception:
            return "Down"