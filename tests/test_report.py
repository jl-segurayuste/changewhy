from changewhy.plugin import CheckResult, Finding
from changewhy.report import build_report, write_json


def test_worst_severity_ninguno_si_no_hay_findings():
    report = build_report(".", "a", "b", [CheckResult(check_name="x", summary="ok")])
    assert report.worst_severity() is None


def test_worst_severity_toma_el_mas_grave():
    results = [
        CheckResult(
            check_name="x",
            summary="ok",
            findings=[Finding(severity="info", title="a"), Finding(severity="medium", title="b")],
        )
    ]
    report = build_report(".", "a", "b", results)
    assert report.worst_severity() == "medium"


def test_to_console_incluye_refs_y_sin_emojis():
    results = [
        CheckResult(
            check_name="api_diff",
            summary="1 cambio",
            findings=[Finding(severity="medium", title="Eliminado: foo()", path="mod.py")],
        )
    ]
    report = build_report("/repo", "v1.0.0", "v1.1.0", results)
    out = report.to_console()
    assert "v1.0.0 -> v1.1.0" in out
    assert "[MEDIUM]" in out
    assert "🔧" not in out and "⚠" not in out


def test_to_json_valido():
    results = [CheckResult(check_name="x", summary="ok")]
    report = build_report("/repo", "a", "b", results)
    out = write_json(report)
    assert '"check_name": "x"' in out
