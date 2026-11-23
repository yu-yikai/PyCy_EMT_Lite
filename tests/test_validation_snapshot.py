"""Check that local comparison reports bind shared validation source files."""

import pytest

from validation.common import snapshot


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
