SELECT COUNT(*) AS n,
       COUNT(body_mass_g) AS mass_observed,
       COUNT(*) - COUNT(body_mass_g) AS mass_missing,
       COUNT(sex) AS sex_observed,
       SUM(CASE WHEN bill_length_mm IS NOT NULL AND bill_depth_mm IS NOT NULL
                 AND flipper_length_mm IS NOT NULL AND body_mass_g IS NOT NULL
                 AND sex IS NOT NULL THEN 1 ELSE 0 END) AS complete_cases,
       AVG(body_mass_g) AS mean_mass_g,
       MIN(year) AS first_year, MAX(year) AS last_year
FROM observations;
