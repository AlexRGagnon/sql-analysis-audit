"""Independent Python oracles plus malformed-input and analytical-regression checks."""
from collections import defaultdict
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import unittest

from sql_analysis_audit.audit import (
    COLUMNS, DATA, SQL, Observation, build_report, checked_species_join,
    create_database, describe_association, load_rows, parse_csv, provenance,
    query, render_markdown, verify_snapshot,
)

HEADER = ','.join(COLUMNS) + '\n'
VALID = 'Adelie,Torgersen,39.1,18.7,181,3750,male,2007\n'


class InputTests(unittest.TestCase):
    def test_snapshot_integrity_and_upstream_blob(self):
        raw = DATA.read_bytes()
        self.assertEqual(verify_snapshot(), provenance()['sha256'])
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        self.assertEqual(blob, provenance()['upstream_git_blob'])

    def test_snapshot_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'bad.csv'
            p.write_bytes(DATA.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                build_report(p)

    def test_exact_header_required(self):
        for header in ('', HEADER.replace('species', 'Species'), HEADER.replace('sex,year', 'year,sex')):
            with self.subTest(header=header), self.assertRaises(ValueError):
                parse_csv(header + VALID)

    def test_empty_data_rejected(self):
        with self.assertRaisesRegex(ValueError, 'at least one'):
            parse_csv(HEADER)

    def test_explicit_missing_values_preserved(self):
        row = parse_csv(HEADER + 'Adelie,Torgersen,NA,NA,NA,NA,NA,2007\n')[0]
        self.assertIsNone(row.body_mass_g)
        self.assertIsNone(row.sex)
        self.assertEqual(row.year, 2007)

    def test_wrong_column_count_rejected(self):
        for line in (VALID.rstrip() + ',extra\n', ','.join(VALID.split(',')[:-1]) + '\n'):
            with self.subTest(line=line), self.assertRaises(ValueError):
                parse_csv(HEADER + line)

    def test_unknown_categories_rejected(self):
        for before, after in [('Adelie', 'Unknown'), ('Torgersen', 'Nowhere'), ('male', 'unspecified')]:
            with self.subTest(after=after), self.assertRaises(ValueError):
                parse_csv(HEADER + VALID.replace(before, after))

    def test_bad_measurements_rejected(self):
        for token in ('nan', 'inf', '-inf', '0', '-1', 'text', ''):
            with self.subTest(token=token), self.assertRaises(ValueError):
                parse_csv(HEADER + VALID.replace('3750', token))

    def test_invalid_years_rejected(self):
        for token in ('2007.0', '2006', '2010', 'NA', '2e3'):
            with self.subTest(token=token), self.assertRaises(ValueError):
                parse_csv(HEADER + VALID.replace('2007', token))

    def test_equal_measurements_do_not_imply_duplicate_identity(self):
        rows = parse_csv(HEADER + VALID + VALID)
        con = create_database(rows)
        try:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM observations').fetchone()[0], 2)
            self.assertEqual(con.execute('SELECT COUNT(DISTINCT observation_id) FROM observations').fetchone()[0], 2)
        finally:
            con.close()


class SQLTests(unittest.TestCase):
    def setUp(self):
        self.rows = load_rows()
        self.con = create_database(self.rows)
        self.addCleanup(self.con.close)

    def test_profile_matches_independent_reference(self):
        p = query(self.con, 'profile')[0]
        mass = [r.body_mass_g for r in self.rows if r.body_mass_g is not None]
        self.assertEqual(p['n'], 344)
        self.assertEqual(p['mass_observed'], len(mass))
        self.assertEqual(p['mass_observed'], 342)
        self.assertEqual(p['complete_cases'], 333)
        self.assertEqual(p['sex_observed'], 333)
        self.assertAlmostEqual(p['mean_mass_g'], statistics.mean(mass), places=10)

    def test_group_aggregates_and_window_shares(self):
        groups = defaultdict(list)
        for row in self.rows:
            groups[row.species].append(row)
        result = query(self.con, 'species')
        self.assertAlmostEqual(sum(r['observation_share'] for r in result), 1.0)
        for row in result:
            values = groups[row['species']]
            mass = [r.body_mass_g for r in values if r.body_mass_g is not None]
            self.assertEqual(row['n'], len(values))
            self.assertEqual(row['mass_observed'], len(mass))
            self.assertAlmostEqual(row['mean_mass_g'], statistics.mean(mass), places=10)
            self.assertAlmostEqual(row['observation_share'], len(values)/len(self.rows))
        self.assertEqual(next(r['mass_rank'] for r in result if r['species']=='Gentoo'), 1)

    def test_yearly_lag_matches_python(self):
        groups = defaultdict(list)
        for row in self.rows:
            if row.body_mass_g is not None:
                groups[(row.species, row.year)].append(row.body_mass_g)
        prior = {}
        results = query(self.con, 'yearly')
        self.assertEqual(len(results), 9)
        for row in results:
            value = statistics.mean(groups[(row['species'], row['year'])])
            self.assertAlmostEqual(row['mean_mass_g'], value, places=10)
            if row['species'] in prior:
                self.assertAlmostEqual(row['sample_mean_change_g'], value-prior[row['species']], places=10)
            else:
                self.assertIsNone(row['prior_sample_mean_g'])
                self.assertIsNone(row['sample_mean_change_g'])
            prior[row['species']] = value

    def test_weighted_group_mean_recovers_pooled_mean(self):
        result = query(self.con, 'weighted_mean')[0]
        mass = [r.body_mass_g for r in self.rows if r.body_mass_g is not None]
        self.assertAlmostEqual(result['correct_pooled_mean_g'], statistics.mean(mass), places=10)
        self.assertGreater(abs(result['equal_species_mean_g']-statistics.mean(mass)), 20)

    def test_associations_against_independent_python(self):
        pairs = [r for r in self.rows if r.flipper_length_mm is not None and r.body_mass_g is not None]
        x = [r.flipper_length_mm for r in pairs]
        y = [r.body_mass_g for r in pairs]
        gx, gy = {}, {}
        for species in {r.species for r in pairs}:
            subgroup = [r for r in pairs if r.species == species]
            gx[species] = statistics.mean(r.flipper_length_mm for r in subgroup)
            gy[species] = statistics.mean(r.body_mass_g for r in subgroup)
        sx = [r.flipper_length_mm-gx[r.species] for r in pairs]
        sy = [r.body_mass_g-gy[r.species] for r in pairs]
        result = {r['scope']: r for r in describe_association(query(self.con, 'association'))}
        self.assertAlmostEqual(result['pooled']['pearson_r'], statistics.correlation(x, y), places=12)
        self.assertAlmostEqual(result['species_centered']['pearson_r'], statistics.correlation(sx, sy), places=12)
        self.assertAlmostEqual(result['pooled']['slope_g_per_mm'], statistics.linear_regression(x, y).slope, places=10)
        self.assertEqual(result['pooled']['n'], len(pairs))

    def test_unknown_query_name_rejected(self):
        for name in ('schema', '../schema', 'DROP TABLE observations'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                query(self.con, name)
        self.assertEqual(query(self.con, 'profile')[0]['n'], 344)

    def test_database_constraints(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("UPDATE observations SET body_mass_g=-1 WHERE observation_id=1")
        self.assertEqual(self.con.execute('SELECT body_mass_g FROM observations WHERE observation_id=1').fetchone()[0], 3750)
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("UPDATE observations SET species='Unknown' WHERE observation_id=1")

    def test_safe_join_cardinality_and_literal_labels(self):
        labels = [('Adelie', "O'Reilly; DROP TABLE observations;"), ('Chinstrap','C'), ('Gentoo','G')]
        result = checked_species_join(self.con, labels)
        self.assertEqual(len(result), 344)
        self.assertEqual(len({r['observation_id'] for r in result}), 344)
        self.assertEqual(result[0]['label'], labels[0][1])
        self.assertEqual(query(self.con, 'profile')[0]['n'], 344)

    def test_duplicate_dimension_rejected_without_mutation(self):
        valid = [('Adelie','A'), ('Chinstrap','C'), ('Gentoo','G')]
        before = checked_species_join(self.con, valid)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            checked_species_join(self.con, valid + [('Adelie','duplicate')])
        self.assertEqual(checked_species_join(self.con, valid), before)

    def test_incomplete_unknown_or_empty_dimension_rejected(self):
        cases = [[('Adelie','A')], [('Unknown','U')], [('Adelie','')]]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                checked_species_join(self.con, case)


class ReportTests(unittest.TestCase):
    def test_constructed_failures_are_detected_and_quantified(self):
        r = build_report()
        cases = {c['id']: c for c in r['review_cases']}
        self.assertEqual(len(cases), 5)
        self.assertLess(cases['null-denominator']['candidate_mean_g'], cases['null-denominator']['correct_mean_g'])
        self.assertEqual(cases['join-fanout']['candidate_rows'], 496)
        self.assertEqual(cases['join-fanout']['correct_rows'], 344)
        self.assertEqual(cases['unnecessary-complete-cases']['candidate_n'], 333)
        self.assertEqual(cases['unnecessary-complete-cases']['correct_n'], 342)
        self.assertNotAlmostEqual(cases['causal-overclaim']['pooled_r'], cases['causal-overclaim']['species_centered_r'], places=2)
        self.assertEqual(cases['causal-overclaim']['verdict'], 'not-supported')
        self.assertIn('no model was queried', r['scope'])

    def test_report_is_deterministic(self):
        first, second = build_report(), build_report()
        self.assertEqual(json.dumps(first, sort_keys=True, allow_nan=False), json.dumps(second, sort_keys=True, allow_nan=False))
        self.assertEqual(len(first['sql_sha256']), 6)
        for name, digest in first['sql_sha256'].items():
            self.assertEqual(digest, hashlib.sha256((SQL/name).read_bytes()).hexdigest())

    def test_markdown_includes_scope_and_attribution(self):
        text = render_markdown(build_report())
        self.assertIn('344 observations', text)
        self.assertIn('342 observed masses', text)
        self.assertIn('CC0-1.0', text)
        self.assertIn('not causal or population inference', text)
        self.assertIn('Five authored', text)

    def test_cli_roundtrip_and_refusal_to_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)/'result'
            command = [sys.executable, '-m', 'sql_analysis_audit', '--out', str(out)]
            run = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            first_bytes = (out/'report.json').read_bytes()
            self.assertEqual(json.loads(first_bytes)['profile']['n'], 344)
            again = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertEqual(again.returncode, 2)
            self.assertIn('already exists', again.stderr)
            self.assertEqual((out/'report.json').read_bytes(), first_bytes)

    def test_repeated_cli_outputs_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            outputs=[]
            for name in ('a', 'b'):
                out=Path(d)/name
                subprocess.run([sys.executable,'-m','sql_analysis_audit','--out',str(out)], check=True, capture_output=True, timeout=30)
                outputs.append((out/'report.json').read_bytes())
            self.assertEqual(*outputs)


if __name__ == '__main__':
    unittest.main()
