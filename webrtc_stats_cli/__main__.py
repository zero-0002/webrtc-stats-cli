"""Command-line entry point: `webrtc-stats path/to/getstats.json`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .report import build_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="webrtc-stats",
        description="Summarize a WebRTC getStats() JSON dump.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="-",
        help="JSON file produced by RTCPeerConnection.getStats(); '-' for stdin.",
    )
    args = parser.parse_args(argv)

    try:
        if args.path == "-":
            text = sys.stdin.read()
        else:
            text = Path(args.path).read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"error: cannot read {args.path}: {exc}", file=sys.stderr)
        return 2

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 2

    print(build_report(raw).render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
