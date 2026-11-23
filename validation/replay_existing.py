"""Replay an accepted comparison from its exact local input snapshot."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from validation.common.runner import sha256

CASES = {
    "11": ("pll_dynamic_response", "input_snapshot"),
    "12": ("two_level_pwm_pscad", "inputs"),
}


def _archive_path(root: Path, relative: str) -> Path:
    parts = PurePosixPath(relative)
    if parts.as_posix() != relative or parts.is_absolute() or ".." in parts.parts or any(c in relative for c in "\\:"):
        raise ValueError(f"Expected a repository-relative archive path: {relative!r}")
    path = root / relative
    if not path.resolve().is_relative_to(root):
        raise ValueError(f"Archive path escapes its directory: {relative!r}")
    return path


def replay(root: Path, number: str) -> None:
    """Check the original bytes, restore them in a detached checkout, then compare."""
    case, folder = CASES[number]
    public = json.loads((root / "validation" / "cases" / case / "validation_report.json").read_bytes())
    accepted = public["complete_report"]
    report_path = _archive_path(root, accepted["path"])
    if not report_path.is_file() or sha256(report_path) != accepted["sha256"]:
        raise ValueError(f"Missing or changed accepted local report: {accepted['path']}")
    report = json.loads(report_path.read_bytes())
    if report["passed"] is not True or report["case_id"] != case:
        raise ValueError(f"Unexpected accepted comparison report: {accepted['path']}")

    snapshot = report_path.parent / folder
    bindings = report["native_input_sha256"] | report["code_and_protocol_sha256"]
    for relative, digest in bindings.items():
        path = _archive_path(snapshot, relative)
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"Missing or changed snapshot input: {path}")

    run = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination = root / "local_reference" / f"replay-{number}-{run}"
    destination.mkdir()
    revision = report["git_head_at_run"]
    git = ["git", "-c", f"safe.directory={root.as_posix()}"]
    # Copy the historical Git objects without writing to the active repository or using a remote.
    pack = subprocess.check_output([*git, "pack-objects", "--stdout", "--revs"],
                                   cwd=root, input=f"{revision}\n".encode("ascii"))
    subprocess.run(["git", "init", "--quiet", "--template="], cwd=destination, check=True)
    subprocess.run(["git", "index-pack", "--stdin"], cwd=destination, input=pack, stdout=subprocess.DEVNULL, check=True)
    subprocess.run(["git", "-c", "core.autocrlf=false", "checkout", "--detach", "--quiet", revision],
                   cwd=destination, check=True)
    for relative, digest in bindings.items():
        target = _archive_path(destination, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(snapshot / relative, target)
        if sha256(target) != digest:
            raise ValueError(f"Input changed while restoring: {relative}")

    print(f"Historical source: {revision}\nReplay checkout: {destination}", flush=True)
    env = os.environ.copy()
    for name in ("UV_PROJECT_ENVIRONMENT", "VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME"):
        env.pop(name, None)
    env["MPLBACKEND"] = "Agg"
    subprocess.run(["uv", "run", "--locked", "python", "-m", f"validation.cases.{case}.compare"],
                   cwd=destination, env=env, check=True)
    replay_dir = destination / "local_reference" / case / "comparison_results"
    new_report = next(replay_dir.glob("*/report.json"), None)
    if new_report is None:
        raise ValueError(f"Replay did not create a report in {replay_dir}")
    replayed = json.loads(new_report.read_bytes())
    if (replayed["passed"] is not True or replayed["candidate_executed"] is not True
            or replayed["git_head_at_run"] != revision or replayed["case_id"] != case
            or any(replayed[key] != report[key] for key in ("code_and_protocol_sha256", "native_input_sha256"))):
        raise ValueError(f"Replay did not pass with the accepted inputs: {new_report}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=CASES, help="11 (Simulink PLL) or 12 (PSCAD PWM)")
    args = parser.parse_args()
    try:
        replay(Path(__file__).resolve().parents[1], args.case)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
