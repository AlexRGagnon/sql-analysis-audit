# SQL Analysis Audit

A reproducible review of analytical SQL against real, attributed data. It combines a Python/SQLite pipeline, inspectable SQL files, an executed Jupyter notebook, and five deliberately flawed analyses with measured corrections.

This is a new independent portfolio study. It is not a collection of employer assessment questions, a transcript of model failures, or evidence of historical consulting work. No model is called by this project.

## Read the evidence

- [Executed notebook](notebooks/analysis.executed.ipynb): queries, actual outputs, checks, and interpretation.
- [Measured report](examples/report.md) and [machine-readable results](examples/report.json).
- [Methodology and data provenance](docs/METHODOLOGY.md).
- [Validation](VALIDATION.md): commands, environment, and verified outcomes.

## Run locally

Python 3.11+ and SQLite 3.37+ are required. The analysis and tests use only the Python standard library. All analysis runs offline against the included snapshot.

```sh
python -m venv .venv
# Activate the environment using your platform's normal command.
python -m pip install -e .
python -m unittest discover -s tests -v
python -m sql_analysis_audit --out runs/my-audit
```

The output directory must not already exist. The command validates the dataset checksum, loads strict SQLite tables, runs the queries, and writes `report.json` and `report.md`.

Without installing the package, set `PYTHONPATH=src`. For PowerShell:

```powershell
$env:PYTHONPATH='src'
python -m unittest discover -s tests -v
python -m sql_analysis_audit --out runs/my-audit
```

## Execute the notebook yourself

```sh
python -m pip install -e ".[notebook]"
python scripts/execute_notebook.py --output runs/notebook/analysis.ipynb
```

The execution script uses a temporary kernelspec pointing at the selected Python interpreter. It starts a fresh local Jupyter kernel, stops on any error, refuses to overwrite an existing output, and does not register a global kernel. The original notebook has no stored outputs; the committed executed notebook is a separate artifact.

`requirements-notebook-windows-py313.lock` records the exact notebook dependency versions validated on Windows/Python 3.13. It includes platform-specific packages and is not a universal cross-platform lock. Other platforms should use the notebook extra above. Package downloads are needed for installation, not for analysis. No cloud services, paid APIs, telemetry, or GitHub Actions.

## Analytical contracts

1. **Missingness:** `NA` becomes SQL `NULL`, not zero. Means use the actual measurement denominator.
2. **Weighting:** an observation-weighted mean is distinct from an equally weighted mean of species means.
3. **Join cardinality:** a species dimension must have one key per observed species. Duplicate keys are rejected before joining; legitimate identical measurements are not deduplicated.
4. **Sample definition:** deleting records with unrelated missing fields changes the sample and needs justification.
5. **Interpretation:** pooled and species-centered associations are descriptive; neither establishes a causal effect.

SQL examples include CTEs, conditional aggregation, `LAG`, `DENSE_RANK`, partitioned window averages, and cardinality-checked joins. Independent Python calculations check SQL means, proportions, correlations, slopes, and lagged changes.

## Dataset and scope

The snapshot contains 344 Palmer penguin observations collected in 2007-2009. The upstream simplified table is preserved byte-for-byte, with its pinned Git commit, Git blob hash, SHA-256, license, and citations in [provenance.json](src/sql_analysis_audit/data/provenance.json).

The data are CC0-1.0, according to the [dataset maintainers](https://allisonhorst.github.io/palmerpenguins/#license). Original code in this repository is MIT licensed. Data attribution: Horst, Hill & Gorman (2020), *palmerpenguins*, doi:10.5281/zenodo.3960218; original study Gorman et al. (2014), doi:10.1371/journal.pone.0090081.

This small dataset was chosen for inspectable data-quality and reasoning tests, not a scale benchmark. Row IDs are file ordinals, not original animal identifiers. The simplified table does not establish a probability sample or longitudinal subject identities. Year-to-year sample differences are not individual growth estimates. The report makes no population, causal, predictive-performance, or p-value claims. The fanout tags are explicitly synthetic review fixtures, not added source facts.
