#!/usr/bin/env python
from __future__ import print_function

import io
import itertools
import json
import os
import sys

from jsonschema import ValidationError

from IPython import nbformat
from IPython.utils.importstring import import_item


def main(paths):
    failed = False
    for path in paths:
        with io.open(path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, 4)
        try:
            nbformat.validate(nb)
        except ValidationError as e:
            print(path, 'failed')
            print(e)
        else:
            print(path)
            with io.open(path, 'w', encoding='utf-8') as f:
                nbformat.write(nb, f)

def find_notebooks(path):
    for d, _, files in os.walk(path):
        for f in files:
            if f.endswith('.ipynb'):
                yield os.path.join(d, f)

if __name__ == '__main__':
    paths = []
    for path in sys.argv[1:]:
        path = os.path.expanduser(path)
        if os.path.isdir(path):
            next_paths = find_notebooks(path)
        else:
            next_paths = [path]
        paths = itertools.chain(paths, next_paths)
    sys.exit(main(paths))
