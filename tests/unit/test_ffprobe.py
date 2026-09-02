import pytest

from climbvision.errors import ClimbVisionError
from climbvision.media import ffprobe


def test_the_recorded_demuxer_options_are_the_ones_actually_passed():
    # The manifest claims these options were in force. They are only true by construction if
    # every probe call really passes them, so the mapping and the argv must agree.
    assert ffprobe.DEMUXER_OPTIONS
    for name, value in ffprobe.DEMUXER_OPTIONS.items():
        flag = f"-{name}"
        assert flag in ffprobe.DEMUXER_ARGS
        assert ffprobe.DEMUXER_ARGS[ffprobe.DEMUXER_ARGS.index(flag) + 1] == str(int(value))
    assert len(ffprobe.DEMUXER_ARGS) == 2 * len(ffprobe.DEMUXER_OPTIONS)


def test_the_base_arguments_are_the_agreed_probe_prefix():
    assert ffprobe.BASE_ARGS == (
        "-hide_banner",
        "-loglevel",
        "error",
        "-print_format",
        "json",
        "-show_error",
    )
    assert ffprobe.STREAMS_ARGS == ("-show_format", "-show_streams")
    assert ffprobe.PACKETS_ARGS == (
        "-select_streams",
        "v:0",
        "-show_entries",
        "packet=pts,dts,duration,flags",
    )


def test_the_version_call_omits_show_error():
    # ffprobe exits 1 on `-show_error` without an input file, so the version probe must not
    # inherit it.
    assert "-show_error" not in ffprobe.VERSION_ARGS
    assert "-show_program_version" in ffprobe.VERSION_ARGS


def test_a_missing_ffprobe_is_a_named_error(monkeypatch):
    monkeypatch.setenv("PATH", "")
    with pytest.raises(ClimbVisionError) as error:
        ffprobe.executable()
    assert error.value.code == "FFPROBE_NOT_FOUND"
    assert "install ffmpeg" in error.value.message
