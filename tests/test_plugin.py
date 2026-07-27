import pytest

from changewhy.plugin import CheckResult, Finding


def test_finding_severity_valida():
    f = Finding(severity="high", title="x")
    assert f.severity == "high"


def test_finding_severity_invalida_lanza():
    with pytest.raises(ValueError):
        Finding(severity="critical", title="x")


def test_check_result_por_defecto_sin_findings():
    r = CheckResult(check_name="x", summary="ok")
    assert r.findings == []
