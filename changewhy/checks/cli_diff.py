from __future__ import annotations

import tomllib
from pathlib import Path

from changewhy.gitref import read_file_at_ref
from changewhy.plugin import CheckResult, Finding


def _scripts_at_ref(repo_path: Path, ref: str) -> dict[str, str]:
    text = read_file_at_ref(repo_path, ref, "pyproject.toml")
    if text is None:
        return {}
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return {}
    return dict(data.get("project", {}).get("scripts", {}))


class CliDiffCheck:
    """Comandos de [project.scripts] añadidos/eliminados/redirigidos entre dos refs."""

    name = "cli_diff"

    def run(self, repo_path: Path, ref_a: str, ref_b: str) -> CheckResult:
        scripts_a = _scripts_at_ref(repo_path, ref_a)
        scripts_b = _scripts_at_ref(repo_path, ref_b)

        findings: list[Finding] = []
        for cmd in sorted(set(scripts_b) - set(scripts_a)):
            findings.append(Finding(severity="info", title=f"Comando añadido: {cmd}"))
        for cmd in sorted(set(scripts_a) - set(scripts_b)):
            findings.append(
                Finding(
                    severity="medium",
                    title=f"Comando eliminado: {cmd}",
                    detail="Quien lo use en scripts/CI dejará de funcionar.",
                )
            )
        for cmd in sorted(set(scripts_a) & set(scripts_b)):
            if scripts_a[cmd] != scripts_b[cmd]:
                findings.append(
                    Finding(
                        severity="low",
                        title=f"Comando redirigido: {cmd} ({scripts_a[cmd]} -> {scripts_b[cmd]})",
                    )
                )

        return CheckResult(
            check_name=self.name,
            summary=f"{len(findings)} cambio(s) en comandos CLI.",
            findings=findings,
        )
