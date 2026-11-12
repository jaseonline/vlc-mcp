# vlc-mcp
![vlc-mcp](https://socialify.git.ci/jaseonline/vlc-mcp/image?description=1&font=Raleway&forks=1&issues=1&language=1&name=1&owner=1&pattern=Solid&pulls=1&stargazers=1&theme=Dark)

[![Super-Linter](https://github.com/jaseonline/vlc-mcp/actions/workflows/super-linter.yml/badge.svg)](https://github.com/jaseonline/vlc-mcp/actions/workflows/super-linter.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-green)](LICENSE)

vlc-mcp is a Model Context Protocol (MCP) server that lets an AI assistant such as Claude find, play and control videos in VLC. It talks to VLC's built-in HTTP interface and runs locally over stdio.

_Last updated: 2026-11-12_

## Features

- **Library:** list every `.mkv` and `.mp4` under your video folder, or browse folders through VLC's own file browser.
- **Playback:** play a video full screen with a chosen embedded subtitle language. Also play, pause, stop, skip, seek, change speed, set the aspect ratio and fix audio or subtitle sync.
- **Volume:** set, read or step the volume from 0 to 200%.
- **Tracks:** list and switch titles, chapters, audio, video and subtitle tracks, and load external subtitle files.
- **Playlist:** add, play, clear and sort items, and toggle shuffle, loop and repeat.
- **Equalizer:** turn it on or off, pick a preset, and set the preamp and each of the 10 bands.
- **Extras:** fetch the cover art for the current item, and run raw VLM (VideoLAN Manager) commands.

## Prerequisites

| Requirement | Why |
| --- | --- |
| [VLC](https://www.videolan.org/vlc/) with the web (HTTP) interface on | Every tool sends its commands through it |
| [uv](https://docs.astral.sh/uv/) | Installs and runs the server |
| Python 3.10+ | Runtime (uv can install it for you) |
| [MediaInfo](https://mediaarea.net/en/MediaInfo) CLI on `PATH` | `show_video` reads it to find the embedded subtitle tracks |

### Turn on VLC's HTTP interface

From the command line:

```sh
vlc --extraintf http --http-host localhost --http-port 8085 --http-password "choose-a-password"
```

Or in the VLC GUI:

1. **Tools → Preferences**, then set **Show settings** to **All**.
2. **Interface → Main interfaces**: tick **Web**.
3. **Interface → Main interfaces → Lua**: set a **Lua HTTP password**.
4. Restart VLC. The port defaults to 8080, so either pass `--http-port 8085` or set `VLC_HTTP_PORT=8080`.

To check it works, open `http://localhost:8085`, leave the username blank and enter the password.

## Installation

Run the server straight from GitHub with uv:

```sh
uvx --from git+https://github.com/jaseonline/vlc-mcp vlc-mcp
```

Or clone it for local use or development:

```sh
git clone https://github.com/jaseonline/vlc-mcp.git
cd vlc-mcp
uv sync
uv run vlc-mcp
```

## Configuration

The server is configured through environment variables. Set them in your MCP client's config. It exits at start-up if `ROOT_VIDEO_FOLDER` is missing.

| Variable | Required | Description |
| --- | --- | --- |
| `ROOT_VIDEO_FOLDER` | Yes | Folder that holds your videos. Tool paths are relative to it. |
| `VLC_HTTP_PASSWORD` | Yes, in practice | Password for VLC's HTTP interface. The fallback `your_password` will fail VLC's login. |
| `VLC_HTTP_HOST` | No | Host where VLC is listening. Defaults to `localhost`. |
| `VLC_HTTP_PORT` | No | Port VLC's HTTP interface listens on. Defaults to `8085`. |

### Claude Desktop

Add the server to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vlc": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/jaseonline/vlc-mcp", "vlc-mcp"],
      "env": {
        "ROOT_VIDEO_FOLDER": "D:\\Videos",
        "VLC_HTTP_PASSWORD": "choose-a-password"
      }
    }
  }
}
```

### Claude Code

```sh
claude mcp add vlc \
  -e ROOT_VIDEO_FOLDER="D:\Videos" \
  -e VLC_HTTP_PASSWORD="choose-a-password" \
  -- uvx --from git+https://github.com/jaseonline/vlc-mcp vlc-mcp
```

## Usage

Once the server is connected, ask for what you want in plain language. For example:

> "What films have I got?"
> "Play *Arrival* with English subtitles."
> "Skip back 30 seconds and turn it down to 60%."
> "The audio's out of sync. Delay it by half a second."
> "Queue the next three episodes and turn on shuffle."

### Tools

| Area | Tool | What it does |
| --- | --- | --- |
| Library | `get_available_videos` | Lists every `.mkv` and `.mp4` under `ROOT_VIDEO_FOLDER` |
| | `browse_folder` | Lists the files and folders VLC can see in a folder |
| | `show_video` | Plays a video full screen, with an optional subtitle language code such as `eng` |
| Status | `get_status` | Shows the state, position, file, rate, playlist modes and full-screen state |
| Transport | `vlc_control` | Runs `play`, `pause`, `toggle`, `stop`, `next`, `previous` or `fullscreen` |
| | `seek` | Jumps to a time or percentage, absolute or relative: `30s`, `-10s`, `+1h:2m:3s`, `50%` |
| | `set_playback_rate` | Sets the speed (`1.0` is normal) |
| | `set_aspect_ratio` | Sets the aspect ratio: `16:9`, `4:3`, `235:100` and others, or `default` to reset |
| | `set_sync_delay` | Sets the audio or subtitle delay in seconds |
| Volume | `set_volume`, `get_volume`, `adjust_volume` | Sets, reads or steps the volume, 0 to 200% |
| Tracks | `get_tracks` | Lists the streams, titles and chapters of the current item |
| | `select_track` | Switches the title, chapter, audio, video or subtitle track (`-1` turns subtitles off) |
| | `add_subtitle` | Loads an external subtitle file such as `.srt` |
| Playlist | `get_playlist` | Lists the items with their ids and marks the current one |
| | `enqueue_video` | Adds a video to the end without playing it |
| | `play_playlist_item` | Plays an item by its id |
| | `remove_playlist_item` | Removes an item (VLC marks this as unsupported, so it may not work) |
| | `clear_playlist` | Empties the playlist |
| | `sort_playlist` | Sorts by `id`, `name`, `author`, `random` or `track_number`, optionally in reverse |
| | `toggle_playlist_mode` | Turns `random`, `loop` or `repeat` on or off |
| Equalizer | `get_equalizer` | Shows the preamp, the band gains and the presets |
| | `set_equalizer` | Turns it on or off, picks a preset, and sets the preamp or one band (−20 to 20 dB) |
| Extras | `get_album_art` | Returns the cover image for the current item or a playlist item |
| | `vlm` | Runs a raw VLM command, or lists the VLM elements when no command is given |

`show_video` sets the volume to 100%, starts playback, waits about four seconds and then switches to full screen.

## Development

```sh
uv sync --extra dev        # install ruff and pre-commit
uv run pre-commit install  # run the hooks on every commit
uv run ruff check .        # lint
uv run ruff format .       # format
uv run pytest              # tests (VLC is mocked, so none needs to be running)
```

To try the tools interactively without an AI client, use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```sh
npx @modelcontextprotocol/inspector uv run vlc-mcp
```

Set `ROOT_VIDEO_FOLDER` and `VLC_HTTP_PASSWORD` in your shell first.

Logs go to stderr, because stdout carries the MCP protocol stream.

## Security

- Keep VLC's HTTP interface on `localhost`. Its only protection is a password sent with HTTP Basic auth over plain HTTP.
- `vlm` passes commands straight to VLC, and paths can point outside `ROOT_VIDEO_FOLDER` when given as absolute paths. Only connect the server to clients you trust.

Report vulnerabilities privately: see [SECURITY.md](SECURITY.md).

## Project layout

| Path | Contents |
| --- | --- |
| `src/vlc_mcp/main.py` | The MCP server and all its tools |
| `tests/` | pytest suite, with VLC's HTTP interface mocked |
| `docs/requests.txt` | Reference for VLC's HTTP interface commands |
| `.github/workflows/` | CI: tests and lockfile check, Super-Linter, GitGuardian, Claude review |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

[MIT](LICENSE)
