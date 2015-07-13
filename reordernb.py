#!/usr/bin/env python
"""
Simple example script for reordering notebook cells based on their prompt number.

This is mostly a toy for @ivanov

Usage: `reordernb.py foo.ipynb [bar.ipynb [...]]`

Cells without a prompt number (e.g. markdown, header, unexecuted code cells)
are associated with the first subsequent code cell that *has* been executed.

So the notebook:

# header

# markdown

# In [2]: foo

# markdown 2

In [1]: bar

# markdown 3

will be reordered as:

# markdown 2

In [1]: bar

# header

# markdown

# In [2]: foo

# markdown 3

"""

import os
import sys
import time

from IPython.nbformat.current import reads, writes

def get_prompt(cell):
    """unused case for the key"""
    if cell.cell_type != 'code':
        return 0
    else:
        return getattr(cell, 'prompt_number', 999)

def cmp_cells(a, b):
    """compares two cell prompt numbers
    
    If both cells do not have a prompt,
    they are assumed to be equal.
    """
    if (
        a.cell_type != 'code' or \
        b.cell_type != 'code' or \
        a.get('prompt_number', None) is None or \
        b.get('prompt_number', None) is None
        ):
        return 0
    return cmp(a.prompt_number, b.prompt_number)

def cmp_chunks(a, b):
    """compare *chunks* of cells,
    
    assumes only the last cell of the chunk has prompt info."""
    return cmp_cells(a[-1], b[-1])


def chunk_cells(cells):
    """chunk cells, such that all non-code cells *leading up to a code cell*
    are associated with that code cell.
    
    returns list of lists of cells, which should be ordered together.
    The last cell of each chunk is the ordered code cell
    (or not, as may be the case of the last chunk).
    This last cell should be used for ordering the chunks
    """
    chunks = []
    chunk = []
    for cell in cells:
        chunk.append(cell)
        prompt = cell.get('prompt_number', None)
        if prompt is not None:
            chunks.append(chunk)
            chunk = []
    if chunk:
        chunks.append(chunk)
    return chunks

def reorder_notebook(nb):
    """reorder the cells in this notebook
    
    order is based on the cell execution order
    
    non-code cells are associated with the first subsequent code cell as a chunk of cells
    """
    new_cells = []
    cells = nb.worksheets[0].cells
    chunks = chunk_cells(cells)
    chunks = sorted(chunks, cmp=cmp_chunks)
    # crazy flattening double list comprehension
    new_cells = [ cell for chunk in chunks for cell in chunk ]
    nb.worksheets[0].cells = new_cells

if __name__ == '__main__':
    for ipynb in sys.argv[1:]:
        print >> sys.stderr, "reordering %s" % ipynb
        with open(ipynb) as f:
            nb = reads(f.read(), 'json')
        reorder_notebook(nb)
        print writes(nb, 'json')
        