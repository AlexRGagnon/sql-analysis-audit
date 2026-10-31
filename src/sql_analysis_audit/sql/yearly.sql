WITH grouped AS (
  SELECT species, year, COUNT(*) AS n, COUNT(body_mass_g) AS mass_observed,
         AVG(body_mass_g) AS mean_mass_g
  FROM observations GROUP BY species, year
), lagged AS (
  SELECT *, LAG(mean_mass_g) OVER (PARTITION BY species ORDER BY year)
         AS prior_sample_mean_g FROM grouped
)
SELECT *, mean_mass_g - prior_sample_mean_g AS sample_mean_change_g
FROM lagged ORDER BY species, year;
