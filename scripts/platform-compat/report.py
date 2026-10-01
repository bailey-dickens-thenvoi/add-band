"""Publish bounded, credential-free results from the single bootstrap test."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.etree import ElementTree

SCENARIO = "addband-openclaw-bootstrap-scripted"
TEST = "test_published_bootstrap_scripted[openclaw]"


def verdict(raw: Path | None, exit_code: int) -> dict[str, str]:
    row = {
        "outcome": "incomplete",
        "category": "setup",
        "reason": "Bootstrap setup did not complete",
    }
    if raw is None or not raw.is_file():
        return row
    try:
        cases = list(ElementTree.parse(raw).iter("testcase"))
    except ElementTree.ParseError:
        return row
    if len(cases) != 1 or cases[0].get("name") != TEST:
        return row
    case = cases[0]
    if case.find("error") is not None:
        row["reason"] = "Bootstrap fixture setup or cleanup failed"
    elif case.find("skipped") is not None:
        row["reason"] = "Required bootstrap scenario was skipped"
    elif case.find("failure") is not None:
        row.update(
            outcome="fail",
            category="runtime",
            reason="Bootstrap or scripted reply check failed",
        )
    elif exit_code == 0:
        row.update(
            outcome="pass",
            category="runtime",
            reason="Verbatim bootstrap and scripted reply passed",
        )
    return row


def write_report(directory: Path, row: dict[str, str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    result = {
        "scenario_id": SCENARIO,
        "observed_coverage": "user-bootstrap",
        "model_mode": "strict",
        **row,
    }
    (directory / "results.json").write_text(
        json.dumps({"scenarios": [result]}, indent=2) + "\n", encoding="utf-8"
    )
    suite = ElementTree.Element(
        "testsuite",
        name="addband-platform-compat",
        tests="1",
        failures=str(int(row["outcome"] == "fail")),
        errors=str(int(row["outcome"] == "incomplete")),
    )
    case = ElementTree.SubElement(suite, "testcase", name=SCENARIO)
    if row["outcome"] != "pass":
        ElementTree.SubElement(
            case,
            "failure" if row["outcome"] == "fail" else "error",
            message=row["reason"],
        )
    ElementTree.ElementTree(suite).write(
        directory / "junit.xml", encoding="utf-8", xml_declaration=True
    )


if __name__ == "__main__":
    raw = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    row = verdict(raw, int(sys.argv[3]) if raw is not None else 1)
    write_report(Path(sys.argv[1]), row)
    # Initialization succeeds so the wrapper can continue to setup.
    raise SystemExit(0 if raw is None or row["outcome"] == "pass" else 1)
