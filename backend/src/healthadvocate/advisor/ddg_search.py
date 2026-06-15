"""DuckDuckGo web search (no API key required).

``SearchClient`` is the injectable boundary; ``DuckDuckGoSearchClient`` is the
real implementation backed by the duckduckgo-search package. Results carry a
snippet for synthesis plus title/url for citation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchClient(Protocol):
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]: ...


class DuckDuckGoSearchClient:
    """Live DuckDuckGo text search. Degrades to an empty list on failure."""

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        # The package was renamed duckduckgo_search -> ddgs; prefer the new name.
        try:
            from ddgs import DDGS
        except ImportError:  # pragma: no cover - fallback for older installs
            from duckduckgo_search import DDGS

        try:
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=max_results))
        except Exception:
            # Network/rate-limit issues should not break the /ask response;
            # the advisor degrades to "no advice" rather than erroring.
            return []

        return [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("href", ""),
                snippet=item.get("body", ""),
            )
            for item in (raw or [])
        ]
