"""Isolated incremental search debugger with a fake repository."""

from __future__ import annotations

import os
from contextlib import contextmanager
from unittest.mock import Mock, patch

from services.anime.search import incremental_search_anime


class FakeRepository:
    """Minimal fake repository for exercising incremental search behavior."""

    def __init__(self) -> None:
        self.search_results: dict[str, list[str]] = {}
        self.search_calls: list[str] = []
        self._last_query = ""
        self._last_results: list[str] = []

    def setup_search_result(self, query: str, results: list[str]) -> None:
        self.search_results[query.lower()] = results

    def clear_search_results(self) -> None:
        return None

    def search_anime(self, query: str, verbose: bool = True) -> None:
        self.search_calls.append(query)
        self._last_query = query
        self._last_results = self.search_results.get(query.lower(), [])

    def get_search_metadata(self):
        return Mock(used_query=self._last_query)

    def get_anime_titles_with_sources(self, filter_by_query=None, original_query=None):
        return self._last_results


@contextmanager
def fake_loading(_message: str):
    yield


def build_hime_repository() -> FakeRepository:
    """Scenario matching the user's report: broad 'hime' search, refined rescue via re-search."""
    repo = FakeRepository()
    repo.setup_search_result(
        "hime",
        [
            "chimera [dattebayo]",
            "himegoto [animesdigital, animesonlinecc, dattebayo]",
            "arete hime [dattebayo]",
            "koihime musou [animesonlinecc]",
            "mushikaburi hime [animefire, animesonlinecc]",
            "chou kaguya hime [animefire, dattebayo]",
            "kyuuketsuhime miyu [animefire]",
            "shikabane hime aka [animesdigital, animesonlinecc]",
            "hanyou no yashahime [dattebayo]",
            "shikabane hime kuro [animesdigital]",
            "tensui no sakuna hime [animefire, animesdigital, animesonlinecc, anitube]",
            "koihimemusou ova omake [animefire]",
            "niehime to kemono no ou [animefire, animesdigital, animesonlinecc]",
            "ryuu to sobakasu no hime [animefire]",
            "akagami no shirayuki hime [animesdigital, animesonlinecc, dattebayo]",
            "choushin hime dangaizer 3 [dattebayo]",
            "andersen douwa ningyohime [dattebayo]",
            "kuragehime eiyuu retsuden [animefire]",
            "akagami no shirayuki hime 2 [animesdigital]",
            "hanyou no yashahime dublado [dattebayo]",
            "T1",
            "T2",
            "T3",
            "T4",
            "T5",
            "T6",
            "T7",
            "T8",
            "T9",
            "T10",
            "T11",
            "T12",
            "T13",
            "T14",
            "T15",
            "T16",
            "T17",
            "T18",
            "T19",
            "T20",
            "T21",
        ],
    )
    repo.setup_search_result(
        "hime kishi",
        ["Hime Kishi wa Barbaroi no Yome [animefire]"],
    )
    return repo


def build_hime_late_match_repository() -> FakeRepository:
    """Scenario where intermediate refined searches are empty until a later phrase."""
    repo = FakeRepository()
    repo.setup_search_result(
        "hime",
        [
            "chimera [dattebayo]",
            "himegoto [animesdigital, animesonlinecc, dattebayo]",
            "arete hime [dattebayo]",
            "koihime musou [animesonlinecc]",
            "mushikaburi hime [animefire, animesonlinecc]",
            "chou kaguya hime [animefire, dattebayo]",
            "kyuuketsuhime miyu [animefire]",
            "shikabane hime aka [animesdigital, animesonlinecc]",
            "hanyou no yashahime [dattebayo]",
            "shikabane hime kuro [animesdigital]",
            "tensui no sakuna hime [animefire, animesdigital, animesonlinecc, anitube]",
            "koihimemusou ova omake [animefire]",
            "niehime to kemono no ou [animefire, animesdigital, animesonlinecc]",
            "ryuu to sobakasu no hime [animefire]",
            "akagami no shirayuki hime [animesdigital, animesonlinecc, dattebayo]",
            "choushin hime dangaizer 3 [dattebayo]",
            "andersen douwa ningyohime [dattebayo]",
            "kuragehime eiyuu retsuden [animefire]",
            "akagami no shirayuki hime 2 [animesdigital]",
            "hanyou no yashahime dublado [dattebayo]",
            "T1",
            "T2",
            "T3",
            "T4",
            "T5",
            "T6",
            "T7",
            "T8",
            "T9",
            "T10",
            "T11",
            "T12",
            "T13",
            "T14",
            "T15",
            "T16",
            "T17",
            "T18",
            "T19",
            "T20",
            "T21",
        ],
    )
    repo.setup_search_result("hime kishi", [])
    repo.setup_search_result("hime kishi wa", [])
    repo.setup_search_result(
        "hime kishi wa barbaroi",
        ["Hime Kishi wa Barbaroi no Yome [animefire]"],
    )
    return repo


def run_scenario(name: str, repo: FakeRepository, query: str) -> None:
    print(f"\n=== {name} ===")
    print(f"query: {query}")
    os.environ["ANI_TUPI_DEBUG_INCREMENTAL_SEARCH"] = "1"

    with (
        patch("services.anime.search.rep", repo),
        patch("services.anime.search.loading", fake_loading),
        patch(
            "utils.anilist_discovery.auto_discover_anilist_id",
            side_effect=Exception("debug mode"),
        ),
    ):
        state, results = incremental_search_anime(query)

    current = state.get_current()
    print(f"search_calls: {repo.search_calls}")
    if current:
        print(
            "final_state:",
            {
                "word_count": current.word_count,
                "query": current.query,
                "used_query": current.used_query,
                "results": len(current.results),
            },
        )
    print("final_results:", results[:5], "..." if len(results) > 5 else "")


if __name__ == "__main__":
    run_scenario(
        "hime_case",
        build_hime_repository(),
        "Hime Kishi wa Barbaroi no Yome",
    )
    run_scenario(
        "hime_late_match_case",
        build_hime_late_match_repository(),
        "Hime Kishi wa Barbaroi no Yome",
    )
