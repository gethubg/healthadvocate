"""Tests for the food advisor (search + synthesis mocked)."""

from __future__ import annotations

from healthadvocate.advisor.ddg_search import SearchResult
from healthadvocate.advisor.food_advisor import FoodAdvisor, build_query
from healthadvocate.models import AbnormalFinding, Direction


class FakeSearch:
    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results
        self.queries: list[str] = []

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        self.queries.append(query)
        return self._results


class FakeSynth:
    def __init__(self, foods: list[str]) -> None:
        self._foods = foods
        self.calls: list[tuple[str, Direction, int]] = []

    def synthesize(self, parameter, direction, results) -> list[str]:
        self.calls.append((parameter, direction, len(results)))
        return self._foods


def _finding(name="Sodium", direction=Direction.HIGH) -> AbnormalFinding:
    return AbnormalFinding(
        parameter=name, value=148, unit="mmol/L",
        ref_low=135, ref_high=145, direction=direction,
    )


def test_build_query_high_vs_low():
    assert "lower high Sodium" in build_query(_finding(direction=Direction.HIGH))
    assert "Sodium is low" in build_query(_finding(direction=Direction.LOW))


def test_advise_returns_foods_and_sources():
    results = [
        SearchResult("Salt and sodium", "https://ex.com/a", "Avoid processed meats..."),
        SearchResult("Low-sodium diet", "https://ex.com/b", "Limit canned soups..."),
    ]
    advisor = FoodAdvisor(FakeSearch(results), FakeSynth(["Processed meats", "Canned soups"]))

    advice = advisor.advise(_finding())

    assert advice.parameter == "Sodium"
    assert advice.foods_to_avoid == ["Processed meats", "Canned soups"]
    assert [s.url for s in advice.sources] == ["https://ex.com/a", "https://ex.com/b"]


def test_advise_degrades_gracefully_when_no_results():
    synth = FakeSynth(["should not be called"])
    advisor = FoodAdvisor(FakeSearch([]), synth)

    advice = advisor.advise(_finding())

    assert advice.foods_to_avoid == []
    assert advice.sources == []
    assert synth.calls == []  # synthesizer skipped entirely


def test_advise_all_maps_each_finding():
    results = [SearchResult("t", "https://ex.com/x", "snippet")]
    search = FakeSearch(results)
    advisor = FoodAdvisor(search, FakeSynth(["Food"]))

    findings = [_finding("Sodium", Direction.HIGH), _finding("Glucose", Direction.LOW)]
    out = advisor.advise_all(findings)

    assert [a.parameter for a in out] == ["Sodium", "Glucose"]
    assert len(search.queries) == 2


def test_sources_drop_entries_without_url():
    results = [
        SearchResult("has url", "https://ex.com/a", "s"),
        SearchResult("no url", "", "s"),
    ]
    advisor = FoodAdvisor(FakeSearch(results), FakeSynth(["Food"]))

    advice = advisor.advise(_finding())

    assert len(advice.sources) == 1
    assert advice.sources[0].url == "https://ex.com/a"
