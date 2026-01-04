# Spec: MPV Playback Navigation

## MODIFIED Requirements

### Shift+N Navigation
#### Scenario: Marking current episode as watched and moving to next
- **GIVEN** a video is playing in MPV via ani-tupi's IPC system
- **WHEN** the user presses `Shift+N`
- **THEN** the system MUST:
  1. Record the current episode as watched in the local history.
  2. Sync progress to AniList if the user is authenticated.
  3. Search for the next episode's stream URL.
  4. If found, command MPV to load the next episode's URL.
  5. If NOT found, display an OSD message "No more episodes available".
  6. Display an OSD message "Loading Episode [N]..." upon successful retrieval.
