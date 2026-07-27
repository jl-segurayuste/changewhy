from conftest import commit_all, write

from changewhy.gitref import list_files_at_ref, read_file_at_ref


def test_list_files_at_ref(git_repo):
    write(git_repo, "a.py", "x = 1\n")
    sha = commit_all(git_repo)
    assert list_files_at_ref(git_repo, sha) == {"a.py"}


def test_list_files_at_ref_distintos_commits(git_repo):
    write(git_repo, "a.py", "x = 1\n")
    sha1 = commit_all(git_repo, "primero")
    write(git_repo, "b.py", "y = 2\n")
    sha2 = commit_all(git_repo, "segundo")
    assert list_files_at_ref(git_repo, sha1) == {"a.py"}
    assert list_files_at_ref(git_repo, sha2) == {"a.py", "b.py"}


def test_read_file_at_ref(git_repo):
    write(git_repo, "a.py", "x = 1\n")
    sha = commit_all(git_repo)
    assert read_file_at_ref(git_repo, sha, "a.py") == "x = 1\n"


def test_read_file_at_ref_inexistente(git_repo):
    write(git_repo, "a.py", "x = 1\n")
    sha = commit_all(git_repo)
    assert read_file_at_ref(git_repo, sha, "no-existe.py") is None
