from typing import Any
from omagent.tools.base import Tool


class SQLQueryTool(Tool):
    """Query SQLite or DuckDB databases."""

    @property
    def name(self) -> str:
        return "sql_query"

    @property
    def description(self) -> str:
        return (
            "Execute SQL queries against SQLite or DuckDB databases. "
            "Returns results as a list of rows. Use for structured data querying, "
            "aggregations, joins, and data exploration."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SQL query to execute."},
                "db_path": {"type": "string", "description": "Path to the database file."},
                "db_type": {
                    "type": "string",
                    "enum": ["sqlite", "duckdb"],
                    "description": "Database type (default: sqlite).",
                },
            },
            "required": ["query", "db_path"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        query = input["query"]
        db_path = input["db_path"]
        db_type = input.get("db_type", "sqlite")

        try:
            if db_type == "duckdb":
                try:
                    import duckdb
                except ImportError:
                    return {"error": "duckdb not installed. pip install duckdb"}
                conn = duckdb.connect(db_path)
                try:
                    result = conn.execute(query)
                    columns = [desc[0] for desc in result.description]
                    rows = result.fetchall()
                    return {
                        "output": [dict(zip(columns, row)) for row in rows[:500]],
                        "columns": columns,
                        "row_count": len(rows),
                    }
                finally:
                    conn.close()
            else:
                import sqlite3
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                try:
                    cursor = conn.execute(query)
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        return {
                            "output": [dict(row) for row in rows[:500]],
                            "columns": columns,
                            "row_count": len(rows),
                        }
                    else:
                        conn.commit()
                        return {"output": f"Query executed. Rows affected: {cursor.rowcount}"}
                finally:
                    conn.close()
        except Exception as e:
            return {"error": f"SQL error: {e}"}
