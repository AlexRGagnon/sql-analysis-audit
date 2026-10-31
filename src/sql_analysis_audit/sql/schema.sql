CREATE TABLE observations (
  observation_id INTEGER PRIMARY KEY,
  species TEXT NOT NULL CHECK(species IN ('Adelie','Chinstrap','Gentoo')),
  island TEXT NOT NULL CHECK(island IN ('Biscoe','Dream','Torgersen')),
  bill_length_mm REAL CHECK(bill_length_mm > 0),
  bill_depth_mm REAL CHECK(bill_depth_mm > 0),
  flipper_length_mm REAL CHECK(flipper_length_mm > 0),
  body_mass_g REAL CHECK(body_mass_g > 0),
  sex TEXT CHECK(sex IN ('female','male')),
  year INTEGER NOT NULL CHECK(year BETWEEN 2007 AND 2009)
) STRICT;
CREATE INDEX observations_species_year ON observations(species, year);
