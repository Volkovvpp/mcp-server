import argparse
from src.mcp.mcp import mcp_router
from src.core.logger import logger
from src.factory.singleton_factory import get_lclient, get_dclient


def parse_args():
    parser = argparse.ArgumentParser(description="MCP Server Launcher")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport type: stdio (default) or streamable-http",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP mode (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP mode (default: 8000)",
    )
    parser.add_argument(
        "--path",
        default="/",
        help="Path prefix for HTTP mode (default: /)",
    )
    return parser.parse_args()


async def shutdown_clients():
    """Корректно закрывает все singleton-клиенты перед завершением работы."""
    try:
        lclient = await get_lclient()
        await lclient.close()
    except Exception:
        pass

    try:
        dclient = await get_dclient()
        await dclient.close()
    except Exception:
        pass

    logger.info("🔻 Все DiscoveryApiClient корректно закрыты")


def main():
    args = parse_args()

    try:
        if args.transport == "stdio":
            logger.info("🚀 Starting Main MCP via stdio")
            mcp_router.run(transport="stdio", show_banner=True)

        else:
            logger.info(f"🚀 Starting Main MCP via HTTP at {args.host}:{args.port}{args.path}")
            mcp_router.run(
                transport="streamable-http",
                show_banner=True,
                host=args.host,
                port=args.port,
                path=args.path,
            )

    finally:
        # Здесь MCP run() уже завершился → корректно закрываем клиентов
        import asyncio
        asyncio.run(shutdown_clients())


if __name__ == "__main__":
    main()


# Через stdio
# python -m src.main --transport stdio
# Через HTTP
# python -m src.main --transport streamable-http --host 127.0.0.1 --port 8000 --path /api