"""Core aggregation logic for WebRTC getStats() dumps.

A getStats() dump is a JSON array (or object keyed by id) of RTCStats records.
This module extracts the fields that actually matter when triaging a call:
inbound/outbound RTP throughput, packet loss, jitter and frame rate.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any


def _iter_records(raw: Any) -> Iterable[dict]:
    """getStats() serializes either as a list or as an id->record map."""
    if isinstance(raw, list):
        yield from (r for r in raw if isinstance(r, dict))
    elif isinstance(raw, dict):
        yield from (r for r in raw.values() if isinstance(r, dict))


@dataclass
class Stream:
    kind: str
    direction: str
    ssrc: int | None = None
    codec: str | None = None
    packets: int = 0
    packets_lost: int = 0
    bytes: int = 0
    jitter_ms: float | None = None
    frames_per_second: float | None = None

    @property
    def loss_ratio(self) -> float:
        total = self.packets + self.packets_lost
        return (self.packets_lost / total) if total else 0.0


@dataclass
class Report:
    streams: list[Stream] = field(default_factory=list)

    @property
    def inbound(self) -> list[Stream]:
        return [s for s in self.streams if s.direction == "inbound"]

    @property
    def outbound(self) -> list[Stream]:
        return [s for s in self.streams if s.direction == "outbound"]

    def render(self) -> str:
        if not self.streams:
            return "No inbound/outbound RTP records found in the dump."
        lines = ["WebRTC stats report", "=" * 19, ""]
        for group, title in ((self.inbound, "Inbound"), (self.outbound, "Outbound")):
            if not group:
                continue
            lines.append(f"{title} RTP:")
            for s in group:
                fps = f", {s.frames_per_second:.1f} fps" if s.frames_per_second else ""
                jit = f", jitter {s.jitter_ms:.1f} ms" if s.jitter_ms is not None else ""
                lines.append(
                    f"  [{s.kind}] codec={s.codec or '?'} "
                    f"{s.bytes / 1024:.1f} KiB, "
                    f"loss {s.loss_ratio * 100:.2f}%{jit}{fps}"
                )
            lines.append("")
        return "\n".join(lines).rstrip()


def _codec_names(records: Iterable[dict]) -> dict[str, str]:
    names: dict[str, str] = {}
    for r in records:
        if r.get("type") == "codec" and "id" in r:
            mime = r.get("mimeType", "")
            names[r["id"]] = mime.split("/")[-1] if mime else r.get("id", "")
    return names


def build_report(raw: Any) -> Report:
    records = list(_iter_records(raw))
    codecs = _codec_names(records)
    report = Report()
    for r in records:
        rtype = r.get("type", "")
        if rtype not in ("inbound-rtp", "outbound-rtp", "remote-inbound-rtp"):
            continue
        direction = "outbound" if rtype.startswith("outbound") else "inbound"
        jitter = r.get("jitter")
        report.streams.append(
            Stream(
                kind=r.get("kind", r.get("mediaType", "?")),
                direction=direction,
                ssrc=r.get("ssrc"),
                codec=codecs.get(r.get("codecId", "")),
                packets=int(r.get("packetsReceived") or r.get("packetsSent") or 0),
                packets_lost=int(r.get("packetsLost") or 0),
                bytes=int(r.get("bytesReceived") or r.get("bytesSent") or 0),
                jitter_ms=(float(jitter) * 1000) if jitter is not None else None,
                frames_per_second=r.get("framesPerSecond"),
            )
        )
    return report
