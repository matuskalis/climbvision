"""Render docs/img/hero.svg from a real ingest of a committed synthetic fixture.

The figure is drawn from the files `climbvision ingest` wrote, not from the in-memory objects,
and the script re-hashes those files against the run record before it draws anything. It has no
dependencies beyond climbvision itself and needs ffprobe on PATH. Output is deterministic for a
given ffprobe: the random run id and the wall-clock time are never drawn. It draws two clocks, so
the clip needs a timestamp on every packet and a known average frame rate.

Usage: uv run python scripts/render_hero.py [video] [out.svg]
"""

import json
import sys
import tempfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from xml.sax.saxutils import escape

from climbvision.errors import ClimbVisionError
from climbvision.hashing import sha256_bytes
from climbvision.ingest import PROBE_PACKETS_SUFFIX, PROBE_STREAMS_SUFFIX, ingest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIDEO = REPO_ROOT / "tests" / "fixtures" / "video" / "vfr_160x120_2s.mp4"
DEFAULT_OUT = REPO_ROOT / "docs" / "img" / "hero.svg"

WIDTH = 1200
HEIGHT = 764
MARGIN = 56
AXIS_LEFT = 340
AXIS_RIGHT = WIDTH - MARGIN
TICK_WIDTH = 4
TICK_HEIGHT = 44
CONTAINER_LANE_TOP = 188
NAIVE_LANE_TOP = 292
AXIS_Y = 368
QUALITY_TOP = 494
RECEIPT_TOP = 628
HASH_PREFIX_LENGTH = 12

SANS = "'Avenir Next Condensed', 'Arial Narrow', 'Roboto Condensed', 'Helvetica Neue', Arial"
MONO = "ui-monospace, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

STYLE = f"""
  :root {{
    --ground: #f1f3f2; --ink: #14181b; --muted: #57626a; --blue: #1f4fd8;
    --red: #c9252d; --ok: #0b6f5f; --link: #b4bdc2;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --ground: #0f1316; --ink: #e9eef1; --muted: #9aa6ad; --blue: #7aa2ff;
      --red: #ff7b72; --ok: #4fd1b5; --link: #3a454c;
    }}
  }}
  .ground {{ fill: var(--ground); }}
  .ink {{ fill: var(--ink); }}
  .muted {{ fill: var(--muted); }}
  .blue {{ fill: var(--blue); }}
  .red {{ fill: var(--red); }}
  .ok {{ fill: var(--ok); }}
  .sans {{ font-family: {SANS}, sans-serif; }}
  .mono {{ font-family: {MONO}; }}
  .link {{ stroke: var(--link); stroke-width: 1.5; }}
  .focus {{ stroke: var(--ink); stroke-width: 3; }}
  .axis {{ stroke: var(--ink); stroke-width: 2; }}
"""


@dataclass(frozen=True)
class Run:
    video_name: str
    asset_id: str
    manifest_sha256: str
    frame_index_sha256: str
    ffprobe_version: str
    time_base: Fraction
    pts: list[int]
    duration_us: int
    avg_frame_rate: Fraction
    quality: list[dict]
    hashes_checked: int


def run_ingest(video: Path) -> Run:
    with tempfile.TemporaryDirectory() as scratch:
        out_root = Path(scratch)
        recording = ingest(video, out_root)
        directory = out_root / "recordings" / recording.asset_id
        manifest_bytes = (directory / "recording.json").read_bytes()
        frame_index_bytes = (directory / "frame_index.json").read_bytes()
        (run_path,) = [
            path
            for path in (directory / "runs").glob("run-*.json")
            if not path.name.endswith(".raw.json")
        ]
        run = json.loads(run_path.read_bytes())
        streams_raw = (directory / "runs" / f"{run['run_id']}{PROBE_STREAMS_SUFFIX}").read_bytes()
        packets_raw = (directory / "runs" / f"{run['run_id']}{PROBE_PACKETS_SUFFIX}").read_bytes()

    manifest = json.loads(manifest_bytes)
    frame_index = json.loads(frame_index_bytes)
    chain = {
        "manifest": (sha256_bytes(manifest_bytes), run["manifest_sha256"]),
        "frame index": (sha256_bytes(frame_index_bytes), manifest["frame_index_sha256"]),
        "raw streams": (sha256_bytes(streams_raw), run["probe_streams_sha256"]),
        "raw packets": (sha256_bytes(packets_raw), run["probe_packets_sha256"]),
    }
    for name, (recomputed, recorded) in chain.items():
        if recomputed != recorded:
            sys.exit(f"hash chain broken at {name}: recomputed {recomputed}, recorded {recorded}")

    base = frame_index["time_base"]
    rate = manifest["video_stream"]["avg_frame_rate"]
    if rate is None or None in frame_index["pts"]:
        sys.exit(f"{run['input_basename']} has no frame rate or a packet without a timestamp")
    return Run(
        video_name=run["input_basename"],
        asset_id=manifest["asset_id"],
        manifest_sha256=run["manifest_sha256"],
        frame_index_sha256=manifest["frame_index_sha256"],
        ffprobe_version=run["ffprobe_version"],
        time_base=Fraction(base["num"], base["den"]),
        pts=frame_index["pts"],
        duration_us=manifest["duration_us"],
        avg_frame_rate=Fraction(rate["num"], rate["den"]),
        quality=manifest["quality"],
        hashes_checked=len(chain),
    )


def container_time(run: Run, index: int) -> Fraction:
    return run.pts[index] * run.time_base


def naive_time(run: Run, index: int) -> Fraction:
    return index / run.avg_frame_rate


def worst_disagreement(run: Run) -> int:
    gaps = [abs(container_time(run, i) - naive_time(run, i)) for i in range(len(run.pts))]
    return gaps.index(max(gaps))


def short(digest: str) -> str:
    return digest.removeprefix("sha256-")[:HASH_PREFIX_LENGTH] + "…"


def verdict_text(entry: dict) -> tuple[str, str]:
    measured, limit = entry["measurement"], entry["threshold"]
    match entry["flag"]:
        case "resolution_below_min":
            size = f"{measured['width']}x{measured['height']}"
            return "resolution", f"{size}, floor {limit['min_width']}x{limit['min_height']}"
        case "frame_rate_below_min":
            return "frame rate", f"{measured['avg_frame_rate']}, floor {limit['min_frame_rate']}"
        case "variable_frame_rate":
            deltas = measured["distinct_pts_delta_count"]
            return (
                "variable rate",
                f"{deltas} PTS deltas, limit {limit['max_distinct_pts_delta_count']}",
            )
        case "timestamps_absent":
            return (
                "timestamps",
                f"{measured['pts_present_count']} of {measured['packet_count']} packets",
            )
    raise ValueError(f"unhandled quality flag {entry['flag']}")


def text(x: float, y: float, content: str, css: str, size: int, **attributes: str) -> str:
    extra = "".join(f' {name.replace("_", "-")}="{value}"' for name, value in attributes.items())
    return f'<text class="{css}" x="{x:.1f}" y="{y}" font-size="{size}"{extra}>{content}</text>'


def header(run: Run, count: int) -> list[str]:
    return [
        text(MARGIN, 100, f"{count} frames, two clocks", "ink sans", 56, font_weight="800"),
        text(
            MARGIN,
            138,
            "A real ingest of a synthetic clip whose frames were dropped on purpose. "
            "Drawn from the files it wrote.",
            "muted sans",
            21,
        ),
        text(
            AXIS_RIGHT,
            100,
            f"climbvision ingest {escape(run.video_name)}",
            "muted mono",
            16,
            text_anchor="end",
        ),
    ]


def lane_label(top: int, css: str, title: str, lines: tuple[str, str]) -> list[str]:
    label = [
        text(MARGIN, top + 18, title, f"{css} sans", 19, font_weight="700", letter_spacing="1")
    ]
    for row, line in enumerate(lines):
        label.append(text(MARGIN, top + 40 + row * 22, escape(line), "muted sans", 17))
    return label


def timeline(run: Run, worst: int) -> list[str]:
    seconds = Fraction(run.duration_us, 1_000_000)
    scale = Fraction(AXIS_RIGHT - AXIS_LEFT) / seconds

    def x_of(moment: Fraction) -> float:
        return float(AXIS_LEFT + moment * scale)

    rate = run.avg_frame_rate
    base = run.time_base
    parts = lane_label(
        CONTAINER_LANE_TOP,
        "blue",
        "CONTAINER TIMESTAMPS",
        ("recorded as integer ticks", f"of {base.numerator}/{base.denominator} s"),
    )
    parts += lane_label(
        NAIVE_LANE_TOP,
        "red",
        "FRAME NUMBER ÷ AVG RATE",
        (f"{rate.numerator}/{rate.denominator} fps as reported", "never used for time"),
    )

    container_bottom = CONTAINER_LANE_TOP + TICK_HEIGHT
    for index in range(len(run.pts)):
        css = "focus" if index == worst else "link"
        x_container = x_of(container_time(run, index))
        x_naive = x_of(naive_time(run, index))
        parts.append(
            f'<line class="{css}" x1="{x_container:.1f}" y1="{container_bottom}" '
            f'x2="{x_naive:.1f}" y2="{NAIVE_LANE_TOP}"/>'
        )
    for index in range(len(run.pts)):
        for top, lane_css, moment in (
            (CONTAINER_LANE_TOP, "blue", container_time(run, index)),
            (NAIVE_LANE_TOP, "red", naive_time(run, index)),
        ):
            x = x_of(moment) - TICK_WIDTH / 2
            parts.append(
                f'<rect class="{lane_css}" x="{x:.1f}" y="{top}" '
                f'width="{TICK_WIDTH}" height="{TICK_HEIGHT}"/>'
            )

    parts.append(
        f'<line class="axis" x1="{AXIS_LEFT}" y1="{AXIS_Y}" x2="{AXIS_RIGHT}" y2="{AXIS_Y}"/>'
    )
    ticks = [(Fraction(half, 2), f"{half / 2:g} s") for half in range(int(seconds * 2) + 1)]
    ticks.append((seconds, f"{float(seconds):.3f} s"))
    for moment, label in ticks:
        x = x_of(moment)
        anchor = "end" if moment == seconds else "middle"
        parts.append(
            f'<line class="axis" x1="{x:.1f}" y1="{AXIS_Y}" x2="{x:.1f}" y2="{AXIS_Y + 8}"/>'
        )
        parts.append(text(x, AXIS_Y + 30, label, "muted mono", 16, text_anchor=anchor))

    parts.append(
        text(
            x_of(container_time(run, worst)),
            CONTAINER_LANE_TOP - 10,
            str(worst),
            "ink mono",
            16,
            font_weight="700",
            text_anchor="middle",
        )
    )
    parts.append(
        text(
            x_of(naive_time(run, worst)),
            NAIVE_LANE_TOP + TICK_HEIGHT + 20,
            str(worst),
            "ink mono",
            16,
            font_weight="700",
            text_anchor="middle",
        )
    )
    return parts


def callout(run: Run, worst: int) -> str:
    true, naive = container_time(run, worst), naive_time(run, worst)
    gap_ms = abs(true - naive) * 1000
    container = f'<tspan class="blue" font-weight="700">{float(true):.3f} s</tspan>'
    counted = f'<tspan class="red" font-weight="700">{float(naive):.3f} s</tspan>'
    return text(
        AXIS_LEFT,
        AXIS_Y + 76,
        f"Frame {worst} is at {container} in the container and at {counted} "
        f"by frame number / rate: {float(gap_ms):.0f} ms apart.",
        "ink sans",
        21,
    )


def quality_row(run: Run) -> list[str]:
    parts = [
        text(
            MARGIN,
            QUALITY_TOP,
            "QUALITY FLAGS, NOT REJECTIONS",
            "muted sans",
            17,
            font_weight="700",
            letter_spacing="1",
        ),
        text(
            AXIS_RIGHT,
            QUALITY_TOP,
            "this clip is outside the envelope on purpose; the run still exited 0",
            "muted mono",
            15,
            text_anchor="end",
        ),
    ]
    top = QUALITY_TOP + 38
    width = (AXIS_RIGHT - MARGIN) / len(run.quality)
    for position, entry in enumerate(run.quality):
        label, detail = verdict_text(entry)
        status = entry["status"]
        css = "ok" if status == "ok" else "red"
        x = MARGIN + position * width
        if status == "ok":
            parts.append(f'<rect class="{css}" x="{x:.1f}" y="{top - 15}" width="16" height="16"/>')
        else:
            points = f"{x:.1f},{top + 1} {x + 16:.1f},{top + 1} {x + 8:.1f},{top - 15}"
            parts.append(f'<polygon class="{css}" points="{points}"/>')
        parts.append(text(x + 26, top, status.upper(), f"{css} mono", 16, font_weight="700"))
        parts.append(text(x + 26, top + 24, label, "ink sans", 19, font_weight="700"))
        parts.append(text(x + 26, top + 46, escape(detail), "muted mono", 16))
    return parts


def receipt(run: Run) -> list[str]:
    parts = [
        text(
            MARGIN,
            RECEIPT_TOP,
            "WHAT THE RUN WROTE",
            "muted sans",
            17,
            font_weight="700",
            letter_spacing="1",
        ),
        text(
            AXIS_RIGHT,
            RECEIPT_TOP,
            f"{run.hashes_checked} hashes re-computed from the files on disk: all match",
            "muted mono",
            15,
            text_anchor="end",
        ),
    ]
    rows = (
        ("asset_id", short(run.asset_id), "sha256 of the file bytes, so a rename changes nothing"),
        (
            "recording.json",
            short(run.manifest_sha256),
            "canonical JSON, byte-identical on every re-ingest",
        ),
        (
            "frame_index.json",
            short(run.frame_index_sha256),
            "hash kept in the manifest, ticks sorted by PTS",
        ),
        (
            "runs/run-<id>.json",
            "append-only",
            f"names manifest, config, ffprobe {run.ffprobe_version} and raw probe output by hash",
        ),
    )
    for row, (key, value, note) in enumerate(rows):
        y = RECEIPT_TOP + 30 + row * 24
        parts.append(text(MARGIN, y, escape(key), "ink mono", 16))
        parts.append(text(MARGIN + 224, y, escape(value), "ink mono", 16, font_weight="700"))
        parts.append(text(MARGIN + 424, y, escape(note), "muted mono", 16))
    return parts


def render(run: Run) -> str:
    count = len(run.pts)
    worst = worst_disagreement(run)
    gap_ms = abs(container_time(run, worst) - naive_time(run, worst)) * 1000
    body = "\n  ".join(
        header(run, count)
        + timeline(run, worst)
        + [callout(run, worst)]
        + quality_row(run)
        + receipt(run)
    )
    description = (
        f"{count} frames of a synthetic variable-frame-rate clip, placed at their container "
        "timestamps and at frame number divided by the average frame rate. "
        f"The worst disagreement is {float(gap_ms):.0f} ms."
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'width="{WIDTH}" height="{HEIGHT}" role="img" aria-labelledby="t d">\n'
        f'  <title id="t">{count} frames, two clocks</title>\n'
        f'  <desc id="d">{escape(description)}</desc>\n'
        f"  <style>{STYLE}</style>\n"
        f'  <rect class="ground" width="{WIDTH}" height="{HEIGHT}"/>\n'
        f"  {body}\n"
        "</svg>\n"
    )


def main() -> None:
    video = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_VIDEO
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    try:
        svg = render(run_ingest(video))
    except ClimbVisionError as error:
        sys.exit(f"error: {error.code}: {error.message}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"wrote {out} ({len(svg.encode('utf-8'))} bytes)")


if __name__ == "__main__":
    main()
