from neo4j import GraphDatabase


class Neo4jConnection:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def session(self):
        return self.driver.session()

    def run(self, query: str, params: dict | None = None):
        with self.session() as session:
            session.run(query, parameters=params or {})

    def close(self):
        self.driver.close()
