# Local validation — 2026-10-30

## Environment

Windows on the authorized development workstation; Python 3.13.3; SQLite 3.49.1. Optional notebook tooling: nbformat 5.11.1, nbclient 0.11.0, ipykernel 7.4.0. Exact notebook dependencies are recorded in `requirements-notebook-windows-py313.lock`. Core analysis requires no third-party Python dependencies.

## Executed checks

- `python -m unittest discover -s tests -v`: **25 tests passed** against the editable installation.
- Built a wheel, created a separate virtual environment, and installed the wheel with `--no-index --no-deps`. Re-ran the same **25 tests successfully** using `python -I` so the source directory and PYTHONPATH could not shadow the installed package.
- Executed the CLI from the installed wheel. Its report was byte-identical to the published example: SHA-256 `d2f917fd5b64f2a02278e19d0bc8b5ed19309deb5c72af732e55b4f249b5d528`.
- Executed the notebook in fresh local kernels: **8 code cells, zero error outputs**. A second execution produced identical code-cell sources and outputs when execution timing metadata was excluded.
- Checked the source CSV against the upstream Git blob hash and the committed SHA-256. The installed wheel includes the snapshot, SQL files, provenance, and data-attribution notice.
- `python -m pip check`: no broken requirements.

Tests cover malformed input, non-finite/negative measurements, invalid categories/years, checksum tampering, NULL handling, independent Python references for SQL aggregates and associations, window calculations, dimension-key validation, literal parameterized labels, reproducible reports, and refusal to overwrite existing outputs. Repeated equal measurements remain separate observations.

## Reproduce

```sh
python -m pip install -e ".[notebook]"
python -m unittest discover -s tests -v
python -m sql_analysis_audit --out runs/recheck
python scripts/execute_notebook.py --output runs/recheck/analysis.ipynb
python scripts/compare_notebooks.py notebooks/analysis.executed.ipynb runs/recheck/analysis.ipynb
```

The report is deterministic in the recorded environment. Its runtime version fields intentionally change on another Python/SQLite version. Floating-point differences across engines/platforms are not promised to be byte-identical; tests use numerical tolerances against independent references.

## Warnings and limits

The tested Jupyter stack emitted nonfatal Windows selector-thread and unencrypted local-kernel TCP warnings. Notebook execution succeeded. The execution script checks that the kernel binds to a loopback address; this is not a network-facing service or an encrypted multi-user deployment.

No browser-based visual review, Linux/macOS execution, large-data benchmark, model evaluation against real model outputs, or causal/population inference is claimed. The five flawed analyses are authored fixtures. The dataset is real; the illustrative duplicate-tag dimension is synthetic and marked as such.

All computation ran locally. GitHub hosts source only; no GitHub Actions, hosted notebooks, paid APIs, or cloud training were used.
