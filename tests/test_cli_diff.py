from conftest import commit_all, write

from changewhy.checks.cli_diff import CliDiffCheck


def test_comando_anadido(git_repo):
    write(git_repo, "pyproject.toml", '[project]\nname="x"\n[project.scripts]\nfoo = "x:main"\n')
    sha_a = commit_all(git_repo, "a")
    write(
        git_repo,
        "pyproject.toml",
        '[project]\nname="x"\n[project.scripts]\nfoo = "x:main"\nbar = "x:bar_main"\n',
    )
    sha_b = commit_all(git_repo, "b")

    result = CliDiffCheck().run(git_repo, sha_a, sha_b)
    assert any("añadido: bar" in f.title for f in result.findings)


def test_comando_eliminado(git_repo):
    write(
        git_repo,
        "pyproject.toml",
        '[project]\nname="x"\n[project.scripts]\nfoo = "x:main"\nbar = "x:bar_main"\n',
    )
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "pyproject.toml", '[project]\nname="x"\n[project.scripts]\nfoo = "x:main"\n')
    sha_b = commit_all(git_repo, "b")

    result = CliDiffCheck().run(git_repo, sha_a, sha_b)
    hit = next(f for f in result.findings if "eliminado: bar" in f.title)
    assert hit.severity == "medium"


def test_comando_redirigido(git_repo):
    write(git_repo, "pyproject.toml", '[project]\nname="x"\n[project.scripts]\nfoo = "x:main"\n')
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "pyproject.toml", '[project]\nname="x"\n[project.scripts]\nfoo = "x:new_main"\n')
    sha_b = commit_all(git_repo, "b")

    result = CliDiffCheck().run(git_repo, sha_a, sha_b)
    assert any("redirigido" in f.title for f in result.findings)


def test_sin_pyproject_no_hay_hallazgos(git_repo):
    write(git_repo, "a.py", "x = 1\n")
    sha_a = commit_all(git_repo, "a")
    result = CliDiffCheck().run(git_repo, sha_a, sha_a)
    assert result.findings == []
