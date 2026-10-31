# SQL analysis audit: measured results

Dataset: 344 observations; 342 observed masses; 2 missing masses; 333 complete cases.

Observed-mass mean: **4201.754386 g**.

| Species | Rows | Measured masses | Mean mass (g) |
|---|---:|---:|---:|
| Adelie | 152 | 151 | 3700.662252 |
| Chinstrap | 68 | 68 | 3733.088235 |
| Gentoo | 124 | 123 | 5076.016260 |

## Review cases

### null-denominator: reject

Constructed claim: SUM(body_mass_g) / COUNT(*) is the observed-mass mean.

COUNT(*) includes missing masses while SUM ignores them. Use AVG(body_mass_g), or divide by COUNT(body_mass_g). The estimand is the mean among measured masses, not an imputed population mean.

### unweighted-subgroup-means: reject

Constructed claim: The equally weighted mean of species means is the pooled observation mean.

Equal-species weighting answers a different question. Recover the observation-weighted mean using each species nonmissing mass count, not its total row count.

### join-fanout: reject

Constructed claim: Joining species tags preserves the number of observations.

A deliberately duplicated dimension key replicates Adelie observations. Reject duplicate keys before joining. DISTINCT is not a general repair because distinct real observations can share measurements.

### unnecessary-complete-cases: reject-for-stated-estimand

Constructed claim: Estimating the observed-mass mean requires every unrelated field to be present.

Filtering on sex and bill measurements discards additional usable masses. Complete-case analysis can be appropriate for a specified multivariable model, but it changes the sample here; missingness may be informative.

### causal-overclaim: not-supported

Constructed claim: The pooled mass/flipper association establishes a causal effect applicable to each species.

Pooled and within-species centered associations answer different descriptive questions. Neither identifies causation. Species adjustment alone does not resolve sex, year, sampling, or other confounding.

## Interpretation boundaries

Five authored flawed-analysis fixtures; no model was queried and no employer assessment was used. Descriptive analysis of a fixed historical sample, not causal or population inference.

Row IDs are source-file ordinals, not original animal identifiers. Yearly changes compare samples, not within-animal growth. No p-values, confidence intervals, predictive accuracy, or population-generalization claims are attached to these descriptive results.

Data: Horst, Hill & Gorman (2020), palmerpenguins, CC0-1.0; original study Gorman et al. (2014), doi:10.1371/journal.pone.0090081.

The JSON report retains source provenance, SQL hashes, all case measurements, and runtime versions.
