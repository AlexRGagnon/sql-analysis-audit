"""Audited SQL over a fixed, attributed real-data snapshot; no network at runtime."""
from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import re
import sqlite3
from typing import Iterable, Sequence

PACKAGE = Path(__file__).resolve().parent
DATA = PACKAGE / 'data' / 'penguins.csv'
SQL = PACKAGE / 'sql'
COLUMNS = ('species', 'island', 'bill_length_mm', 'bill_depth_mm',
           'flipper_length_mm', 'body_mass_g', 'sex', 'year')
SPECIES = frozenset(('Adelie', 'Chinstrap', 'Gentoo'))
ISLANDS = frozenset(('Biscoe', 'Dream', 'Torgersen'))
QUERY_NAMES = ('profile', 'species', 'yearly', 'association', 'weighted_mean')


@dataclass(frozen=True)
class Observation:
    species: str
    island: str
    bill_length_mm: float | None
    bill_depth_mm: float | None
    flipper_length_mm: float | None
    body_mass_g: float | None
    sex: str | None
    year: int


def provenance() -> dict:
    return json.loads((PACKAGE / 'data' / 'provenance.json').read_text(encoding='utf-8'))


def verify_snapshot(path: Path = DATA) -> str:
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if digest != provenance()['sha256']:
        raise ValueError('Dataset SHA-256 differs from the committed provenance manifest')
    return digest


def parse_csv(text: str) -> list[Observation]:
    reader = csv.DictReader(io.StringIO(text, newline=''))
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise ValueError('CSV header must exactly match the eight documented columns')
    result = []
    for line, row in enumerate(reader, start=2):
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f'CSV row {line}: wrong number of columns')
        clean = {k: v.strip() for k, v in row.items()}
        try:
            if clean['species'] not in SPECIES or clean['island'] not in ISLANDS:
                raise ValueError('unknown species or island')
            numbers = {}
            for key in COLUMNS[2:6]:
                raw = clean[key]
                value = None if raw == 'NA' else float(raw)
                if value is not None and (not math.isfinite(value) or value <= 0):
                    raise ValueError(f'{key} must be positive and finite, or NA')
                numbers[key] = value
            sex = None if clean['sex'] == 'NA' else clean['sex']
            if sex not in (None, 'female', 'male'):
                raise ValueError('unknown sex label')
            year_text = clean['year']
            if not re.fullmatch(r'200[789]', year_text):
                raise ValueError('year must be an integer from 2007 through 2009')
            result.append(Observation(clean['species'], clean['island'],
                                      **numbers, sex=sex, year=int(year_text)))
        except (TypeError, ValueError) as exc:
            raise ValueError(f'CSV row {line}: {exc}') from exc
    if not result:
        raise ValueError('CSV must contain at least one observation')
    return result


def load_rows(path: Path = DATA) -> list[Observation]:
    return parse_csv(Path(path).read_text(encoding='utf-8'))


def create_database(rows: Iterable[Observation]) -> sqlite3.Connection:
    if sqlite3.sqlite_version_info < (3, 37, 0):
        raise RuntimeError('SQLite 3.37+ is required for STRICT tables')
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    try:
        con.executescript((SQL / 'schema.sql').read_text(encoding='utf-8'))
        with con:
            con.executemany(
                'INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?)',
                ((i, *asdict(row).values()) for i, row in enumerate(rows, 1)))
        return con
    except Exception:
        con.close()
        raise


def query(con: sqlite3.Connection, name: str) -> list[dict]:
    if name not in QUERY_NAMES:
        raise ValueError(f'Unknown named query: {name!r}')
    statement = (SQL / f'{name}.sql').read_text(encoding='utf-8')
    return [dict(row) for row in con.execute(statement)]


def checked_species_join(con: sqlite3.Connection,
                         metadata: Sequence[tuple[str, str]]) -> list[dict]:
    """Enforce a complete many-to-one dimension, without collapsing fact rows."""
    known = {r[0] for r in con.execute('SELECT DISTINCT species FROM observations')}
    labels = {}
    for species, label in metadata:
        if species in labels:
            raise ValueError('Duplicate species dimension key: ' + species)
        if species not in known or not isinstance(label, str) or not label.strip():
            raise ValueError('Unknown species or empty dimension label')
        labels[species] = label
    if set(labels) != known:
        raise ValueError('Species dimension does not cover all fact-table keys')
    with con:
        con.execute('CREATE TEMP TABLE IF NOT EXISTS species_metadata '
                    '(species TEXT PRIMARY KEY, label TEXT NOT NULL) STRICT')
        con.execute('DELETE FROM species_metadata')
        con.executemany('INSERT INTO species_metadata VALUES (?,?)', labels.items())
    joined = [dict(r) for r in con.execute(
        'SELECT o.observation_id, o.species, m.label FROM observations o '
        'JOIN species_metadata m ON o.species=m.species ORDER BY o.observation_id')]
    expected = con.execute('SELECT COUNT(*) FROM observations').fetchone()[0]
    if len(joined) != expected or len({r['observation_id'] for r in joined}) != expected:
        raise RuntimeError('Join cardinality invariant failed')
    return joined


def describe_association(rows: list[dict]) -> list[dict]:
    result = []
    for row in rows:
        row = dict(row)
        denominator = math.sqrt(row['ss_x'] * row['ss_y']) if row['ss_x'] and row['ss_y'] else 0.0
        row['pearson_r'] = row['cross_product'] / denominator if denominator else None
        row['slope_g_per_mm'] = row['cross_product'] / row['ss_x'] if row['ss_x'] else None
        result.append(row)
    return result


def build_report(path: Path = DATA) -> dict:
    digest = verify_snapshot(path)
    rows = load_rows(path)
    con = create_database(rows)
    try:
        profile = query(con, 'profile')[0]
        by_species = query(con, 'species')
        weighted = query(con, 'weighted_mean')[0]
        association = describe_association(query(con, 'association'))
        bad_denominator = con.execute(
            'SELECT 1.0*SUM(body_mass_g)/COUNT(*) FROM observations').fetchone()[0]
        complete = con.execute('SELECT COUNT(*) n, AVG(body_mass_g) mean_g FROM observations '
            'WHERE bill_length_mm IS NOT NULL AND bill_depth_mm IS NOT NULL '
            'AND flipper_length_mm IS NOT NULL AND body_mass_g IS NOT NULL '
            'AND sex IS NOT NULL').fetchone()
        # Deliberate review fixture; these tags are NOT part of the source dataset.
        tags = [('Adelie', 'field'), ('Adelie', 'reviewed'),
                ('Chinstrap', 'field'), ('Gentoo', 'field')]
        con.execute('CREATE TEMP TABLE illustrative_tags(species TEXT, label TEXT)')
        con.executemany('INSERT INTO illustrative_tags VALUES (?,?)', tags)
        fanout = con.execute('SELECT COUNT(*) FROM observations o '
                            'JOIN illustrative_tags d ON o.species=d.species').fetchone()[0]
        try:
            checked_species_join(con, tags)
        except ValueError as exc:
            guard_message = str(exc)
        else:
            raise RuntimeError('Duplicate dimension fixture escaped validation')
        joined = checked_species_join(con, [(s, s + ' label') for s in sorted(SPECIES)])
        cases = [
            {'id': 'null-denominator', 'verdict': 'reject',
             'claim': 'SUM(body_mass_g) / COUNT(*) is the observed-mass mean.',
             'candidate_mean_g': bad_denominator, 'correct_mean_g': profile['mean_mass_g'],
             'explanation': 'COUNT(*) includes missing masses while SUM ignores them. Use AVG(body_mass_g), or divide by COUNT(body_mass_g). The estimand is the mean among measured masses, not an imputed population mean.'},
            {'id': 'unweighted-subgroup-means', 'verdict': 'reject',
             'claim': 'The equally weighted mean of species means is the pooled observation mean.',
             'candidate_mean_g': weighted['equal_species_mean_g'],
             'correct_mean_g': weighted['correct_pooled_mean_g'],
             'explanation': 'Equal-species weighting answers a different question. Recover the observation-weighted mean using each species nonmissing mass count, not its total row count.'},
            {'id': 'join-fanout', 'verdict': 'reject',
             'claim': 'Joining species tags preserves the number of observations.',
             'candidate_rows': fanout, 'correct_rows': len(joined),
             'guard_message': guard_message,
             'explanation': 'A deliberately duplicated dimension key replicates Adelie observations. Reject duplicate keys before joining. DISTINCT is not a general repair because distinct real observations can share measurements.'},
            {'id': 'unnecessary-complete-cases', 'verdict': 'reject-for-stated-estimand',
             'claim': 'Estimating the observed-mass mean requires every unrelated field to be present.',
             'candidate_n': complete['n'], 'correct_n': profile['mass_observed'],
             'candidate_mean_g': complete['mean_g'], 'correct_mean_g': profile['mean_mass_g'],
             'explanation': 'Filtering on sex and bill measurements discards additional usable masses. Complete-case analysis can be appropriate for a specified multivariable model, but it changes the sample here; missingness may be informative.'},
            {'id': 'causal-overclaim', 'verdict': 'not-supported',
             'claim': 'The pooled mass/flipper association establishes a causal effect applicable to each species.',
             'pooled_r': association[0]['pearson_r'],
             'species_centered_r': association[1]['pearson_r'],
             'explanation': 'Pooled and within-species centered associations answer different descriptive questions. Neither identifies causation. Species adjustment alone does not resolve sex, year, sampling, or other confounding.'}
        ]
        return {'format_version': 1, 'data': {**provenance(), 'verified_sha256': digest,
                    'observations': len(rows)},
                'runtime': {'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version},
                'sql_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(SQL.glob('*.sql'))},
                'profile': profile, 'species': by_species, 'yearly': query(con, 'yearly'),
                'weighted_means': weighted, 'association': association,
                'join_audit': {'fact_rows': len(rows), 'joined_rows': len(joined),
                               'unique_observation_ids': len({r['observation_id'] for r in joined})},
                'review_cases': cases,
                'scope': 'Five authored flawed-analysis fixtures; no model was queried and no employer assessment was used. Descriptive analysis of a fixed historical sample, not causal or population inference.'}
    finally:
        con.close()


def render_markdown(report: dict) -> str:
    p = report['profile']
    lines = ['# SQL analysis audit: measured results', '',
             f"Dataset: {p['n']} observations; {p['mass_observed']} observed masses; "
             f"{p['mass_missing']} missing masses; {p['complete_cases']} complete cases.", '',
             f"Observed-mass mean: **{p['mean_mass_g']:.6f} g**.", '',
             '| Species | Rows | Measured masses | Mean mass (g) |',
             '|---|---:|---:|---:|']
    for s in report['species']:
        lines.append(f"| {s['species']} | {s['n']} | {s['mass_observed']} | {s['mean_mass_g']:.6f} |")
    lines.extend(['', '## Review cases', ''])
    for case in report['review_cases']:
        lines.extend([f"### {case['id']}: {case['verdict']}", '',
                      'Constructed claim: ' + case['claim'], '', case['explanation'], ''])
    lines.extend(['## Interpretation boundaries', '', report['scope'], '',
        'Row IDs are source-file ordinals, not original animal identifiers. Yearly changes compare samples, not within-animal growth. No p-values, confidence intervals, predictive accuracy, or population-generalization claims are attached to these descriptive results.', '',
        'Data: Horst, Hill & Gorman (2020), palmerpenguins, CC0-1.0; original study Gorman et al. (2014), doi:10.1371/journal.pone.0090081.', '',
        'The JSON report retains source provenance, SQL hashes, all case measurements, and runtime versions.', ''])
    return '\n'.join(lines)
