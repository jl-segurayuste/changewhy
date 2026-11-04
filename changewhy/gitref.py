from __future__ import annotations

import subprocess
from pathlib import Path


def list_files_at_ref(repo_path: Path, ref: str) -> set[str]:
    result = subprocess.run(
        ["git", "-c", "core.quotePath=false", "ls-tree", "-r", "--name-only", ref],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return set()
    return {line for line in result.stdout.splitlines() if line}


def read_file_at_ref(repo_path: Path, ref: str, relpath: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:{relpath}"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def is_commit(repo_path: Path, ref: str) -> bool:
    """¿`ref` existe y apunta a un commit? Una ref mal escrita daba un árbol vacío y todo salía
    como «añadido»: un changelog falso con código de salida 0."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "--end-of-options", f"{ref}^{{commit}}"],
        cwd=repo_path,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0
