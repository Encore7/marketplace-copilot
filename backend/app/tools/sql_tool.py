from __future__ import annotations

import re
from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator

from ..db.session import get_warehouse_connection
from ..observability.llm_obs import traceable_node
from ..observability.logging import get_logger

logger = get_logger("tools.sql")


class SQLQueryInput(BaseModel):
    """
    Internal tool input model for running read-only SQL against the seller warehouse.

    This is mainly for debugging and advanced analysis agents.
    We enforce:
      - SELECT-only queries
      - No obvious DDL/DML keywords
    """

    query: str = Field(..., description="SQL SELECT query to run against the warehouse")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Named parameters to bind into the query (DuckDB-style).",
    )

    @field_validator("query")
    @classmethod
    def validate_select_only(cls, value: str) -> str:
        text = value.strip().lower()

        if not text.startswith("select"):
            raise ValueError("Only SELECT queries are allowed for sql_tool")

        forbidden_keywords = [
            "insert",
            "update",
            "delete",
            "drop",
            "alter",
            "create table",
            "truncate",
            "merge",
        ]
        if any(kw in text for kw in forbidden_keywords):
            raise ValueError("DDL/DML statements are not allowed in sql_tool")

        allowed_tables = [
            "products",
            "competitors",
            "inventory",
            "reviews",
            "sales_history",
        ]
        pattern = r"\bfrom\s+([a-zA-Z0-9_]+)"
        table_matches = re.findall(pattern, text)
        for tbl in table_matches:
            if tbl not in allowed_tables:
                raise ValueError(f"Table '{tbl}' is not allowed in sql_tool")

        return value


class SQLQueryRow(BaseModel):
    """
    Generic row representation from a SQL query.
    We store column values in a dict for flexibility.
    """

    data: Dict[str, Any]


class SQLQueryOutput(BaseModel):
    """
    Output of a SQL query: rows and row count.
    """

    rows: List[SQLQueryRow]
    row_count: int


@traceable_node("tool.sql")
def run_sql_query(input_data: SQLQueryInput) -> SQLQueryOutput:
    """
    Execute a validated, read-only SQL query against the seller warehouse.
    """
    logger.info("Running SQL query via sql_tool")

    with get_warehouse_connection() as conn:
        if input_data.params:
            df = conn.execute(input_data.query, input_data.params).df()
        else:
            df = conn.execute(input_data.query).df()

    records = df.to_dict(orient="records")
    rows = [SQLQueryRow(data=row) for row in records]

    return SQLQueryOutput(rows=rows, row_count=len(rows))
