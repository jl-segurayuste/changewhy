from __future__ import annotations

import tomllib
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

from changewhy.gitref import read_file_at_ref
from changewhy.plugin import CheckResult, Finding

# Nombre canónico (PEP 503) -> (nombre tal como se declaró, especificador).
# Comparar por el nombre literal haría que un simple recapitalizado entre
# refs ("requests" -> "Requests", con la misma versión) se reportara como
# "eliminada + añadida" en vez de ningún cambio real -- o, peor, enmascarase
# un cambio de versión genuino que ocurriera en el mismo commit.
_DeclaredDeps = dict[str, tuple[str, SpecifierSet]]


def _parse_requirement_line(line: str) -> Requirement | None:
    line = line.split("#", 1)[0].strip()
    if not line or line.startswith("-"):
        return None
    try:
        return Requirement(line)
    except InvalidRequirement:
        return None


def _parse_requirements_txt(text: str) -> _DeclaredDeps:
    declared: _DeclaredDeps = {}
    for line in text.splitlines():
        req = _parse_requirement_line(line)
        if req is not None:
            declared[canonicalize_name(req.name)] = (req.name, req.specifier)
    return declared


def _parse_pyproject_toml(text: str) -> _DeclaredDeps:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return {}
    project = data.get("project", {})
    declared: _DeclaredDeps = {}
    for line in project.get("dependencies", []):
        req = _parse_requirement_line(line)
        if req is not None:
            declared[canonicalize_name(req.name)] = (req.name, req.specifier)
    # Los extras (`pip install pkg[x]`) también los instala quien usa el paquete.
    for extra, lines in project.get("optional-dependencies", {}).items():
        for line in lines:
            req = _parse_requirement_line(line)
            if req is not None:
                key = f"{canonicalize_name(req.name)}[{extra}]"
                declared[key] = (f"{req.name} (extra {extra}) ", req.specifier)
    return declared


def _declared_deps_at_ref(repo_path: Path, ref: str) -> _DeclaredDeps:
    declared: _DeclaredDeps = {}
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
        for key in sorted(set(deps_b) - set(deps_a)):
            name, specifier = deps_b[key]
            findings.append(
                Finding(severity="info", title=f"Dependencia añadida: {name}{specifier}")
            )
        for key in sorted(set(deps_a) - set(deps_b)):
            name, specifier = deps_a[key]
            findings.append(
                Finding(severity="low", title=f"Dependencia eliminada: {name}{specifier}")
            )
        for key in sorted(set(deps_a) & set(deps_b)):
            name_a, specifier_a = deps_a[key]
            name_b, specifier_b = deps_b[key]
            if str(specifier_a) != str(specifier_b):
                findings.append(
                    Finding(
                        severity="low",
                        title=f"Versión cambiada: {name_a}{specifier_a} -> {name_b}{specifier_b}",
                    )
                )

        return CheckResult(
            check_name=self.name,
            summary=f"{len(findings)} cambio(s) de dependencias.",
            findings=findings,
        )
