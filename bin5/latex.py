"""
Generazione documenti PDF da LaTeX con templates jinja2

Uso per test:

    python3 latex.py [-h] [anno pratica]

Dove:

    -h: mostra questa pagina ed esce

    Senza argomenti: genera un file da dati preordinati

    Se sono specificati anno e pratica (es: 2022/127): viene generato il file
    relativo alla richiesta della pratica specificata

"""

import sys
import os
import subprocess
import logging
import random

from jinja2 import Environment
from jinja2 import FileSystemLoader
from PyPDF2 import PdfReader, PdfWriter

from constants import FILEDIR   # Necessario per test
import ftools as ft             # Necessario per test

# VERSION 3.0    05/01/2018  - Versione python3
# VERSION 3.1    17/10/2019  - path pdflatex configurabile
# VERSION 3.2    17/10/2019  - Corretto formato per inclusione
# VERSION 3.3    13/07/2021  - Corretto test offline
# VERSION 3.4    28/2/2023   - Migliorato test offline
# VERSION 3.5    24/4/2024   - Semplificato path programma pdflatex

__author__ = 'Luca Fini'
__version__ = '3.5'
__date__ = '24/4/2024'

class PDFLATEX:         # pylint: disable=R0903
    "Info ausiliaria per lancio di pdflatex"
    cmd = '/usr/bin/pdflatex'

_NOTA1 = 'Il prezzo '+chr(232)+' specificato in Euro ('+chr(8364)+')'
_NOTA2 = """

Prolungamento della nota con lo scopo di generare un documento di almeno due pagine.

Si va quindi sovente a capo e si cerca di aggiungere testo
senza particolare significato, con il solo scopo di occupare spazio.

Come promemoria questo test dovrebbe anche includere un allegato per verificare
il funzionamento del meccanismo degli allegati.

Aggiungo ancora qualche linea, in modo che si vada a capo con un po' di testo
e non solo con la firma.

Ma siccome ancora non basta aggiungo altro testo. Se non basta ancora dovrò rivolgermi 
a brani letterari.

Sembra che questo sia sufficiente a mandare a capo almeno un po' della nota.
"""

TEST_ACQUISTO = {'data_richiesta': '19/7/1952',
                 'nome_richiedente': 'Luca Fini',
                 'dettaglio_ordine': 1,
                 'str_costo_ord_it': '100 € + I.V.A. 22%, incluso trasporto',
                 'cig': '01-234',
                 'cup': "234-01",
                 'capitolo': '12.345.67',
                 'iva': '22% esclusa',
                 'note_ordine': _NOTA1+_NOTA2,
                 'numero_pratica': 132,
                 'fornitore_nome': 'Esselunga',
                 'fornitore_sede': 'Via Lupo, 6',
                 'fornitore_codfisc': '0552343071',
                 'fornitore_partiva': '0552343071',
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

def set_path(pdflatex):
    "Imposta path per pdflatex"
    PDFLATEX.cmd = pdflatex

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

class BATCHMODE:         # pylint: disable=R0903
    "Flag per selezione batchmode"
    on = True

class SplittedAttachment:
    "Genera pagine PDF per allegato"
    def __init__(self, destdir, pdffile, debug=False):
        self.debug = debug
        pdfa = PdfReader(open(pdffile, mode='rb'))     # pylint: disable=R1732
        npages = len(pdfa.pages)
        self.pagefiles = [os.path.join(destdir, f"atc_page-{np}.pdf") \
                         for np in range(npages)]
        for npage, pgfile in enumerate(self.pagefiles):
            output = PdfWriter()
            output.add_page(pdfa.pages[npage])
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
\\quad
\\begin{flushright}
\\vspace{-25mm}
{\\small Allegato %d / Pag. %d}
\\end{flushright}
%%\\vspace{-15mm}
"""

INSERISCI_PAGINA = """\\makebox[\\textwidth]{\\includegraphics[height=0.9\\textheight]{%s}}
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
    with open(sfname, 'r', encoding='utf8') as src, open(fname, 'w', encoding='utf8') as dst:
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

def makepdf(destdir, pdfname, template, debug=False, attach=None, **data):  #pylint: disable=R0915,R0914
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
    cmd = [PDFLATEX.cmd]
    if BATCHMODE.on:
        cmd.extend(['-interaction', 'batchmode'])
    cmd.extend(['-output-directory', tpath, tmplatex])
    logging.info('LaTeX cmd: %s', ' '.join(cmd))
    with subprocess.Popen(cmd, stderr=subprocess.PIPE) as subp:
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
    except Exception as excp:  #pylint: disable=W0703
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

ARGERR = 'Errore argomenti: usa -h per help'

def main():
    "Procedura di test"
    print()
    print(f'latex.py. {__author__} - Version: {__version__}, {__date__}')
    print()

    if '-h' in sys.argv:
        print(__doc__)
        sys.exit()

    if len(sys.argv) == 1:
        test1()
        sys.exit()

    if len(sys.argv) == 3:
        try:
            anno = int(sys.argv[1])
            pratica = int(sys.argv[2])
        except:                          # pylint: disable=W0702
            print(ARGERR)
            sys.exit()
        test2(anno, pratica)
        sys.exit()
    print(ARGERR)

def test1():
    'test rapido'
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    templfile = os.path.join(FILEDIR, 'ordine_italiano.tex')
    pdffile = 'test_document.pdf'
    headerpath=os.path.join(FILEDIR, "header.png")
    footerpath=os.path.join(FILEDIR, "footer.png")
    attach=[os.path.join(FILEDIR, "test_attach.pdf")]

    BATCHMODE.on = False
    ret = makepdf('.', pdffile, templfile, debug=True,
                  pratica=TEST_ACQUISTO, user=TEST_USER, sede=TEST_SEDE,
                  headerpath=headerpath,
                  footerpath=footerpath,
                  attach=attach,
                  indirizzo=TEST_INDIRIZZO, website=TEST_WEBSITE)

    if ret:
        print("Created file:", pdffile)
    else:
        print("Some error")

def test2(anno, nprat):
    'generazione vera richiesta pratica'
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    pratica = ft.get_pratica(anno, nprat)

    templfile = os.path.join(FILEDIR, 'richiesta.tex')
    pdffile = 'test_document.pdf'
    headerpath=os.path.join(FILEDIR, "header.png")
    footerpath=os.path.join(FILEDIR, "footer.png")
    attach=[os.path.join(FILEDIR, "test_attach.pdf")]

    BATCHMODE.on = False
    ret = makepdf('.', pdffile, templfile, debug=True,
                  pratica=pratica, user=TEST_USER, sede=TEST_SEDE,
                  headerpath=headerpath,
                  footerpath=footerpath,
                  attach=attach,
                  indirizzo=TEST_INDIRIZZO, website=TEST_WEBSITE)

    if ret:
        print("creato file:", pdffile)
    else:
        print("Verifica errori")

if __name__ == '__main__':
    main()
