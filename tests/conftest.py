import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def localstack_diff() -> str:
    """
    Clone the localstack repo and return the output of `git show 6269d348d072`.

    This is session-scoped to avoid cloning multiple times during the test run.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path = Path(tmp_dir) / "localstack"

        # Clone without blobs or checkout - fetches only commit metadata
        subprocess.run(
            [
                "git",
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                "https://github.com/localstack/localstack",
                str(repo_path),
            ],
            check=True,
            capture_output=True,
        )

        # Get the diff content (fetches only the blobs needed for this commit)
        result = subprocess.run(
            ["git", "-C", str(repo_path), "show", "6269d348d072"],
            check=True,
            capture_output=True,
            text=True,
        )

        return result.stdout
