from __future__ import annotations

import ast
from pathlib import Path

from changewhy.gitref import list_files_at_ref, read_file_at_ref
from changewhy.plugin import CheckResult, Finding

_EXCLUDED_PARTS = {"tests", "test", "examples"}


def _is_relevant(relpath: str) -> bool:
    """Excluye tests/ejemplos: no son la API pública que le importa a alguien
    que instala el paquete, y contarlos como "cambios de API" es puro ruido
    (funciones test_* no empiezan por "_" pero tampoco son API real)."""
    if not relpath.endswith(".py"):
        return False
    parts = set(Path(relpath).parts[:-1])
    return not (parts & _EXCLUDED_PARTS)


def extract_signatures(source: str) -> dict[str, str]:
    """Nombre.completo -> firma de cada función/método público de nivel superior."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    sigs: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            sigs[node.name] = ast.unparse(node.args)
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_"):
                    sigs[f"{node.name}.{item.name}"] = ast.unparse(item.args)
    return sigs


class ApiDiffCheck:
    """Diff de la API pública de Python (funciones y métodos top-level, sin '_' inicial) entre dos refs."""

    name = "api_diff"

    def run(self, repo_path: Path, ref_a: str, ref_b: str) -> CheckResult:
        files_a = {f for f in list_files_at_ref(repo_path, ref_a) if _is_relevant(f)}
        files_b = {f for f in list_files_at_ref(repo_path, ref_b) if _is_relevant(f)}

        findings: list[Finding] = []
        files_checked = 0

        for relpath in sorted(files_a & files_b):
            src_a = read_file_at_ref(repo_path, ref_a, relpath)
            src_b = read_file_at_ref(repo_path, ref_b, relpath)
            if src_a is None or src_b is None:
                continue
            files_checked += 1

            sigs_a = extract_signatures(src_a)
            sigs_b = extract_signatures(src_b)

            for name in sorted(set(sigs_b) - set(sigs_a)):
                findings.append(
                    Finding(
                        severity="info",
                        title=f"Añadido: {name}({sigs_b[name]})",
                        path=relpath,
                    )
                )
            for name in sorted(set(sigs_a) - set(sigs_b)):
                findings.append(
                    Finding(
                        severity="medium",
                        title=f"Eliminado: {name}({sigs_a[name]})",
                        detail="Posible cambio incompatible si alguien lo usaba.",
                        path=relpath,
                    )
                )
            for name in sorted(set(sigs_a) & set(sigs_b)):
                if sigs_a[name] != sigs_b[name]:
                    findings.append(
                        Finding(
                            severity="medium",
                            title=f"Firma cambiada: {name}({sigs_a[name]}) -> {name}({sigs_b[name]})",
                            detail="Posible cambio incompatible si alguien lo usaba.",
                            path=relpath,
                        )
                    )

        for relpath in sorted(files_b - files_a):
            findings.append(Finding(severity="info", title=f"Fichero nuevo: {relpath}", path=relpath))
        for relpath in sorted(files_a - files_b):
            findings.append(
                Finding(severity="medium", title=f"Fichero eliminado: {relpath}", path=relpath)
            )

        return CheckResult(
            check_name=self.name,
            summary=f"{files_checked} fichero(s) .py comparados, {len(findings)} cambio(s) de API.",
            findings=findings,
        )
