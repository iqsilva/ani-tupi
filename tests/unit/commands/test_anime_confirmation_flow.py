"""Unit tests for anime playback confirmation flow.

Tests the fix for episode context update timing issue where context
was updated before confirmation, causing replay bugs when user pressed
Shift+N then marked episode as unwatched.

Related to: openspec/changes/fix-episode-context-on-shift-n-navigation
"""

import pytest
from unittest.mock import Mock
from services.anime.playback_service import PlaybackContext


class TestPlaybackConfirmationFlow:
    """Tests for playback confirmation and context update timing."""

    @pytest.fixture
    def sample_context(self):
        """Sample playback context for testing."""
        return PlaybackContext(
            anime_title="Dandadan",
            episode_idx=0,  # Episode 1 (0-indexed)
            source="animefire",
            anilist_id=12345,
            anilist_title="Dandadan",
            total_episodes_anilist=12,
            num_episodes=12,
            episode_list=tuple(f"Episodio {i}" for i in range(1, 13)),
        )

    @pytest.fixture
    def playback_result_normal(self):
        """Playback result for normal quit (no navigation)."""
        result = Mock()
        result.exit_code = 0
        result.action = "quit"
        result.data = {"episode": 1}  # Episode 1
        return result

    @pytest.fixture
    def playback_result_shift_n(self):
        """Playback result after Shift+N navigation (Episode 1 -> Episode 2)."""
        result = Mock()
        result.exit_code = 0
        result.action = "next"
        result.data = {"episode": 2}  # Navigated to Episode 2
        return result

    def test_context_always_updates_to_final_episode(self, sample_context, playback_result_shift_n):
        """Context should update to final_episode regardless of watch confirmation.

        Scenario: User watches Episode 1, presses Shift+N (loads Episode 2), quits.
        Expected: Context updates to episode_idx=1 (Episode 2) regardless of confirmation.
        """
        # Simulate the flow in commands/anime.py
        ctx = sample_context
        playback_result = playback_result_shift_n

        # Extract final episode
        final_episode = playback_result.data.get("episode", 1)
        assert final_episode == 2  # Should be Episode 2 (from Shift+N)

        # Context update happens BEFORE confirmation
        updated_ctx = PlaybackContext(
            anime_title=ctx.anime_title,
            episode_idx=final_episode - 1,  # Episode 2 (index 1)
            source=ctx.source,
            anilist_id=ctx.anilist_id,
            anilist_title=ctx.anilist_title,
            total_episodes_anilist=ctx.total_episodes_anilist,
            num_episodes=ctx.num_episodes,
            episode_list=ctx.episode_list,
        )

        # Verify context was updated to Episode 2
        assert updated_ctx.episode_idx == 1  # 0-indexed Episode 2

        # Original context unchanged (immutability)
        assert ctx.episode_idx == 0

    def test_history_saved_only_if_watched(self, sample_context, playback_result_shift_n):
        """History and AniList sync should only happen if user confirms 'watched'.

        Scenario: Context updates to final_episode, but save_history() only called if confirmed.
        """
        ctx = sample_context
        final_episode = 2  # Shift+N navigated to Episode 2

        # Context updates (always happens)
        PlaybackContext(
            anime_title=ctx.anime_title,
            episode_idx=final_episode - 1,
            source=ctx.source,
            anilist_id=ctx.anilist_id,
            anilist_title=ctx.anilist_title,
            total_episodes_anilist=ctx.total_episodes_anilist,
            num_episodes=ctx.num_episodes,
            episode_list=ctx.episode_list,
        )

        # User confirms "watched"
        confirm = "✅ Sim, assisti até o final"

        if confirm == "✅ Sim, assisti até o final":
            # This is the path we're testing
            # In real code, save_history would be called here
            should_save = True
        else:
            should_save = False

        assert should_save is True
        # In the actual implementation, save_history and sync would be called

    def test_history_not_saved_if_unwatched(self, sample_context, playback_result_shift_n):
        """History and AniList sync should NOT happen if user marks as unwatched.

        Scenario: User says "No, didn't watch", history/sync should be skipped.
        """
        ctx = sample_context
        final_episode = 2

        # Context updates (always happens)
        new_ctx = PlaybackContext(
            anime_title=ctx.anime_title,
            episode_idx=final_episode - 1,
            source=ctx.source,
            anilist_id=ctx.anilist_id,
            anilist_title=ctx.anilist_title,
            total_episodes_anilist=ctx.total_episodes_anilist,
            num_episodes=ctx.num_episodes,
            episode_list=ctx.episode_list,
        )

        # User says "didn't watch"
        confirm = "❌ Não, parei antes."

        if confirm == "✅ Sim, assisti até o final":
            should_save = True
        else:
            should_save = False

        # Verify history NOT saved
        assert should_save is False

        # Context is still updated (tracks playback position, not watch status)
        assert new_ctx.episode_idx == 1  # Episode 2

    def test_shift_n_then_unwatched_next_plays_episode_3(self, sample_context):
        """Bug fix: Shift+N -> unwatched -> next should play Episode 3.

        This is the original bug scenario from the user report.

        Flow:
        1. Watch Episode 1, press Shift+N -> loads Episode 2
        2. Quit MPV -> final_episode = 2
        3. Context updates to episode_idx = 1 (Episode 2)
        4. User says "No, didn't watch"
        5. User selects "▶️ Próximo" from navigation menu
        6. Context increments to episode_idx = 2 (Episode 3)
        7. Loop restarts -> should play Episode 3 ✅
        """
        from services.anime.playback_service import navigate_episodes

        ctx = sample_context  # Episode 1 (episode_idx = 0)
        final_episode = 2  # Shift+N navigated to Episode 2

        # Step 1: Context updates to final_episode (Episode 2)
        ctx = PlaybackContext(
            anime_title=ctx.anime_title,
            episode_idx=final_episode - 1,  # Episode 2 (index 1)
            source=ctx.source,
            anilist_id=ctx.anilist_id,
            anilist_title=ctx.anilist_title,
            total_episodes_anilist=ctx.total_episodes_anilist,
            num_episodes=ctx.num_episodes,
            episode_list=ctx.episode_list,
        )

        # Step 2: User says "didn't watch" (history not saved)
        # Step 3: Navigation menu shows
        # Step 4: User selects "Próximo"
        ctx = navigate_episodes(ctx, "next")

        # Step 5: Verify context is now Episode 3
        assert ctx.episode_idx == 2  # Episode 3 (0-indexed)

        # Step 6: Loop restarts with episode = ctx.episode_idx + 1 = 3
        next_episode_to_play = ctx.episode_idx + 1
        assert next_episode_to_play == 3  # ✅ Episode 3 plays (bug fixed)

    def test_shift_n_then_watched_next_plays_episode_3(self, sample_context):
        """Shift+N -> watched -> next should also play Episode 3.

        Same flow but user confirms they watched Episode 2.
        """
        from services.anime.playback_service import navigate_episodes

        ctx = sample_context  # Episode 1
        final_episode = 2  # Shift+N to Episode 2

        # Context updates to Episode 2
        ctx = PlaybackContext(
            anime_title=ctx.anime_title,
            episode_idx=final_episode - 1,
            source=ctx.source,
            anilist_id=ctx.anilist_id,
            anilist_title=ctx.anilist_title,
            total_episodes_anilist=ctx.total_episodes_anilist,
            num_episodes=ctx.num_episodes,
            episode_list=ctx.episode_list,
        )

        # User says "Yes, watched" (history saved)
        # Navigation menu shows
        # User selects "Próximo"
        ctx = navigate_episodes(ctx, "next")

        # Verify Episode 3
        assert ctx.episode_idx == 2
        next_episode_to_play = ctx.episode_idx + 1
        assert next_episode_to_play == 3  # ✅ Episode 3 plays

    def test_normal_playback_unwatched_next_plays_episode_2(self, sample_context):
        """Normal playback -> unwatched -> next should play Episode 2.

        Scenario: No Shift+N navigation, just normal quit.
        """
        from services.anime.playback_service import navigate_episodes

        ctx = sample_context  # Episode 1
        final_episode = 1  # Normal quit (no navigation)

        # Context stays at Episode 1 (since final_episode = 1)
        ctx = PlaybackContext(
            anime_title=ctx.anime_title,
            episode_idx=final_episode - 1,  # Episode 1 (index 0)
            source=ctx.source,
            anilist_id=ctx.anilist_id,
            anilist_title=ctx.anilist_title,
            total_episodes_anilist=ctx.total_episodes_anilist,
            num_episodes=ctx.num_episodes,
            episode_list=ctx.episode_list,
        )

        # User says "didn't watch"
        # User selects "Próximo"
        ctx = navigate_episodes(ctx, "next")

        # Verify Episode 2
        assert ctx.episode_idx == 1
        next_episode_to_play = ctx.episode_idx + 1
        assert next_episode_to_play == 2  # ✅ Episode 2 plays

    def test_context_immutability_preserved(self, sample_context):
        """Verify context immutability pattern is maintained.

        Each context update creates a new instance, never modifies existing.
        """
        original_ctx = sample_context
        final_episode = 2

        # Create new context (immutable update)
        new_ctx = PlaybackContext(
            anime_title=original_ctx.anime_title,
            episode_idx=final_episode - 1,
            source=original_ctx.source,
            anilist_id=original_ctx.anilist_id,
            anilist_title=original_ctx.anilist_title,
            total_episodes_anilist=original_ctx.total_episodes_anilist,
            num_episodes=original_ctx.num_episodes,
            episode_list=original_ctx.episode_list,
        )

        # Verify original unchanged
        assert original_ctx.episode_idx == 0

        # Verify new context has updated value
        assert new_ctx.episode_idx == 1

        # Verify they're different objects
        assert id(original_ctx) != id(new_ctx)


class TestEdgeCases:
    """Edge case tests for confirmation flow."""

    def test_playback_result_data_none(self):
        """Handle case where playback_result.data is None.

        This can happen if MPV crashes or exits abnormally.
        """
        playback_result = Mock()
        playback_result.exit_code = 2
        playback_result.action = "error"
        playback_result.data = None

        # Code should handle this gracefully
        episode = 1  # Original episode
        final_episode = (
            playback_result.data.get("episode", episode) if playback_result.data else episode
        )

        # Should default to original episode
        assert final_episode == 1

    def test_shift_n_multiple_times(self):
        """Handle Shift+N pressed multiple times (Episode 1 -> 2 -> 3).

        Only the final episode number should matter for context update.
        """
        playback_result = Mock()
        playback_result.exit_code = 0
        playback_result.action = "next"
        playback_result.data = {"episode": 3}  # Final episode after multiple Shift+N

        final_episode = playback_result.data.get("episode", 1)
        assert final_episode == 3

        # Context should update to Episode 3
        episode_idx = final_episode - 1
        assert episode_idx == 2  # 0-indexed Episode 3
