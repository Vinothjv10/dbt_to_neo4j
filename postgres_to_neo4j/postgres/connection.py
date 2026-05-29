import psycopg2
import psycopg2.extras


class PostgresConnection:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._conn = None

    def __enter__(self):
        self._conn = psycopg2.connect(self.dsn)
        self._conn.set_session(autocommit=True)
        return self

    def __exit__(self, *args):
        self.close()

    @property
    def conn(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.dsn)
            self._conn.set_session(autocommit=True)
        return self._conn

    def cursor(self):
        return self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
