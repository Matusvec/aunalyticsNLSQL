from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.services.mcp_client import MCPClient, MCPClientError, MCPToolExecutionError
from app.services.ollama_service import (
    choose_ask_next_step,
    choose_direct_query_step,
)
from mcp_sqlite.db_utils import build_schema_summary_impl


MAX_TOOL_STEPS = 3
MAX_TOOL_RESULT_CHARS = 4000


class ToolTrace(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result_preview: str
    structured_result: dict[str, Any] | None = None
    is_error: bool = False


class AskWithToolsResult(BaseModel):
    answer: str
    tool_calls: list[ToolTrace] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    limit_applied: int | None = None
    sql: str | None = None


def _format_tools_for_model(tools: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for tool in tools:
        input_schema = tool.get("inputSchema") or {}
        lines.append(
            json.dumps(
                {
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "input_schema": input_schema,
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(lines)


def _stringify_tool_result(result: dict[str, Any]) -> str:
    if result.get("structuredContent") is not None:
        text = json.dumps(result["structuredContent"], ensure_ascii=False, indent=2)
    else:
        content = result.get("content", [])
        text_parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        text = "\n".join(part for part in text_parts if part) or json.dumps(result, ensure_ascii=False, indent=2)

    if len(text) > MAX_TOOL_RESULT_CHARS:
        return text[:MAX_TOOL_RESULT_CHARS] + "\n...[truncated]"
    return text


def _extract_query_payload(result: dict[str, Any]) -> dict[str, Any] | None:
    structured = result.get("structuredContent")
    if isinstance(structured, dict) and {"columns", "rows", "row_count"} <= structured.keys():
        return structured

    content = result.get("content", [])
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not isinstance(text, str):
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and {"columns", "rows", "row_count"} <= parsed.keys():
            return parsed

    return None


async def ask_question_with_tools(question: str, db_filename: str, limit: int = 200) -> AskWithToolsResult:
    client = MCPClient()
    schema_summary = build_schema_summary_impl(db_filename)
    tool_traces: list[ToolTrace] = []
    latest_query_payload: dict[str, Any] | None = None
    latest_sql: str | None = None

    direct_plan = await choose_direct_query_step(
        question=question,
        db_filename=db_filename,
        limit=limit,
        schema_summary=schema_summary,
    )

    if direct_plan.action == "respond":
        return AskWithToolsResult(answer=direct_plan.answer, tool_calls=tool_traces)

    if direct_plan.action == "call_tool" and direct_plan.sql.strip():
        direct_sql = direct_plan.sql.strip()
        direct_arguments = {
            "db_filename": db_filename,
            "sql": direct_sql,
            "limit": limit,
        }
        latest_sql = direct_sql

        try:
            tool_result = await client.call_tool("run_sql_readonly", direct_arguments)
        except (MCPClientError, MCPToolExecutionError) as exc:
            tool_traces.append(
                ToolTrace(
                    tool_name="run_sql_readonly",
                    arguments=direct_arguments,
                    result_preview=str(exc),
                    structured_result=None,
                    is_error=True,
                )
            )
        else:
            latest_query_payload = _extract_query_payload(tool_result) or {}
            tool_traces.append(
                ToolTrace(
                    tool_name="run_sql_readonly",
                    arguments=direct_arguments,
                    result_preview=_stringify_tool_result(tool_result),
                    structured_result=tool_result.get("structuredContent")
                    if isinstance(tool_result.get("structuredContent"), dict)
                    else latest_query_payload,
                    is_error=bool(tool_result.get("isError")),
                )
            )
            return AskWithToolsResult(
                answer="",
                tool_calls=tool_traces,
                columns=latest_query_payload.get("columns", []),
                rows=latest_query_payload.get("rows", []),
                row_count=latest_query_payload.get("row_count", 0),
                limit_applied=latest_query_payload.get("limit_applied"),
                sql=latest_sql,
            )

    try:
        tools = await client.list_tools()
    except MCPClientError as exc:
        raise RuntimeError(f"Could not connect to MCP server at {client.server_url}: {exc}") from exc

    tool_catalog = _format_tools_for_model(tools)

    for _ in range(MAX_TOOL_STEPS):
        decision = await choose_ask_next_step(
            question=question,
            db_filename=db_filename,
            limit=limit,
            schema_summary=schema_summary,
            tool_catalog=tool_catalog,
            tool_history=[
                {
                    "tool_name": trace.tool_name,
                    "arguments": trace.arguments,
                    "result_preview": trace.result_preview,
                    "structured_result": trace.structured_result,
                    "is_error": trace.is_error,
                }
                for trace in tool_traces
            ],
        )

        if decision.action == "respond":
            return AskWithToolsResult(
                answer="",
                tool_calls=tool_traces,
                columns=(latest_query_payload or {}).get("columns", []),
                rows=(latest_query_payload or {}).get("rows", []),
                row_count=(latest_query_payload or {}).get("row_count", 0),
                limit_applied=(latest_query_payload or {}).get("limit_applied"),
                sql=latest_sql,
            )

        tool_name = decision.tool_name
        if not tool_name:
            raise RuntimeError("Model requested a tool call without a tool name")

        tool_arguments = dict(decision.tool_arguments)
        if tool_name in {
            "list_tables",
            "describe_table",
            "get_foreign_keys",
            "sample_rows",
            "run_sql_readonly",
        }:
            tool_arguments.setdefault("db_filename", db_filename)
        if tool_name == "run_sql_readonly":
            tool_arguments.setdefault("limit", limit)
            latest_sql = str(tool_arguments.get("sql", latest_sql or ""))

        try:
            tool_result = await client.call_tool(tool_name, tool_arguments)
        except (MCPClientError, MCPToolExecutionError) as exc:
            tool_traces.append(
                ToolTrace(
                    tool_name=tool_name,
                    arguments=tool_arguments,
                    result_preview=str(exc),
                    structured_result=None,
                    is_error=True,
                )
            )
            continue

        latest_query_payload = _extract_query_payload(tool_result) or latest_query_payload
        tool_traces.append(
            ToolTrace(
                tool_name=tool_name,
                arguments=tool_arguments,
                result_preview=_stringify_tool_result(tool_result),
                structured_result=tool_result.get("structuredContent")
                if isinstance(tool_result.get("structuredContent"), dict)
                else latest_query_payload,
                is_error=bool(tool_result.get("isError")),
            )
        )

    raise RuntimeError("Model did not finish the tool workflow within the allowed number of steps")
