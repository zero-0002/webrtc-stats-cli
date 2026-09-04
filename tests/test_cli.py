"""End-to-end tests for the `webrtc-stats` command line entry point."""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from webrtc_stats_cli.__main__ import main

FIXTURE = Path(__file__).parent / "fixtures" / "getstats.json"


def test_reads_a_file_argument(capsys):
    assert main([str(FIXTURE)]) == 0
    assert "Inbound RTP:" in capsys.readouterr().out


def test_reads_stdin_by_default(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(FIXTURE.read_text(encoding="utf-8")))
    assert main([]) == 0
    assert "Outbound RTP:" in capsys.readouterr().out


def test_tolerates_a_utf8_bom(tmp_path, capsys):
    path = tmp_path / "bom.json"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8-sig")
    assert main([str(path)]) == 0
    assert "Inbound RTP:" in capsys.readouterr().out


def test_missing_file_exits_with_code_2(tmp_path, capsys):
    assert main([str(tmp_path / "nope.json")]) == 2
    assert "cannot read" in capsys.readouterr().err


def test_invalid_json_exits_with_code_2(tmp_path, capsys):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    assert main([str(path)]) == 2
    assert "invalid JSON" in capsys.readouterr().err


def test_dump_without_rtp_records(tmp_path, capsys):
    path = tmp_path / "empty.json"
    path.write_text("[]", encoding="utf-8")
    assert main([str(path)]) == 0
    assert "No inbound/outbound RTP records found" in capsys.readouterr().out


def test_help_exits_cleanly(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    assert "webrtc-stats" in capsys.readouterr().out
