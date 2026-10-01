"""Fail-closed and sanitization behavior of the platform report boundary."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/platform-compat/report.py"
spec = importlib.util.spec_from_file_location("compat_report", SCRIPT)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


@pytest.mark.parametrize(
    ("child", "code", "expected"),
    [
        ("", 0, "pass"),
        ("", 1, "incomplete"),
        ('<skipped message="reason"/>', 0, "incomplete"),
        ('<error message="secret-in-error"/>', 1, "incomplete"),
        ('<failure message="secret-in-error">sensitive-body</failure>', 1, "fail"),
    ],
)
def test_report_maps_verdict_without_copying_raw_messages(
    tmp_path, child, code, expected
):
    raw = tmp_path / "raw.xml"
    raw.write_text(
        f'<testsuite><testcase name="{report.TEST}">{child}</testcase></testsuite>'
    )
    row = report.verdict(raw, code)
    report.write_report(tmp_path, row)
    assert row["outcome"] == expected
    for file in ("results.json", "junit.xml"):
        text = (tmp_path / file).read_text()
        assert "secret-in-error" not in text and "sensitive-body" not in text


def test_missing_or_wrong_test_never_passes(tmp_path):
    raw = tmp_path / "raw.xml"
    raw.write_text('<testsuite><testcase name="unrelated"/></testsuite>')
    assert report.verdict(raw, 0)["outcome"] == "incomplete"
    assert report.verdict(tmp_path / "missing.xml", 0)["outcome"] == "incomplete"
