from conftest import commit_all, write

from changewhy.checks.dependency_diff import DependencyDiffCheck


def test_dependencia_anadida(git_repo):
    write(git_repo, "requirements.txt", "click>=8.0\n")
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "requirements.txt", "click>=8.0\nrequests>=2.31\n")
    sha_b = commit_all(git_repo, "b")

    result = DependencyDiffCheck().run(git_repo, sha_a, sha_b)
    assert any("añadida: requests" in f.title for f in result.findings)


def test_dependencia_eliminada(git_repo):
    write(git_repo, "requirements.txt", "click>=8.0\nrequests>=2.31\n")
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "requirements.txt", "click>=8.0\n")
    sha_b = commit_all(git_repo, "b")

    result = DependencyDiffCheck().run(git_repo, sha_a, sha_b)
    hit = next(f for f in result.findings if "eliminada: requests" in f.title)
    assert hit.severity == "low"


def test_version_cambiada(git_repo):
    write(git_repo, "requirements.txt", "numpy>=1.26,<2\n")
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "requirements.txt", "numpy>=2.0\n")
    sha_b = commit_all(git_repo, "b")

    result = DependencyDiffCheck().run(git_repo, sha_a, sha_b)
    assert any("Versión cambiada" in f.title for f in result.findings)


def test_pyproject_toml_tambien_se_compara(git_repo):
    write(git_repo, "pyproject.toml", '[project]\nname="x"\ndependencies = ["click"]\n')
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "pyproject.toml", '[project]\nname="x"\ndependencies = ["click", "pydantic>=2.6"]\n')
    sha_b = commit_all(git_repo, "b")

    result = DependencyDiffCheck().run(git_repo, sha_a, sha_b)
    assert any("pydantic" in f.title for f in result.findings)


def test_sin_cambios_no_hay_hallazgos(git_repo):
    write(git_repo, "requirements.txt", "click>=8.0\n")
    sha_a = commit_all(git_repo, "a")
    result = DependencyDiffCheck().run(git_repo, sha_a, sha_a)
    assert result.findings == []
