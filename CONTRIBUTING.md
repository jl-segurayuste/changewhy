# Contribuir

## Añadir un check nuevo

Cada check implementa el protocolo `Check` (`changewhy/plugin.py`):

```python
class MiCheck:
    name = "mi_check"

    def run(self, repo_path: Path, ref_a: str, ref_b: str) -> CheckResult:
        ...
```

Usa `changewhy.gitref.list_files_at_ref`/`read_file_at_ref` para leer
contenido en cada ref — nunca hagas checkout ni ejecutes el código de
ninguno de los dos.

Se registra vía entry point en tu propio `pyproject.toml`:

```toml
[project.entry-points."changewhy.checks"]
mi_check = "mi_paquete.check:MiCheck"
```

## Antes de un PR

- `ruff check .` y `pytest` en verde.
- Todo check nuevo necesita tests con al menos: cambio detectado, sin
  cambios (mismo ref dos veces), y el caso límite de que el fichero
  relevante no exista en uno de los dos refs.
