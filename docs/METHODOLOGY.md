# Methodology and review rubric

## Question and estimands

The principal numerical target is the mean body mass among observations with a recorded mass in this fixed dataset. Secondary outputs describe species-specific and species/year-specific samples. We do not assume that observed records represent every penguin, that missingness is random, or that all years measured the same animals.

An equally weighted species mean is a valid alternative estimand when deliberately requested; it is wrong only when mislabeled as an observation-weighted pooled mean. Similarly, complete-case filtering can be needed by a specified multivariable analysis. The review cases explicitly state their target before judging a candidate.

## Provenance

The original CSV is from the upstream palmerpenguins project, pinned to commit `8957207b78d6ccd1b4654a9dd9c9041b657478ab`. It was downloaded directly on the local development machine and its Git blob hash was checked against the upstream contents API. Runtime SHA-256 verification checks consistency with the committed manifest; it is not a digital signature and does not protect against an attacker replacing both files.

The raw data are not rewritten or deduplicated. A temporary in-memory database assigns stable file-ordinal observation IDs. Missing values remain NULL. The input contract checks all column names, category labels, row widths, measurement positivity/finiteness, and years. It rejects malformed input rather than silently coercing it.

Data are licensed CC0-1.0 as documented by the maintainers. Source: https://allisonhorst.github.io/palmerpenguins/ . Original ecological study: https://doi.org/10.1371/journal.pone.0090081 . Citation: Horst AM, Hill AP, Gorman KB (2020), https://doi.org/10.5281/zenodo.3960218 . Data should be interpreted with the original study's sampling design; this repository is a methods demonstration, not a new biological result.

## Five constructed review cases

| Case | Defect | Evidence / correction |
|---|---|---|
| Missing denominator | SUM ignores NULL values while COUNT(*) includes their rows | Compare the candidate with AVG(body_mass_g) and independent Python mean |
| Unweighted subgroup means | Each species receives equal weight despite unequal observed-mass counts | Weight species means by COUNT(body_mass_g) |
| Join fanout | Two tags for one species replicate its fact rows | Reject duplicate dimension keys and reconcile fact IDs before/after the join |
| Unnecessary complete cases | Removing unrelated missing fields discards usable masses | Match exclusion rules to the stated estimand and disclose sample changes |
| Causal overclaim | A pooled association is interpreted as a causal within-species effect | Show pooled and species-centered descriptive results, and withhold causal conclusions |

The candidate claims are authored negative controls, not captured AI responses. Numeric tests establish that the shown queries disagree with their stated targets. A causal claim's unsupported status follows from the design, not from a special statistical test that proves absence of causation.

## Statistical details

The association query forms complete mass/flipper pairs. Pooled Pearson correlation uses centered sums of squares and cross-products. The species-centered version first subtracts each species' mean from both variables and then computes the correlation of those residuals. That is a within-species residual association, not the average of three species correlations. Slopes have units g/mm. Independent Python `statistics` calculations are the regression oracle.

The within-species calculation is not a causal adjustment strategy: sex, year, selection, and other variables can still matter. No significance testing, multiple-comparison search, confidence interval, or predictive model is run. There is no train/test claim to imply.

## Review criteria

A defensible response states the target quantity, identifies the exact defect, reproduces it, supplies a corrected computation, and explains what remains unsupported. Correctness includes honest uncertainty and scope, not only code execution. Queries and reports include deterministic hashes and runtime versions so results can be traced to their inputs.

## References for implementation

SQLite aggregate semantics: https://sqlite.org/lang_aggfunc.html

SQLite window functions: https://sqlite.org/windowfunctions.html

Jupyter notebook execution: https://nbclient.readthedocs.io/en/latest/client.html
