#!/usr/bin/env python
"""
Strip notebook prompts

For use as a git pre-commit hook

Usage: `stripnbprompts.py foo.ipynb > stripped.ipynb`

"""

import os
import sys
import time

from IPython.nbformat.current import reads, writes

def strip_prompts(nb):
    """reorder the cells in this notebook
    
    order is based on the cell execution order
    
    non-code cells are associated with the first subsequent code cell as a chunk of cells
    """
    for cell in nb.worksheets[0].cells:
        if 'prompt_number' in cell:
            print >> sys.stderr, "stripping In [%s]" % cell.prompt_number
            cell.prompt_number = None

if __name__ == '__main__':
    for ipynb in sys.argv[1:]:
        print >> sys.stderr, "stripping prompts from %s" % ipynb
        with open(ipynb) as f:
            nb = reads(f.read(), 'json')
        strip_prompts(nb)
        print writes(nb, 'json')
        
