WITH grouped AS (
  SELECT species, COUNT(*) AS n, COUNT(body_mass_g) AS mass_observed,
         AVG(body_mass_g) AS mean_mass_g
  FROM observations GROUP BY species
)
SELECT species, n, mass_observed, mean_mass_g,
       1.0 * n / SUM(n) OVER () AS observation_share,
       DENSE_RANK() OVER (ORDER BY mean_mass_g DESC) AS mass_rank
FROM grouped ORDER BY species;
