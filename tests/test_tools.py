import asyncio

import requests
from conftest import FakeResponse

from vlc_mcp import main


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Volume: VLC's scale is 0-512 with 256 = 100%
# ---------------------------------------------------------------------------


def test_set_volume_converts_percent_to_vlc_scale(vlc):
    assert run(main.set_volume(50)) == "Volume set to 50%."
    assert vlc.commands() == [{"command": "volume", "val": 128}]


def test_set_volume_rejects_out_of_range(vlc):
    assert "Invalid volume level" in run(main.set_volume(201))
    assert vlc.calls == []


def test_get_volume_reports_percent(vlc):
    vlc.responses["/requests/status.json"] = FakeResponse({"volume": 384})
    assert run(main.get_volume()) == "Current volume: 150%"


def test_adjust_volume_clamps_to_200(vlc):
    vlc.responses["/requests/status.json"] = FakeResponse({"volume": 500})
    assert run(main.adjust_volume(50)) == "Volume adjusted from 195% to 200%"
    assert vlc.commands()[-1] == {"command": "volume", "val": 512}


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------


def test_seek_passes_value_through(vlc):
    run(main.seek("-10s"))
    assert vlc.commands() == [{"command": "seek", "val": "-10s"}]


def test_vlc_control_maps_actions(vlc):
    assert run(main.vlc_control("next")) == "Skipped to the next item."
    assert vlc.commands() == [{"command": "pl_next"}]


def test_vlc_control_rejects_unknown_action(vlc):
    assert run(main.vlc_control("rewind")).startswith("Unknown action")
    assert vlc.calls == []


def test_set_playback_rate_rejects_zero(vlc):
    assert "greater than 0" in run(main.set_playback_rate(0))
    assert vlc.calls == []


def test_set_sync_delay_uses_stream_command(vlc):
    run(main.set_sync_delay("subtitle", -0.5))
    assert vlc.commands() == [{"command": "subdelay", "val": -0.5}]


def test_command_failure_is_reported_not_raised(vlc):
    vlc.error = requests.ConnectionError("refused")
    assert run(main.vlc_control("stop")).startswith("VLC command failed")


# ---------------------------------------------------------------------------
# Status and decoding
# ---------------------------------------------------------------------------


def test_get_status_decodes_utf8_filenames(vlc):
    # VLC sends UTF-8 without a charset; vlc_json must not fall back to ISO-8859-1
    payload = {"state": "playing", "information": {"category": {"meta": {"filename": "Amélie.mkv"}}}}
    vlc.responses["/requests/status.json"] = FakeResponse(payload)
    assert "File: Amélie.mkv" in run(main.get_status())


def test_get_status_reports_connection_errors(vlc):
    vlc.error = requests.ConnectionError("refused")
    assert run(main.get_status()).startswith("Failed to get status")


def _playing(filename="Amélie.mkv", plid=4):
    return {"state": "playing", "currentplid": plid, "information": {"category": {"meta": {"filename": filename}}}}


def test_get_current_file_name_only_skips_playlist(vlc):
    vlc.responses["/requests/status.json"] = FakeResponse(_playing())
    assert run(main.get_current_file()) == "Current file: Amélie.mkv"
    assert [path for path, _ in vlc.calls] == ["/requests/status.json"]


def test_get_current_file_with_path_uses_current_playlist_item(vlc):
    vlc.responses["/requests/status.json"] = FakeResponse(_playing())
    tree = {
        "children": [
            {
                "name": "Playlist",
                "children": [
                    {"type": "leaf", "id": "3", "uri": "file:///D:/Films/Other.mkv"},
                    {"type": "leaf", "id": "4", "uri": "file:///D:/Films/Am%C3%A9lie.mkv"},
                ],
            }
        ]
    }
    vlc.responses["/requests/playlist.json"] = FakeResponse(tree)
    result = run(main.get_current_file(include_path=True))
    assert result.splitlines()[0] == "Current file: Amélie.mkv"
    assert result.splitlines()[1].startswith("Path: ") and result.endswith("Amélie.mkv")
    assert "Other" not in result


def test_get_current_file_with_path_keeps_stream_uri(vlc):
    vlc.responses["/requests/status.json"] = FakeResponse(_playing("live"))
    tree = {"children": [{"type": "leaf", "id": "4", "uri": "http://example.test/live"}]}
    vlc.responses["/requests/playlist.json"] = FakeResponse(tree)
    assert run(main.get_current_file(include_path=True)).endswith("Path: http://example.test/live")


def test_get_current_file_when_stopped(vlc):
    vlc.responses["/requests/status.json"] = FakeResponse({"state": "stopped", "currentplid": -1})
    assert run(main.get_current_file(include_path=True)) == "Nothing is playing."


# ---------------------------------------------------------------------------
# Playlist
# ---------------------------------------------------------------------------


def test_get_playlist_lists_only_playlist_leaves(vlc):
    tree = {
        "children": [
            {
                "name": "Playlist",
                "children": [
                    {"type": "leaf", "id": "4", "name": "One", "duration": 60, "current": "current"},
                    {"type": "node", "children": [{"type": "leaf", "id": "5", "name": "Two", "duration": -1}]},
                ],
            },
            {"name": "Media Library", "children": [{"type": "leaf", "id": "9", "name": "Elsewhere"}]},
        ]
    }
    vlc.responses["/requests/playlist.json"] = FakeResponse(tree)
    assert run(main.get_playlist()).splitlines() == ["* id=4: One (60s)", "  id=5: Two (unknown length)"]


def test_get_playlist_empty(vlc):
    vlc.responses["/requests/playlist.json"] = FakeResponse({"children": [{"name": "Playlist", "children": []}]})
    assert run(main.get_playlist()) == "The playlist is empty."


def test_sort_playlist_sends_mode_and_direction(vlc):
    run(main.sort_playlist("name", reverse=True))
    assert vlc.commands() == [{"command": "pl_sort", "id": 1, "val": 1}]


def test_play_playlist_item_without_id_omits_it(vlc):
    run(main.play_playlist_item())
    assert vlc.commands() == [{"command": "pl_play"}]


def test_enqueue_video_checks_file_exists(vlc, media_root):
    assert "does not exist" in run(main.enqueue_video("missing.mkv"))
    assert vlc.calls == []


def test_enqueue_video_sends_file_uri(vlc, media_root):
    (media_root / "film.mkv").write_bytes(b"")
    run(main.enqueue_video("film.mkv"))
    [command] = vlc.commands()
    assert command["command"] == "in_enqueue"
    assert command["input"].startswith("file:") and command["input"].endswith("film.mkv")


# ---------------------------------------------------------------------------
# Equalizer
# ---------------------------------------------------------------------------


def test_get_equalizer_disabled(vlc):
    vlc.responses["/requests/status.json"] = FakeResponse({"equalizer": []})
    assert run(main.get_equalizer()) == "The equalizer is disabled."


def test_get_equalizer_parses_numbered_keys(vlc):
    equalizer = {"preamp": 2, "bands": {'band id="1"': -3, 'band id="0"': 4}, "presets": {'preset id="0"': "Flat"}}
    vlc.responses["/requests/status.json"] = FakeResponse({"equalizer": equalizer})
    result = run(main.get_equalizer())
    assert "  0 (60 Hz): 4 dB\n  1 (170 Hz): -3 dB" in result
    assert "  0: Flat" in result


def test_set_equalizer_requires_band_and_gain_together(vlc):
    assert run(main.set_equalizer(band=3)) == "band and gain_db must be given together."
    assert vlc.calls == []


def test_set_equalizer_enables_first_and_disables_last(vlc):
    run(main.set_equalizer(enabled=True, preset_id=2, band=0, gain_db=5))
    assert [c["command"] for c in vlc.commands()] == ["enableeq", "setpreset", "equalizer"]

    vlc.calls.clear()
    run(main.set_equalizer(enabled=False, preamp_db=1))
    assert [c["command"] for c in vlc.commands()] == ["preamp", "enableeq"]


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------


def test_get_available_videos_lists_mkv_and_mp4_relative(media_root):
    (media_root / "b").mkdir()
    for name in ["a.mkv", "b/c.mp4", "notes.txt"]:
        (media_root / name).write_bytes(b"")
    assert main.get_available_videos().splitlines() == [
        "a.mkv",
        str(media_root.joinpath("b", "c.mp4").relative_to(media_root)),
    ]


def test_get_album_art_returns_image(vlc):
    vlc.responses["/art"] = FakeResponse(content=b"\x89PNG", headers={"Content-Type": "image/png"})
    image = run(main.get_album_art())
    assert isinstance(image, main.Image)


def test_tool_count():
    names = {tool.name for tool in run(main.app.list_tools())}
    assert len(names) == 27
    assert {"show_video", "set_equalizer", "vlm"} <= names
