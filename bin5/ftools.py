"""
Tools per la procedura acquisti.py

Uso da linea di comando:
    python ftools.py access     - test username/password
    python ftools.py ndecis     - Visualizza ultimo num. decisione di contrarre
    python ftools.py nprat      - Visualizza ultimo num. pratica
    python ftools.py plist      - Visualizza elenco pratiche
    python ftools.py prat nprat - Visualizza File dati di una pratica
    python ftools.py ulist      - Visualizza lista utenti
    python ftools.py user uid   - Mostra/crea/modifica utente

                              Comandi per supporto sviluppo e debug:
    python ftools.py all    - Elenca tutti i campi definiti in tutte le pratiche
    python ftools.py pass   - Genera file per password
    python ftools.py show   - Mostra file per password
    python ftools.py values - Mostra tutti i valori del campo dato
    python ftools.py where  - Elenco pratiche con valore di campo dato
"""

# VERSION 4.0    4/1/2018  Versione python 3
# VERSION 4.1    5/10/2018 Modificato termine "cram" in "codf"
# VERSION 4.2    14/2/2019 Correzioni alla generazione dei costi
# VERSION 4.3    1/3/2019 Ancora correzioni alla generazione dei costi
# VERSION 4.4    1/3/2019 Migliorato parsing di data-ora
# VERSION 4.5    3/11/2020 aggiunto display errori in render_item_as_form()
# VERSION 4.6    30/11/2020 aggiunto metodo __len__ a DocList
# VERSION 4.7    05/12/2020 Integrazioni per usere GMail come server di posta
# VERSION 4.8    10/05/2021 Modifiche per inserimento logo in testa ai documenti
#                           Attivazione di GMail come server di posta (anche per errori)
# VERSION 4.8.1  12/07/2021 Aggiunta MyException per risolvere problema su stringa_valore
# VERSION 4.8.2  18/11/2021 Aggiunta funzione _last_resort_log() e modificata funzione
#                           di autenticazione
# VERSION 4.8.3  29/11/2021 Corretto errore in autenticazione
# VERSION 4.9    11/11/2023 passato con pylint
# VERSION 5.0    8/4/2024 Nuova versione.

import sys
import os
import time
import re
import base64
import pwd
import hashlib
import string
import stat
import random
from pprint import pprint
import readline           # pylint: disable=W0611
import subprocess
import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
from logging import StreamHandler
from functools import reduce
from getpass import getpass

import ldap3
from Crypto.Cipher import AES
import pam

from constants import *       # pylint: disable=W0614,W0401
import table as tb
import latex
import send_email as sm

# pylint: disable=C0302, W0703

__author__ = 'Luca Fini'
__version__ = '5.0'
__date__ = '6/3/2024'

if hasattr(pam, 'authenticate'):      # Arrangia per diverse versioni del modulo pam
    PAM_AUTH = pam.authenticate
else:
    PAM_AUTH = pam.pam().authenticate

USER_DN = 'uid=%s,ou=people,dc=inaf,dc=it'

class GlobLists:         # pylint: disable=R0903
    "Liste usate dalla procedura. Definite in fase di inizializzazione"
    USERLIST = None
    CODFLIST = None
    HELPLIST = []

class MyException(RuntimeError):
    "Exception arricchita"

class GMailHandler(StreamHandler):           # pylint: disable=R0903
    "Logging handler che usa GMail API"
    def __init__(self, fromaddr, toaddr, subject):
        super().__init__()
        self.fromaddr = fromaddr
        self.dest = [toaddr]
        self.subject = subject
#       print("GMailHandler init:", self.dest)

    def emit(self, record):
        "Invia messaggio di log via GMail"
        try:
            sm.send("", None, self.fromaddr, self.dest, self.subject, self.format(record))
        except Exception as excp:
            _last_resort_log(f"Errore invio email a: {self.dest}\n- {excp}")

########################################## Table support
class FTable(tb.Table):
    "definizione tabelle con estensioni per rendering HTML"
    def __init__(self, path, header=None, sortable=()):
        tb.Table.__init__(self, path, header)
        self.sortable = [x for x in sortable if x in self.header]

    def render_item_as_form(self, title, form, action,            # pylint: disable=R0913
                            nrow=0, ignore=(), errors=()):
        "HTML rendering di un campo per uso in un form"
        html = [TABLE_HEADER]
        if title:
            html.append(f'<h1> {title} </h1>')
        if errors:
            html.append("<hr><b><font color=red>Attenzione:</font></b><br />")
            for err in errors:
                html.append("&nbsp;&nbsp; - "+err+"<br />")
            html.append("<hr>")
        html.append(f'<form method="POST" action="{action}">')
        if nrow > 0:
            html.append(f'<b>Record N. {nrow}</b><p>')
        html.append('<dl>')
        for fname in self.header[1:]:
            if fname in ignore:
                continue
            val = str(form[fname])
            html.append(f'<dt> {form[fname].label} <dd> {val}')
        html.append('</dl>')
        html.append(str(form['annulla']) + '&nbsp;&nbsp;' + str(form['avanti']))
        if nrow > 0:
            html.append('<hr>'+str(form['cancella']))
        html.append('</form>')
        return '\n'.join(html)

    def render_item_as_text(self, title, nrow, index=False):
        "HTML rendering di un campo"
        html = [TABLE_HEADER]
        if title:
            html.append(f'<h1> {title} </h1>')
        if index:
            fields = self.header
        else:
            fields = self.header[1:]
        row = self.get_row(nrow, index=index, as_dict=True)
        html.append(f'<b>Record N. {nrow}</b><p>')
        html.append('<dl>')
        for fld in fields:
            val = row[fld]
            html.append(f'<dt> {fld} <dd> {val}')
        html.append('</dl>')
        return '\n'.join(html)

    def render(self, title=None, menu=(), select_url=(), sort_url=(),      # pylint: disable=R0912,R0913,R0914
               edit_symb=EDIT_SYMB, index=False, sort_on=1, footer='',
               select=None, messages=()):
        "HTML rendering della tabella"
        def _formrow(row):
            dname = row[0]
            ret = f'<tr><td><a href="{select_url[0]}/{dname}">{edit_symb}</a></td><td>'
            return ret+'</td><td>'.join([str(r) for r in row[1:]])+'</td></tr>'
        def _fullrow(row):
            return '<tr><td>'+'</td><td>'.join([str(r) for r in row])+'</td></tr>'
        def _shortrow(row):
            return '<tr><td>'+'</td><td>'.join([str(r) for r in row[1:]])+'</td></tr>'
        def _fmtheader(name):
            uname = str(name)
            if uname in self.sortable and sort_url:
                uname = uname+'&nbsp;&nbsp;<a href='+sort_url[0]+'/'+uname+'>'+sort_url[1]+'</a>'
            return '<th>'+uname+'</th>'

        html = [TABLE_HEADER]
        if title:
            html.append(f'<h1> {title} </h1>')
        if messages:
            html.append('<hr>')
            for msg in messages:
                html.append(f'<p> {msg} </p>')
            html.append('<hr>')
        render_menu = []
        for mnu in menu:
            render_menu.append(f'<a href="{mnu[0]}">{mnu[1]}</a>')
        if render_menu:
            html.append('&nbsp;|&nbsp'.join(render_menu))
        if select_url:
            html.append(f'<hr>{select_url[1]}')
        if select_url:
            dorow = _formrow
            fields = ['&nbsp;'] + self.header[1:]
        elif index:
            dorow = _fullrow
            fields = ['&nbsp;'] + self.header[1:]
        else:
            dorow = _shortrow
            fields = self.header[1:]
        html.append('<table border=1><tr>'+ \
                    reduce(lambda x, y: str(x)+_fmtheader(y), fields, '')+'</tr>')
        self.sort(sort_on)
        if select:
            allrows = [x for x in self.rows if select(x)]
        else:
            allrows = self.rows
        for row in allrows:
            html.append(dorow(row))
        html.append('</table>')
        if footer:
            html.append(f'<center><font size=1>{footer}</font></center>')
        return '\n'.join(html)

########################################## End table support

class Matchty:               # pylint: disable=R0903
    "classe per verificare il corretto tipo di un file"
    def __init__(self, tlist):
        def addp(name):
            "normalizza nome estensione"
            if name[0] != '.':
                name = '.'+name
            return name.lower()
        self.tlist = [addp(t) for t in tlist]

    def check(self, name):
        "verifica estensione"
        ext = os.path.splitext(name)[1]
        return ext.lower() in self.tlist

class DocList:               # pylint: disable=R0903
    "definizione lista documenti"
    def __init__(self, thedir, fname,                        # pylint: disable=R0913
                 year=None,
                 directory_filter=lambda x: True,
                 filename_filter=lambda x: True,
                 content_filter=lambda x: True,
                 sort=None,
                 extract=None):
        self.years = get_years(thedir)  # Rendi noto quali altri
        self.years.sort()               # anni sono disponibili
        if is_year(year):
            self.year = str(year)
        else:
            self.year = str(thisyear())
        ydir = os.path.join(thedir, self.year)
        self.records = []
        self.errors = []
        try:
            pdirs = [x for x in os.listdir(ydir) if IS_PRAT_DIR.match(x)]
        except FileNotFoundError:
            pdirs = []
        else:
            pdirs = [os.path.join(ydir, x) for x in pdirs if directory_filter(x)]
            pdirs.sort()
        for pdir in pdirs:
            fnm = os.path.join(pdir, fname)
            if filename_filter(fnm):
                try:
                    rec = tb.jload(fnm)
                except tb.TableException:
                    self.errors.append(fnm)
                    continue
                if rec and content_filter(rec):
                    if extract:
                        rec = {key:value for key, value in rec.items() if key in extract}
                    self.records.append(rec)
        if sort:
            self.records.sort(key=sort)

    def __len__(self):
        "metodo standard per lunghezza"
        return len(self.records)

class PratIterator:
    "Iteratore sulle pratiche dell'anno specificato"
    def __init__(self, year=None):
        if not year:
            year = thisyear()
        self.ydir = os.path.join(DATADIR, str(year))
        self.pratdir = iter(os.listdir(self.ydir))

    def __iter__(self):
        return self

    def __next__(self):
        nextdir = self.pratdir.__next__()
        pratfile = os.path.join(self.ydir, nextdir, "pratica.json")
        try:
            prat = tb.jload(pratfile)
        except tb.TableException:
            prat = {}
        return prat


def version():
    "Riporta versione del modulo"
    return f"ftools.py. Versione {__version__} - {__author__}, {__date__}"

CHARS = string.ascii_letters+string.digits

NON_ABILITATO = """
non sei abilitato all'uso della procedura come "%s".
Per ottenere l'abilitazione devi rivolgerti all'amministrazione
"""

def checkdir():
    "Verifica esistenza della directory per dati e riporta il path"
    thedir = DATADIR
    if not os.path.exists(thedir):
        print()
        print(f"Directory {thedir} inesistente")
        print("\nDevi creare le directory di lavoro\n")
        sys.exit()
    return thedir

CONFIG = tb.jload((checkdir(), 'config.json'))

def setformatter():
    'definisce formato di log'
    logger = logging.getLogger()
    if not hasattr(logger, 'fHandler'):
        return
    fmtstr = '%(asctime)s '+ logger.host_info + ' ['+logger.user_info+'] %(levelname)s %(message)s'
    formatter = logging.Formatter(fmt=fmtstr)
    logger.fHandler.setFormatter(formatter)
    if hasattr(logger, 'eHandler'):
        logger.eHandler.setFormatter(formatter)

def _last_resort_log(message):
    "funzione chamata quando c'è un errore nel logger"
    fname = os.path.join(WORKDIR, time.strftime("%Y-%m-%dT%H:%M:%S.lrl"))
    with open(fname, "a", encoding='utf8') as f_out:
        print(message, file=f_out)

def set_file_logger(path):
    "imposta logger su file"
    logger = logging.getLogger()
    fpath = os.path.join(*path)
    hndl = RotatingFileHandler(fpath, maxBytes=1000000, backupCount=3, encoding='utf8')
    logger.fHandler = hndl
    logger.setLevel(logging.INFO)
    logger.host_info = 'x.x.x.x'
    logger.user_info = '----------'
    logger.addHandler(hndl)
    setformatter()

def set_mail_logger(mailhost, sender, recipient, subject):
    "imposta logger via e-email"
    logger = logging.getLogger()
    if mailhost == '-':
        ehndl = GMailHandler(sender, recipient, subject)
        logger.info("Abilitato log via GMail")
    else:
        ehndl = SMTPHandler(mailhost, sender, recipient, subject)
        logger.info("Abilitato log via SMTP: %s", mailhost)
    ehndl.setLevel(logging.ERROR)
    logger.eHandler = ehndl
    logger.addHandler(ehndl)
    setformatter()

I16 = b'1ZxqYcE4LjMc72oy'
P24 = 'xyCjhWT3fPtOel5MN02RDUYE'

def encrypt(plaintext, passw=""):
    "codifica una stringa con password"
    _pwd = (passw+P24).encode("utf8")[:24]
    obj = AES.new(_pwd, AES.MODE_CFB, I16)
    return obj.encrypt(plaintext.encode('utf8'))

def decrypt(ciphertext, passw=""):
    "decodifica una stringa con password"
    _pwd = (passw+P24).encode("utf8")[:24]
    obj = AES.new(_pwd, AES.MODE_CFB, I16)
    return obj.decrypt(bytes(ciphertext)).decode("utf8")

def ldap_authenticate(userid, password, server_ip, server_port, timeout=10):
    """Autenticazione ID/Password da server LDAP.
Ritorno: -1 (errore LDAP), 0 id/pw non validi, 1 id/pw validi"""
    if server_ip in ("", "-"):
        return 0
    server = ldap3.Server(server_ip, port=int(server_port), connect_timeout=timeout)
    conn = ldap3.Connection(server, USER_DN%userid, password)
    try:
        auth = conn.bind()
    except ldap3.core.exceptions.LDAPExceptionError:
        return -1
    if auth:
        return 1
    return 0

def send_email(mailhost, sender, recipients, subj, body, attach=None, debug_addr=''):    # pylint: disable=R0913
    "Invio messaggio e-mail"
    if debug_addr:
        warning = f"MODO DEBUG - destinatari originali: {', '.join(recipients)}\n\n"
        message = warning+body
        dest = [debug_addr]
        subjd = subj+' (DEBUG)'
    else:
        message = body
        dest = recipients
        subjd = subj
    if mailhost.strip() == "-":
        mailhost = None
    try:
        sm.send(mailhost, None, sender, dest, subjd, message, attach)
    except Exception as excp:
        errmsg = f"Mail to: {', '.join(recipients)} - "+str(excp)
        logging.error(errmsg)
        return ''
    return dest

LETTERS = 'ABCDEFGHIJKLMNOPQRTSUVWXYZ'

def byinitial(inlist, key=lambda x: x, remove_empty=True):
    "Returns inlist organized by Initial"

    byin = {l: [] for l in LETTERS+'~'}

    for user in inlist:
        letter = key(user)[0].upper()
        if letter not in LETTERS:
            letter = '~'
        byin[letter].append(user)

    if remove_empty:
        to_remove = [idx for idx in byin if not byin[idx]]
        for idx in  to_remove:
            del byin[idx]

    for idx in byin:
        byin[idx].sort(key=key)
    return byin

def find_max_prat(year=None):
    "Cerca il massimo valore del numero pratica"
    if not year:
        year = thisyear()
    yys = f'{year}'
    dpath = os.path.join(DATADIR, yys)
    if not os.path.exists(dpath):
        return 0
    try:
        plist = os.listdir(dpath)
    except Exception:
        return 0
    if not plist:
        return 0
    plist.sort()
    prat = int(plist[-1].split('_')[1])
    return prat

def _find_max_field(what, year=None):
    "Cerca il massimo valore del campo specificato (della forma: nnn/yyyy)"
    if not year:
        year = thisyear()
    if not isinstance(what, (list, tuple)):
        what = (what,)
    yys = f'{year}'
    dpath = os.path.join(DATADIR, yys)
    try:
        plist = os.listdir(dpath)
    except Exception:
        plist = []
    maxfld = 0
    prat = ''
    for nprat in plist:
        path = os.path.join(dpath, nprat)
        try:
            dati_pratica = tb.jload((path, 'pratica.json'))
        except tb.TableException:
            logging.error("Errore lettura pratica %s", path)
            continue
        for item in what:
            value = dati_pratica.get(item)
            try:
                nnyy = value.split('/')
            except Exception:
                continue
            if len(nnyy) == 2:
                try:
                    nvalue = int(nnyy[0])
                except Exception:
                    continue
                else:
                    if maxfld < nvalue:
                        maxfld = nvalue
                        prat = nprat
    return maxfld, prat

def find_max_decis(year=None):
    "Cerca il massimo valore del numero decisione di contrarre"
    return _find_max_field("numero_decisione", year)


def clean_locks(datadir):
    "Rimuove lock file 'zombi'"
    tree = os.walk(datadir)
    for dpath, _unused, fnames in tree:
        for name in fnames:
            if name[-5:] == '.lock':
                lockfile = os.path.join(dpath, name)
                os.unlink(lockfile)

def host(url):
    "Estra la porzione 'host' da una URL"
    splt = url.split(':')
    return ':'.join(splt[0:2])

def html_escape(strng):
    "Semplice escape per stringhe HTML"
    strng = strng.replace('&', '&amp;')  # Must be first
    strng = strng.replace('<', "&lt;")
    strng = strng.replace('>', "&gt;")
    return strng

def html_params(params, escape=True):
    "Converte un dict in stringa con sintassi HTML"
    if escape:
        filt = html_escape
    else:
        filt = lambda x: x
    parlist = []
    for key, value in params.items():
        parlist.append(f'{key}={filt(value)}')
    return ' '.join(parlist)

def today(fulltime=True):
    "Riporta data odierna"
    if fulltime:
        return time.strftime('%d/%m/%Y %H:%M')
    return time.strftime('%d/%m/%Y')

def date_to_time(date):
    "Converts a date (g/m/a [h:m]) into epoch. Returns None if date invalid"
    if ":" in date:
        fmt = "%d/%m/%Y %H:%M"
    else:
        fmt = "%d/%m/%Y"
    try:
        tstruc = time.strptime(date.strip(), fmt)
    except Exception:
        ret = None
    else:
        ret = time.mktime(tstruc)
    return ret

NUMB_RE = re.compile("\\d+(,\\d{2})?$")
def is_number(number):
    "Verifica che il campo sia un numero nella forma: 111[,22]"
    try:
        isnumb = NUMB_RE.match(number)
    except Exception:
        return False
    return isnumb

def internal_error(msg=''):
    "Riporta errore in formato HTML"
    ret = "<h1>Errore interno</h1>"
    if msg:
        ret += f"<h3>{msg}</h3>"
    return ret

def thisyear():
    "Riporta l'anno corrente"
    return time.localtime().tm_year

def findfiles(basedir, prefix):
    "trova file con prefisso di nome dato"
    files = os.listdir(basedir)
    ret = [x for x in files if x.startswith(prefix)]
    return ret

def flist(basedir, filetypes=(), exclude=()):
    "Genera lista file di tipo assegnato"
    try:
        allfiles = os.listdir(basedir)
    except Exception:
        return []
    if filetypes:
        mty = Matchty(filetypes)
        allfiles = [f for f in allfiles if mty.check(f) and f not in exclude]
    allfiles.sort()
    return allfiles

def newdir(thedir):
    "Crea una directory con log"
    try:
        os.makedirs(thedir, 0o740)
    except Exception as excp:
        logging.error("Errore creazione directory %s [%s]", thedir, str(excp))
        ret = ''
    else:
        logging.info("Creata directory: %s", thedir)
        ret = thedir
    return ret

def spawn(command, inp=None):
    "Lancia comando dato"
    with subprocess.Popen(command, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE) as sbp:
        stdoutdata, stderrdata = sbp.communicate(inp)
    return (stdoutdata, stderrdata)

def procinfo():
    "Riporta informazioni sulprocesso"
    unm = os.uname()
    pyv = sys.version_info
    ret = [('User', pwd.getpwuid(os.getuid())[0]),
           ('PID', str(os.getpid())),
           ('OS', f'{unm[0]}-{unm[4]} {unm[2]}'),
           ('Python', f'{pyv[0]}.{pyv[1]}.{pyv[2]}')]
    return ret

def swapname(name):
    "Scambia 'cognome, nome' e riporta 'nome, cognome'"
    spn = name.split(', ')
    if len(spn) == 2:
        ret = f'{spn[1].strip()} {spn[0].strip()}'
    else:
        ret = name
    return ret

def modello_decisione(mod_acquisto):                  # pylint: disable=R0911
    "Stabilisce il template per la decisione di contrarre"
    if mod_acquisto == TRATT_MEPA_40:
        return "decisione"
#   if mod_acquisto == INFER_5000:
#       return "determina_inf5000"
#   if mod_acquisto == INFER_1000:
#       return "determina_inf1000"
#   if mod_acquisto == TRATT_MEPA_40:
#       return "determina_trattmepa_40"
#   if mod_acquisto == SUPER_5000:
#       return "determina_sup5000"
#   if mod_acquisto == SUPER_1000:
#       return "determina_sup1000"
#   if mod_acquisto == RDO_MEPA:
#       return "determina_rdo"
#   if mod_acquisto == PROC_NEG:
#       return "determina_procneg"
#   if mod_acquisto == MANIF_INT:
#       return "determina_manif"
    raise RuntimeError(f'Errore scelta modello decisione (mod.acquisto: {mod_acquisto}')

def makepdf(destdir, templ_name, pdf_name, debug=False, include="", **data):   # pylint: disable=R0913
    "Crea documento PDF da template LaTeX e dict di termini"
    tfile = os.path.join(FILEDIR, templ_name)+'.tex'
    pdfname = pdf_name+'.pdf'
    logging.info("Creazione documento da: %s come: %s/%s", tfile, destdir, pdfname)
    logging.info("Dati documento: %s", ', '.join(list(data.keys())))
    if  include:
        attach = os.path.join(destdir, include)
        logging.info("Includo file: %s", attach)
        attach_list = [attach]
    else:
        attach_list = None
    ndata = data.copy()
    ndata["headerpath"] = os.path.join(FILEDIR, "header.png")
    ndata["footerpath"] = os.path.join(FILEDIR, "footer.png")
    ndata["titolo_direttore"] = CONFIG['titolo_direttore']
    ndata["titolo_direttore_uk"] = CONFIG['titolo_direttore_uk']
    ndata["nome_direttore"] = CONFIG['nome_direttore']
    ndata["dir_is_m"] = CONFIG['gender_direttore'].lower() == 'm'
    latex.makepdf(destdir, pdfname, tfile, attach=attach_list, debug=debug, **ndata)

def get_user(userid):
    "Riporta record di utente"
    usr = GlobLists.USERLIST.where('userid', userid, as_dict=True)
    if usr:
        ret = usr[0]
        ret['email'] = ret['email'].strip()
        return usr[0]
    return {}

def _fullname(email):
    "Riporta il nome completo di utente, dato indirizzo e-mail"
    rec = GlobLists.USERLIST.where('email', email)
    if rec:
        return rec[0][5]
    return 'Sconosciuto'

def _read_userlist():
    "Legge la lista utenti"
    GlobLists.USERLIST = FTable((DATADIR, 'userlist.json'))
    if GlobLists.USERLIST.empty():
        logging.error("Errore lettura userlist: %s", GlobLists.USERLIST.filename)
    user_sn = GlobLists.USERLIST.columns((2, 3))
    user_fn = [f'{x[0]} {x[1]}' for x in user_sn]
    GlobLists.USERLIST.add_column(6, 'fullname', column=user_fn)
    logging.info("Lista utenti aggiornata")

def update_userlist():
    "Aggiorna la lista utenti"
    if not GlobLists.USERLIST:
        _read_userlist()
        return
    if GlobLists.USERLIST.needs_update():
        _read_userlist()

def _read_codflist():
    "Legge la lista dei codici Fu.Ob."
    GlobLists.CODFLIST = FTable((DATADIR, 'codf.json'))
    if GlobLists.CODFLIST.empty():
        logging.warning("Errore lettura lista codici fondi: %s", GlobLists.CODFLIST.filename)
                          # Integrazione codflist (aggiunge nome esteso)
    resp_em = GlobLists.CODFLIST.column(4)
    resp_names = [_fullname(x) for x in resp_em]
    GlobLists.CODFLIST.add_column(1, 'nome_Responsabile', column=resp_names)
    logging.info("Lista Codici Fu.Ob. aggiornata")

def update_codflist():
    "Aggiorna la lista dei codici Fu.Ob."
    if not GlobLists.CODFLIST:
        _read_codflist()
        return
    if GlobLists.CODFLIST.needs_update():
        _read_codflist()

def init_helplist():
    "Genera una lista dei file di nome 'help_*.html' nella directory dei file ausiliari"
    _helpfilt = re.compile('help_.+[.]html')
    try:
        flst = os.listdir(FILEDIR)
    except Exception:
        GlobLists.HELPLIST = []
    else:
        GlobLists.HELPLIST = [x[5:-5] for x in flst if _helpfilt.match(x)]

def _crypt(username, passw):
    'rimpiazzo di crypt.crypt (deprecato)'
    return base64.b64encode(encrypt(username, passw)).decode('ascii')

def authenticate(userid, password, ldap_host, ldap_port):            # pylint: disable=R0911
    "Autenticazione utente. ldap: indirizzo IP server LDAP, o vuoto"
    user = get_user(userid)
    if (pswd := user.get('pw')) != '-':
        if _crypt(password, userid) == pswd:
            logging.info('autenticazione locale OK')
            return True, "Accesso autorizzato"
    auth_ok = False
    ret = ldap_authenticate(userid, password, ldap_host, ldap_port)
    if ret < 0:
        logging.error("Errore di connessione al server LDAP")
    elif ret > 0:
        auth_ok = True
        logging.info("autenticazione LDAP OK")
    if not auth_ok:
        auth_ok = PAM_AUTH(userid, password)
        logging.info('autenticazione PAM OK')
    if not auth_ok:
        return False, "ID/password errati"
    if user:
        return True, "Accesso autorizzato"
    return False, NON_ABILITATO%userid

def makeuser(userid):                         # pylint: disable=R0912,R0915
    "Crea record di utente"
    thedir = checkdir()
    header = ['userid', 'surname', 'name', 'email', 'flags', 'pw']
    uls = FTable((thedir, 'userlist.json'), header)

    print()
    user = uls.where('userid', userid)
    if user:
        user = user[0]
        print()
        print("Dati per l'utente:", userid)
        print(" -                    Nome: "+user[2])
        print(" -                 Cognome: "+user[1])
        print(" -                   Email: "+user[3])
        print(" - Password ('-': usa PAM): "+user[5])
        print(" -               Privilegi: "+user[4])
        print()
        print("Legenda privilegi: A, amministrazione; D, developer; L, modifica LDAP")
        print()
        ans = input('Modificare/Cancellare utente [m/c]? ')
        ans = ans[:1].lower()
        if ans == "c":
            ans = input(f"Confermi cancellazione utente {user[2]} {user[1]}, [{userid}]? ")
            ans = ans[:1].lower()
            if ans == "s":
                rec = uls.where('userid', userid, index=True)
                if rec:
                    pos = rec[0][0]
                    uls.delete_row(pos)
                    uls.save()
                    print(f"Record utente {userid} cancellato")
            return
        if ans != "m":
            return
    else:
        user = ["", "", "", "", "", ""]
        print("Definizione dati per utente:", userid)
    name = input(f" -                      Nome [{user[2]}]: ")
    surname = input(f" -                   Cognome [{user[1]}]: ")
    email = input(f" -                     Email [{user[3]}]: ")
    while True:
        password = input(" - Password ('-': usa PAM/LDAP): ")
        if password:
            break
    flags = input(f" -                 Privilegi (ALD) [{user[4]}]: ")
    if not name:
        name = user[2]
    else:
        name = name.capitalize()
    if not surname:
        surname = user[1]
    else:
        surname = surname.capitalize()
    if not email:
        email = user[3]
    else:
        email = email.lower()
    if not flags:
        flags = user[4]

    print("Dati specificati per l'utente:")
    print()
    print(" -    Userid:", userid)
    print(" -      Nome:", name)
    print(" -   Cognome:", surname)
    print(" -     Email:", email)
    print(" -  Password:", password)
    print(" - Privilegi:", flags)
    print()
    if password == "-":
        pwcrypt = '-'
    else:
        pwcrypt = _crypt(password, userid)
    rec = uls.where('userid', userid, as_dict=True, index=True)
    if rec:
        pos = rec[0]['_IND_']
    else:
        pos = 0
    ans = input("Confermi modifica? ")
    ans = ans[:1].lower()
    if ans == 's':
        row = uls.get_row(0, as_dict=True, default='')
        row.update({'userid': userid, 'email': email, 'name': name, 'surname': surname,
                    'pw': pwcrypt, 'flags': flags})
        uls.insert_row(row, pos)
        uls.save()
        print(f"Record utente {userid} modificato")
    else:
        print("Nessuna modifica")

def signature(path):
    "Return sha256 signature for file"
    fname = os.path.join(*path)
    shsum = hashlib.sha256()
    try:
        with open(fname, mode='rb') as fds:
            shsum.update(fds.read())
    except Exception:
        return ''
    return shsum.hexdigest()

def setfield(thedir, userid, field, value):
    "imposta valore di un campo nel record di utente"
    uls = FTable((thedir, 'userlist.json'))
    user = uls.where('userid', userid, as_dict=True, index=True)
    if user:
        user = user[0]
        user[field] = value
        uls.insert_row(user, pos=0)
        uls.save()
        print(f"Utente {userid}. campo {field} fatto uguale a: {value}")
    else:
        print(f"L'utente {userid} non esiste")

def is_year(year):
    "verifica numero anno corretto"
    try:
        nyr = int(year)
    except Exception:
        return False
    return 2000 < nyr < 3000

def get_pratica(anno, num):
    'riporta la pratica indicata come dict'
    basedir = namebasedir(anno, num)
    return tb.jload((basedir, PRAT_JFILE))

def get_years(ddate):
    "trova elenco anni definiti"
    try:
        years = [x for x in os.listdir(ddate) if is_year(x)]
    except Exception:
        years = []
    return years

def namebasedir(anno, num):
    "genera path directory per nuova pratica"
    stanno = f'{int(anno):04d}'
    stnum = f'{int(num):06d}'
    basedir = os.path.join(DATADIR, stanno, stanno+'_'+stnum)
    return basedir

IS_PRAT_DIR = re.compile(r'\d{4}_\d{6}')   #  Seleziona directory per pratica

def remove(path, show_error=True):
    "Remove files"
    fullname = tb.getpath(path)
    try:
        os.unlink(fullname)
    except Exception as excp:
        if show_error:
            logging.error("Error removing file: %s [%s]", fullname, str(excp))
    else:
        logging.info("Removed file: %s", fullname)


def testlogin():
    "Test funzionamento login"
    print('Prova userid/password')
    userid = input("Userid: ")
    psw = getpass()
    thedir = checkdir()
    config = tb.jload((thedir, 'config.json'))
    ldap_host = config.get("ldap_host", "-")
    ldap_port = config.get("ldap_port", 0)
    try:
        update_userlist()
    except Exception:
        print()
        print("Lista utenti non accessibile\n")
        return
    ret, why = authenticate(userid, psw, ldap_host, ldap_port)
    if ret:
        print(f' - Accesso: OK [{why}]')
    else:
        print(f' - Accesso: NO [{why}]')

def show64file(filename):
    "Mostra file json codificato"
    f64 = os.path.join(DATADIR, filename)
    obj64 = tb.jload_b64(f64)
    print()
    print(obj64)

def protect(fpath):
    "set proper mode bits on given filepath"
    os.chmod(fpath, stat.S_IRUSR+stat.S_IWUSR)

def randstr(lng):
    "Genera stringa casuale di linghezzadata"
    return ''.join([random.choice(CHARS) for i in range(lng)])

def makepwfile(ldappw=False):
    "Crea file per password"
    pwpath = os.path.join(DATADIR, 'pwfile.json')
    pop3pw = input('password per accesso POP3: ')
    if not pop3pw:
        return
    pwdict = {'pop3_pw': pop3pw, 'secret_key': randstr(30)}
    if ldappw:
        managerpw = input('password per LDAP manager (accesso R/W): ')
        anonymouspw = input('password per LDAP anonimo (accesso R): ')
        pwdict['manager_pw'] = managerpw
        pwdict['anonymous_pw'] = anonymouspw
    tb.jsave_b64(pwpath, pwdict)
    protect(pwpath)

def input_anno():
    "Richiesta interattiva anno"
    year = input('Anno: ')
    if year:
        year = int(year)
    else:
        year = thisyear()
    return year

def showmaxdecis():
    "Trova massimo numero di decisione di contrarre"
    year = input_anno()
    ndet, prat = find_max_decis(year)
    print()
    print(f"Ultima edecisione di contrarre anno {year}: {ndet} (pratica: {prat})")

def showmaxprat():
    "Trova massimo numero di pratica"
    year = input_anno()
    prat = find_max_prat(year)
    print()
    print(f"Ultima pratica anno {year}: {prat}")

_EXTRACT = (NUMERO_PRATICA, DATA_RICHIESTA, NOME_RICHIEDENTE,
            NOME_RESPONSABILE, DESCRIZIONE_ACQUISTO)

def allfields(year=None):
    "Mostra tutti i campi nei file pratica.json con il numero di presenze"
    fields = {}
    for prat in PratIterator(year):
        pkeys = prat.keys()
        for key in pkeys:
            if key in fields:
                fields[key] += 1
            else:
                fields[key] = 1
    return fields

def allfieldvals(fields, year=None):
    "Mostra tutti le combinazioni di valori nei campi dati"
    uniq = set()
    for prat in PratIterator(year):
        values = [str(prat.get(f)) for f in fields]
        sval = ", ".join(values)
        uniq.add(sval)
    ret = list(uniq)
    ret.sort()
    return ret

def showallfields():
    "mostra tutti i campi nei file pratica"
    year = input_anno()
    print("Elenco di tutti i campi nei file pratica per l'anno", year)
    elenco = allfields(year)
    sortedk = list(elenco.keys())
    sortedk.sort()
    for field in sortedk:
        print(" -", field, " ", elenco[field])

def showusers():
    "Mostra lista utenti"
    thedir = checkdir()
    uls = FTable((thedir, 'userlist.json'))
    uls.sort("surname")

    for usr in uls:
        fname = f"{usr[2]}, {usr[3]} [{usr[1]}]"
        print(f"{fname:>42} {usr[4]:>30}  {usr[5]}")

def showvalues():
    "Elenca tutti i valori nei campi delle pratiche"
    year = input_anno()
    fields = []
    while True:
        field = input("Campo (Vuoto per terminare)? ").strip()
        if not field:
            break
        fields.append(field)
    vals = allfieldvals(fields, year)
    print(f"Elenco combinazioni valori nei campi: {', '.join(fields)} per l'anno {year}")
    for val in vals:
        print(" -", val)

def matching(key, klist):
    "Riporta gli elementi in klist che danno match positivo"
    if isinstance(key, int):
        return [x for x in klist if key == x]
    return [x for x in klist if key in x]

def showwhere():
    "Elenca pratiche con valore del campo dato"
    year = input_anno()
    while True:
        nome_campo = input("Nome del campo (anche incompleto): ")
        if nome_campo:
            break
    while True:
        val = input("Valore: ")
        if val:
            break
    mostra = input("Mostra anche: ")
    try:
        ival = int(val)
    except ValueError:
        pass
    else:
        val = ival
    for prat in PratIterator(year):
        fields = matching(nome_campo, prat.keys())
        vals = [prat.get(f) for f in fields]
        if matching(val, vals):
            altro = prat.get(mostra, "")
            print(prat.get("numero_pratica"), "-", altro)

def showdata(nprat):
    "Visualizza dati di una pratica"
    if nprat:
        print()
        year = input_anno()
        basedir = namebasedir(year, nprat)
        dati_pratica = tb.jload((basedir, PRAT_JFILE))
        pprint(dati_pratica, indent=4)
    else:
        print()
        print("Errore numero pratica:", nprat)

def showpratiche():
    "Mostra elenco pratiche"
    year = input_anno()
    print("Elenco pratiche per l'anno", year)
    elenco = DocList(DATADIR, 'pratica.json', year=year, extract=_EXTRACT)
    for rec in elenco.records:
        print(f" - {rec[NUMERO_PRATICA]} {rec[DATA_RICHIESTA]}",
              f"{rec[NOME_RICHIEDENTE]}/{rec[NOME_RESPONSABILE]}")
        print(f"   {rec[DESCRIZIONE_ACQUISTO]}")
    if elenco.errors:
        print("Errori di accesso alle pratiche:")
        for err in elenco.errors:
            print("  ", err)

def main():                                           # pylint: disable=R0912
    "Procedura per uso da linea di comando e test"
    if len(sys.argv) <= 1:
        print(version())
        print(__doc__)
        sys.exit()
    args = sys.argv[1:] + ['', '', '', '']

    verb = args[0]+'  '
    verb = verb[:2].lower()

    if verb == 'ac':
        testlogin()
    elif verb == 'al':
        showallfields()
    elif verb == 'nd':
        showmaxdecis()
    elif verb == 'np':
        showmaxprat()
    elif verb == 'pa':
        makepwfile(True)
    elif verb == 'pl':
        showpratiche()
    elif verb == 'pr':
        showdata(sys.argv[2])
    elif verb == 'sh':
        show64file('pwfile.json')
    elif verb == 'ul':
        showusers()
    elif verb == 'us':
        makeuser(sys.argv[2])
    elif verb == 'va':
        showvalues()
    elif verb == 'wh':
        showwhere()
    else:
        print(version())
        print(__doc__)
    sys.exit()

if __name__ == '__main__':
    main()
