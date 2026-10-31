WITH pairs AS (
  SELECT species, flipper_length_mm AS x, body_mass_g AS y
  FROM observations
  WHERE flipper_length_mm IS NOT NULL AND body_mass_g IS NOT NULL
), centered AS (
  SELECT x - AVG(x) OVER () AS dx, y - AVG(y) OVER () AS dy,
         x - AVG(x) OVER (PARTITION BY species) AS sx,
         y - AVG(y) OVER (PARTITION BY species) AS sy
  FROM pairs
)
SELECT 'pooled' AS scope, COUNT(*) AS n,
       SUM(dx*dx) AS ss_x, SUM(dy*dy) AS ss_y, SUM(dx*dy) AS cross_product
FROM centered
UNION ALL
SELECT 'species_centered', COUNT(*), SUM(sx*sx), SUM(sy*sy), SUM(sx*sy)
FROM centered ORDER BY scope;
