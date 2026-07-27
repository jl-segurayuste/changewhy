from conftest import commit_all, write

from changewhy.runner import discover_checks, run_checks


def test_discover_checks_incluye_los_builtin():
    checks = discover_checks()
    expected = {"api_diff", "dependency_diff", "cli_diff"}
    assert expected <= set(checks)


def test_run_checks_devuelve_un_resultado_por_check(git_repo):
    write(git_repo, "a.py", "x = 1\n")
    sha = commit_all(git_repo)
    results = run_checks(git_repo, sha, sha, only={"api_diff", "cli_diff"})
    names = {r.check_name for r in results}
    assert names == {"api_diff", "cli_diff"}


def test_run_checks_skip_excluye(git_repo):
    write(git_repo, "a.py", "x = 1\n")
    sha = commit_all(git_repo)
    results = run_checks(git_repo, sha, sha, only={"api_diff", "cli_diff"}, skip={"cli_diff"})
    names = {r.check_name for r in results}
    assert "cli_diff" not in names
    assert "api_diff" in names


def test_run_checks_captura_excepcion_de_un_check_roto(git_repo, monkeypatch):
    import changewhy.runner as runner_module

    class BrokenCheck:
        name = "broken"

        def run(self, repo_path, ref_a, ref_b):
            raise RuntimeError("boom")

    monkeypatch.setattr(runner_module, "discover_checks", lambda: {"broken": BrokenCheck})
    write(git_repo, "a.py", "x = 1\n")
    sha = commit_all(git_repo)
    results = run_checks(git_repo, sha, sha)
    assert len(results) == 1
    assert results[0].error is not None
    assert "boom" in results[0].summary
