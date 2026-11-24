"""Check that local comparison reports bind shared validation source files."""

import shutil
import subprocess
from pathlib import Path

import pytest

from validation.common import snapshot


def test_exact_reference_inputs_survive_autocrlf_checkout(tmp_path, monkeypatch):
    git_executable = shutil.which("git")
    if git_executable is None:
        pytest.skip("Git is required to verify checkout line endings")

    source = Path(__file__).resolve().parents[1]
    buck = Path("validation/cases/synchronous_buck")
    vsc = Path("validation/cases/grid_connected_vsc_open_loop")
    records = Path("docs/development_roadmap/experiments")
    inputs = (
        *(buck / name for name in (
            "acceptance_plan.md", "audit_reference.py", "export_reference.m", "manifest.json",
            "native_logging_api_addendum.md", "normalization.py", "parameters.json",
            "reference_solver_addendum.json", "reference_solver_addendum.md",
        )),
        Path("validation/common/comparison.py"),
        *(vsc / name for name in ("parameters.json", "qualified_reference_report.json", "reference_protocol.json")),
        *(records / name for name in (
            "d1_dual_vsc_long_native_20261123.json", "d1_dual_vsc_long_protocol_20261123.json",
            "d1_pjm5_emt_protocol_20261123.json", "d1_pjm5_pscad_reference_20261123.json",
        )),
    )
    repository = tmp_path / "repository"
    repository.mkdir()
    empty_attributes = tmp_path / "empty-attributes"
    empty_attributes.touch()
    monkeypatch.setenv("GIT_ATTR_NOSYSTEM", "1")
    git = [git_executable, "-c", "core.autocrlf=true", "-c", "core.safecrlf=false",
           "-c", f"core.attributesFile={empty_attributes}"]
    subprocess.run([*git, "init", "--quiet", "--template="], cwd=repository, check=True)
    shutil.copyfile(source / ".gitattributes", repository / ".gitattributes")

    original = {}
    for relative in inputs:
        # Start with the repository's canonical LF bytes regardless of this worktree's line endings.
        original[relative] = (source / relative).read_bytes().replace(b"\r\n", b"\n")
        target = repository / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(original[relative])
    (repository / "control.txt").write_bytes(b"unprotected text\n")
    subprocess.run([*git, "add", "--force", "--", ".gitattributes", "control.txt",
                    *(path.as_posix() for path in inputs)], cwd=repository, check=True)
    checkout = tmp_path / "checkout"
    subprocess.run([*git, "checkout-index", "--all", f"--prefix={checkout.as_posix()}/"],
                   cwd=repository, check=True)

    assert (checkout / "control.txt").read_bytes() == b"unprotected text\r\n"
    for relative, expected in original.items():
        assert (checkout / relative).read_bytes() == expected, relative


@pytest.mark.parametrize("changed", [None, "original", "snapshot"])
def test_snapshot_records_shared_sources_and_detects_edits(tmp_path, monkeypatch, changed):
    root = tmp_path.resolve()
    shared = root / "validation" / "common" / "shared.py"
    shared.parent.mkdir(parents=True)
    shared.write_bytes(b"answer = 42\n")
    for name in ("case.json", "uv.lock", "pyproject.toml"):
        (root / name).touch()

    responses = iter(("0123456789abcdef\n", " M validation/common/shared.py\n"))
    monkeypatch.setattr(snapshot.subprocess, "check_output", lambda *args, **kwargs: next(responses))
    folder = root / "local_reference" / "run" / "inputs"
    sources, report = snapshot.snapshot_sources(root, folder, root / "case.json")
    copy = folder / shared.relative_to(root)

    assert report["source_head"] == "0123456789abcdef"
    assert report["git_status_at_run"] == [" M validation/common/shared.py"]
    assert report["source_sha256"]["validation/common/shared.py"] == sources[shared]
    assert copy.read_bytes() == shared.read_bytes()
    if changed is None:
        snapshot.verify_inputs(root, folder, sources, {})
    else:
        target = shared if changed == "original" else copy
        target.write_bytes(b"answer = 0\n")
        with pytest.raises(ValueError, match="changed during comparison"):
            snapshot.verify_inputs(root, folder, sources, {})
