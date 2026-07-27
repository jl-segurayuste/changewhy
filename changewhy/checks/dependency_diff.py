from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet

from changewhy.gitref import read_file_at_ref
from changewhy.plugin import CheckResult, Finding


def _parse_requirement_line(line: str) -> Requirement | None:
    line = line.split("#", 1)[0].strip()
    if not line or line.startswith("-"):
        return None
    try:
        return Requirement(line)
    except InvalidRequirement:
        return None


def _parse_requirements_txt(text: str) -> dict[str, SpecifierSet]:
    declared: dict[str, SpecifierSet] = {}
    for line in text.splitlines():
        req = _parse_requirement_line(line)
        if req is not None:
            declared[req.name] = req.specifier
    return declared


def _parse_pyproject_toml(text: str) -> dict[str, SpecifierSet]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return {}
    project = data.get("project", {})
    declared: dict[str, SpecifierSet] = {}
    for line in project.get("dependencies", []):
        req = _parse_requirement_line(line)
        if req is not None:
            declared[req.name] = req.specifier
    return declared


def _declared_deps_at_ref(repo_path: Path, ref: str) -> dict[str, SpecifierSet]:
    declared: dict[str, SpecifierSet] = {}
    req_text = read_file_at_ref(repo_path, ref, "requirements.txt")
    if req_text is not None:
        declared.update(_parse_requirements_txt(req_text))
    pyproject_text = read_file_at_ref(repo_path, ref, "pyproject.toml")
    if pyproject_text is not None:
        declared.update(_parse_pyproject_toml(pyproject_text))
    return declared


class DependencyDiffCheck:
    """Cambios en las dependencias declaradas (requirements.txt/pyproject.toml) entre dos refs."""

    name = "dependency_diff"

    def run(self, repo_path: Path, ref_a: str, ref_b: str) -> CheckResult:
        deps_a = _declared_deps_at_ref(repo_path, ref_a)
        deps_b = _declared_deps_at_ref(repo_path, ref_b)

        findings: list[Finding] = []
        for pkg in sorted(set(deps_b) - set(deps_a)):
            findings.append(
                Finding(severity="info", title=f"Dependencia añadida: {pkg}{deps_b[pkg]}")
            )
        for pkg in sorted(set(deps_a) - set(deps_b)):
            findings.append(
                Finding(severity="low", title=f"Dependencia eliminada: {pkg}{deps_a[pkg]}")
            )
        for pkg in sorted(set(deps_a) & set(deps_b)):
            if str(deps_a[pkg]) != str(deps_b[pkg]):
                findings.append(
                    Finding(
                        severity="low",
                        title=f"Versión cambiada: {pkg}{deps_a[pkg]} -> {pkg}{deps_b[pkg]}",
                    )
                )

        return CheckResult(
            check_name=self.name,
            summary=f"{len(findings)} cambio(s) de dependencias.",
            findings=findings,
        )
