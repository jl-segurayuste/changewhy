from __future__ import annotations

import ast
import copy
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


def _public_functions(source: str) -> dict[str, ast.arguments]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    funcs: dict[str, ast.arguments] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            funcs[node.name] = node.args
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_"):
                    funcs[f"{node.name}.{item.name}"] = item.args
    return funcs


def extract_signatures(source: str) -> dict[str, str]:
    """Nombre.completo -> firma de cada función/método público de nivel superior."""
    return {name: ast.unparse(args) for name, args in _public_functions(source).items()}


def _params(args: ast.arguments) -> tuple[list[tuple[str, bool]], dict[str, bool], bool, bool]:
    """(posicionales [(nombre, tiene_default)], solo-nombre {nombre: tiene_default}, *args, **kwargs)."""
    positional = [*args.posonlyargs, *args.args]
    first_default = len(positional) - len(args.defaults)
    pos = [(a.arg, i >= first_default) for i, a in enumerate(positional)]
    kwonly = {a.arg: d is not None for a, d in zip(args.kwonlyargs, args.kw_defaults, strict=True)}
    return pos, kwonly, args.vararg is not None, args.kwarg is not None


def _strip_annotations(args: ast.arguments) -> str:
    args = copy.deepcopy(args)
    for a in [*args.posonlyargs, *args.args, *args.kwonlyargs, args.vararg, args.kwarg]:
        if a is not None:
            a.annotation = None
    return ast.unparse(args)


def classify_change(old: ast.arguments, new: ast.arguments) -> str:
    """"annotations" (solo tipos), "compatible" (parámetros opcionales nuevos) o "breaking".

    Antes cualquier diferencia contaba como posible incompatibilidad: cambiar `dict=None` por
    `dict | None=None` o añadir un parámetro opcional al final salían como avisos medios."""
    if _strip_annotations(old) == _strip_annotations(new):
        return "annotations"
    old_pos, old_kw, old_var, old_kwargs = _params(old)
    new_pos, new_kw, new_var, new_kwargs = _params(new)
    if (old_var and not new_var) or (old_kwargs and not new_kwargs):
        return "breaking"
    if [n for n, _ in new_pos[: len(old_pos)]] != [n for n, _ in old_pos]:
        return "breaking"                                     # se quitan o reordenan posicionales
    if any(had and not has for (_, had), (_, has) in zip(old_pos, new_pos, strict=False)):
        return "breaking"                                     # un parámetro pierde su valor por defecto
    if not all(has for _, has in new_pos[len(old_pos):]):
        return "breaking"                                     # posicional nuevo obligatorio
    for name, had in old_kw.items():
        if name not in new_kw or (had and not new_kw[name]):
            return "breaking"
    if not all(has for name, has in new_kw.items() if name not in old_kw):
        return "breaking"                                     # solo-nombre nuevo obligatorio
    return "compatible"


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

            funcs_a = _public_functions(src_a)
            funcs_b = _public_functions(src_b)
            sigs_a = {name: ast.unparse(args) for name, args in funcs_a.items()}
            sigs_b = {name: ast.unparse(args) for name, args in funcs_b.items()}

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
                    kind = classify_change(funcs_a[name], funcs_b[name])
                    severity, detail = {
                        "annotations": ("info", "Solo cambian las anotaciones de tipo: compatible."),
                        "compatible": ("low", "Parámetros opcionales nuevos: las llamadas existentes siguen valiendo."),
                        "breaking": ("medium", "Posible cambio incompatible si alguien lo usaba."),
                    }[kind]
                    findings.append(
                        Finding(
                            severity=severity,
                            title=f"Firma cambiada: {name}({sigs_a[name]}) -> {name}({sigs_b[name]})",
                            detail=detail,
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
