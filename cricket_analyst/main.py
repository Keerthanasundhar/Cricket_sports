"""CLI: python -m cricket_analyst.main ["question"]"""
import asyncio
import sys

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

from .graph import build_graph
from .observability import configure_tracing, setup_logging


async def amain(questions):
    client = MultiServerMCPClient({"cricket": {
        "command": sys.executable, "args": ["-m", "cricket_analyst.mcp_server"], "transport": "stdio"}})
    graph = build_graph(await client.get_tools())
    if questions:
        for q in questions:
            print((await graph.ainvoke({"query": q}))["answer"])
        return
    while True:
        q = input("\nAsk (blank to quit)> ").strip()
        if not q:
            break
        print((await graph.ainvoke({"query": q}))["answer"])


if __name__ == "__main__":
    load_dotenv()
    configure_tracing()
    setup_logging()
    asyncio.run(amain(sys.argv[1:]))
