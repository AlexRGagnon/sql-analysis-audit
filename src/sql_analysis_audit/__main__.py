"""CLI: verified offline analysis, refusing to replace an existing output directory."""
import argparse
import json
from pathlib import Path
import sys
from .audit import build_report, render_markdown


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='New output directory')
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise FileExistsError('Output directory already exists; choose a new path')
        report = build_report()
        payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n'
        markdown = render_markdown(report)
        args.out.mkdir(parents=True, exist_ok=False)
        (args.out / 'report.json').write_text(payload, encoding='utf-8', newline='\n')
        (args.out / 'report.md').write_text(markdown, encoding='utf-8', newline='\n')
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2
    print(f"Verified {report['profile']['n']} observations; wrote report.json and report.md")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
