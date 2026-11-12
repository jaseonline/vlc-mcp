# Changelog

All notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/).

## Unreleased

### Added

- 18 new MCP tools, bringing the total to 26:
  - Transport: `set_playback_rate`, `set_aspect_ratio`, `set_sync_delay`.
  - Tracks: `get_tracks`, `select_track`, `add_subtitle`.
  - Playlist: `get_playlist`, `enqueue_video`, `play_playlist_item`, `remove_playlist_item`, `clear_playlist`, `sort_playlist`, `toggle_playlist_mode`.
  - Equalizer: `get_equalizer`, `set_equalizer`.
  - Library and extras: `browse_folder`, `get_album_art`, `vlm`.
- `vlc_control` now accepts `toggle`, `next` and `previous` as well as `play`, `pause`, `stop` and `fullscreen`.
- `get_status` now reports the playback rate, the random, loop and repeat modes, and the full-screen state.
- `docs/requests.txt`: reference for VLC's HTTP interface commands.
- README covering setup, configuration and every tool.
- pytest suite (`uv run pytest`) that mocks VLC's HTTP interface.
- `Test` workflow: runs `uv lock --check` and the tests on Python 3.10 and 3.14 for every push and pull request to `main`.

### Changed

- Migrated to `mcp` 2.x (`mcp>=2.3`, `MCPServer`). Tools no longer take a `Context` argument.
- Logging goes to stderr, leaving stdout for the MCP protocol stream.
- `vlc_control fullscreen` now toggles full screen instead of always turning it on.

### Fixed

- The built package now contains the code. Setuptools now looks in `src/`; before, wheels held only metadata.
- `show_video` no longer blocks the server's event loop while it waits for playback to start (`asyncio.sleep` replaces `time.sleep`).
- Non-ASCII file and track names are decoded as UTF-8 rather than ISO-8859-1.
- `get_available_subtitles` has the correct return type hint.

### Known issues

- `remove_playlist_item` relies on a command VLC marks as unsupported, so it may do nothing.

### Project

- Initial project structure from `jaseonline/repo-template`.
