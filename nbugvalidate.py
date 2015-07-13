#!/usr/bin/env python
from __future__ import print_function

import io
import itertools
import json
import os
import sys

from jsonschema import ValidationError

from IPython.nbformat import current
from IPython.nbformat.v4 import upgrade
from IPython.utils.importstring import import_item

def open_nb(path, version):
    reads_json = import_item("IPython.nbformat.v%s.reads_json" % version)
    with io.open(path, encoding='utf-8') as f:
        return reads_json(f.read())

def get_version(path):
    with io.open(path, 'r', encoding='utf-8') as f:
        nbjson = json.load(f)
    
    return nbjson['nbformat']
    

def validate_notebook_at(path, version=None):
    if version is None:
        version = get_version(path)
    
    nb = open_nb(path, version)
    nb2 = upgrade(nb)
    try:
        current.validate(nb2, version=4)
    except ValidationError as e:
        return e

# def better_validation_error(error, version):
#     version = 4
#     key = error.schema_path[-1]
#     if key.endswith('Of'):
#         # oneOf errors aren't informative.
#         # if it's a cell type or output_type error,
#         # try validating directly for a better error message
#
#         ref = None
#         if 'cell_type' in error.instance:
#             ref = error.instance['cell_type'] + "_cell"
#         elif 'output_type' in error.instance:
#             ref = error.instance['output_type']
#
#         if ref:
#             try:
#                 current.validate(error.instance,
#                     ref,
#                     version=version
#                 )
#             except ValidationError as e:
#                 return better_validation_error(e, version)
#             except:
#                 # if it fails for some reason,
#                 # let the original error through
#                 pass
#
#     return error

def main(paths):
    failed = False
    for path in paths:
        try:
            version = get_version(path)
        except (IOError, ValueError) as e:
            error = e
            failed = True
            status = 'error'
        else:
            try:
                error = validate_notebook_at(path, version)
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
            if status == 'invalid':
                error = better_validation_error(error, version)
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
