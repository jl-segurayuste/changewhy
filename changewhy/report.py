from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from changewhy.plugin import SEVERITIES, CheckResult

_SEVERITY_ORDER = {sev: idx for idx, sev in enumerate(SEVERITIES)}


class Report(BaseModel):
    repo_path: str
    ref_a: str
    ref_b: str
    results: list[CheckResult]

    def all_findings(self) -> list[tuple[str, object]]:
        return [(r.check_name, f) for r in self.results for f in r.findings]

    def worst_severity(self) -> str | None:
        sevs = [f.severity for _, f in self.all_findings()]
        if not sevs:
            return None
        return max(sevs, key=lambda s: _SEVERITY_ORDER[s])

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_console(self) -> str:
        lines = [f"changewhy — {self.repo_path} ({self.ref_a} -> {self.ref_b})", ""]
        for result in self.results:
            lines.append(f"── {result.check_name} " + "─" * max(0, 40 - len(result.check_name)))
            if result.error:
                lines.append(f"  ERROR: {result.summary}")
                lines.append("")
                continue
            lines.append(f"  {result.summary}")
            for f in result.findings:
                loc = f" ({f.path})" if f.path else ""
                label = f"[{f.severity.upper():<6}]"
                lines.append(f"  {label} {f.title}{loc}")
                if f.detail:
                    lines.append(f"           {f.detail}")
            lines.append("")

        total = len(self.all_findings())
        lines.append(f"Total: {total} cambio(s).")
        return "\n".join(lines)


def build_report(repo_path: Path, ref_a: str, ref_b: str, results: list[CheckResult]) -> Report:
    return Report(repo_path=str(repo_path), ref_a=ref_a, ref_b=ref_b, results=results)


def write_json(report: Report) -> str:
    return json.dumps(json.loads(report.to_json()), ensure_ascii=False, indent=2)
