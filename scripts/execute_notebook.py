"""Execute the authored notebook in a fresh local kernel, using this interpreter."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

import nbformat
from nbclient import NotebookClient


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    output=args.output.resolve()
    if output.exists():
        parser.error('Output already exists; choose a new file')
    root=Path(__file__).resolve().parents[1]
    nb=nbformat.read(root/'notebooks/analysis.ipynb', as_version=4)
    nbformat.validate(nb)
    for cell in nb.cells:
        if cell.cell_type == 'code':
            cell.outputs=[]
            cell.execution_count=None
            cell.metadata.pop('execution', None)
    old_path=os.environ.get('JUPYTER_PATH')
    try:
        with tempfile.TemporaryDirectory(prefix='sql-audit-kernel-') as temp:
            directory=Path(temp)/'kernels'/'sql-audit-local'
            directory.mkdir(parents=True)
            spec={'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
                  'display_name':'SQL Audit local interpreter','language':'python'}
            (directory/'kernel.json').write_text(json.dumps(spec), encoding='utf-8')
            os.environ['JUPYTER_PATH']=temp + (os.pathsep+old_path if old_path else '')
            client=NotebookClient(nb, timeout=60, kernel_name='sql-audit-local',
                                  allow_errors=False, resources={'metadata':{'path':str(root)}})
            def require_loopback(notebook):
                if client.km.ip not in ('127.0.0.1', '::1'):
                    raise RuntimeError('Refusing a non-loopback notebook kernel')
            client.on_notebook_start = require_loopback
            client.execute()
    finally:
        if old_path is None:
            os.environ.pop('JUPYTER_PATH', None)
        else:
            os.environ['JUPYTER_PATH']=old_path
    code=[c for c in nb.cells if c.cell_type=='code']
    if not code or any(c.execution_count is None for c in code):
        raise RuntimeError('Notebook did not execute every code cell')
    if any(o.output_type=='error' for c in code for o in c.outputs):
        raise RuntimeError('Notebook includes error outputs')
    nbformat.validate(nb)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='\n') as handle:
        nbformat.write(nb, handle)
    print(json.dumps({'executed_code_cells':len(code), 'error_outputs':0}))


if __name__=='__main__':
    main()
