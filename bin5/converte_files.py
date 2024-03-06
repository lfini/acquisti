"""
Converte i file di pratiche per passaggio a nomi INAF

L.Fini - Novembre 2020
"""

import os
import json
import pickle

TEST = True
DEBUG = False

TO_CONVERT = ("config.json", "codf.json")

if TEST:
    DATADIR = "/home/lfini/py/acquisti/data"
else:
    DATADIR = "/home/public/acquisti/data"

ALLCHARS = "abcdefghijklmnopqrstuvwxyz"
TOREMOVE = "' "

TTABLE = "".maketrans(ALLCHARS, ALLCHARS, TOREMOVE)

INAF_EMAIL = "@inaf.it"

class FileConverter:
    "Conversione di un singolo file"
    def __init__(self, fpath, useridtable, emailtable):
        self.fpath = fpath
        self.useridt = useridtable
        self.emailt = emailtable
        with open(self.fpath) as inp:
            self.obj = json.load(inp)
        self.newobj = self._convert(self.obj)

    def _convert_dict(self, adict):
        "Conversione dictionary"
        newdict = {}
        for key, value in adict.items():
            newval = self._convert(value)
            newdict[key] = newval
        return newdict

    def _convert_list(self, alist):
        "Conversione list"
        newlist = []
        for value in alist:
            newlist.append(self._convert(value))
        return newlist

    def _convert(self, value):
        "Conversione oggetto generico"
        if isinstance(value, dict):
            return self._convert_dict(value)
        if isinstance(value, list):
            return self._convert_list(value)
        if value in self.useridt:
            print("Converting userid:", value, "->", self.useridt[value])
            value = self.useridt[value]
        elif value in self.emailt:
            print("Converting email:", value, "->", self.emailt[value])
            value = self.emailt[value]
        return value

    def write(self):
        "Scrive oggetto convertito nel file"
        if DEBUG:
            print("DEBUG: non convertito file:", self.fpath)
        else:
            with open(self.fpath, "w") as out:
                json.dump(self.newobj, out, indent=2)
            print("Convertito file:", self.fpath)

tab_file = "convert_data.pkl"
with open(tab_file, "rb") as inp:
    data = pickle.load(inp)

userid_table = data["userid_table"]
email_table = data["email_table"]

print("Conversione file config e codf")
for fname in TO_CONVERT:
    fpath = os.path.join(DATADIR, fname)
    dconv = FileConverter(fpath, userid_table, email_table)
    dconv.write()

print("Conversione file pratiche")
tree = os.walk(os.path.join(DATADIR, "2020"))
for root, _unused, fnames in tree:
    for fname in fnames:
        if fname == "pratica.json":
            fpath = os.path.join(root, fname)
            dconv = FileConverter(fpath, userid_table, email_table)
            dconv.write()
