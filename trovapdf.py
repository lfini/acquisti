"""
Trova file *.pdf contenente la parola data

Uso:

      trovapdf.py  <directory> <parola>
"""

import sys
import os

thedir = sys.argv[1]
word = sys.argv[2]
tree = os.walk(thedir)
for dpath, dnames, fnames in tree:
    for fname in fnames:
        if fname.endswith((".pdf", ".PDF")):
            pdffile = os.path.join(dpath, fname)
            ret = subprocess.run((pdftotext, pdffile, tempfile))
            if ret.returncode == 0:
                 if grep(word, tempfile):
                     print(pdffile)

