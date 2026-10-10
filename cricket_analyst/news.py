"""Tavily-backed news retrieval with freshness checking."""
import os

from .guardrails import assess_freshness


class NewsClient:
    def __init__(self):
        key = os.getenv("TAVILY_API_KEY")
        self.client = None
        if key:
            from tavily import TavilyClient
            self.client = TavilyClient(api_key=key)

    @property
    def available(self):
        return self.client is not None

    def search(self, queries, days=2, max_results=6):
        """Run queries, de-duplicate by URL, annotate freshness. Sync (call via to_thread)."""
        seen, results = set(), []
        for q in queries:
            resp = self.client.search(query=q, topic="news", days=days, max_results=max_results)
            for r in resp.get("results", []):
                if r["url"] not in seen:
                    seen.add(r["url"]); results.append(r)
        return assess_freshness(results)
