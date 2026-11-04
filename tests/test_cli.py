from conftest import commit_all, write

from changewhy.cli import main


def test_diff_sin_cambios_exit_0(git_repo, capsys):
    write(git_repo, "a.py", "def foo():\n    pass\n")
    sha = commit_all(git_repo)
    rc = main(["diff", sha, sha, str(git_repo), "--fail-on", "medium"])
    assert rc == 0


def test_diff_con_funcion_eliminada_exit_1(git_repo, capsys):
    write(git_repo, "mod.py", "def foo():\n    pass\n\n\ndef bar():\n    pass\n")
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "mod.py", "def foo():\n    pass\n")
    sha_b = commit_all(git_repo, "b")

    rc = main(["diff", sha_a, sha_b, str(git_repo), "--fail-on", "medium"])
    assert rc == 1


def test_diff_json(git_repo, capsys):
    write(git_repo, "a.py", "x = 1\n")
    sha = commit_all(git_repo)
    main(["diff", sha, sha, str(git_repo), "--json"])
    out = capsys.readouterr().out
    assert '"check_name"' in out


def test_diff_only(git_repo, capsys):
    write(git_repo, "mod.py", "def foo():\n    pass\n")
    sha_a = commit_all(git_repo, "a")
    write(git_repo, "mod.py", "def foo():\n    pass\n\n\ndef bar():\n    pass\n")
    sha_b = commit_all(git_repo, "b")

    main(["diff", sha_a, sha_b, str(git_repo), "--only", "api_diff"])
    out = capsys.readouterr().out
    assert "api_diff" in out
    assert "dependency_diff" not in out


def test_list_checks(capsys):
    main(["list-checks"])
    out = capsys.readouterr().out
    assert "api_diff" in out
    assert "dependency_diff" in out
    assert "cli_diff" in out


def test_ref_inexistente_sale_2(git_repo, capsys):
    write(git_repo, "a.py", "x = 1\n")
    sha = commit_all(git_repo)
    assert main(["diff", "v9.9.9", sha, str(git_repo)]) == 2
    assert "v9.9.9" in capsys.readouterr().err


def test_check_desconocido_sale_2(git_repo, capsys):
    write(git_repo, "a.py", "x = 1\n")
    sha = commit_all(git_repo)
    assert main(["diff", sha, sha, str(git_repo), "--only", "typo"]) == 2
