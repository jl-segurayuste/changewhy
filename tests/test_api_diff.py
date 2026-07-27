from conftest import commit_all, write

from changewhy.checks.api_diff import ApiDiffCheck, extract_signatures


def test_extract_signatures_funcion_top_level():
    sigs = extract_signatures("def foo(a, b=1):\n    pass\n")
    assert "foo" in sigs


def test_extract_signatures_ignora_privadas():
    sigs = extract_signatures("def _helper():\n    pass\n")
    assert sigs == {}


def test_extract_signatures_metodos_de_clase():
    sigs = extract_signatures("class Foo:\n    def bar(self, x):\n        pass\n")
    assert "Foo.bar" in sigs


def test_extract_signatures_codigo_invalido_no_rompe():
    assert extract_signatures("esto no es python [[[") == {}


def test_detecta_funcion_anadida(git_repo):
    write(git_repo, "mod.py", "def foo():\n    pass\n")
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "mod.py", "def foo():\n    pass\n\n\ndef bar():\n    pass\n")
    sha_b = commit_all(git_repo, "b")

    result = ApiDiffCheck().run(git_repo, sha_a, sha_b)
    titles = [f.title for f in result.findings]
    assert any("Añadido: bar" in t for t in titles)


def test_detecta_funcion_eliminada(git_repo):
    write(git_repo, "mod.py", "def foo():\n    pass\n\n\ndef bar():\n    pass\n")
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "mod.py", "def foo():\n    pass\n")
    sha_b = commit_all(git_repo, "b")

    result = ApiDiffCheck().run(git_repo, sha_a, sha_b)
    hit = next(f for f in result.findings if "Eliminado: bar" in f.title)
    assert hit.severity == "medium"


def test_detecta_firma_cambiada(git_repo):
    write(git_repo, "mod.py", "def foo(a):\n    pass\n")
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "mod.py", "def foo(a, b):\n    pass\n")
    sha_b = commit_all(git_repo, "b")

    result = ApiDiffCheck().run(git_repo, sha_a, sha_b)
    assert any("Firma cambiada" in f.title for f in result.findings)


def test_fichero_nuevo_se_reporta(git_repo):
    write(git_repo, "a.py", "x = 1\n")
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "b.py", "y = 2\n")
    sha_b = commit_all(git_repo, "b")

    result = ApiDiffCheck().run(git_repo, sha_a, sha_b)
    assert any("Fichero nuevo: b.py" in f.title for f in result.findings)


def test_ignora_ficheros_de_tests(git_repo):
    write(git_repo, "src/mod.py", "def foo():\n    pass\n")
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "src/mod.py", "def foo():\n    pass\n")
    write(git_repo, "tests/test_mod.py", "def test_foo():\n    pass\n")
    sha_b = commit_all(git_repo, "b")

    result = ApiDiffCheck().run(git_repo, sha_a, sha_b)
    assert result.findings == []


def test_sin_cambios_no_hay_hallazgos(git_repo):
    write(git_repo, "a.py", "def foo():\n    pass\n")
    sha_a = commit_all(git_repo, "a")

    result = ApiDiffCheck().run(git_repo, sha_a, sha_a)
    assert result.findings == []
