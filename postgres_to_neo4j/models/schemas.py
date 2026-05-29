from dataclasses import dataclass, field


@dataclass
class TableInfo:
    table_schema: str
    table_name: str
    table_type: str


@dataclass
class ColumnInfo:
    column_name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    default: str | None
    ordinal_position: int


@dataclass
class ForeignKeyInfo:
    constraint_name: str
    fk_column: str
    ref_schema: str
    ref_table: str
    ref_column: str
    table_schema: str = ""
    table_name: str = ""


@dataclass
class ViewDepInfo:
    ref_schema: str
    ref_table: str


@dataclass
class TableData:
    table: TableInfo
    columns: list[ColumnInfo] = field(default_factory=list)
    foreign_keys: list[ForeignKeyInfo] = field(default_factory=list)
    view_depends_on: list[ViewDepInfo] = field(default_factory=list)
