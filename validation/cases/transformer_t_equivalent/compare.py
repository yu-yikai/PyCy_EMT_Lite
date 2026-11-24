"""Run with: uv run python -m validation.cases.transformer_t_equivalent.compare."""

import runpy
from pathlib import Path

from validation.common.runner import run_comparison


def main() -> None:
    directory = Path(__file__).resolve().parent
    example = directory.parents[2] / "examples/23_transformer_t_equivalent.py"
    case = runpy.run_path(str(example))["define_case"]()
    report = run_comparison(case, directory / "manifest.json", example)
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
