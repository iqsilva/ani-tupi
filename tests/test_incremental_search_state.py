"""Unit tests for IncrementalSearchState class."""

import pytest
from services.anime_service import SearchResultSet, IncrementalSearchState


class TestSearchResultSet:
    """Tests for SearchResultSet dataclass."""

    def test_create_valid_result_set(self):
        """Test creating a valid SearchResultSet."""
        results = ["Anime 1 - Source1", "Anime 2 - Source2"]
        result_set = SearchResultSet(
            word_count=3,
            query="boku no hero",
            results=results,
            source_counts={"Source1": 1, "Source2": 1}
        )
        assert result_set.word_count == 3
        assert result_set.query == "boku no hero"
        assert result_set.results == results
        assert result_set.source_counts == {"Source1": 1, "Source2": 1}

    def test_invalid_word_count_zero(self):
        """Test that zero word count raises ValueError."""
        with pytest.raises(ValueError, match="word_count must be positive"):
            SearchResultSet(
                word_count=0,
                query="test",
                results=[]
            )

    def test_invalid_word_count_negative(self):
        """Test that negative word count raises ValueError."""
        with pytest.raises(ValueError, match="word_count must be positive"):
            SearchResultSet(
                word_count=-1,
                query="test",
                results=[]
            )

    def test_default_source_counts(self):
        """Test that source_counts defaults to empty dict."""
        result_set = SearchResultSet(
            word_count=1,
            query="anime",
            results=["Test"]
        )
        assert result_set.source_counts == {}


class TestIncrementalSearchState:
    """Tests for IncrementalSearchState class."""

    def test_create_empty_state(self):
        """Test creating an empty search state."""
        state = IncrementalSearchState()
        assert state.search_history == []
        assert state.current_index == -1
        assert state.get_current() is None
        assert not state.has_previous()
        assert not state.has_next()

    def test_add_single_result(self):
        """Test adding a single result."""
        state = IncrementalSearchState()
        results = ["Anime 1 - Source1"]
        state.add_result(3, "boku no hero", results)

        assert len(state.search_history) == 1
        assert state.current_index == 0
        current = state.get_current()
        assert current is not None
        assert current.word_count == 3
        assert current.query == "boku no hero"
        assert current.results == results

    def test_add_multiple_results_sequential(self):
        """Test adding multiple results sequentially."""
        state = IncrementalSearchState()

        # Add 3-word result
        state.add_result(3, "boku no hero", ["Anime 1", "Anime 2"])
        assert state.current_index == 0

        # Add 4-word result
        state.add_result(4, "boku no hero academia", ["Anime 1", "Anime 2", "Anime 3"])
        assert state.current_index == 1

        # Add 5-word result
        state.add_result(5, "boku no hero academia 5", ["Anime 1"])
        assert state.current_index == 2

        assert len(state.search_history) == 3

    def test_go_back_from_end(self):
        """Test navigating backward from end of history."""
        state = IncrementalSearchState()
        state.add_result(3, "boku no hero", ["A"])
        state.add_result(4, "boku no hero academia", ["A", "B"])
        state.add_result(5, "boku no hero academia 5", ["A"])

        # Navigate backward
        prev = state.go_back()
        assert prev is not None
        assert prev.word_count == 4
        assert state.current_index == 1

        # Navigate backward again
        prev = state.go_back()
        assert prev is not None
        assert prev.word_count == 3
        assert state.current_index == 0

    def test_go_back_at_beginning(self):
        """Test that go_back returns None at beginning."""
        state = IncrementalSearchState()
        state.add_result(3, "boku no hero", ["A"])

        prev = state.go_back()
        assert prev is None
        assert state.current_index == 0

    def test_go_forward_after_backward(self):
        """Test navigating forward after going backward."""
        state = IncrementalSearchState()
        state.add_result(3, "boku no hero", ["A"])
        state.add_result(4, "boku no hero academia", ["A", "B"])
        state.add_result(5, "boku no hero academia 5", ["A"])

        # Go backward twice
        state.go_back()
        state.go_back()
        assert state.current_index == 0

        # Go forward
        next_result = state.go_forward()
        assert next_result is not None
        assert next_result.word_count == 4
        assert state.current_index == 1

    def test_go_forward_at_end(self):
        """Test that go_forward returns None at end."""
        state = IncrementalSearchState()
        state.add_result(3, "boku no hero", ["A"])

        forward = state.go_forward()
        assert forward is None
        assert state.current_index == 0

    def test_has_previous_boundary(self):
        """Test has_previous at boundaries."""
        state = IncrementalSearchState()
        state.add_result(3, "test1", ["A"])
        assert not state.has_previous()

        state.add_result(4, "test2", ["B"])
        assert state.has_previous()

        state.go_back()
        assert not state.has_previous()

    def test_has_next_boundary(self):
        """Test has_next at boundaries."""
        state = IncrementalSearchState()
        state.add_result(3, "test1", ["A"])
        state.add_result(4, "test2", ["B"])

        assert not state.has_next()

        state.go_back()
        assert state.has_next()

    def test_navigate_discard_forward_history(self):
        """Test that adding after backward navigation discards forward history."""
        state = IncrementalSearchState()
        state.add_result(3, "test1", ["A"])
        state.add_result(4, "test2", ["B"])
        state.add_result(5, "test3", ["C"])

        # Navigate backward twice
        state.go_back()
        state.go_back()
        assert state.current_index == 0
        assert len(state.search_history) == 3

        # Add new result (should discard the 5-word result)
        state.add_result(4, "test2_new", ["D"])
        assert len(state.search_history) == 2
        assert state.current_index == 1
        assert state.get_current().query == "test2_new"

    def test_clear(self):
        """Test clearing state."""
        state = IncrementalSearchState()
        state.add_result(3, "test", ["A"])
        state.add_result(4, "test2", ["B"])

        state.clear()
        assert state.search_history == []
        assert state.current_index == -1
        assert state.get_current() is None

    def test_repr(self):
        """Test string representation."""
        state = IncrementalSearchState()
        state.add_result(3, "test", ["A", "B"])
        repr_str = repr(state)

        assert "IncrementalSearchState" in repr_str
        assert "3 words" in repr_str
        assert "2 results" in repr_str

    def test_repr_empty(self):
        """Test repr with empty state."""
        state = IncrementalSearchState()
        repr_str = repr(state)

        assert "IncrementalSearchState" in repr_str
        assert "none" in repr_str
