#!/usr/bin/env python
import sys

from IPython.nbformat import read, write

def order_prompts(fname):
    print(fname)
    nb = read(fname, 4)
    counter = 1
    for cell in nb.cells:
        if cell.cell_type != 'code':
            continue
        if cell.get('execution_count'):
            cell.execution_count = counter
            for output in cell.outputs:
                if output.output_type == 'execute_result':
                    output.execution_count = counter
            counter += 1
    # remove trailing empty cell
    while nb.cells and not nb.cells[-1].source:
        nb.cells.pop(-1)
    
    write(nb, fname, 4)

if __name__ == '__main__':
    for fname in sys.argv[1:]:
        order_prompts(fname)

