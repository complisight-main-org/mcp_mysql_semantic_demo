"""MCP client: connect, discover tools, and call the semantic query tool."""
import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_URL = "http://127.0.0.1:8000/mcp"

async def main():
    async with streamable_http_client(MCP_URL) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Available MCP tools:")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")

            # This direct call demonstrates MCP. In an LLM-powered host,
            # the model would choose the tool and fill these arguments.
            result = await session.call_tool(
                "query_metrics",
                {
                    "metrics": ["error_rate", "request_count"],
                    "dimensions": ["tenant_id"],
                    "start_time": "2026-10-01T00:00:00",
                    "end_time": "2026-11-01T00:00:00",
                    "limit": 10,
                },
            )
            for item in result.content:
                if hasattr(item, "text"):
                    print(item.text)
                else:
                    print(item)

if __name__ == "__main__":
    asyncio.run(main())
