from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from implementation.init_db import DB_PATH


class ValidationError(Exception):
    """Raised when a database request cannot be safely executed."""


class SQLiteAdapter:
    """Small SQLite data layer for the lab MCP tools."""

    SUPPORTED_OPERATORS = {
        "eq": "=",
        "=": "=",
        "ne": "!=",
        "!=": "!=",
        "gt": ">",
        ">": ">",
        "gte": ">=",
        ">=": ">=",
        "lt": "<",
        "<": "<",
        "lte": "<=",
        "<=": "<=",
        "like": "LIKE",
        "in": "IN",
        "is_null": "IS NULL",
        "not_null": "IS NOT NULL",
    }
    AGGREGATES = {"count", "avg", "sum", "min", "max"}
    MAX_LIMIT = 100

    def __init__(self, db_path: Path | str = DB_PATH):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database not found at {self.db_path}. Run implementation/init_db.py first."
            )

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = MEMORY")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def list_tables(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> dict[str, Any]:
        table = self.validate_table(table)
        with self.connect() as conn:
            rows = conn.execute(f"PRAGMA table_info({self.quote_identifier(table)})").fetchall()

        return {
            "table": table,
            "columns": [
                {
                    "name": row["name"],
                    "type": row["type"],
                    "not_null": bool(row["notnull"]),
                    "default_value": row["dflt_value"],
                    "primary_key": bool(row["pk"]),
                }
                for row in rows
            ],
        }

    def get_database_schema(self) -> dict[str, Any]:
        return {
            "tables": {
                table: self.get_table_schema(table)["columns"]
                for table in self.list_tables()
            }
        }

    def search(
        self,
        table: str,
        columns: Sequence[str] | str | None = None,
        filters: Any = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> list[dict[str, Any]]:
        table = self.validate_table(table)
        limit = self.validate_limit(limit)
        offset = self.validate_offset(offset)

        selected_columns = self.resolve_columns(table, columns)
        select_sql = ", ".join(self.quote_identifier(column) for column in selected_columns)
        where_sql, params = self.build_where_clause(table, filters)

        sql = f"SELECT {select_sql} FROM {self.quote_identifier(table)}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        if order_by:
            order_by = self.validate_column(table, order_by)
            direction = "DESC" if descending else "ASC"
            sql += f" ORDER BY {self.quote_identifier(order_by)} {direction}"
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def insert(self, table: str, values: Mapping[str, Any]) -> dict[str, Any]:
        table = self.validate_table(table)
        if not isinstance(values, Mapping) or not values:
            raise ValidationError("Insert values must be a non-empty object.")

        columns = [self.validate_column(table, column) for column in values]
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(self.quote_identifier(column) for column in columns)
        params = [values[column] for column in columns]

        sql = (
            f"INSERT INTO {self.quote_identifier(table)} ({column_sql}) "
            f"VALUES ({placeholders})"
        )

        try:
            with self.connect() as conn:
                cursor = conn.execute(sql, params)
                conn.commit()
                inserted = dict(values)
                if "id" in self.column_names(table) and "id" not in inserted:
                    inserted["id"] = cursor.lastrowid
                return inserted
        except sqlite3.IntegrityError as exc:
            raise ValidationError(f"Insert failed: {exc}") from exc

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: Any = None,
        group_by: Sequence[str] | str | None = None,
    ) -> list[dict[str, Any]]:
        table = self.validate_table(table)
        metric = self.validate_metric(metric)
        group_columns = self.resolve_group_by(table, group_by)
        where_sql, params = self.build_where_clause(table, filters)

        if metric == "count" and column is None:
            aggregate_sql = "COUNT(*)"
        else:
            if column is None:
                raise ValidationError(f"Metric '{metric}' requires a column.")
            column = self.validate_column(table, column)
            aggregate_sql = f"{metric.upper()}({self.quote_identifier(column)})"

        select_parts = [self.quote_identifier(column) for column in group_columns]
        select_parts.append(f"{aggregate_sql} AS value")
        sql = f"SELECT {', '.join(select_parts)} FROM {self.quote_identifier(table)}"
        if where_sql:
            sql += f" WHERE {where_sql}"
        if group_columns:
            group_sql = ", ".join(self.quote_identifier(column) for column in group_columns)
            sql += f" GROUP BY {group_sql} ORDER BY {group_sql}"

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def build_where_clause(self, table: str, filters: Any) -> tuple[str, list[Any]]:
        normalized_filters = self.normalize_filters(filters)
        clauses: list[str] = []
        params: list[Any] = []

        for filter_item in normalized_filters:
            column = self.validate_column(table, filter_item["column"])
            operator = self.validate_operator(filter_item.get("op", "eq"))
            has_value = "value" in filter_item
            value = filter_item.get("value")
            column_sql = self.quote_identifier(column)

            if operator in {"IS NULL", "IS NOT NULL"}:
                clauses.append(f"{column_sql} {operator}")
                continue
            if not has_value:
                raise ValidationError(f"Filter for column '{column}' is missing a value.")
            if operator == "IN":
                if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
                    raise ValidationError("The 'in' operator requires a non-empty list value.")
                if not value:
                    raise ValidationError("The 'in' operator requires a non-empty list value.")
                placeholders = ", ".join("?" for _ in value)
                clauses.append(f"{column_sql} IN ({placeholders})")
                params.extend(value)
                continue
            if value is None and operator == "=":
                clauses.append(f"{column_sql} IS NULL")
                continue
            if value is None and operator == "!=":
                clauses.append(f"{column_sql} IS NOT NULL")
                continue

            clauses.append(f"{column_sql} {operator} ?")
            params.append(value)

        return " AND ".join(clauses), params

    def normalize_filters(self, filters: Any) -> list[dict[str, Any]]:
        if filters is None or filters == {} or filters == []:
            return []

        if isinstance(filters, Mapping):
            if "column" in filters:
                return [dict(filters)]
            return [
                {"column": column, "op": "eq", "value": value}
                for column, value in filters.items()
            ]

        if isinstance(filters, Sequence) and not isinstance(filters, (str, bytes)):
            normalized = []
            for item in filters:
                if not isinstance(item, Mapping) or "column" not in item:
                    raise ValidationError(
                        "Each filter must be an object with at least a 'column' key."
                    )
                normalized.append(dict(item))
            return normalized

        raise ValidationError("Filters must be an object or a list of filter objects.")

    def resolve_columns(self, table: str, columns: Sequence[str] | str | None) -> list[str]:
        if columns is None or columns == "*":
            return self.column_names(table)
        if isinstance(columns, str):
            return [self.validate_column(table, columns)]
        if not columns:
            raise ValidationError("Columns must not be an empty list.")
        return [self.validate_column(table, column) for column in columns]

    def resolve_group_by(self, table: str, group_by: Sequence[str] | str | None) -> list[str]:
        if group_by is None:
            return []
        if isinstance(group_by, str):
            return [self.validate_column(table, group_by)]
        if not group_by:
            raise ValidationError("group_by must not be an empty list.")
        return [self.validate_column(table, column) for column in group_by]

    def validate_table(self, table: str) -> str:
        if not isinstance(table, str) or not table:
            raise ValidationError("Table name must be a non-empty string.")
        if table not in self.list_tables():
            raise ValidationError(f"Unknown table: {table}")
        return table

    def validate_column(self, table: str, column: str) -> str:
        if not isinstance(column, str) or not column:
            raise ValidationError("Column name must be a non-empty string.")
        if column not in self.column_names(table):
            raise ValidationError(f"Unknown column for table '{table}': {column}")
        return column

    def validate_operator(self, operator: str) -> str:
        if not isinstance(operator, str):
            raise ValidationError("Filter operator must be a string.")
        operator = operator.lower()
        if operator not in self.SUPPORTED_OPERATORS:
            raise ValidationError(f"Unsupported filter operator: {operator}")
        return self.SUPPORTED_OPERATORS[operator]

    def validate_metric(self, metric: str) -> str:
        if not isinstance(metric, str):
            raise ValidationError("Aggregate metric must be a string.")
        metric = metric.lower()
        if metric not in self.AGGREGATES:
            raise ValidationError(f"Unsupported aggregate metric: {metric}")
        return metric

    def validate_limit(self, limit: int) -> int:
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise ValidationError("Limit must be an integer.")
        if limit < 1 or limit > self.MAX_LIMIT:
            raise ValidationError(f"Limit must be between 1 and {self.MAX_LIMIT}.")
        return limit

    def validate_offset(self, offset: int) -> int:
        if not isinstance(offset, int) or isinstance(offset, bool):
            raise ValidationError("Offset must be an integer.")
        if offset < 0:
            raise ValidationError("Offset must be greater than or equal to 0.")
        return offset

    def column_names(self, table: str) -> list[str]:
        schema = self.get_table_schema(table)
        return [column["name"] for column in schema["columns"]]

    @staticmethod
    def quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'
