import asyncio
import os
from neo4j import GraphDatabase

_instance = None
_lock = asyncio.Lock()


class GraphStore:
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        # Accept explicit args first; fall back to env vars; then defaults that
        # match the docker-compose values so tests work without a full .env.
        neo4j_uri = uri or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = user or os.environ.get("NEO4J_USER", "neo4j")
        neo4j_password = password or os.environ.get("NEO4J_PASSWORD", "password123")

        self._driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password),
        )

    def upsert_entities(
        self, entities: list[dict], relations: list[dict], namespace: str
    ) -> int:
        with self._driver.session() as session:
            for entity in entities:
                session.run(
                    "MERGE (e:Entity {name: $name, namespace: $ns}) "
                    "SET e.type = $type, e.description = $description",
                    name=entity["name"],
                    ns=namespace,
                    type=entity.get("type", "Unknown"),
                    description=entity.get("description", ""),
                )
            for rel in relations:
                session.run(
                    "MATCH (a:Entity {name: $from_name, namespace: $ns}) "
                    "MATCH (b:Entity {name: $to_name, namespace: $ns}) "
                    "MERGE (a)-[r:RELATES_TO {rel_type: $rel_type, namespace: $ns}]->(b)",
                    from_name=rel["from"],
                    to_name=rel["to"],
                    rel_type=rel.get("type", "RELATED_TO"),
                    ns=namespace,
                )
        return len(entities)

    def query_related(
        self, entity_names: list[str], namespace: str, hops: int = 2
    ) -> list[dict]:
        cypher = (
            "MATCH (e:Entity) WHERE e.name IN $names AND e.namespace = $ns "
            "OPTIONAL MATCH (e)-[:RELATES_TO*1..2]-(related:Entity {namespace: $ns}) "
            "WITH collect(distinct e) + collect(distinct related) AS all_e "
            "UNWIND all_e AS entity "
            "RETURN distinct entity.name AS name, entity.type AS type, "
            "entity.description AS description"
        )
        with self._driver.session() as session:
            result = session.run(cypher, names=entity_names, ns=namespace)
            return [dict(row) for row in result]

    def clear_namespace(self, namespace: str) -> None:
        with self._driver.session() as session:
            session.run(
                "MATCH (e:Entity {namespace: $ns}) DETACH DELETE e",
                ns=namespace,
            )

    def close(self) -> None:
        self._driver.close()


async def get_graph_store() -> "GraphStore":
    """Return a module-level singleton, wiring credentials from app settings."""
    global _instance
    async with _lock:
        if _instance is None:
            # Import here to avoid loading heavy config at module import time.
            from config import get_settings
            settings = get_settings()
            _instance = GraphStore(
                uri=settings.NEO4J_URI,
                user=settings.NEO4J_USER,
                password=settings.NEO4J_PASSWORD,
            )
    return _instance
