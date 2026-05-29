import os
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv


# Project root = directory containing .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)


@dataclass
class PostgresConfig:
    dsn: str

    @classmethod
    def from_env(cls) -> "PostgresConfig":
        _load_env()
        return cls(dsn=os.getenv("PG_DSN", "postgresql://user:pass@localhost:5432/mydb"))


@dataclass
class Neo4jConfig:
    uri: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        _load_env()
        return cls(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
        )


@dataclass
class ExtractionConfig:
    include_foreign_keys: bool = True
    include_view_deps: bool = True
    include_column_lineage: bool = True


@dataclass
class Neo4jWriteConfig:
    clear_before_write: bool = True
    batch_size: int = 100


@dataclass
class LoggingConfig:
    verbose: bool = False


@dataclass
class TablesConfig:
    patterns: list[str]

    @classmethod
    def from_yaml(cls, path: str | Path) -> "TablesConfig":
        import yaml
        path = _resolve_path(path)
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(patterns=data.get("tables", []))

    @classmethod
    def from_env(cls) -> "TablesConfig":
        _load_env()
        path = os.getenv("TABLES_CONFIG", "config/tables.yaml")
        return cls.from_yaml(path)


@dataclass
class PipelineSettings:
    neo4j_write: Neo4jWriteConfig
    extraction: ExtractionConfig
    logging: LoggingConfig

    @classmethod
    def from_yaml(cls, path: str | Path) -> "PipelineSettings":
        import yaml
        path = _resolve_path(path)
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        n4j = data.get("neo4j", {})
        ext = data.get("extraction", {})
        log = data.get("logging", {})

        return cls(
            neo4j_write=Neo4jWriteConfig(
                clear_before_write=n4j.get("clear_before_write", True),
                batch_size=n4j.get("batch_size", 100),
            ),
            extraction=ExtractionConfig(
                include_foreign_keys=ext.get("include_foreign_keys", True),
                include_view_deps=ext.get("include_view_deps", True),
                include_column_lineage=ext.get("include_column_lineage", True),
            ),
            logging=LoggingConfig(verbose=log.get("verbose", False)),
        )

    @classmethod
    def from_env(cls) -> "PipelineSettings":
        _load_env()
        path = os.getenv("SETTINGS_CONFIG", "config/settings.yaml")
        return cls.from_yaml(path)


def _resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p
