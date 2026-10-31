"""Compare executed notebook content while excluding execution timing metadata."""
import argparse
import json
from pathlib import Path


def normalized(path: Path):
    notebook=json.loads(path.read_text(encoding='utf-8'))
    result=[]
    for cell in notebook['cells']:
        if cell['cell_type'] != 'code':
            continue
        if cell.get('execution_count') is None:
            raise ValueError(f'Unexecuted code cell in {path.name}')
        outputs=cell.get('outputs', [])
        if any(output.get('output_type')=='error' for output in outputs):
            raise ValueError(f'Error output in {path.name}')
        result.append({'source':cell['source'], 'outputs':outputs})
    if not result:
        raise ValueError('No code cells found')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first',type=Path)
    parser.add_argument('second',type=Path)
    args=parser.parse_args()
    first, second=normalized(args.first), normalized(args.second)
    if first != second:
        raise SystemExit('Executed notebook sources or outputs differ')
    print(f'Identical executed sources and outputs across {len(first)} code cells')


if __name__=='__main__':
    main()
