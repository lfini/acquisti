"""
Rinomina i files allegati secondo nuovo schema
"""
import sys
import os
import re

import ftools as ft
from constants import *

DATADIR = ft.datapath()
ALL_MATCH = re.compile("[AB]\\d\\d_")
DOIT = False

if '-f' in sys.argv:
    DOIT = True

TREE = os.walk(DATADIR)
for dp, dnames, fnames in TREE:
    for fn in fnames:
        if ALL_MATCH.match(fn):
            continue
        if fn in (DETA_PDF_FILE, DETB_PDF_FILE, ORD_PDF_FILE, RIC_PDF_FILE):
            continue
        name, ext = os.path.splitext(fn)
        if ext in UPLOAD_TYPES:
            fpath = os.path.join(dp, fn)
            if name == "CapitolatoRDO":
                newname = "A07_Capitolato_RDO"
            elif name == "Dichiarazione_Imposta_bollo":
                newname = "A06_Dichiarazione_Imposta_bollo"
            elif name == "Lettera_Invito":
                newname = "A06_Lettera_Invito"
            elif name == "Lettera_Invito_MEPA":
                newname = "A06_Lettera_Invito_MEPA"
            elif name == "Lista_dettagliata_per_ordine":
                newname = "A40_Lista_dettagliata_per_ordine"
            elif name == "Offerta_Ditta":
                newname = "A10_Offerta_ditta"
            elif name == "Bozza_Ordine_MePA":
                newname = "A10_Bozza_Ordine_MEPA"
            else:
                newname = "A99_"+name
            if DOIT:
                newpath = os.path.join(dp, newname+ext)
                os.rename(fpath, newpath)
                print("renamed", name, newname)
            else:
                print(name, "-->", newname)
