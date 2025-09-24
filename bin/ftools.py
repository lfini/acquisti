"""
Tools per la procedura acquisti.py

Uso da linea di comando:
    python ftools.py access      - Test accesso con username/password
    python ftools.py all         - Elenca tutti i campi definiti in tutte le pratiche
    python ftools.py ddecis      - Trova num.decisione duplicati
    python ftools.py filt        - Test filtri per pratiche
    python ftools.py fulltest    - Esegue numerosi test (tutti quelli che è possibile fare
                                   automaticamente
    python ftools.py ldecis      - Genera files decisioni.lst (liste decisioni)
    python ftools.py ndecis      - Visualizza ultimo num. decisione di contrarre
    python ftools.py nprat       - Visualizza ultimo num. pratica
    python ftools.py pass        - Genera file per password
    python ftools.py plist       - Visualizza elenco pratiche
    python ftools.py prat nprat  - Visualizza File dati di una pratica
    python ftools.py show        - Mostra file per password
    python ftools.py steal nprat - "Ruba" pratica (sostituisce webmaster a richiedente,
                                   responsabile e RUP)
    python ftools.py tab         - Mostra tabelle degli stati
    python ftools.py ulist       - Visualizza lista utenti
    python ftools.py user uid    - Mostra/crea/modifica utente
    python ftools.py values      - Mostra tutti i valori del campo dato
    python ftools.py where       - Elenco pratiche con valore di campo dato
"""

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
import readline  # pylint: disable=W0611
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from logging import StreamHandler
from functools import reduce
from getpass import getpass
from collections import defaultdict

import ldap3
from Crypto.Cipher import AES
import pam

import constants as cs
from constants import CdP
import table as tb
import send_email as sm

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
# VERSION 5.1    8/4/2024 Nuova versione in produzione
# VERSION 5.2    8/4/2024 Corretto selezione pratiche (funzione trova_pratiche())
# VERSION 5.3    10/12/2024 Corretta diagnostica in authenticate()
#                           Aggiunti filtri per direttore vicario
# VERSION 5.4    20/01/2025 Modificato determinazione ultima decisione
# VERSION 5.4.1  21/01/2025 Corretto bug nel calcolo numero di pratica
#                           Corretto filtro di selezione pratica in attesa RUP
# VERSION 5.5    23/01/2025 Aggiunto test estensivo
# VERSION 5.6    23/01/2025 Aggiunta funzione "steal"
# VERSION 5.7    23/01/2025 Aggiunta funzione mostra tabelle di stati
# VERSION 5.8    25/04/2025 Modificata funzione "remove"
# VERSION 5.9    10/06/2025 Corretto bug nella selezione delle pratiche annullate

__author__ = "Luca Fini"
__version__ = "5.9"
__date__ = "10/06/2025"

# pylint: disable=C0302, W0718

if hasattr(pam, "authenticate"):  # Arrangia per diverse versioni del modulo pam
    PAM_AUTH = pam.authenticate
else:
    PAM_AUTH = pam.pam().authenticate

USER_DN = "uid=%s,ou=people,dc=inaf,dc=it"

STEAL_WARN = """
Attenzione: stai cambiando richiedente, responsable e RUP della
            pratica N. {}.
"""


class GlobLists:  # pylint: disable=R0903
    "Liste usate dalla procedura. Definite in fase di inizializzazione"
    USERLIST = None
    CODFLIST = None
    HELPLIST = []


class MyException(RuntimeError):
    "Exception arricchita"


class GMailHandler(StreamHandler):  # pylint: disable=R0903
    "Logging handler che usa GMail API"

    def __init__(self, fromaddr, toaddr, subject):
        super().__init__()
        self.fromaddr = fromaddr
        self.dest = [toaddr]
        self.subject = subject

    def emit(self, record):
        "Invia messaggio di log via GMail"
        try:
            sm.send(
                "", None, self.fromaddr, self.dest, self.subject, self.format(record)
            )
        except Exception as excp:
            _last_resort_log(f"Errore invio email a: {self.dest}\n- {excp}")


########################################## Table support
class FTable(tb.Table):
    "definizione tabelle con estensioni per rendering HTML"

    def __init__(self, path, header=None, sortable=()):
        tb.Table.__init__(self, path, header)
        self.sortable = [x for x in sortable if x in self.header]

    def render_item_as_form(  # pylint: disable=R0913,R0917
        self,
        title,
        form,
        action,
        nrow=0,
        ignore=(),
        errors=(),
    ):
        "HTML rendering di un campo per uso in un form"
        html = [cs.TABLE_HEADER]
        if title:
            html.append(f"<h1> {title} </h1>")
        if errors:
            html.append("<hr><b><font color=red>Attenzione:</font></b><br />")
            for err in errors:
                html.append("&nbsp;&nbsp; - " + err + "<br />")
            html.append("<hr>")
        html.append(f'<form method="POST" action="{action}">')
        if nrow > 0:
            html.append(f"<b>Record N. {nrow}</b><p>")
        html.append("<dl>")
        for fname in self.header[1:]:
            if fname in ignore:
                continue
            val = str(form[fname])
            html.append(f"<dt> {form[fname].label} <dd> {val}")
        html.append("</dl>")
        html.append(str(form["annulla"]) + "&nbsp;&nbsp;" + str(form["avanti"]))
        if nrow > 0:
            html.append("<hr>" + str(form["cancella"]))
        html.append("</form>")
        return "\n".join(html)

    def render_item_as_text(self, title, nrow, index=False):
        "HTML rendering di un campo"
        html = [cs.TABLE_HEADER]
        if title:
            html.append(f"<h1> {title} </h1>")
        if index:
            fields = self.header
        else:
            fields = self.header[1:]
        row = self.get_row(nrow, index=index, as_dict=True)
        html.append(f"<b>Record N. {nrow}</b><p>")
        html.append("<dl>")
        for fld in fields:
            val = row[fld]
            html.append(f"<dt> {fld} <dd> {val}")
        html.append("</dl>")
        return "\n".join(html)

    def render(        # pylint: disable=R0912,R0913,R0914,R0917
        self,
        title=None,
        menu=(),
        select_url=(),
        sort_url=(),
        edit_symb=cs.EDIT_SYMB,
        index=False,
        sort_on=1,
        footer="",
        select=None,
        messages=(),
    ):
        "HTML rendering della tabella"

        def _formrow(row):
            dname = row[0]
            ret = f'<tr><td><a href="{select_url[0]}/{dname}">{edit_symb}</a></td><td>'
            return ret + "</td><td>".join([str(r) for r in row[1:]]) + "</td></tr>"

        def _fullrow(row):
            return "<tr><td>" + "</td><td>".join([str(r) for r in row]) + "</td></tr>"

        def _shortrow(row):
            return (
                "<tr><td>" + "</td><td>".join([str(r) for r in row[1:]]) + "</td></tr>"
            )

        def _fmtheader(name):
            uname = str(name)
            if uname in self.sortable and sort_url:
                uname = (
                    uname
                    + "&nbsp;&nbsp;<a href="
                    + sort_url[0]
                    + "/"
                    + uname
                    + ">"
                    + sort_url[1]
                    + "</a>"
                )
            return "<th>" + uname + "</th>"

        html = [cs.TABLE_HEADER]
        if title:
            html.append(f"<h1> {title} </h1>")
        if messages:
            html.append("<hr>")
            for msg in messages:
                html.append(f"<p> {msg} </p>")
            html.append("<hr>")
        render_menu = []
        for mnu in menu:
            render_menu.append(f'<a href="{mnu[0]}">{mnu[1]}</a>')
        if render_menu:
            html.append("&nbsp;|&nbsp".join(render_menu))
        if select_url:
            html.append(f"<hr>{select_url[1]}")
        if select_url:
            dorow = _formrow
            fields = ["&nbsp;"] + self.header[1:]
        elif index:
            dorow = _fullrow
            fields = ["&nbsp;"] + self.header[1:]
        else:
            dorow = _shortrow
            fields = self.header[1:]
        html.append(
            "<table border=1><tr>"
            + reduce(lambda x, y: str(x) + _fmtheader(y), fields, "")
            + "</tr>"
        )
        self.sort(sort_on)
        if select:
            allrows = [x for x in self.rows if select(x)]
        else:
            allrows = self.rows
        for row in allrows:
            html.append(dorow(row))
        html.append("</table>")
        if footer:
            html.append(f"<center><font size=1>{footer}</font></center>")
        return "\n".join(html)


########################################## End table support


class Matchty:  # pylint: disable=R0903
    "classe per verificare il corretto tipo di un file"

    def __init__(self, tlist):
        def addp(name):
            "normalizza nome estensione"
            if name[0] != ".":
                name = "." + name
            return name.lower()

        self.tlist = [addp(t) for t in tlist]

    def check(self, name):
        "verifica estensione"
        ext = os.path.splitext(name)[1]
        return ext.lower() in self.tlist


class DocList:  # pylint: disable=R0903
    "definizione lista documenti"

    def __init__(      # pylint: disable=R0913,R0917
        self,
        thedir,
        fname,
        year=None,
        directory_filter=lambda x: True,
        filename_filter=lambda x: True,
        content_filter=lambda x: True,
        sort=None,
        extract=None,
    ):
        self.years = get_years(thedir)  # Rendi noto quali altri
        self.years.sort()  # anni sono disponibili
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
                        rec = {
                            key: value for key, value in rec.items() if key in extract
                        }
                    self.records.append(rec)
        if sort:
            self.records.sort(key=sort)

    def __len__(self):
        "metodo standard per lunghezza"
        return len(self.records)

    def __iter__(self):
        return self.records.__iter__()


class PratIterator:
    "Iteratore sulle pratiche dell'anno specificato"

    def __init__(self, year=None):
        if not year:
            year = thisyear()
        self.ydir = os.path.join(cs.DATADIR, str(year))
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


CHARS = string.ascii_letters + string.digits

NON_ABILITATO = """
non sei abilitato all'uso della procedura come "%s".
Per ottenere l'abilitazione devi rivolgerti all'amministrazione
"""


def checkdir():
    "Verifica esistenza della directory per dati e riporta il path"
    thedir = cs.DATADIR
    if not os.path.exists(thedir):
        print()
        print(f"Directory {thedir} inesistente")
        print("\nDevi creare le directory di lavoro\n")
        sys.exit()
    return thedir


CONFIG = tb.jload((checkdir(), "config.json"))


def _last_resort_log(message):
    "funzione chamata quando c'è un errore nel logger"
    fname = os.path.join(cs.WORKDIR, time.strftime("%Y-%m-%dT%H:%M:%S.lrl"))
    with open(fname, "a", encoding="utf8") as f_out:
        print(message, file=f_out)


class MyFormatter(logging.Formatter):
    "formatter per logging"
    remote = "-"
    userid = "-"

    def format(self, record):
        if not record.msg.startswith("["):
            record.msg = f"[{MyFormatter.remote}:{MyFormatter.userid}] " + record.msg
        ret = super().format(record)
        return ret


def set_log_context(remote, userid):
    "Imposta contesto per logger"
    MyFormatter.remote = remote
    MyFormatter.userid = userid


def set_logger(applogger, path, sender, recipient, subject):
    "imposta logger su file e via mail"
    fpath = os.path.join(*path)
    formatter = MyFormatter("%(asctime)s %(levelname)s %(message)s")
    hndl = RotatingFileHandler(fpath, maxBytes=1000000, backupCount=3, encoding="utf8")
    hndl.setLevel(logging.INFO)
    hndl.setFormatter(formatter)
    applogger.addHandler(hndl)

    hndl = GMailHandler(sender, recipient, subject)
    hndl.setLevel(logging.ERROR)
    hndl.setFormatter(formatter)
    applogger.addHandler(hndl)
    applogger.info("Abilitato log errori via GMail")


I16 = b"1ZxqYcE4LjMc72oy"
P24 = "xyCjhWT3fPtOel5MN02RDUYE"


def encrypt(plaintext, passw=""):
    "codifica una stringa con password"
    _pwd = (passw + P24).encode("utf8")[:24]
    obj = AES.new(_pwd, AES.MODE_CFB, I16)
    return obj.encrypt(plaintext.encode("utf8"))


def decrypt(ciphertext, passw=""):
    "decodifica una stringa con password"
    _pwd = (passw + P24).encode("utf8")[:24]
    obj = AES.new(_pwd, AES.MODE_CFB, I16)
    return obj.decrypt(bytes(ciphertext)).decode("utf8")


def ldap_authenticate(userid, password, server_ip, server_port, timeout=10):
    """Autenticazione ID/Password da server LDAP.
    Ritorno: -1 (errore LDAP), 0 id/pw non validi, 1 id/pw validi"""
    if server_ip in ("", "-"):
        return 0
    server = ldap3.Server(server_ip, port=int(server_port), connect_timeout=timeout)
    conn = ldap3.Connection(server, USER_DN % userid, password)
    try:
        auth = conn.bind()
    except ldap3.core.exceptions.LDAPExceptionError:
        return -1
    if auth:
        return 1
    return 0


def send_email(  # pylint: disable=R0913,R0917
    mailhost,
    sender,
    recipients,
    subj,
    body,
    attach=None,
    debug_addr="",
):
    "Invio messaggio e-mail"
    if debug_addr:
        warning = f"MODO DEBUG - destinatari originali: {', '.join(recipients)}\n\n"
        message = warning + body
        dest = [debug_addr]
        subjd = subj + " (DEBUG)"
    else:
        message = body
        dest = recipients
        subjd = subj
    if mailhost.strip() == "-":
        mailhost = None
    sm.send(mailhost, None, sender, dest, subjd, message, attach)


LETTERS = "ABCDEFGHIJKLMNOPQRTSUVWXYZ"


def byinitial(inlist, key=lambda x: x, remove_empty=True):
    "Returns inlist organized by Initial"

    byin = {l: [] for l in LETTERS + "~"}

    for user in inlist:
        letter = key(user)[0].upper()
        if letter not in LETTERS:
            letter = "~"
        byin[letter].append(user)

    if remove_empty:
        to_remove = [idx for idx in byin if not byin[idx]]
        for idx in to_remove:
            del byin[idx]

    for idx in byin:
        byin[idx].sort(key=key)
    return byin


def find_max_prat(year=None):
    "Cerca il massimo valore del numero pratica"
    if not year:
        year = thisyear()
    yys = f"{year}"
    dpath = os.path.join(cs.DATADIR, yys)
    if not os.path.exists(dpath):
        return 0
    try:
        plist = [x for x in os.listdir(dpath) if x.startswith(yys)]
    except Exception:
        return 0
    if not plist:
        return 0
    plist.sort()
    prat = int(plist[-1].split("_")[1])
    return prat


def _find_max_field(what, year=None):
    "Cerca il massimo valore del campo specificato (della forma: nnn/yyyy)"
    if not year:
        year = thisyear()
    if not isinstance(what, (list, tuple)):
        what = (what,)
    yys = f"{year}"
    dpath = os.path.join(cs.DATADIR, yys)
    try:
        plist = os.listdir(dpath)
    except Exception:
        plist = []
    maxfld = 0
    prat = ""
    for nprat in plist:
        path = os.path.join(dpath, nprat)
        dati_pratica = tb.jload((path, "pratica.json"))
        for item in what:
            value = dati_pratica.get(item)
            try:
                nnyy = value.split("/")
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


def find_all_decis(year=None):
    "legge lista decisioni"
    if not year:
        year = thisyear()
    yys = f"{year}"
    dpath = os.path.join(cs.DATADIR, yys, cs.DECIS_FILE)
    dlist = []
    with open(dpath, encoding="utf8") as f_in:
        for line in f_in:
            splt = line.split()
            dlist.append((int(splt[0]), splt[1], splt[2]))
    return dlist


def find_max_decis(year=None):
    "Cerca il massimo valore del numero decisione di contrarre"
    dlist = find_all_decis(year)
    dlist.sort(key=lambda x: x[0])
    if dlist:
        return dlist[-1]
    return 0, "", ""


def find_dup_decis(year=None):
    "trova duplicati in lista decisioni"
    dlist = find_all_decis(year)
    ddict = defaultdict(list)
    for ndecis, date, nprat in dlist:
        ddict[ndecis].append((ndecis, date, nprat))
    dupl = [ddict[x] for x in ddict if len(ddict[x]) > 1]
    dupl = [x for y in dupl for x in y]
    return dupl


def check_dupl_decis(ndecis, year=None):
    "verifica se numero di decisione risulta duplicato"
    dlist = [x[0] for x in find_dup_decis(year)]
    return ndecis in dlist


def savedecis(prat, year):
    "salva nuovo numero di decisione"
    yys = str(year)
    dpath = os.path.join(cs.DATADIR, yys, cs.DECIS_FILE)
    ndec = int(prat[cs.NUMERO_DECISIONE].split("/")[0])
    with open(dpath, "a", encoding="utf8") as f_out:
        print(
            cs.DECIS_FMT.format(
                ndecis=ndec, date=prat[cs.DATA_DECISIONE], nprat=prat[cs.NUMERO_PRATICA]
            ),
            file=f_out,
        )


def clean_locks(datadir):
    "Rimuove lock file 'zombi'"
    tree = os.walk(datadir)
    for dpath, _unused, fnames in tree:
        for name in fnames:
            if name[-5:] == ".lock":
                lockfile = os.path.join(dpath, name)
                os.unlink(lockfile)


def host(url):
    "Estrae la porzione 'host' da una URL"
    splt = url.split(":")
    return ":".join(splt[0:2])


def html_escape(strng):
    "Semplice escape per stringhe HTML"
    strng = strng.replace("&", "&amp;")  # Must be first
    strng = strng.replace("<", "&lt;")
    strng = strng.replace(">", "&gt;")
    return strng


def html_params(params, escape=True):
    "Converte un dict in stringa con sintassi HTML"
    if escape:
        filt = html_escape
    else:
        filt = lambda x: x  # pylint: disable=C3001
    parlist = []
    for key, value in params.items():
        parlist.append(f"{key}={filt(value)}")
    return " ".join(parlist)


def today(fulltime=True):
    "Riporta data odierna"
    if fulltime:
        return time.strftime("%d/%m/%Y %H:%M:%S")
    return time.strftime("%d/%m/%Y")


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


def internal_error(msg=""):
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
    if basedir:
        files = os.listdir(basedir)
        return [x for x in files if x.startswith(prefix)]
    return []


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
    os.makedirs(thedir, 0o740)
    return thedir


def spawn(command, inp=None):
    "Lancia comando dato"
    with subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as sbp:
        stdoutdata, stderrdata = sbp.communicate(inp)
    return (stdoutdata, stderrdata)


def procinfo():
    "Riporta informazioni sulprocesso"
    unm = os.uname()
    pyv = sys.version_info
    ret = [
        ("User", pwd.getpwuid(os.getuid())[0]),
        ("PID", str(os.getpid())),
        ("OS", f"{unm[0]}-{unm[4]} {unm[2]}"),
        ("Python", f"{pyv[0]}.{pyv[1]}.{pyv[2]}"),
    ]
    return ret


def swapname(name):
    "Scambia 'cognome, nome' e riporta 'nome, cognome'"
    spn = name.split(", ")
    if len(spn) == 2:
        ret = f"{spn[1].strip()} {spn[0].strip()}"
    else:
        ret = name
    return ret


def get_user(userid):
    "Riporta record di utente"
    usr = GlobLists.USERLIST.where("userid", userid, as_dict=True)
    if usr:
        ret = usr[0]
        ret["email"] = ret["email"].strip()
        return ret
    return {}


def _fullname(email):
    "Riporta il nome completo di utente, dato indirizzo e-mail"
    rec = GlobLists.USERLIST.where("email", email)
    if rec:
        return rec[0][5]
    return "Sconosciuto"


def _read_userlist():
    "Legge la lista utenti"
    GlobLists.USERLIST = FTable((cs.DATADIR, "userlist.json"))
    if GlobLists.USERLIST.empty():
        raise RuntimeError(f"Errore lettura userlist: {GlobLists.USERLIST.filename}")
    user_sn = GlobLists.USERLIST.columns((2, 3))
    user_fn = [f"{x[0]} {x[1]}" for x in user_sn]
    GlobLists.USERLIST.add_column(6, "fullname", column=user_fn)


def update_userlist():
    "Aggiorna la lista utenti"
    if not GlobLists.USERLIST:
        _read_userlist()
        return
    if GlobLists.USERLIST.needs_update():
        _read_userlist()


def _read_codflist():
    "Legge la lista dei codici Fu.Ob."
    GlobLists.CODFLIST = FTable((cs.DATADIR, "codf.json"))
    if GlobLists.CODFLIST.empty():
        raise RuntimeError(
            f"Errore lettura lista codici fondi: {GlobLists.CODFLIST.filename}"
        )
        # Integrazione codflist (aggiunge nome esteso)
    resp_em = GlobLists.CODFLIST.column(4)
    resp_names = [_fullname(x) for x in resp_em]
    GlobLists.CODFLIST.add_column(1, "nome_Responsabile", column=resp_names)


def update_codflist():
    "Aggiorna la lista dei codici Fu.Ob."
    if not GlobLists.CODFLIST:
        _read_codflist()
        return
    if GlobLists.CODFLIST.needs_update():
        _read_codflist()


def init_helplist():
    "Genera una lista dei file di nome 'help_*.html' nella directory dei file ausiliari"
    _helpfilt = re.compile("help_.+[.]html")
    try:
        flst = os.listdir(cs.FILEDIR)
    except Exception:
        GlobLists.HELPLIST = []
    else:
        GlobLists.HELPLIST = [x[5:-5] for x in flst if _helpfilt.match(x)]


def _crypt(username, passw):
    "rimpiazzo di crypt.crypt (deprecato)"
    return base64.b64encode(encrypt(username, passw)).decode("ascii")


def authenticate(userid, password, ldap_host, ldap_port):  # pylint: disable=R0911
    "Autenticazione utente. ldap: indirizzo IP server LDAP, o vuoto"
    user = get_user(userid)
    if not user:
        return False, NON_ABILITATO % userid
    if (pswd := user.get("pw")) != "-":
        if _crypt(password, userid) == pswd:
            return True, "Accesso autorizzato (CRYPT)"
    auth_ok = PAM_AUTH(userid, password)
    if auth_ok:
        return True, "Accesso autorizzato (PAM)"
    if ldap_host:
        ret = ldap_authenticate(userid, password, ldap_host, ldap_port)
        if ret < 0:
            return False, "Errore di connessione al server LDAP"
        if ret > 0:
            return True, "Accesso autorizzato (LDAP)"
    return False, "Errore ID/Password"


def makeuser(userid):  # pylint: disable=R0912,R0915
    "Crea record di utente"
    thedir = checkdir()
    header = ["userid", "surname", "name", "email", "flags", "pw"]
    uls = FTable((thedir, "userlist.json"), header)

    print()
    user = uls.where("userid", userid)
    if user:
        user = user[0]
        print()
        print("Dati per l'utente:", userid)
        print(" -                         Nome: " + user[2])
        print(" -                      Cognome: " + user[1])
        print(" -                        Email: " + user[3])
        print(" - Password ('-': usa PAM/LDAP): " + user[5])
        print(" -                    Privilegi: " + user[4])
        print()
        print("Legenda privilegi: A, amministrazione; D, developer; L, modifica LDAP")
        print()
        ans = input("Modificare/Cancellare utente [m/c]? ")
        ans = ans[:1].lower()
        if ans == "c":
            ans = input(
                f"Confermi cancellazione utente {user[2]} {user[1]}, [{userid}]? "
            )
            ans = ans[:1].lower()
            if ans == "s":
                rec = uls.where("userid", userid, index=True)
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
        pwcrypt = "-"
    else:
        pwcrypt = _crypt(password, userid)
    rec = uls.where("userid", userid, as_dict=True, index=True)
    if rec:
        pos = rec[0]["_IND_"]
    else:
        pos = 0
    ans = input("Confermi modifica? ")
    ans = ans[:1].lower()
    if ans == "s":
        row = uls.get_row(0, as_dict=True, default="")
        row.update(
            {
                "userid": userid,
                "email": email,
                "name": name,
                "surname": surname,
                "pw": pwcrypt,
                "flags": flags,
            }
        )
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
        with open(fname, mode="rb") as fds:
            shsum.update(fds.read())
    except Exception:
        return ""
    return shsum.hexdigest()


def setfield(thedir, userid, field, value):
    "imposta valore di un campo nel record di utente"
    uls = FTable((thedir, "userlist.json"))
    user = uls.where("userid", userid, as_dict=True, index=True)
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
    "riporta la pratica indicata come dict"
    basedir = namebasedir(anno, num)
    return tb.jload((basedir, cs.PRAT_JFILE))


def get_years(ddate):
    "trova elenco anni definiti"
    try:
        years = [x for x in os.listdir(ddate) if is_year(x)]
    except Exception:
        years = []
    return years


def namebasedir(anno, num):
    "genera path directory per nuova pratica"
    stanno = f"{int(anno):04d}"
    stnum = f"{int(num):06d}"
    basedir = os.path.join(cs.DATADIR, stanno, stanno + "_" + stnum)
    return basedir


IS_PRAT_DIR = re.compile(r"\d{4}_\d{6}")  #  Seleziona directory per pratica


def file_search(basename):
    "cerca file con dato basename"
    thedir, name = os.path.split(basename)
    found = [x for x in os.listdir(thedir) if x.startswith(name)]
    if found:
        return os.path.join(thedir, found[0])
    return None


def remove(path, prefix=False):
    "Remove files ignora FileNotFoudError. prefix==True: nome file senza estensione"
    fullbasename = tb.getpath(path)
    if prefix:
        fullname = file_search(fullbasename)
        if fullname is None:
            return f"FileNotFoud: {fullbasename}.*"
    else:
        fullname = fullbasename
    try:
        os.unlink(fullname)
    except FileNotFoundError:
        return f"FileNotFoud: {fullname}"
    return f"Rimosso file: {fullname}"


def testlogin():
    "Test funzionamento login"
    print("Prova userid/password")
    userid = input("Userid: ")
    psw = getpass()
    thedir = checkdir()
    config = tb.jload((thedir, "config.json"))
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
        print(f" - Accesso: OK [{why}]")
    else:
        print(f" - Accesso: NO [{why}]")


def show64file(filename):
    "Mostra file json codificato"
    f64 = os.path.join(cs.DATADIR, filename)
    obj64 = tb.jload_b64(f64)
    print()
    print(obj64)


def steal(num):
    "ruba pratica"
    anno = input_anno()
    num = int(num)
    prat = get_pratica(anno, num)
    print(STEAL_WARN.format(prat[cs.NUMERO_PRATICA]))
    conf = input("Sei sicuro? ")
    if conf.lower().strip() not in "ys":
        return
    if cs.NOME_RICHIEDENTE in prat:
        prat[cs.NOME_RICHIEDENTE] = CONFIG[cs.NOME_WEBMASTER]
    if cs.NOME_RESPONSABILE in prat:
        prat[cs.NOME_RESPONSABILE] = CONFIG[cs.NOME_WEBMASTER]
    if cs.NOME_RUP in prat:
        prat[cs.NOME_RUP] = CONFIG[cs.NOME_WEBMASTER]
    if cs.EMAIL_RICHIEDENTE in prat:
        prat[cs.EMAIL_RICHIEDENTE] = CONFIG[cs.EMAIL_WEBMASTER]
    if cs.EMAIL_RESPONSABILE in prat:
        prat[cs.EMAIL_RESPONSABILE] = CONFIG[cs.EMAIL_WEBMASTER]
    if cs.EMAIL_RUP in prat:
        prat[cs.EMAIL_RUP] = CONFIG[cs.EMAIL_WEBMASTER]
    basedir = namebasedir(anno, num)
    tb.jsave((basedir, cs.PRAT_JFILE), prat)


def protect(fpath):
    "set proper mode bits on given filepath"
    os.chmod(fpath, stat.S_IRUSR + stat.S_IWUSR)


def randstr(lng):
    "Genera stringa casuale di linghezzadata"
    return "".join([random.choice(CHARS) for i in range(lng)])


def makepwfile(ldappw=False):
    "Crea file per password"
    pwpath = os.path.join(cs.DATADIR, "pwfile.json")
    pop3pw = input("password per accesso POP3: ")
    if not pop3pw:
        return
    pwdict = {"pop3_pw": pop3pw, "secret_key": randstr(30)}
    if ldappw:
        managerpw = input("password per LDAP manager (accesso R/W): ")
        anonymouspw = input("password per LDAP anonimo (accesso R): ")
        pwdict["manager_pw"] = managerpw
        pwdict["anonymous_pw"] = anonymouspw
    tb.jsave_b64(pwpath, pwdict)
    protect(pwpath)


def input_anno():
    "Richiesta interattiva anno"
    year = input("Anno: ")
    if year:
        year = int(year)
    else:
        year = thisyear()
    return year


def makelistdecis():
    "Genera files per lista decisioni"
    years = get_years(cs.DATADIR)
    ydict = defaultdict(list)
    for year in years:
        for prat in PratIterator(year):
            ndecis, date, nprat = (
                prat.get(cs.NUMERO_DECISIONE),
                prat.get(cs.DATA_DECISIONE),
                prat.get(cs.NUMERO_PRATICA),
            )
            if ndecis:
                num, anno = ndecis.split("/")
                ydict[anno].append((int(num), date, nprat))
    for year, ylist in ydict.items():
        ylist.sort(key=lambda x: x[0])
        yfile = os.path.join(cs.DATADIR, year, cs.DECIS_FILE)
        with open(yfile, "w", encoding="utf8") as f_out:
            for val in ylist:
                print(
                    cs.DECIS_FMT.format(ndecis=val[0], date=val[1], nprat=val[2]),
                    file=f_out,
                )
        print("Creato file:", yfile)


def duplistdecis():
    "trova duplicati in lista decisioni"
    year = input_anno()
    dupl = find_dup_decis(year)
    print("Duplicati in lista decisioni")
    for dup in dupl:
        print(" ", dup)


def showmaxdecis():
    "Trova massimo numero di decisione di contrarre"
    year = input_anno()
    ndet, date, prat = find_max_decis(year)
    print()
    print(
        f"Ultima edecisione di contrarre: {ndet}/{year} data: {date} (pratica: {prat})"
    )


def showmaxprat():
    "Trova massimo numero di pratica"
    year = input_anno()
    prat = find_max_prat(year)
    print()
    print(f"Ultima pratica anno {year}: {prat}")


_EXTRACT = (
    cs.NUMERO_PRATICA,
    cs.DATA_PRATICA,
    cs.NOME_RICHIEDENTE,
    cs.NOME_RESPONSABILE,
    cs.DESCRIZIONE_ACQUISTO,
)


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


def allfieldvals(field, year=None):
    "lista dei valori di un campo dato per l'anno"
    values = [
        (p.get(cs.NUMERO_PRATICA, ""), p.get(field, "")) for p in PratIterator(year)
    ]
    values.sort(key=lambda x: x[0])
    return values


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
    uls = FTable((thedir, "userlist.json"))
    uls.sort("surname")

    for usr in uls:
        fname = f"{usr[2]}, {usr[3]} [{usr[1]}]"
        print(f"{fname:>42} {usr[4]:>30}  {usr[5]}")


def showvalues():
    "Elenca tutti i valori nei campi delle pratiche"
    year = input_anno()
    field = input("Campo? ").strip()
    if not field:
        return
    vals = allfieldvals(field, year)
    print(f"  N.prat, {field}")
    for val in vals:
        print("  ", val)


def _int(item):
    "funzione ausiliaria per sort pratiche"
    nprat = item.get(cs.NUMERO_PRATICA, "0/0").split("/")[0]
    return int(nprat)


PRAT_APE = "Elenco pratiche aperte "
PRAT_CHI = "Elenco pratiche chiuse "
PRAT_APP = "Elenco pratiche approvate "
PRAT_DAP = "Elenco pratiche da approvare "
PRAT_NOR = "Elenco pratiche in attesa di indicazione del RUP"

FILTRI = {
    "ALL_A/ALL_C": "pratica aperta/chiusa",
    "RIC_A/RIC_C": "pratica aperta/chiusa come richiedente",
    "RUP_A/RUP_C": "pratica aperta/chiusa come RUP",
    "RES_0/RES_1": "pratica da approvare/approvata come responsabile dei fondi",
    "DIR_0/DIR_1": "pratica da approvare/approvata come direttore",
    "VIC_0/VIC_1": "pratica da approvare/approvata come vicario",
    "NOR": "pratica in attesa indicazione RUP",
    "GEN": "seguono stringhe per: stato, richiedente, responsabile, RUP, descrizione",
}


# pylint: disable=C3001
def trova_pratiche_1(
    anno, filtro, user_email, ascendente=True
):  # pylint: disable=R0912,R0911,R0915
    "genera lista pratiche in base ai filtri definiti"
    sort_f = _int if ascendente else lambda x: -_int(x)
    oper = filtro[:3]
    if oper == "ALL":  # Lista pratiche aperte/chiuse
        if filtro[-1] == "A":
            filtro = lambda x: x.get(cs.PRATICA_APERTA)
            title = PRAT_APE
        else:
            filtro = lambda x: not x.get(cs.PRATICA_APERTA)
            title = PRAT_CHI
        return (
            DocList(
                cs.DATADIR, cs.PRAT_JFILE, anno, content_filter=filtro, sort=sort_f
            ),
            title,
        )
    if oper == "RIC":  # Lista pratiche aperte/chiuse come richiedente
        str_ruolo = "come richiedente"
        if filtro[-1] == "A":  # pratica aperta
            filtro = lambda x: x.get(cs.EMAIL_RICHIEDENTE) == user_email and x.get(
                cs.PRATICA_APERTA
            )
            title = PRAT_APE + str_ruolo
        else:  # pratica chiusa
            filtro = lambda x: x.get(cs.EMAIL_RICHIEDENTE) == user_email and not x.get(
                cs.PRATICA_APERTA
            )
            title = PRAT_CHI + str_ruolo
        return (
            DocList(
                cs.DATADIR, cs.PRAT_JFILE, anno, content_filter=filtro, sort=sort_f
            ),
            title,
        )
    if oper == "RES":  # Lista pratiche da approvare/approvate come resp. fondi
        str_ruolo = "come responsabile dei fondi"
        if filtro[-1] == "0":  # pratica da approvare
            filtro = (
                lambda x: x.get(cs.EMAIL_RESPONSABILE) == user_email
                and x.get(cs.TAB_PASSI, [0])[-1] == CdP.PIR
            )
            title = PRAT_DAP + str_ruolo
        else:  # pratica approvata
            filtro = (
                lambda x: x.get(cs.EMAIL_RESPONSABILE) == user_email
                and x.get(cs.TAB_PASSI, [0])[-1] >= CdP.PAR
            )
            title = PRAT_APP + str_ruolo
        return (
            DocList(
                cs.DATADIR, cs.PRAT_JFILE, anno, content_filter=filtro, sort=sort_f
            ),
            title,
        )
    if oper == "RUP":  # Lista pratiche aperte/chiuse come RUP
        str_ruolo = "come RUP"
        if filtro[-1] == "A":
            filtro = lambda x: x.get(cs.EMAIL_RUP) == user_email and x.get(
                cs.PRATICA_APERTA
            )
            title = PRAT_APE + str_ruolo
        else:
            filtro = lambda x: x.get(cs.EMAIL_RUP) == user_email and not x.get(
                cs.PRATICA_APERTA
            )
            title = PRAT_CHI + str_ruolo
        return (
            DocList(
                cs.DATADIR, cs.PRAT_JFILE, anno, content_filter=filtro, sort=sort_f
            ),
            title,
        )
    if oper == "VIC":  # Lista pratiche da autorizzare/autorizzate dal Direttore vicario
        str_ruolo = "dal Direttore vicario"
        if filtro[-1] == "1":
            filtro = (
                lambda x: x.get(cs.RUP_FIRMA_VICARIO)
                and x.get(cs.TAB_PASSI, [0])[-1] > CdP.IRD
            )
            title = PRAT_APP + str_ruolo
        else:
            filtro = (
                lambda x: x.get(cs.RUP_FIRMA_VICARIO)
                and x.get(cs.TAB_PASSI, [0])[-1] == CdP.IRD
            )
            title = PRAT_DAP + str_ruolo
        return (
            DocList(
                cs.DATADIR, cs.PRAT_JFILE, anno, content_filter=filtro, sort=sort_f
            ),
            title,
        )
    if oper == "DIR":  # Lista pratiche da autorizzare/autorizzate dal Direttore
        str_ruolo = "dal Direttore"
        if filtro[-1] == "1":
            filtro = lambda x: x.get(cs.TAB_PASSI, [0])[-1] >= CdP.AUD
            title = PRAT_APP + str_ruolo
        else:
            filtro = lambda x: x.get(cs.TAB_PASSI, [0])[-1] == CdP.IRD
            title = PRAT_DAP + str_ruolo
        return (
            DocList(
                cs.DATADIR, cs.PRAT_JFILE, anno, content_filter=filtro, sort=sort_f
            ),
            title,
        )
    if oper == "NOR":  # Lista pratiche in attesa di indicazione del RUP
        title = PRAT_NOR
        filtro = lambda x: not x.get(cs.EMAIL_RUP, "") and x.get(cs.PRATICA_APERTA)
    else:
        raise RuntimeError(f"Operazione non valida in lista pratiche ({oper})")

    return (
        DocList(cs.DATADIR, cs.PRAT_JFILE, anno, content_filter=filtro, sort=sort_f),
        title,
    )


def trova_pratiche_2(  # pylint: disable=R0913,R0917
    anno,
    stato,
    match_rich,
    match_resp,
    match_rup,
    match_descr,
    ascendente=False,
):
    "genera lista pratiche con match parola parziali"
    sort_f = _int if ascendente else lambda x: -_int(x)
    match_list = []
    expr_list = []
    if stato.lower().startswith("a"):
        match_list.append(lambda x: x[cs.PRATICA_APERTA])
        expr_list.append("aperta")
    elif stato.lower().startswith("c"):
        match_list.append(lambda x: not x[cs.PRATICA_APERTA])
        expr_list.append("chiusa")
    elif stato.lower().startswith("n"):
        match_list.append(lambda x: (x.get(cs.TAB_PASSI, [None])[-1] == CdP.ANN))
        expr_list.append("annullata")
    if match_rich:
        match_rich = match_rich.lower()
        match_list.append(
            lambda x: match_rich in x.get(cs.NOME_RICHIEDENTE, "").lower()
        )
        expr_list.append(f"{match_rich} come richiedente")
    if match_resp:
        match_resp = match_resp.lower()
        match_list.append(
            lambda x: match_resp in x.get(cs.NOME_RESPONSABILE, "").lower()
        )
        expr_list.append(f"{match_resp} come responsabile")
    if match_rup:
        match_rup = match_rup.lower()
        match_list.append(lambda x: match_rup in x.get(cs.NOME_RUP, "").lower())
        expr_list.append(f"{match_rup} come RUP")
    if match_descr:
        match_descr = match_descr.lower()
        match_list.append(
            lambda x: match_descr in x.get(cs.DESCRIZIONE_ACQUISTO, "").lower()
        )
        expr_list.append(f"{match_descr} nella descrizione")
    log_expr = ", ".join(expr_list)

    def logical_and(x):
        "definìsce filtro su dati pratica"
        for func in match_list:
            if not func(x):
                return False
        return True

    print("FTOOLS title:", log_expr)
    return (
        DocList(
            cs.DATADIR, cs.PRAT_JFILE, anno, content_filter=logical_and, sort=sort_f
        ),
        log_expr,
    )


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
        dati_pratica = tb.jload((basedir, cs.PRAT_JFILE))
        pprint(dati_pratica, indent=4)
    else:
        print()
        print("Errore numero pratica:", nprat)


def showpratiche():
    "Mostra elenco pratiche"
    year = input_anno()
    print("Elenco pratiche per l'anno", year)
    elenco = DocList(cs.DATADIR, "pratica.json", year=year, extract=_EXTRACT)
    for rec in elenco.records:
        print(
            f" - {rec.get(cs.NUMERO_PRATICA, 'Num?')} {rec.get(cs.DATA_PRATICA, 'Data?')}",
            f"{rec.get(cs.NOME_RICHIEDENTE, 'Ric?')}/{rec.get(cs.NOME_RESPONSABILE, 'Resp?')}",
        )
        print(f"   {rec.get(cs.DESCRIZIONE_ACQUISTO, 'Descr?')}")
    if elenco.errors:
        print("Errori di accesso alle pratiche:")
        for err in elenco.errors:
            print("  ", err)


def filtra():
    "test lista pratiche con filtro"
    anno = input_anno()
    print()
    print("Filtri definiti:")
    for nome, descr in FILTRI.items():
        print(f"  {nome}: {descr}")
    filtro = input("Filtro? ")
    if filtro.startswith("GEN"):
        args = ([x.strip() for x in filtro[3:].split(",")] + ["", "", "", ""])[:5]
        prats, title = trova_pratiche_2(anno, *args)
    else:
        email = input("Email del ruolo (se necessario) ")
        prats, title = trova_pratiche_1(anno, filtro, email)
    print()
    print("Ricerca:", title)
    print(f"Selezionate {len(prats)} pratiche")
    ans = input("Vuoi vederle? ")
    if ans[:1].lower() in ("sy"):
        for prat in prats:
            print(
                f'N. {prat.get(cs.NUMERO_PRATICA, "?")} ',
                f'- {prat.get(cs.DATA_PRATICA, "?")} ',
                f'- Rich: {prat.get(cs.EMAIL_RICHIEDENTE, "?")}',
                f'- Resp: {prat.get(cs.EMAIL_RESPONSABILE, "?")}',
                f'- RUP: {prat.get(cs.EMAIL_RUP, "?")}',
            )


def fulltest():
    """
    Esegui tutti i test che possono essere fatti in automatico e che non
    modificano i dati
    """
    year = input_anno()
    uls = FTable((cs.DATADIR, "userlist.json"))
    uls.sort("surname")
    unum = random.randint(0, len(uls))
    user = uls.get_row(unum)
    print(f"** Utente N. {unum} su {len(uls)}:", user)
    elenco = DocList(cs.DATADIR, "pratica.json", year=year)
    print(f"** Recupero lista pratiche: trovate {len(elenco)} pratiche")
    if elenco.errors:
        print("** NOTA: trovati errori nella generazione della lista pratiche")
        for err in elenco.errors:
            print("   ", err)
    nprat = find_max_prat(year)
    print("** Ultimo numero pratica:", nprat)
    pnum = random.randint(1, len(elenco) + 1)
    basedir = namebasedir(year, pnum)
    d_prat = tb.jload((basedir, cs.PRAT_JFILE))
    print("**         Pratica: N. =", d_prat[cs.NUMERO_PRATICA])
    print("           Richiedente =", d_prat[cs.NOME_RICHIEDENTE])
    print("                  Data =", d_prat[cs.DATA_PRATICA])
    passo = d_prat[cs.TAB_PASSI][-1]
    print("                 Stato =", cs.TABELLA_PASSI[passo][0])
    ndet, date, prat = find_max_decis(year)
    print("** Ultima decisione N. =", ndet, f" (data: {date}, pratica: {prat})")


def showstates():
    "Mostra tabelle degli stati"
    tab = cs.TABELLA_PASSI
    for code, mode in cs.MENU_MOD_ACQ:
        print(f"----- {mode} -----")
        step = CdP.INI
        while True:
            if isinstance(step, dict):
                step = step[code]  # pylint: disable=E1136
            info = tab[step]
            print(" .", step, "-", info[0], "-->", info[2])
            if step == CdP.FIN:
                break
            step = info[4]


def main():  # pylint: disable=R0912
    "Procedura per uso da linea di comando e test"
    if len(sys.argv) <= 1:
        print(version())
        print(__doc__)
        sys.exit()
    args = sys.argv[1:] + ["", "", "", ""]

    verb = args[0] + "  "
    verb = verb[:2].lower()

    if verb == "ac":
        testlogin()
    elif verb == "al":
        showallfields()
    elif verb == "fi":
        filtra()
    elif verb == "fu":
        fulltest()
    elif verb == "dd":
        duplistdecis()
    elif verb == "ld":
        makelistdecis()
    elif verb == "nd":
        showmaxdecis()
    elif verb == "np":
        showmaxprat()
    elif verb == "pa":
        makepwfile(True)
    elif verb == "pl":
        showpratiche()
    elif verb == "pr":
        showdata(sys.argv[2])
    elif verb == "sh":
        show64file("pwfile.json")
    elif verb == "st":
        steal(sys.argv[2])
    elif verb == "ta":
        showstates()
    elif verb == "ul":
        showusers()
    elif verb == "us":
        makeuser(sys.argv[2])
    elif verb == "va":
        showvalues()
    elif verb == "wh":
        showwhere()
    else:
        print(version())
        print(__doc__)
    sys.exit()


if __name__ == "__main__":
    main()
