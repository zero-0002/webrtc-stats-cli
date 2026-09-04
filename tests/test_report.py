"""Unit tests for the getStats() aggregation logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from webrtc_stats_cli import Report, build_report
from webrtc_stats_cli.report import Stream

FIXTURE = Path(__file__).parent / "fixtures" / "getstats.json"


@pytest.fixture
def dump() -> list:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_build_report_splits_by_direction(dump):
    report = build_report(dump)
    assert [s.kind for s in report.inbound] == ["audio", "video"]
    assert [s.kind for s in report.outbound] == ["audio", "video"]


def test_non_rtp_records_are_ignored(dump):
    # The fixture carries codec and transport records too; neither is a stream.
    assert len(build_report(dump).streams) == 4


def test_codec_is_resolved_through_codec_id(dump):
    report = build_report(dump)
    assert {s.codec for s in report.streams} == {"opus", "VP8"}


def test_counters_are_read_from_the_matching_direction(dump):
    report = build_report(dump)
    inbound_audio = report.inbound[0]
    outbound_audio = report.outbound[0]
    assert (inbound_audio.packets, inbound_audio.bytes) == (4820, 385600)
    assert (outbound_audio.packets, outbound_audio.bytes) == (4900, 392000)


def test_jitter_is_converted_to_milliseconds(dump):
    report = build_report(dump)
    assert report.inbound[0].jitter_ms == pytest.approx(4.0)
    assert report.outbound[0].jitter_ms is None


def test_accepts_an_id_keyed_object_dump(dump):
    keyed = {record["id"]: record for record in dump}
    assert len(build_report(keyed).streams) == len(build_report(dump).streams)


def test_unknown_shapes_yield_an_empty_report():
    assert build_report(None).streams == []
    assert build_report(["not a record", 42]).streams == []


@pytest.mark.parametrize(
    ("packets", "lost", "expected"),
    [(0, 0, 0.0), (99, 1, 0.01), (0, 5, 1.0)],
)
def test_loss_ratio(packets, lost, expected):
    stream = Stream(kind="audio", direction="inbound", packets=packets, packets_lost=lost)
    assert stream.loss_ratio == pytest.approx(expected)


def test_render_reports_both_directions(dump):
    rendered = build_report(dump).render()
    assert "Inbound RTP:" in rendered
    assert "Outbound RTP:" in rendered
    assert "codec=opus" in rendered
    assert "jitter 4.0 ms" in rendered
    assert "29.5 fps" in rendered
    assert not rendered.endswith("\n")


def test_render_without_streams():
    assert Report().render() == "No inbound/outbound RTP records found in the dump."


def test_render_omits_the_empty_direction():
    report = Report(streams=[Stream(kind="audio", direction="inbound")])
    assert "Outbound RTP:" not in report.render()
