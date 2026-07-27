from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

Severity = str
SEVERITIES: tuple[Severity, ...] = ("info", "low", "medium", "high")


class Finding(BaseModel):
    severity: Severity
    title: str
    detail: str = ""
    path: str | None = None

    def model_post_init(self, context: object, /) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"severity {self.severity!r} no es una de {SEVERITIES}")


class CheckResult(BaseModel):
    check_name: str
    summary: str
    findings: list[Finding] = Field(default_factory=list)
    error: str | None = None


class Check(Protocol):
    name: str

    def run(self, repo_path: Path, ref_a: str, ref_b: str) -> CheckResult: ...
