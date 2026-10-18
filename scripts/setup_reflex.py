"""Repeatable Codespaces setup; preserve custom source during Reflex init."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile


def initialize(project: Path) -> None:
    if (project / ".web").is_dir():
        return
    env = {**os.environ, "CI": "1", "REFLEX_TELEMETRY_ENABLED": "false"}
    # Reflex init can refresh templates. Always restore the existing app/config,
    # including if initialization exits unsuccessfully.
    with tempfile.TemporaryDirectory(prefix="lasoai-reflex-init-") as backup:
        backup = Path(backup)
        shutil.copy2(project / "rxconfig.py", backup / "rxconfig.py")
        shutil.copytree(project / "lasoai_workspace", backup / "lasoai_workspace")
        try:
            subprocess.run(
                ["uv", "run", "reflex", "init", "--name", "lasoai_workspace", "--template", "blank"],
                cwd=project, env=env, check=True,
            )
        finally:
            shutil.copy2(backup / "rxconfig.py", project / "rxconfig.py")
            shutil.copytree(backup / "lasoai_workspace", project / "lasoai_workspace", dirs_exist_ok=True)


def main() -> None:
    project = Path(__file__).resolve().parents[1] / "apps" / "reflex"
    if not shutil.which("uv"):
        raise SystemExit("uv is missing. Rebuild the configured dev container.")
    command = ["uv", "sync"]
    if (project / "uv.lock").exists():
        command.append("--locked")
    subprocess.run(command, cwd=project, check=True)
    initialize(project)
    print("Dependencies and generated assets prepared. Start: bash scripts/start-reflex.sh")
    print("Commit apps/reflex/uv.lock after the first successful resolution.")


if __name__ == "__main__":
    main()
