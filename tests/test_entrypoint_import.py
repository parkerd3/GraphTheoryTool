import os
from pathlib import Path
import subprocess
import sys


def test_direct_main_import_supports_matrix_modules() -> None:
    project_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")

    result = subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
