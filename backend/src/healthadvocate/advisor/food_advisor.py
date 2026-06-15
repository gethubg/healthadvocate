"""Conditional 'foods to avoid' advisory for abnormal lab values.

Triggered only for parameters the analyzer flagged abnormal (bounded web calls).
For each finding it runs a DuckDuckGo search and asks an LLM to extract a concise
list of foods to avoid, citing the sources used.

Both the search and the LLM synthesis are injectable so the orchestration is
unit-testable without network access.
"""

from __future__ import annotations

from typing import Protocol

from healthadvocate.advisor.ddg_search import DuckDuckGoSearchClient, SearchClient, SearchResult
from healthadvocate.config import Settings
from healthadvocate.models import AbnormalFinding, Direction, FoodAdvice, Source


class AdviceSynthesizer(Protocol):
    """Turns search results into a list of foods to avoid for a parameter."""

    def synthesize(
        self, parameter: str, direction: Direction, results: list[SearchResult]
    ) -> list[str]: ...


def build_query(finding: AbnormalFinding) -> str:
    """Compose the web query for a finding.

    HIGH values → how to lower; LOW values → what to avoid when deficient.
    """
    if finding.direction is Direction.HIGH:
        return f"foods to avoid to lower high {finding.parameter}"
    return f"foods to avoid when {finding.parameter} is low"


class FoodAdvisor:
    def __init__(
        self,
        search_client: SearchClient,
        synthesizer: AdviceSynthesizer,
        max_results: int = 5,
    ) -> None:
        self._search = search_client
        self._synthesizer = synthesizer
        self._max_results = max_results

    def advise(self, finding: AbnormalFinding) -> FoodAdvice:
        """Produce advice for a single abnormal finding."""
        results = self._search.search(build_query(finding), max_results=self._max_results)
        if not results:
            # Graceful degradation — no sources, no advice, but no error.
            return FoodAdvice(parameter=finding.parameter, foods_to_avoid=[], sources=[])

        foods = self._synthesizer.synthesize(finding.parameter, finding.direction, results)
        sources = [Source(title=r.title, url=r.url) for r in results if r.url]
        return FoodAdvice(
            parameter=finding.parameter,
            foods_to_avoid=foods,
            sources=sources,
        )

    def advise_all(self, findings: list[AbnormalFinding]) -> list[FoodAdvice]:
        return [self.advise(f) for f in findings]


class LangChainAdviceSynthesizer:
    """Real synthesis path: LangChain + OpenAI over the search snippets."""

    _PROMPT = (
        "You are a careful nutrition assistant. Based ONLY on the search snippets "
        "below, list specific foods a person should AVOID when their {parameter} is "
        "{direction}. Return a short newline-separated list of foods (no numbering, "
        "no commentary). If the snippets do not support any, return nothing.\n\n"
        "Search snippets:\n{snippets}"
    )

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def synthesize(
        self, parameter: str, direction: Direction, results: list[SearchResult]
    ) -> list[str]:
        from langchain_openai import ChatOpenAI

        snippets = "\n".join(f"- {r.title}: {r.snippet}" for r in results)
        prompt = self._PROMPT.format(
            parameter=parameter, direction=direction.value, snippets=snippets
        )
        llm = ChatOpenAI(
            model=self._settings.openai_llm_model,
            api_key=self._settings.openai_api_key,
            temperature=0,
        )
        text = llm.invoke(prompt).content
        return [line.strip("-• ").strip() for line in str(text).splitlines() if line.strip()]


def build_default_advisor(settings: Settings) -> FoodAdvisor:
    """Wire the production advisor (live DuckDuckGo + LangChain/OpenAI)."""
    return FoodAdvisor(
        search_client=DuckDuckGoSearchClient(),
        synthesizer=LangChainAdviceSynthesizer(settings),
    )
