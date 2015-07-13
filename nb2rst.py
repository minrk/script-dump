"""starting point for IPython Notebook to Restructured Text

using pandoc in various places
"""

import os,sys,shutil
import glob
import tempfile
import base64

from binascii import hexlify
from hashlib import md5

from IPython.nbformat import current
from IPython.utils.process import find_cmd, getoutput

def pandocify(src, lang):
    """use pandoc to convert various things to rst"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(src)
        fname = f.name
    
    pandoc = find_cmd('pandoc')
    cmd = "%s -r %s -w rst '%s'" % (pandoc, lang, fname)
    try:
        rst = getoutput(cmd)
        return rst
    finally:
        os.unlink(fname)

md2rst = lambda s: pandocify(s, 'markdown')
latex2rst = lambda s: pandocify(s, 'latex')
html2rst = lambda s: pandocify(s, 'html')

def input2rst(code):
    lines = [".. sourcecode:: python", '']
    for line in code.splitlines():
        lines.append(' '*4 + line)
    lines.append('')
    return '\n'.join(lines)

def stream2rst(text):
    lines = ['::', '']
    for line in text.splitlines():
        lines.append(' '*4 + line)
    
    lines.append('')
    return '\n'.join(lines)

# these are identical:
txt2rst = stream2rst

def image2rst(data, ext):
    name = 'image_%s.%s' % (md5(data).hexdigest()[:7], ext)
    mode = 'wb'
    with open(name, mode) as f:
        f.write(data)
    
    return ".. image:: %s" % name
    
def png2rst(png):
    bdata = base64.decodestring(png)
    return image2rst(bdata, 'png')

def svg2rst(svg):
    return image2rst(svg.encode('utf8'), 'svg')

def codecell2rst(cell):
    blobs = [input2rst(cell.input)]
    
    streams = []
    outblobs = []
    for output in cell.outputs:
        if output.output_type == 'stream':
            streams.append(output.text)
        else:
            if 'png' in output:
                outblobs.append(png2rst(output.png))
            elif 'svg' in output:
                outblobs.append(svg2rst(output.svg))
            elif 'latex' in output:
                outblobs.append(latex2rst(output.latex))
            elif 'html' in output:
                outblobs.append(html2rst(output.html))
            elif 'text' in output and output.text:
                outblobs.append(txt2rst(output.text))
    if streams:
        blobs.append(stream2rst(''.join(streams)))
    
    blobs.extend(outblobs)
    return '\n'.join(blobs)

def nb2rst(nb):
    name = nb.metadata.get('name', 'IPython Notebook')
    header = '\n'.join(['='*len(name), name, '='*len(name)])
    blobs = [header]
    for ws in nb.worksheets:
        for cell in ws.cells:
            cell_type = cell.cell_type
            if cell_type == 'markdown':
                blobs.append(md2rst(cell.source))
            elif cell_type == 'code':
                blobs.append(codecell2rst(cell))
            else:
                print "warning: unhandled cell type: ", cell_type
    return '\n\n'.join(blobs)
    

if __name__ == '__main__':
    fname = sys.argv[1]
    with open(fname) as f:
        nb = current.read(f, 'json')
    s = nb2rst(nb)
    with open(fname.replace('.ipynb', '.rst'), 'w') as f:
        f.write(s)
    