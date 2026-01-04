import pytest
from unittest.mock import MagicMock, patch
import json
import subprocess
from utils.video_player import _ipc_event_loop, VideoPlaybackResult

@pytest.mark.unit
def test_ipc_event_loop_mark_next():
    # Mock MPV process
    mock_process = MagicMock(spec=subprocess.Popen)
    mock_process.poll.side_effect = [None, None, 0] # Run twice then exit
    mock_process.returncode = 0
    
    # Mock socket
    mock_sock = MagicMock()
    # Initial connection messages (JSON-RPC)
    # 1. client-message with mark-next
    msg = json.dumps({"event": "client-message", "args": ["mark-next"]}) + "\n"
    mock_sock.recv.side_effect = [msg.encode("utf-8"), b""]
    
    # Mock Repository and HistoryService
    with patch("services.repository.rep") as mock_rep, \
         patch("services.history_service.save_history_from_event") as mock_save, \
         patch("platform.system", return_value="Linux"), \
         patch("socket.socket", return_value=mock_sock):
        
        # Setup repository mock
        mock_rep.search_player.return_value = "http://example.com/next_ep"
        
        episode_context = {
            "anime_title": "Test Anime",
            "episode_number": 1,
            "source": "test_source",
            "url": "http://example.com/ep1",
            "anilist_id": 123
        }
        
        result = _ipc_event_loop(mock_process, "/tmp/test.sock", episode_context)
        
        # Verify history was saved
        mock_save.assert_called_once_with(
            anime_title="Test Anime",
            episode_idx=0,
            action="watched",
            source="test_source",
            anilist_id=123
        )
        
        # Verify repository was searched for next episode
        mock_rep.search_player.assert_called_once_with("Test Anime", 2)
        
        # Verify MPV commands were sent (loadfile and show-text)
        # _send_mpv_command is called several times
        # We check if loadfile for next_url was sent
        sent_messages = [json.loads(call.args[0].decode("utf-8"))["command"] 
                        for call in mock_sock.sendall.call_args_list]
        
        assert ["loadfile", "http://example.com/next_ep", "replace"] in sent_messages
        
        # Context should be updated
        assert episode_context["episode_number"] == 2
        assert episode_context["url"] == "http://example.com/next_ep"
        
        assert result.action == "quit" # Final action after process exit

@pytest.mark.unit
def test_save_history_anilist_sync():
    from services.history_service import save_history_from_event
    
    with patch("services.anilist_service.anilist_client") as mock_anilist, \
         patch("services.history_service._history_store") as mock_store, \
         patch("services.repository.rep") as mock_rep:
        
        mock_anilist.is_authenticated.return_value = True
        mock_anilist.get_media_list_entry.return_value = None # Not in list
        mock_anilist.update_progress.return_value = True
        
        save_history_from_event(
            anime_title="Test Anime",
            episode_idx=4, # Episode 5
            action="watched",
            source="test_source",
            anilist_id=123
        )
        
        # Should add to list first
        mock_anilist.add_to_list.assert_called_once_with(123, "CURRENT")
        # Then update progress
        mock_anilist.update_progress.assert_called_once_with(123, 5)
