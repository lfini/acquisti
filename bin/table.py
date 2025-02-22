# -*- coding: utf-8 -*-
"""
table.py        - gestione tabella

Uso per test:

     python table.py [-f] [-h]
     python table.py file1 file2 

dove:

     -h:     mostra pagina di aiuto
     .f:     esegui test generico completo

se lanciata con due argomenti, confronta ed aggiuorna due tabelle
"""
# VERSION 2.0       4/1/2018    Versione python 3

import json

import sys
import os
import csv
import uuid
import errno
import time
import base64
import random

__author__ = 'Luca Fini'
__version__ = '2.2'
__date__ = '05/10/2024'

class TableException(Exception):
    "Exception raised by this module"

class LockException(Exception):
    "Exception when file is locked"
    def __init__(self, filename, owner):
        Exception.__init__(self, f"File {filename} locked by: {owner}")

class CsvFile:
    "CSV file management class"
    def __init__(self):
        self._csvdata = ''

    def write(self, line):
        "Add a line"
        self._csvdata += str(line)

    def data(self):
        "Return content"
        return self._csvdata

def getpath(path):
    "Build a file path from components"
    if isinstance(path, str):
        return path
    return os.path.join(*path)

def _clean(item):
    if isinstance(item, str):
        return item.strip()
    return item

#pylint: disable=C3001
class Table:                             # pylint: disable=R0902
    """
Table class:
   table.header: array of column names
   table.rows:   array of rows.
   table.opts:   options (currently unused)

   Constructor:
      t = Table(path, header=[], csvfile='', lock='')

      path = ('rel', 'path', ...)
      header = ['field1', field2, ...] used for creation, the _IND_
             field (main key, numerical) is prepended.
      csv  if specified the table is initialized from a CSV file
      lock if not empty, the table file is lock opened with given info"""

    def __init__(self, path, header=None, csvfile='', lock=''):
        self.filename = getpath(path)
        if csvfile:
            self.rows = []
            self.opts = []
            self._maxpos = 0
            self._fromcsv(csvfile)
        else:
            if lock:
                self.lkinfo = _getlock(self.filename, lock)
                try:
                    jdata = _jload(path, nofile={})
                except TableException:
                    _junlock(self.filename)
                    raise
            else:
                jdata = jload(self.filename, nofile={})
                self.lkinfo = None
            if jdata:
                self.header = jdata['header']
                self.rows = jdata['rows']
                self.opts = jdata['opts']
            else:
                if header:
                    self.header = ['_IND_'] + list(header)
                else:
                    raise TableException('A table header must be specified')
                self.rows = []
                self.opts = []
            self.ncols = len(self.header)
            try:
                self._maxpos = max(self.rows, key=lambda x: x[0])[0]
            except:                       # pylint: disable=W0702
                self._maxpos = 0
            self.readtime = time.time()

    def __len__(self):
        return len(self.rows)

    def __iter__(self):
        "Returns an iterator on table elements"
        idx = 0
        while idx < len(self.rows):
            ret = self.rows[idx]
            idx += 1
            yield ret

    def _fromcsv(self, csvfile):
        "Import table data from CSV file"
        with open(csvfile, encoding='utf8') as filed:
            reader = csv.DictReader(filed)
            self.header = ['_IND_'] + reader.fieldnames
            self.ncols = len(self.header)
            for row in reader:
                self.insert_row(row)

    def _index(self, pos):
        "Return row index of row with main key pos"
        try:
            index = [x[0] for x in self.rows].index(pos)
        except:                       # pylint: disable=W0702
            index = -1
        return index

    def _field(self, field):
        "Return a valid field index (or -1)"
        if isinstance(field, str):
            try:
                return self.header.index(field)
            except:                       # pylint: disable=W0702
                return -1
        try:
            indx = int(field)
        except:                       # pylint: disable=W0702
            return -1
        if indx < 0 or indx >= len(self.header):
            return -1
        return indx

    def _insert_list(self, row, pos):
        if len(row) != len(self.header)-1:
            raise TableException('Table row format mismatch')
        clrow = [_clean(r) for r in row]
        indx = self._index(pos)
        if indx >= 0:
            self.rows[indx][1:] = clrow
        else:
            if pos <= 0:
                self._maxpos += 1
                pos = self._maxpos
            self.rows.append([pos]+ clrow)
        return pos

    def _insert_dict(self, row, pos):
        if pos == 0:
            if self.header[0] in row:
                pos = row[self.header[0]]
        try:
            srow = [row[k] for k in self.header[1:]]
        except Exception as excp:
            raise TableException(f'Table row format mismatch [{str(excp)}]') from None
        return self._insert_list(srow, pos)

    def has_duplicates(self):
        "Check that row indexes are not duplicated"
        rowix = [x[0] for x in self.rows]
        setrx = set(rowix)
        return len(setrx) < len(rowix)

    def convert(self, field, func=lambda x: x):
        "Convert a full row applying the given func"
        rix = self._field(field)
        for row in self.rows:
            try:
                row[rix] = func(row[rix])
            except:
                raise TableException(f'Cannot convert row: {row[0]}') from None

    def needs_update(self):
        "Returns true if file has been written since it has been read"
        try:
            ftime = os.stat(self.filename).st_mtime
        except:                       # pylint: disable=W0702
            ftime = 0
        return self.readtime < ftime

    def renumber(self):
        "Renumber rows to have sequentail index (starting from 1)"
        indx = 1
        for row in self.rows:
            row[0] = indx
            indx += 1

    def sort(self, field):
        "Sort table on given field"
        indx = self._field(field)
        if indx >= 0:
            self.rows.sort(key=lambda x: x[indx])

    def column(self, field, unique=False, select=None):
        "Return column of given index or name"
        indx = self._field(field)
        if indx < 0:
            return []
        if select:
            srows = [row for row in self.rows if select(row)]
        else:
            srows = self.rows
        ret = [x[indx] for x in srows]
        if unique:
            setr = set(ret)
            ret = list(setr)
            ret.sort()
        return ret

    def columns(self, fields=(), as_dict=False):
        "Returns rows from table containing only given column fields"
        def select(ffs, row):
            "Column extract function"
            return [row[x] for x in ffs]

        if not fields:
            srow = self.rows
        else:
            ixs = [self._field(x) for x in fields]
            ixs = [x for x in ixs if x >= 0]

            if ixs:
                srow = [select(ixs, x) for x in self.rows]

                if as_dict:
                    srow = [dict(list(zip(self.header, x))) for x in srow]
            else:
                if as_dict:
                    srow = {}
                else:
                    srow = []
        return srow

    def as_csv(self, index=False):
        "return table content as CSV data"

        def _noindex(row):
            return row[1:]

        def _ident(row):
            return row

        if index:
            adj = _ident
        else:
            adj = _noindex
        filed = CsvFile()
        wrow = csv.writer(filed, dialect='excel')
        wrow.writerow(adj(self.header))
        for row in self.rows:
            wrow.writerow(adj(row))
        return filed.data()

    def empty(self):
        "Test if table is empty"
        return len(self.rows) == 0

    def insert_row(self, row, pos=0):
        "Insert row at given pos (or new row if pos=0). Row may be list or dictionary"
        if isinstance(row, list):
            self._insert_list(row, pos)
        elif isinstance(row, dict):
            self._insert_dict(row, pos)
        else:
            raise TableException(f"Illegal type for row ({row})")

    def get_row(self, npos, as_dict=False, index=False, default=None):
        "Return row with index npos"
        srow = [x for x in self.rows if x[0] == npos]
        if not srow:
            if default is None:
                return None
            srow = [default for x in self.header]
        else:
            srow = srow[0]
        if index:
            header = self.header
        else:
            header = self.header[1:]
            srow = srow[1:]
        if as_dict:
            ret = dict(list(zip(header, srow)))
        else:
            ret = srow
        return ret

    def add_column(self, pos, label, value='', column=None):
        "Add a column to a table"
        if label in self.header:
            raise TableException('Duplicate column label: '+label)
        if pos < 1 or pos > len(self.header):
            raise TableException(f'Illegal column index: {pos} [len(header):{len(self.header)}]')
        self.header.insert(pos, label)
        colid = 0
        for row in self.rows:
            try:
                toinsert = column[colid]
            except:                       # pylint: disable=W0702
                toinsert = value
            row.insert(pos, toinsert)
            colid += 1

    def remove_column(self, field):
        "Remove a column"
        indx = self._field(field)
        if indx < 1 or indx >= len(self.header):
            raise TableException(f'Illegal column index: {indx}')
        del self.header[indx]
        for row in self.rows:
            del row[indx]

    def where(self, field, item, as_dict=False, index=False, comp=None):   # pylint: disable=R0913
        "Returns rows with matching field"
        indx = self._field(field)
        if indx < 0:
            return []
        if comp is None:
            if isinstance(item, str):
                match = lambda x: x[indx].strip() == item.strip()
            else:
                match = lambda x: x[indx] == item
        else:
            match = comp
        srow = [x for x in self.rows if match(x)]
        if srow:
            if index:
                header = self.header
            else:
                srow = [x[1:] for x in srow]
                header = self.header[1:]
            if as_dict:
                srow = [dict(list(zip(header, x))) for x in srow]
        return srow

    def as_dict(self, key_field, index=False):
        "Returns the full table as a dictionary, using given field as key"
        indx = self._field(key_field)
        if indx < 0:
            return {}
        if index:
            ret = {x[indx]: x for x in self.rows}
        else:
            ret = {x[indx]: x[1:] for x in self.rows}
        return ret

    def delete_row(self, row):
        "Cancella riga da tabella"
        ret = False
        idx = self._index(row)
        if idx >= 0:
            del self.rows[idx]
            ret = True
        return ret

    def unlock(self, force=False):
        "Unlock file tabella"
        lkinfo = _islocked(self.filename)
        if force or not lkinfo:
            _junlock(self.filename)
        else:
            if self.lkinfo:
                if self.lkinfo[0] != lkinfo[0]:
                    raise LockException(self.filename, lkinfo[2])
                _junlock(self.filename)

    def save(self, fname=""):
        "Salva tabella in file json"
        jdata = {'header': self.header, 'rows': self.rows, 'opts':self.opts}
        if not fname:
            fname = self.filename
        jsave(fname, jdata, lockinfo=self.lkinfo)

def _junlock(path):
    name = getpath(path)
    lockname = name+'.lock'
    try:
        os.unlink(lockname)
    except:                       # pylint: disable=W0702
        pass
    return name

def _islocked(name):
    "Returns lock info if file is locked"
    lockname = name+'.lock'
    try:
        with open(lockname, 'r', encoding='utf8') as jfd:
            lkinfo = json.load(jfd)
    except IOError:
        lkinfo = None
    return lkinfo

def _getlock(name, ident):
    "Tries to lock file. Returns lock info on success"
    lockname = name+'.lock'
    try:
        fno = os.open(lockname, os.O_CREAT|os.O_EXCL|os.O_RDWR, 0o664)
    except OSError as excp:
        if excp.errno == errno.EEXIST:
            with open(lockname, 'r', encoding='utf8') as jfd:
                lkinfo = json.load(jfd)
            raise LockException(name, lkinfo[2]) from None
        raise
    lkinfo = (uuid.uuid4().hex, time.time(), ident)
    filed = os.fdopen(fno, 'w', encoding='utf8')
    json.dump(lkinfo, filed)
    filed.close()
    return lkinfo

def _jload(name, nofile=None):
    try:
        with open(name, encoding='utf8') as jfd:
            ret = json.load(jfd)
    except Exception as excp:                       # pylint: disable=W0703
        if nofile is None:
            raise TableException(f"Errore jload({name}) [{str(excp)}]") from None
        ret = nofile
    return ret

def jload(path, nofile=None):
    'Returns "nofile" if file cannot be read'
    name = getpath(path)
    lkinfo = _islocked(name)
    if lkinfo:
        raise LockException(name, lkinfo[2])
    return _jload(name, nofile)

def jsave(path, data, lockinfo=None):
    "Save object as json file"
    name = getpath(path)
    lkinfo = _islocked(name)
    if lkinfo:
        if (not lockinfo) or (lkinfo[0] != lockinfo[0]):
            raise LockException(name, lkinfo[2])
    try:
        with open(name, mode='w', encoding='utf8') as jfd:
            json.dump(data, jfd, indent=2)
    except Exception as excp:
        raise TableException(f"Error jsave({name}) [{str(excp)}]") from None
    finally:
        fpath = _junlock(path)
        os.chmod(fpath, 0o600)

def jsave_b64(ppath, theobj):
    "base64 encoding of dict saved to jfile"
    name = getpath(ppath)
    b64obj = base64.b64encode(json.dumps(theobj).encode("utf-8")).decode("ascii")
    with open(name, "w", encoding='utf8') as fds:
        fds.write(b64obj)

def jload_b64(ppath):
    "Jload and base64 decode"
    name = getpath(ppath)
    with open(name, "r", encoding='utf8') as fds:
        b64obj = fds.read()
    return json.loads(base64.b64decode(b64obj).decode("utf-8"))


#######         Test code
def usage():
    "Help function"
    print()
    print(f"table.py.  {__author__} - Version: {__version__}, {__date__}")
    print(__doc__)

def fulltest():                        # pylint: disable=R0914,R0915
    "Codice di test"
    table_file = 'test_table.json'
    lock_file = table_file+'.lock'

    try:
        os.unlink(table_file)
    except:                       # pylint: disable=W0702
        pass
    try:
        os.unlink(lock_file)
    except:                       # pylint: disable=W0702
        pass

    tbl = Table(table_file, header=('Field1', 'Field2', 'Field3', 'Field4'))
    known_row = [4, 7, 123, 9]
    rand_row = list(range(4))
    idx = 7
    while idx:
        random.shuffle(rand_row)
        tbl.insert_row(rand_row)
        idx -= 1
    tbl.insert_row(known_row)
    for idx in range(3):
        random.shuffle(rand_row)
        tbl.insert_row(rand_row)

    assert len(tbl) == 11, "Errore creazione table"

    s_row = tbl.get_row(8)
    assert s_row == known_row, "Errore indice riga campione"

    tbl.delete_row(3)
    s_row = tbl.get_row(3)
    assert s_row is None, "Riga 3 non cancellata"

    s_row = tbl.get_row(8)
    assert s_row == known_row, "Errore indice riga campione"

    s_col1 = tbl.column(3)
    s_col2 = tbl.column('Field3')
    assert s_col1 == s_col2, "Errore selezione colonna"

    tbl.sort(3)
    col0 = tbl.column(0)   # Index column
    assert col0[-1] == 8, "Errore indice riga campione, dopo sort"

    tbl.insert_row(known_row, 15)

    tbl.renumber()
    s_row1 = tbl.get_row(10)
    s_row2 = tbl.get_row(11)
    assert s_row1 == known_row and s_row2 == known_row, "Errore renumber()"

    cols = tbl.columns(('Field3', 'Field1'))
    assert cols[-1] == [known_row[2], known_row[0]], "Errore selezione colonne"

    w_rows = tbl.where('Field3', 123, index=True)
    assert len(w_rows) == 2, "Errore metodo where()"
    tbl.save()
    assert os.path.exists(table_file), "File per tabella inesistente"

    tbl = Table(table_file, lock='lock1')

    try:
        tbl = Table(table_file)
    except LockException:
        excp_ok = True
    else:
        excp_ok = True

    assert excp_ok, "Errore lock tabella"

    tbl.unlock()
    tbl = Table(table_file, lock='lock2')
    s_row = tbl.get_row(11)
    assert s_row == known_row, "Errore rilettura tabella"

    dtable = tbl.as_dict(1)
    assert isinstance(dtable, dict), "Errore metodo as_dict()"

    tbl.unlock(force=True)

    adict = {"uno": 1, "pi": 3.1415926, "name": "tarabaralla"}
    jsave_b64("test64.json", adict)
    thesame = jload_b64("test64.json")
    assert adict == thesame, "Errore jsave_b64/jload_b64"

    print("All tests: OK")

def compare(ftab1, ftab2):
    'Confronta tabelle da due file assgnati'
    tab1 = Table(ftab1)
    tab2 = Table(ftab2)
    print('1:', tab1.header)
    print('2:', tab2.header)
    if tab1.header != tab2.header:
        print('Le tabelle hanno colonne differenti:')
        sys.exit()
    else:
        print(' *** Le colonne corrispondono ***')
    codf1 = set(x[1] for x in tab1.rows)
    codf2 = set(x[1] for x in tab2.rows)
    only1 = sorted(list(codf1 - codf1.intersection(codf2)))
    only2 = sorted(list(codf2 - codf1.intersection(codf2)))
    print('1 - Codici presenti SOLO in', ftab1, '***')
    for codf in only1:
        print(' -', codf)
    print('2 - Codici presenti SOLO in', ftab2, '***')
    for codf in only2:
        print(' -', codf)
    print()
    ans = input('Trasferimento codici: 1 (da 1 a 2), 2 (da 2 a 1)? ')
    if ans == '1':
        movecodf(only1, tab1, tab2)
    elif ans == '2':
        movecodf(only2, tab2, tab1)

def movecodf(candidati, taba, tabb):
    'sposta codici da lista candidati da taba a tabb'
    while True:
        if not candidati:
            break
        print()
        for idx, codf in enumerate(candidati):
            print(' ', idx+1, '-', codf)
        ans = input('Indice codf da spostare: (0: fine)? ')
        try:
            idx = int(ans)
        except ValueError:
            break
        if 0 < idx <= len(candidati):
            codf = candidati[idx-1]
            row = taba.where('Codice', codf)
            if len(row) == 1:
                tabb.insert_row(row[0])
                print('Codice:', codf, 'Trasverito')
                del candidati[idx-1]
            else:
                print('La ricerca ha prodotto:', row)
                print('Spostamento non possibile')
        else:
            break
        ans = input('Nome file per tabella aggiornata? ').strip()
        if ans:
            tabb.save(ans)
            print()
            print('Tabella salvata in:', ans)

ARGERR = 'Errore argomenti. Usa -h per aiuto'

def main():
    'Interactive use'
    if '-h' in sys.argv:
        print(__doc__)
        sys.exit()
    if '-f' in sys.argv:
        fulltest()
        sys.exit()

    if len(sys.argv) != 3:
        print(ARGERR)
        sys.exit()

    compare(sys.argv[1], sys.argv[2])

if __name__ == '__main__':
    main()
