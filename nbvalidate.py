#!/usr/bin/env python
from __future__ import print_function

import io
import itertools
import json
import os
import sys

from jsonschema import ValidationError

from IPython.nbformat import validate, read, NO_CONVERT
from IPython.nbformat.reader import get_version
from IPython.utils.importstring import import_item

def open_nb(path):
    with io.open(path, encoding='utf-8') as f:
        return read(f, as_version=NO_CONVERT)

def validate_notebook_at(path):
    nb = open_nb(path)
    (version, version_minor) = get_version(nb)
    try:
        validate(nb, version=version, version_minor=version_minor)
    except ValidationError as e:
        return e

def main(paths):
    failed = False
    for path in paths:
        try:
            error = validate_notebook_at(path)
        except Exception as e:
            error = e
            failed = True
            status = 'error'
        else:
            if error:
                failed = True
                status = 'invalid'
            else:
                status = 'ok'
        
        ndots = max(1, 80 - len(path) - len(status))
        
        print('-' * 80)
        print("%s%s%s" % (
            path,
            ' ' * ndots,
            status)
        )
        if error:
            failed = True
            print()
            print(error)
    
    return failed

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
