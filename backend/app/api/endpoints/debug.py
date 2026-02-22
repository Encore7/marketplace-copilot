from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from ...observability.logging import get_logger
from ...tools.sql_tool import SQLQueryInput, SQLQueryOutput, run_sql_query

logger = get_logger("api.debug")

router = APIRouter(prefix="/debug", tags=["debug"])


class DebugSQLRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    query: str = Field(..., description="Read-only SQL query against allowed tables.")


@router.post(
    "/sql",
    response_model=SQLQueryOutput,
    summary="Run safe read-only SQL for local debugging/demo.",
)
async def debug_sql(payload: DebugSQLRequest) -> SQLQueryOutput:
    try:
        return run_sql_query(SQLQueryInput(query=payload.query))
    except Exception as exc:
        logger.error("Debug SQL query failed", extra={"error": str(exc)})
        raise HTTPException(status_code=400, detail=str(exc)) from exc
