WITH grouped AS (
  SELECT species, COUNT(body_mass_g) AS observed,
         AVG(body_mass_g) AS mean_mass_g
  FROM observations GROUP BY species
)
SELECT SUM(mean_mass_g * observed) / SUM(observed) AS correct_pooled_mean_g,
       AVG(mean_mass_g) AS equal_species_mean_g
FROM grouped;
