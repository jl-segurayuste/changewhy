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


def test_recapitalizado_sin_cambio_real_no_genera_ruido(git_repo):
    # Bug real encontrado 2026-08-09: los nombres se comparaban tal cual, así
    # que un simple recapitalizado ("requests" -> "Requests", como haría un
    # linter o un editor manual, sin tocar la versión) se reportaba como
    # "eliminada + añadida" en vez de "sin cambios" -- ruido puro en el
    # changelog generado.
    write(git_repo, "requirements.txt", "requests>=2.31\n")
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "requirements.txt", "Requests>=2.31\n")
    sha_b = commit_all(git_repo, "b")

    result = DependencyDiffCheck().run(git_repo, sha_a, sha_b)
    assert result.findings == []


def test_recapitalizado_junto_con_cambio_de_version_se_detecta(git_repo):
    # Si el recapitalizado coincide con un cambio de versión real, ese
    # cambio no debe perderse dentro de un falso "eliminada + añadida".
    write(git_repo, "requirements.txt", "requests>=2.28\n")
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "requirements.txt", "Requests>=2.31\n")
    sha_b = commit_all(git_repo, "b")

    result = DependencyDiffCheck().run(git_repo, sha_a, sha_b)
    assert len(result.findings) == 1
    assert "Versión cambiada" in result.findings[0].title


def test_sin_cambios_no_hay_hallazgos(git_repo):
    write(git_repo, "requirements.txt", "click>=8.0\n")
    sha_a = commit_all(git_repo, "a")
    result = DependencyDiffCheck().run(git_repo, sha_a, sha_a)
    assert result.findings == []


def test_extras_de_pyproject(git_repo):
    write(git_repo, "pyproject.toml",
          '[project]\nname = "x"\n[project.optional-dependencies]\ndev = ["pytest>=7"]\n')
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "pyproject.toml",
          '[project]\nname = "x"\n[project.optional-dependencies]\n'
          'dev = ["pytest>=8"]\npdf = ["pypdf>=4"]\n')
    sha_b = commit_all(git_repo, "b")

    titles = [f.title for f in DependencyDiffCheck().run(git_repo, sha_a, sha_b).findings]
    assert "Dependencia añadida: pypdf (extra pdf) >=4" in titles
    assert "Versión cambiada: pytest (extra dev) >=7 -> pytest (extra dev) >=8" in titles
