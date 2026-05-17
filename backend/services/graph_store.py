import asyncio
from neo4j import GraphDatabase

_instance = None
_lock = asyncio.Lock()


class GraphStore:
    def __init__(self, settings=None):
        if settings is None:
            from config import get_settings
            settings = get_settings()
        self._driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
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
            f"OPTIONAL MATCH (e)-[:RELATES_TO*1..{hops}]-(related:Entity {{namespace: $ns}}) "
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
            _instance = GraphStore(settings=get_settings())
    return _instance
