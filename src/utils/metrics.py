from functools import wraps
from time import perf_counter
from typing import Any, Callable

from src.core.logger import logger
from src.db.mongo.mongo import save_metric_to_mongo


def trace_tool(fn: Callable):
    @wraps(fn)
    async def wrapped(*args: Any, **kwargs: Any) -> dict[str, Any]:
        tool_name = fn.__name__
        context = kwargs.get("params") or (args[0] if args else None)
        context_dict = context.model_dump() if context else {}

        start = perf_counter()
        try:
            result = await fn(*args, **kwargs)
            duration = perf_counter() - start

            save_metric_to_mongo({
                "tool_name": tool_name,
                "status": "success",
                "duration": duration,
                "context": context_dict,
                "result_count": result.get("result_count") if isinstance(result, dict) else None,
            })

            logger.info(
                f"[MCP TOOL SUCCESS] {tool_name} took {duration:.3f}s, context={context_dict}"
            )
            return result

        except Exception as exc:
            duration = perf_counter() - start


            save_metric_to_mongo({
                "tool_name": tool_name,
                "status": "failure",
                "duration": duration,
                "context": context_dict,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            })

            logger.error(
                f"[MCP TOOL FAILURE] {tool_name} took {duration:.3f}s, error={exc}, context={context_dict}"
            )

            return {"error": {"type": type(exc).__name__, "message": str(exc)}}

    return wrapped
