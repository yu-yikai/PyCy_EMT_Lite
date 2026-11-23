"""Archive the Python inputs used by a local native-reference comparison."""

from __future__ import annotations

import shutil
import subprocess
from itertools import chain
from pathlib import Path

from validation.common.runner import sha256


def snapshot_sources(root: Path, destination: Path, *case_files: Path) -> tuple[dict[Path, str], dict]:
    """Copy the example, contracts and all shared Python validation dependencies."""
    git = ["git", "-c", f"safe.directory={root.as_posix()}"]
    head = subprocess.check_output([*git, "rev-parse", "HEAD"], cwd=root, text=True).strip()
    status = subprocess.check_output([*git, "status", "--porcelain", "--untracked-files=all"],
                                     cwd=root, text=True).splitlines()
    paths = (*case_files, root / "uv.lock", root / "pyproject.toml",
             *sorted((root / "pycy_emt_lite").rglob("*.py")), *sorted((root / "validation").rglob("*.py")))
    destination.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for path in paths:
        relative = path.relative_to(root)
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"Comparison source escapes repository: {relative}")
        digest = sha256(path)
        copy = destination / relative
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, copy)
        if sha256(copy) != digest:
            raise ValueError(f"Comparison input changed while copying: {relative}")
        hashes[path] = digest
    return hashes, {"source_head": head, "git_status_at_run": status,
                    "source_sha256": {path.relative_to(root).as_posix(): digest for path, digest in hashes.items()}}


def verify_inputs(
    root: Path, destination: Path, sources: dict[Path, str], reference: dict[Path, str],
) -> None:
    """Detect edits to originals or archived source copies before reporting."""
    for path, digest in chain(sources.items(), reference.items()):
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"An input changed during comparison: {path.relative_to(root)}")
    for path, digest in sources.items():
        relative = path.relative_to(root)
        copy = destination / relative
        if not copy.is_file() or sha256(copy) != digest:
            raise ValueError(f"The source snapshot changed during comparison: {relative}")
