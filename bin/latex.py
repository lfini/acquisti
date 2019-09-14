"""
Generazione documenti PDF da LaTeX con templates jinja2
"""

import os
import subprocess
import logging
import random

from jinja2 import Environment
from jinja2 import FileSystemLoader
from PyPDF2 import PdfFileReader, PdfFileWriter

# VERSION 3.0    05/01/2018  - Versione python3

__author__ = 'Luca Fini'
__version__ = '3.1'
__date__ = '20/5/2019'

PDFLATEX = '/usr/bin/pdflatex'

_NOTA = 'Il prezzo '+chr(232)+' specificato in Euro ('+chr(8364)+ \
        ')  *** '+chr(192)+chr(233)+chr(197)+' ***'

TEST_ACQUISTO = {'data_richiesta': '19/7/1952',
                 'nome_richiedente': 'Luca Fini',
                 'str_costo_ord_it': '100 € + I.V.A. 22%, incluso trasporto',
                 'cig': '01-234',
                 'cup': "234-01",
                 'capitolo': '12.345.67',
                 'iva': '22% esclusa',
                 'note': _NOTA,
                 'numero_pratica': 132,
                 'nome_fornitore': 'Esselunga',
                 'ind_fornitore': 'Via Lupo, 6',
                 'numero_ordine': 1432,
                 'data_ordine': '20/7/1952',
                 'nome_direttore': 'Luca Fini',
                 'nome_responsabile': 'Giuseppe Garibaldi',
                 'titolo_direttore': 'Ing.',
                 'descrizione_ordine': 'Un sacco di patate',
                }

TEST_SEDE = 'Osservatorio della Montagna Pistoiese'
TEST_INDIRIZZO = 'Località Pian dei Termini'
TEST_WEBSITE = 'www.oampt.org'

TEST_USER = {'name':'Luca', 'surname': 'Fini'}

CHLIST = {35: "\\#",
          36: "\\$",
          37: "\\%",
          38: "\\&",
          91: "\\[",
          92: "\\backslash",
          93: "\\]",
          94: "\\verb:^:",
          95: "\\_",
          123: "\\{",
          125: "\\}",
          126: "\\verb:~:",
          161: "\\`e",
          163: "\\pounds{}",
          192: "\\`A",
          193: "\\'A",
          200: "\\`E",
          201: "\\'E",
          204: "\\`I",
          205: "\\'I",
          210: "\\`O",
          211: "\\'O",
          217: "\\`U",
          218: "\\'U",
          224: "\\`a",
          225: "\\'a",
          232: "\\`e",
          233: "\\'e",
          236: "\\`i",
          237: "\\'i",
          242: "\\`o",
          243: "\\'o",
          249: "\\`u",
          250: "\\'u",
          8364: "\\euro{}"}

def tempnam(destdir='./', prefix='', suffix=''):
    "Genera un nome file temporaneo"
    randname = ''.join([random.choice('abcdefghijklmnopqrstuvwxyz') for x in range(7)])
    return  os.path.join(destdir, prefix+randname+suffix)

def single_escape(ach):
    "Escape a la TeX un singolo carattere"
    nch = ord(ach)
    sub = CHLIST.get(nch)
    if not sub:
        if nch < 128:
            return chr(nch)
        return "\\ddag{}"
    return sub

def escape_tex(strng):
    "Escape TeX chars nella stringa data"
    ss1 = [single_escape(s) for s in strng]
    return ''.join(ss1)

def sanitize(data):
    "Escapes a-la-TeX the values in data."
    if isinstance(data, str):
        return escape_tex(data)
    if isinstance(data, dict):
        newdata = {}
        for key, item in data.items():
            newdata[key] = sanitize(item)
        return newdata
    if isinstance(data, (tuple, list)):
        newdata = [sanitize(x) for x in data]
        return newdata
    return data

BATCHMODE = True

class SplittedAttachment:
    "Genera pagine PDF per allegato"
    def __init__(self, destdir, pdffile, debug=False):
        self.debug = debug
        pdfa = PdfFileReader(open(pdffile, mode='rb'))
        npages = pdfa.getNumPages()
        self.pagefiles = [os.path.join(destdir, "atc_page-%d.pdf"%np) \
                         for np in range(npages)]
        for npage, pgfile in enumerate(self.pagefiles):
            output = PdfFileWriter()
            output.addPage(pdfa.getPage(npage))
            with open(pgfile, mode="wb") as ofp:
                output.write(ofp)
            logging.debug('Written attachment page: %s', pgfile)

    def __getitem__(self, idx):
        "Implementa accesso come lista"
        return self.pagefiles[idx]

    def clean(self):
        "Cancella file temporanei"
        if not self.debug:
            for pgfile in self.pagefiles:
                os.unlink(pgfile)

INIZIO_ALLEGATO = """
%%%% Inizio allegato %d
"""

HEADER_PAGINA = """
\\newpage
\\vspace{-10mm}{\\small Allegato %d / Pag. %d}
\\vspace{-20mm}
"""

INSERISCI_PAGINA = """\\makebox[\\textwidth]{\\includegraphics[width=\\textwidth]{%s}}
"""

def insert_attachments(dst, atcs, debug=False):
    "Inserisci allegati nel file dato (dst: file pointer aperto)"
    nallegato = 1
    for atc in atcs:
        dst.write(INIZIO_ALLEGATO % nallegato)
        if debug:
            logging.debug('Aggiunta allegato %d', nallegato)
        for npage, page in enumerate(atc):
            hdline = HEADER_PAGINA % (nallegato, npage+1)
            dst.write(hdline)
            dst.write(INSERISCI_PAGINA % page)

def do_attachments(fname, atcs, debug=False):
    "Riscrive il file fname inserendo gli allegati"
    bname, ext = os.path.splitext(fname)
    sfname = bname+'_tmp'+ext
    os.rename(fname, sfname)
    with open(sfname, 'r') as src, open(fname, 'w') as dst:
        while True:
            line = src.readline()
            if not line:
                break
            if '--ALLEGATI--' in line:
                insert_attachments(dst, atcs, debug)
            else:
                dst.write(line)
    os.unlink(sfname)

def cleantempdir(tempdir):
    "Cancella tutti i file dalla directory temporanea"
    try:
        for name in os.listdir(tempdir):
            os.unlink(os.path.join(tempdir, name))
    except FileNotFoundError:
        pass
    try:
        os.rmdir(tempdir)
    except FileNotFoundError:
        pass

def makepdf(destdir, pdfname, template, debug=False, attach=None, **data):
    "Genera file PDF da template LaTeX"
    path, fname = os.path.split(template)
    env = Environment(loader=FileSystemLoader(path))
    tempdir = os.path.join(destdir, 'tmp')
    cleantempdir(tempdir)
    os.mkdir(tempdir)
    env.block_start_string = '((*'
    env.block_end_string = '*))'
    env.variable_start_string = '((('
    env.variable_end_string = ')))'
    env.comment_start_string = '((='
    env.comment_end_string = '=))'
    template = env.get_template(fname)
    tname = tempnam(tempdir)
    tmplatex = tname+'.tex'
    tmppdf = tname+'.pdf'
    tpath, tname = os.path.split(tname)
    if debug:
        logging.debug("Template: %s", template.name)

    atcs = []
    if attach:
        for atch in attach:
            logging.debug('Processing attachment: %s', atch)
            atcs.append(SplittedAttachment(tempdir, atch, debug))

    newdata = sanitize(data)
    with open(tmplatex, encoding='utf-8', mode='w') as fpt:
        tex = template.render(**newdata)
        fpt.write(tex)
    if atcs:
        do_attachments(tmplatex, atcs)
    cmd = [PDFLATEX]
    if BATCHMODE:
        cmd.extend(['-interaction', 'batchmode'])
    cmd.extend(['-output-directory', tpath, tmplatex])
    logging.info('LaTeX cmd: %s', ' '.join(cmd))
    subp = subprocess.Popen(cmd, stderr=subprocess.PIPE)
    errors = subp.stderr.readlines()
    for err in errors:
        logging.error("LaTeX stderr: %s", err.strip())
    pdffile = os.path.join(destdir, pdfname)
    if not os.path.exists(tmppdf):
        logging.error("LaTeX did not generate temp file: %s", tmppdf)
    logging.debug("Renaming %s to %s", tmppdf, pdffile)
    try:
        os.rename(tmppdf, pdffile)
        os.chmod(pdffile, 0o600)
        ret = True
    except Exception as excp:
        ret = True
        logging.error("renaming %s to %s [%s]", tmppdf, pdffile, str(excp))
    if  debug:
        logging.debug("Temp. dir not removed: %s", tempdir)
    else:
        cleantempdir(tempdir)
    return ret

class PrintLogger:
    "Semplice logger di default"
    @staticmethod
    def debug(fmt, *d):
        "Debug output"
        print("DBG - ", fmt%d)
    @staticmethod
    def info(fmt, *d):
        "Info output"
        print("INF - ", fmt%d)
    @staticmethod
    def warning(fmt, *d):
        "Warning output"
        print("WNG - ", fmt%d)
    @staticmethod
    def error(fmt, *d):
        "Error output"
        print("ERR - ", fmt%d)


def test():
    "Procedura di test"
    global BATCHMODE

    print()
    print("latex.py. %s - Version: %s, %s" % (__author__, __version__, __date__))
    print()

    templfile = '../files/ordine_italiano.tex'
    pdffile = 'test_document.pdf'

    BATCHMODE = False
    ret = makepdf('.', pdffile, templfile, attach=["include.pdf"], debug=True,
                  pratica=TEST_ACQUISTO, user=TEST_USER, sede=TEST_SEDE,
                  indirizzo=TEST_INDIRIZZO, website=TEST_WEBSITE)

    if ret:
        print("Created file: %s" % pdffile)
    else:
        print("Some error")

if __name__ == '__main__':
    test()
