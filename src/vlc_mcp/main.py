import asyncio
import json
import logging
import os
import pathlib
import re
import subprocess
import sys
from pathlib import Path

import requests
from mcp.server.mcpserver import Image, MCPServer

app = MCPServer("vlc_movie_player")

# stdout carries the stdio protocol stream, so diagnostics go to stderr. Client-bound
# ctx.info()/ctx.error() logging is deprecated in mcp 2.x (SEP-2577).
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("vlc_mcp")

ROOT_VIDEO_FOLDER = os.getenv("ROOT_VIDEO_FOLDER", "")
if not ROOT_VIDEO_FOLDER:
    print("ROOT_VIDEO_FOLDER not found in environment variables.", file=sys.stderr)
    sys.exit(1)

VLC_HTTP_HOST = os.getenv("VLC_HTTP_HOST", "localhost")
VLC_HTTP_PORT = os.getenv("VLC_HTTP_PORT", "8085")
VLC_HTTP_PASSWORD = os.getenv("VLC_HTTP_PASSWORD", "your_password")

VLC_BASE_URL = f"http://{VLC_HTTP_HOST}:{VLC_HTTP_PORT}"
VLC_AUTH = ("", VLC_HTTP_PASSWORD)

# Sort modes documented in requests.txt (the list is non-exhaustive in VLC itself)
SORT_MODES = {"id": 0, "name": 1, "author": 3, "random": 5, "track_number": 7}

# Any other value sent to VLC resets the aspect ratio, so "default" is accepted as an explicit reset
ASPECT_RATIOS = ["1:1", "4:3", "5:4", "16:9", "16:10", "221:100", "235:100", "239:100", "default"]

EQ_BANDS = ["60 Hz", "170 Hz", "310 Hz", "600 Hz", "1 kHz", "3 kHz", "6 kHz", "12 kHz", "14 kHz", "16 kHz"]

TRACK_COMMANDS = {
    "title": "title",
    "chapter": "chapter",
    "audio": "audio_track",
    "video": "video_track",
    "subtitle": "subtitle_track",
}


async def vlc_get(path: str, params: dict | None = None) -> requests.Response:
    """GET a path from the VLC HTTP interface and raise on HTTP errors."""
    url = f"{VLC_BASE_URL}{path}"
    logger.info(f"Sending VLC request: URL={url}, Params={params}")
    response = requests.get(url, params=params, auth=VLC_AUTH, timeout=10)
    logger.info(f"VLC response status: {response.status_code}")
    response.raise_for_status()
    return response


async def vlc_command(command, **params):
    """Execute a VLC HTTP API command. Keyword arguments set to None are not sent."""
    query = {"command": command, **{key: value for key, value in params.items() if value is not None}}
    try:
        await vlc_get("/requests/status.xml", query)
        return True, ""
    except requests.RequestException as e:
        logger.error(f"VLC command failed: {e}")
        return False, f"VLC command error: {e}"


async def vlc_json(path: str, params: dict | None = None) -> dict:
    """GET a VLC JSON endpoint. VLC sends UTF-8 without a charset, which requests would decode as ISO-8859-1."""
    return json.loads((await vlc_get(path, params)).content.decode("utf-8"))


async def vlc_status() -> dict:
    """Return the parsed status.json document."""
    return await vlc_json("/requests/status.json")


def resolve_media_path(path: str) -> str:
    """Resolve a path relative to ROOT_VIDEO_FOLDER (absolute paths pass through unchanged)."""
    return os.path.join(ROOT_VIDEO_FOLDER, path)


async def vlc_play_video(video_path, subtitle_id=None):
    """Play a video in VLC with optional subtitle."""
    await vlc_command("volume", val=256)
    option = None if subtitle_id is None else f"sub-track={subtitle_id}"

    video_uri = pathlib.Path(video_path).as_uri()

    success, error_message = await vlc_command("in_play", input=video_uri, option=option)
    if success:
        await asyncio.sleep(4)  # wait for the video to start without blocking the server's event loop
        success, error_message = await vlc_command("fullscreen", val=1)
    return success, error_message


# ---------------------------------------------------------------------------
# Status and transport
# ---------------------------------------------------------------------------


@app.tool()
async def get_status() -> str:
    """Get the current status of VLC playback."""
    try:
        status = await vlc_status()

        filename = status.get("information", {}).get("category", {}).get("meta", {}).get("filename", "unknown")

        message = (
            f"Status: {status.get('state', 'unknown')}, time: {status.get('time', 0)}/"
            f"{status.get('length', 0)} seconds, File: {filename}, rate: {status.get('rate', 1)}, "
            f"random: {status.get('random')}, loop: {status.get('loop')}, repeat: {status.get('repeat')}, "
            f"fullscreen: {status.get('fullscreen')}"
        )
        return message
    except requests.RequestException as e:
        return f"Failed to get status: {e}"


@app.tool()
async def seek(value: str) -> str:
    """Seek to a specific position in the video. + or - seek relative to the current position and otherwise absolute.

    Allowed values are of the form:
        [+ or -][<int><h>:][<int><m>:][<int><s>]  or  [+ or -]<int>%
    Examples:
        -10s -> seek 10 seconds backward
        +1h:2m:3s -> seek 1 hour, 2 minutes and 3 seconds forward
        30s -> seek to the 30th second
        50% -> seek to the middle
        -10% -> seek 10% back
    """
    success, error_message = await vlc_command("seek", val=value)
    return f"Seeked to {value}." if success else f"VLC command failed: {error_message}"


@app.tool()
async def vlc_control(action: str) -> str:
    """Control VLC playback.

    Actions:
        play       - resume playback if paused (does nothing if already playing)
        pause      - pause playback (does nothing if already paused)
        toggle     - toggle pause; if stopped, plays the current or first playlist item
        stop       - stop playback
        next       - jump to the next playlist item
        previous   - jump to the previous playlist item
        fullscreen - toggle fullscreen
    """
    actions = {
        "play": ("pl_forceresume", "Resumed playback."),
        "pause": ("pl_forcepause", "Paused playback."),
        "toggle": ("pl_pause", "Toggled pause."),
        "stop": ("pl_stop", "Stopped playback."),
        "next": ("pl_next", "Skipped to the next item."),
        "previous": ("pl_previous", "Went back to the previous item."),
        "fullscreen": ("fullscreen", "Toggled fullscreen."),
    }
    if action not in actions:
        return f"Unknown action: {action}. Use: {', '.join(actions)}."

    command, message = actions[action]
    success, error_message = await vlc_command(command)
    return message if success else f"VLC command failed: {error_message}"


@app.tool()
async def set_playback_rate(rate: float) -> str:
    """Set the playback speed. 1.0 is normal speed, 2.0 is double, 0.5 is half. Must be greater than 0."""
    if rate <= 0:
        return f"Invalid rate: {rate}. The rate must be greater than 0."
    success, error_message = await vlc_command("rate", val=rate)
    return f"Playback rate set to {rate}x." if success else f"VLC command failed: {error_message}"


@app.tool()
async def set_aspect_ratio(ratio: str) -> str:
    """Set the video aspect ratio.

    Args:
        ratio: One of 1:1, 4:3, 5:4, 16:9, 16:10, 221:100, 235:100, 239:100, or "default" to reset.
    """
    if ratio not in ASPECT_RATIOS:
        return f"Invalid aspect ratio: {ratio}. Use one of: {', '.join(ASPECT_RATIOS)}."
    success, error_message = await vlc_command("aspectratio", val=ratio)
    return f"Aspect ratio set to {ratio}." if success else f"VLC command failed: {error_message}"


@app.tool()
async def set_sync_delay(stream: str, seconds: float) -> str:
    """Set the audio or subtitle delay to fix out-of-sync playback.

    Args:
        stream: "audio" or "subtitle"
        seconds: Delay in seconds (can be negative or fractional, e.g. -0.5). 0 resets it.
    """
    commands = {"audio": "audiodelay", "subtitle": "subdelay"}
    if stream not in commands:
        return f"Unknown stream: {stream}. Use: audio, subtitle."
    success, error_message = await vlc_command(commands[stream], val=seconds)
    return f"{stream.capitalize()} delay set to {seconds}s." if success else f"VLC command failed: {error_message}"


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------


@app.tool()
async def set_volume(volume_level: int) -> str:
    """Set the volume level of VLC (0-200, where 100 is normal volume).

    Args:
        volume_level: An integer between 0 and 200 representing the volume percentage
    """
    # Validate volume level
    if not 0 <= volume_level <= 200:
        return f"Invalid volume level: {volume_level}. Please use a value between 0 and 200."

    # VLC uses values from 0-512, where 256 is 100% volume
    vlc_volume = int(volume_level * 256 / 100)

    success, error_message = await vlc_command("volume", val=vlc_volume)

    if success:
        return f"Volume set to {volume_level}%."
    else:
        return f"Failed to set volume: {error_message}"


@app.tool()
async def get_volume() -> str:
    """Get the current volume level of VLC (as a percentage)."""
    try:
        status = await vlc_status()

        # VLC volume range is 0-512, where 256 is 100%
        vlc_volume = status.get("volume", 0)
        percentage = int(vlc_volume * 100 / 256)

        return f"Current volume: {percentage}%"
    except requests.RequestException as e:
        return f"Failed to get volume: {e}"


@app.tool()
async def adjust_volume(change: int) -> str:
    """Increase or decrease the volume by a specified percentage.

    Args:
        change: An integer representing the percentage to change the volume by.
               Positive values increase volume, negative values decrease it.
    """
    try:
        # First get current volume
        status = await vlc_status()

        # Get current volume and convert to percentage
        current_vlc_volume = status.get("volume", 0)
        current_percentage = int(current_vlc_volume * 100 / 256)

        # Calculate new volume percentage
        new_percentage = current_percentage + change
        new_percentage = max(0, min(200, new_percentage))  # Clamp to 0-200%

        # Convert back to VLC volume value
        new_vlc_volume = int(new_percentage * 256 / 100)

        # Set the new volume
        success, error_message = await vlc_command("volume", val=new_vlc_volume)

        if success:
            return f"Volume adjusted from {current_percentage}% to {new_percentage}%"
        else:
            return f"Failed to adjust volume: {error_message}"
    except requests.RequestException as e:
        return f"Failed to adjust volume: {e}"


# ---------------------------------------------------------------------------
# Tracks (titles, chapters, audio, video, subtitles)
# ---------------------------------------------------------------------------


@app.tool()
async def get_tracks() -> str:
    """List the streams (audio, video, subtitle) of the current item, plus titles and chapters.

    Use the stream numbers shown here with select_track.
    """
    try:
        status = await vlc_status()
    except requests.RequestException as e:
        return f"Failed to get tracks: {e}"

    information = status.get("information") or {}
    categories = information.get("category") or {}

    lines = []
    for name, details in categories.items():
        match = re.fullmatch(r"Stream (\d+)", name)
        if not match or not isinstance(details, dict):
            continue
        parts = [str(details[key]) for key in ("Type", "Language", "Description", "Codec") if details.get(key)]
        lines.append(f"Stream {match.group(1)}: {', '.join(parts)}")

    if not lines:
        lines.append("No streams reported (is anything playing?).")

    for kind in ("title", "chapter"):
        available = information.get(f"{kind}s")
        if available:
            lines.append(f"{kind.capitalize()}s: {available} (current: {information.get(kind)})")

    return "\n".join(lines)


@app.tool()
async def select_track(kind: str, track_id: int) -> str:
    """Select a title, chapter, audio track, video track or subtitle track.

    Args:
        kind: One of title, chapter, audio, video, subtitle
        track_id: The stream number from get_tracks (or the title/chapter number). Use -1 for subtitle to disable it.
    """
    if kind not in TRACK_COMMANDS:
        return f"Unknown kind: {kind}. Use: {', '.join(TRACK_COMMANDS)}."
    success, error_message = await vlc_command(TRACK_COMMANDS[kind], val=track_id)
    return f"Selected {kind} {track_id}." if success else f"VLC command failed: {error_message}"


@app.tool()
async def add_subtitle(subtitle_path: str) -> str:
    """Load an external subtitle file into the currently playing video.

    Args:
        subtitle_path: Path relative to the video folder (or an absolute path) of a subtitle file such as .srt
    """
    full_path = resolve_media_path(subtitle_path)
    if not os.path.exists(full_path):
        return f"The file {full_path} does not exist."
    success, error_message = await vlc_command("addsubtitle", val=Path(full_path).as_uri())
    return f"Added subtitle {subtitle_path}." if success else f"VLC command failed: {error_message}"


# ---------------------------------------------------------------------------
# Playlist
# ---------------------------------------------------------------------------


def _collect_leaves(node: dict, leaves: list):
    if node.get("type") == "leaf":
        leaves.append(node)
    for child in node.get("children", []) or []:
        _collect_leaves(child, leaves)


@app.tool()
async def get_playlist() -> str:
    """List the items in the VLC playlist with their ids. The current item is marked with *."""
    try:
        tree = await vlc_json("/requests/playlist.json")
    except requests.RequestException as e:
        return f"Failed to get playlist: {e}"

    # The tree holds both "Playlist" and "Media Library" nodes; only the playlist is relevant here
    playlist_node = next((child for child in tree.get("children", []) if child.get("name") == "Playlist"), tree)

    leaves = []
    _collect_leaves(playlist_node, leaves)
    if not leaves:
        return "The playlist is empty."

    lines = []
    for item in leaves:
        marker = "*" if item.get("current") else " "
        duration = item.get("duration", -1)
        duration_str = f"{duration}s" if isinstance(duration, int) and duration >= 0 else "unknown length"
        lines.append(f"{marker} id={item.get('id')}: {item.get('name')} ({duration_str})")
    return "\n".join(lines)


@app.tool()
async def enqueue_video(video_path: str) -> str:
    """Add a video to the end of the playlist without starting it.

    Args:
        video_path: Path relative to the video folder, as returned by get_available_videos
    """
    full_path = resolve_media_path(video_path)
    if not os.path.exists(full_path):
        return f"The file {full_path} does not exist."
    success, error_message = await vlc_command("in_enqueue", input=Path(full_path).as_uri())
    return f"Added {video_path} to the playlist." if success else f"VLC command failed: {error_message}"


@app.tool()
async def play_playlist_item(item_id: int | None = None) -> str:
    """Play a playlist item by its id (from get_playlist). If item_id is omitted, plays the last active item."""
    success, error_message = await vlc_command("pl_play", id=item_id)
    target = f"item {item_id}" if item_id is not None else "the last active item"
    return f"Playing {target}." if success else f"VLC command failed: {error_message}"


@app.tool()
async def remove_playlist_item(item_id: int) -> str:
    """Remove an item from the playlist by its id. VLC marks this command as unsupported, so it may not work."""
    success, error_message = await vlc_command("pl_delete", id=item_id)
    return f"Requested removal of item {item_id}." if success else f"VLC command failed: {error_message}"


@app.tool()
async def clear_playlist() -> str:
    """Remove every item from the playlist."""
    success, error_message = await vlc_command("pl_empty")
    return "Playlist cleared." if success else f"VLC command failed: {error_message}"


@app.tool()
async def sort_playlist(mode: str, reverse: bool = False) -> str:
    """Sort the playlist.

    Args:
        mode: One of id, name, author, random, track_number
        reverse: True to sort in reverse order
    """
    if mode not in SORT_MODES:
        return f"Unknown sort mode: {mode}. Use: {', '.join(SORT_MODES)}."
    success, error_message = await vlc_command("pl_sort", id=int(reverse), val=SORT_MODES[mode])
    order = "reverse" if reverse else "normal"
    return f"Playlist sorted by {mode} ({order} order)." if success else f"VLC command failed: {error_message}"


@app.tool()
async def toggle_playlist_mode(mode: str) -> str:
    """Toggle a playlist mode on or off and report its new state.

    Args:
        mode: "random" (shuffle), "loop" (repeat whole playlist) or "repeat" (repeat current item)
    """
    commands = {"random": "pl_random", "loop": "pl_loop", "repeat": "pl_repeat"}
    if mode not in commands:
        return f"Unknown mode: {mode}. Use: {', '.join(commands)}."

    success, error_message = await vlc_command(commands[mode])
    if not success:
        return f"VLC command failed: {error_message}"

    try:
        state = "on" if (await vlc_status()).get(mode) else "off"
        return f"{mode.capitalize()} is now {state}."
    except requests.RequestException:
        return f"Toggled {mode}."


# ---------------------------------------------------------------------------
# Equalizer
# ---------------------------------------------------------------------------


def _numbered(mapping: dict | None) -> dict[int, object]:
    """status.json keys equalizer entries as 'band id="3"'; pull the number out of each key."""
    result = {}
    for key, value in (mapping or {}).items():
        match = re.search(r"\d+", key)
        if match:
            result[int(match.group())] = value
    return dict(sorted(result.items()))


@app.tool()
async def get_equalizer() -> str:
    """Show the equalizer state: preamp, band gains and the available presets."""
    try:
        equalizer = (await vlc_status()).get("equalizer")
    except requests.RequestException as e:
        return f"Failed to get equalizer: {e}"

    # VLC returns an empty list when the equalizer is disabled
    if not isinstance(equalizer, dict) or not equalizer:
        return "The equalizer is disabled."

    lines = [f"Preamp: {equalizer.get('preamp')} dB", "Bands:"]
    for band, gain in _numbered(equalizer.get("bands")).items():
        label = EQ_BANDS[band] if band < len(EQ_BANDS) else "?"
        lines.append(f"  {band} ({label}): {gain} dB")
    lines.append("Presets:")
    for preset_id, name in _numbered(equalizer.get("presets")).items():
        lines.append(f"  {preset_id}: {name}")
    return "\n".join(lines)


@app.tool()
async def set_equalizer(
    enabled: bool | None = None,
    preset_id: int | None = None,
    preamp_db: float | None = None,
    band: int | None = None,
    gain_db: float | None = None,
) -> str:
    """Change the equalizer. Only the arguments you pass are applied.

    Args:
        enabled: True to enable, False to disable the equalizer
        preset_id: Preset id from get_equalizer
        preamp_db: Preamp level, -20 to 20 dB
        band: Band 0-9 (0: 60 Hz, 1: 170 Hz, 2: 310 Hz, 3: 600 Hz, 4: 1 kHz, 5: 3 kHz,
              6: 6 kHz, 7: 12 kHz, 8: 14 kHz, 9: 16 kHz). Requires gain_db.
        gain_db: Gain for the band, -20 to 20 dB
    """
    if preamp_db is not None and not -20 <= preamp_db <= 20:
        return f"Invalid preamp: {preamp_db}. Use -20 to 20 dB."
    if (band is None) != (gain_db is None):
        return "band and gain_db must be given together."
    if band is not None and not 0 <= band <= 9:
        return f"Invalid band: {band}. Use 0-9."
    if gain_db is not None and not -20 <= gain_db <= 20:
        return f"Invalid gain: {gain_db}. Use -20 to 20 dB."

    # Enable first so later changes apply to an active equalizer; disable last for the same reason
    steps = []
    if enabled:
        steps.append(("enableeq", {"val": 1}, "enabled"))
    if preset_id is not None:
        steps.append(("setpreset", {"val": preset_id}, f"preset {preset_id}"))
    if preamp_db is not None:
        steps.append(("preamp", {"val": preamp_db}, f"preamp {preamp_db} dB"))
    if band is not None:
        steps.append(("equalizer", {"band": band, "val": gain_db}, f"band {band} {gain_db} dB"))
    if enabled is False:
        steps.append(("enableeq", {"val": 0}, "disabled"))

    if not steps:
        return "Nothing to change."

    done = []
    for command, params, description in steps:
        success, error_message = await vlc_command(command, **params)
        if not success:
            return f"Equalizer: applied {', '.join(done) or 'nothing'}; failed on {description}: {error_message}"
        done.append(description)
    return f"Equalizer: {', '.join(done)}."


# ---------------------------------------------------------------------------
# Library, browsing and album art
# ---------------------------------------------------------------------------


def get_available_subtitles(video_path: str) -> list[dict]:
    command = ["mediainfo", "--Output=JSON", video_path]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
    )
    media_data = json.loads(result.stdout)

    subtitle_list = []
    if "media" in media_data and "track" in media_data["media"]:
        for track in media_data["media"]["track"]:
            if track.get("@type") == "Text":
                subtitle_list.append(
                    {
                        "id": len(subtitle_list),
                        "language": track.get("Language", "und"),
                        "title": track.get("Title", None),
                    }
                )
    return subtitle_list


@app.tool()
def get_available_videos() -> str:
    """Get all available videos with their path."""
    root_path = Path(ROOT_VIDEO_FOLDER)
    video_paths = []
    for ext in ["*.mkv", "*.mp4"]:
        for path in root_path.rglob(ext):
            relative_path = path.relative_to(root_path)
            video_paths.append(str(relative_path))

    video_paths.sort()
    return "\n".join(video_paths)


@app.tool()
async def browse_folder(folder: str = "") -> str:
    """List the files and folders VLC sees in a folder, via VLC's own file browser.

    Args:
        folder: Path relative to the video folder (empty for the video folder itself), or an absolute path
    """
    full_path = Path(resolve_media_path(folder)).resolve()
    try:
        listing = await vlc_json("/requests/browse.json", {"uri": full_path.as_uri()})
    except requests.RequestException as e:
        return f"Failed to browse {full_path}: {e}"

    elements = [element for element in listing.get("element", []) if element.get("name") != ".."]
    if not elements:
        return f"{full_path} is empty or not readable by VLC."

    elements.sort(key=lambda element: (element.get("type") != "dir", element.get("name", "").lower()))
    return "\n".join(f"[{element.get('type')}] {element.get('name')}" for element in elements)


@app.tool()
async def get_album_art(item_id: int | None = None) -> Image | str:
    """Get the album art / cover image for the current item, or for a playlist item id from get_playlist."""
    params = None if item_id is None else {"item": item_id}
    try:
        response = await vlc_get("/art", params)
    except requests.RequestException as e:
        return f"No album art available: {e}"

    image_format = response.headers.get("Content-Type", "image/jpeg").split("/")[-1].split(";")[0]
    return Image(data=response.content, format=image_format)


@app.tool()
async def show_video(video_path: str, subtitle_language_code: str = "") -> str:
    """Show the video using the the video path and the subtitle language code. If the subtitle language code is an empty string, the video will play with no subtitle."""
    full_video_path = os.path.join(ROOT_VIDEO_FOLDER, video_path)
    logger.info(f"Full video path:\n{full_video_path}")

    if not os.path.exists(full_video_path):
        return f"The file {full_video_path} does not exist."

    subtitle_list = get_available_subtitles(full_video_path)

    subtitle_id = None
    if subtitle_language_code != "":
        for subtitle in subtitle_list:
            if subtitle_language_code == subtitle["language"]:
                subtitle_id = subtitle["id"]

        if subtitle_id is None:
            subtitle_str = ", ".join(
                [f"{subtitle_info['language']} - {subtitle_info['title']}" for subtitle_info in subtitle_list]
            )
            return (
                f"No matching subtitle with the language code {subtitle_language_code} "
                f"found for '{video_path}'. These are the available subtitles: {subtitle_str}"
            )

    success, error_message = await vlc_play_video(full_video_path, subtitle_id)
    if success:
        return "The video should now play."
    else:
        return f"Failed to start VLC playback. {error_message}"


# ---------------------------------------------------------------------------
# VLM (VideoLAN Manager: broadcast / VOD streams)
# ---------------------------------------------------------------------------


@app.tool()
async def vlm(command: str = "") -> str:
    """Run a VLM (VideoLAN Manager) command, or list VLM elements when command is empty.

    Args:
        command: A VLM command such as "show", "new mybroadcast broadcast enabled", "control mybroadcast play".
                 Leave empty to list all VLM elements. Returns VLC's raw XML response.
    """
    try:
        if command:
            response = await vlc_get("/requests/vlm_cmd.xml", {"command": command})
        else:
            response = await vlc_get("/requests/vlm.xml")
    except requests.RequestException as e:
        return f"VLM request failed: {e}"
    return response.text


def main():
    app.run()


if __name__ == "__main__":
    main()
