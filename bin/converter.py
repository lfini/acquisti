"""
Conversione ID utenti per passaggio ad email INAF

Uso:
    python convertid vecchio nuovo

"""

import sys
import os
import json

DEBUG = False
TEST = True

TO_CONVERT = ("config.json", "codf.json", "userlist.json")

if TEST:
    DATADIR = "/home/lfini/py/acquisti/data"
else:
    DATADIR = "/home/public/acquisti/data"

if sys.version_info.major != 3:
    print()
    print("E' richiesto python 3!!")
    print()
    sys.exit()


class Converter:
    "Conversione di un singolo file"
    def __init__(self, fpath, old, new):
        self.fpath = fpath
        self.oldem = old
        self.newem = new
        self.oldid = old.split("@")[0]
        self.newid = new.split("@")[0]
        with open(self.fpath) as inp:
            self.obj = json.load(inp)
        self.converted = False
        self.newobj = self._convert(self.obj)

    def _convert_dict(self, adict):
        "Conversione dictionary"
        newdict = {}
        for key, value in adict.items():
            newkey = self._convert(key)
            newval = self._convert(value)
            newdict[newkey] = newval
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
        if self.oldem == value:
            self.converted = True
            return self.newem
        elif self.oldid == value:
            self.converted = True
            return self.newid
        return value

    def write(self):
        "Scrive oggetto convertito nel file"
        if self.converted:
            if not DEBUG:
                with open(self.fpath, "w") as out:
                    json.dump(self.newobj, out, indent=2)
            print("Convertito file:", self.fpath)

def do_gen_files(old, new):
    "Converti campi nei files generali"
    for fname in TO_CONVERT:
        fpath = os.path.join(DATADIR, fname)
        dconv = Converter(fpath, old, new)
        dconv.write()

def do_pratiche(old, new):
    "Converti campi nei files pratiche"
    tree = os.walk(DATADIR)
    for root, _unused, fnames in tree:
        for fname in fnames:
            if fname == "pratica.json":
                fpath = os.path.join(root, fname)
                dconv = Converter(fpath, old, new)
                dconv.write()

def main():
    "programma principale"
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit()
    do_gen_files(sys.argv[1], sys.argv[2])
    do_pratiche(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()
