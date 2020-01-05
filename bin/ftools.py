"""
Tools per la procedura acqusti.py

Uso da linea di comando:
    python ftools.py access     - test username/password
    python ftools.py adm        - Assegna privilegi di amministratore a utente
    python ftools.py ndet       - Visualizza ultimo num. determina
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

import sys
import os
import time
import re
import crypt
import pwd
import smtplib
import hashlib
import string
import stat
import random
from pprint import pprint
import readline
import subprocess
from email.mime.text import MIMEText
import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
from functools import reduce

import ldap3
from Crypto.Cipher import AES
import pam

from constants import *
import table as tb   # Questa serve: non togliere!!
from table import jload, jsave, jload_b64, jsave_b64, Table, getpath
import latex

__author__ = 'Luca Fini'
__version__ = '4.4.1'
__date__ = '05/01/2020'

if hasattr(pam, 'authenticate'):      # Arrangia per diverse versioni del modulo pam
    PAM_AUTH = pam.authenticate
else:
    PAM_AUTH = pam.pam().authenticate

USERLIST = None
CODFLIST = None
HELPLIST = []

USER_DN = 'uid=%s,ou=people,dc=inaf,dc=it'

def pkgroot():
    "Riporta root directory del sistema"
    dpath = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(dpath, ".."))

def datapath():
    "Riporta il path della directory per i dati"
    return os.path.join(pkgroot(), "data")

def filepath():
    "Riporta il path della directory dei files ausiliari"
    return os.path.join(pkgroot(), "files")

def workpath():
    "Riporta il path della directory di lavoro"
    return os.path.join(pkgroot(), "work")

def version():
    "Riporta versione del modulo"
    return "ftools.py. Versione %s - %s, %s"%(__version__, __author__, __date__)

def _setformatter():
    logger = logging.getLogger()
    if not hasattr(logger, 'fHandler'):
        return
    fmtstr = '%(asctime)s '+ logger.host_info + ' ['+logger.user_info+'] %(levelname)s %(message)s'
    formatter = logging.Formatter(fmt=fmtstr)
    logger.fHandler.setFormatter(formatter)
    if hasattr(logger, 'eHandler'):
        logger.eHandler.setFormatter(formatter)

def set_file_logger(path, email=None):
    "imposta logger"

    logger = logging.getLogger()
    fpath = os.path.join(*path)
    hndl = RotatingFileHandler(fpath, maxBytes=10000000, backupCount=3, encoding='utf8')
    logger.fHandler = hndl
    logger.setLevel(logging.INFO)
    logger.host_info = 'x.x.x.x'
    logger.user_info = '----------'
    logger.addHandler(hndl)
    if email:
        ehndl = SMTPHandler(email['mailhost'], email['fromaddr'],
                            email['toaddrs'], email['subject'])
        ehndl.setLevel(logging.ERROR)
        logger.eHandler = ehndl
        logger.addHandler(ehndl)
    _setformatter()

def set_host_info(hostname):
    "Imposta informazioni host per logging"
    logger = logging.getLogger()
    hsplitted = hostname.split(':')
    logger.host_info = hsplitted[0]
    logger.user_info = '----------'
    _setformatter()

def set_user_info(userid):
    "Imposta informazioni utente per logging"
    logger = logging.getLogger()
    if userid:
        logger.user_info = userid
    else:
        logger.user_info = '----------'
    _setformatter()

I16 = '1ZxqYcE4LjMc72oy'
P24 = 'xyCjhWT3fPtOel5MN02RDUYE'

def encrypt(text, passw=""):
    "codifica una stringa con password"
    _pwd = (passw+P24).encode("utf8")[:24]
    obj = AES.new(_pwd, AES.MODE_CFB, I16)
    return list(obj.encrypt(text))

def decrypt(text, passw=""):
    "decodifica una stringa con password"
    _pwd = (passw+P24).encode("utf8")[:24]
    obj = AES.new(_pwd, AES.MODE_CFB, I16)
    return obj.decrypt(bytes(text)).decode("utf8")

def ldap_authenticate(userid, password, server_ip, server_port):
    """Autenticazione ID/Password da server LDAP.
Ritorno: -1 (errore LDAP), 0 id/pw non validi, 1 id/pw validi"""
    if server_ip in ("", "-"):
        return 0
    server = ldap3.Server(server_ip, port=int(server_port))
    conn = ldap3.Connection(server, USER_DN%userid, password)
    try:
        auth = conn.bind()
    except ldap3.core.exceptions.LDAPExceptionError:
        return -1
    if auth:
        return 1
    return 0

def send_email(mailhost, sender, recipients, subj, body, debug_addr=''):
    "Invio messaggio e-mail"
    if debug_addr:
        warning = "MODO DEBUG - destinatari originali: %s\n\n"%', '.join(recipients)
        message = warning+body
        dest = [debug_addr]
        subjd = ' (DEBUG)'
    else:
        message = body
        dest = recipients
        subjd = ''
    smtp = None
    try:
        msg = MIMEText(message.encode('utf8'), 'plain', 'utf8')
        msg['Subject'] = subj+subjd
        msg['From'] = sender
        smtp = smtplib.SMTP(mailhost)
        smtp.sendmail(sender, dest, msg.as_string())
    except Exception as excp:
        errmsg = "Sending mail to: %s - "%', '.join(recipients)+str(excp)
        logging.error(errmsg)
        ret = False
    else:
        ret = True
    if smtp:
        smtp.close()
    return ret

def _clean_resp_codes(rcod):
    "Rimuove codici approvazione scaduti"
    dpath = getpath(rcod)
    try:
        files = os.listdir(dpath)
    except Exception:
        return
    for fname in files:
        fpt = os.path.join(dpath, fname)
        ctime = os.path.getmtime(fpt)
        if time.time()-ctime > APPROVAL_EXPIRATION:
            logging.info("Rimosso file codice approvazione scaduto: %s", fname)
            os.unlink(fpt)

def get_resp_codes(thedir):
    "Crea lista codici di approvazione"
    dpath = os.path.join(thedir, 'approv')
    ret = {}
    try:
        ldir = os.listdir(dpath)
    except OSError:
        return ret
    for fname in ldir:
        code = os.path.splitext(fname)[0]
        fpath = os.path.join(dpath, fname)
        respdata = jload(fpath)
        ret[code] = respdata
    return ret

def set_resp_code(thedir, key, userid, prat, sgn):
    "Crea file con codice approvazione"
    dpath = [thedir, 'approv']
    dname = getpath(dpath)
    if not os.path.exists(dname):
        os.makedirs(dname)
    _clean_resp_codes(dname)
    fname = key+'.json'
    dpath.append(fname)
    ttm = time.asctime(time.localtime())
    jsave(dpath, [userid, prat, sgn, ttm])
    logging.info("Creato file codice approvazione: %s", fname)

def get_resp_code(thedir, key):
    "Trova codice di approvazione"
    tpath = [thedir, 'approv']
    _clean_resp_codes(tpath)
    fname = key+'.json'
    tpath.append(fname)
    return jload(tpath, [])

def del_resp_code(thedir, key):
    "Cancella codice di approvazione"
    fname = os.path.join(thedir, 'approv', key+'.json')
    try:
        os.unlink(fname)
    except Exception:
        pass
    else:
        logging.info("rimosso file codice approvazione: %s", fname)

LETTERS = 'ABCDEFGHIJKLMNOPQRTSUVWXYZ'

def byinitial(inlist, key=lambda x: x, remove_empty=True):
    "Rerturns inlist organized by Initial"

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

def stringa_valore(costo, lang):
    "generazione specifica della stringa valore per il costo del bene"
    importo = costo[IMPORTO].strip()
    valuta = costo[VALUTA].strip()
    iva = costo[IVA].strip()
    iva_free = costo[IVAFREE].strip()

    if not importo:
        return ""
    if valuta == EURO:
        vstr = "€"
    elif valuta == POUND:
        vstr = "£"
    elif valuta == DOLLAR:
        vstr = "$"
    elif valuta == SFR:
        vstr = "SFr"
    else:
        vstr = valuta
    if iva_free:
        istr = "("+iva_free+")"
    elif iva == IVAESENTE:
        istr = "(esente I.V.A.)" if lang == "it" else "(no V.A.T.)"
    elif iva == IVAINCL4:
        istr = "(I.V.A. 4% inclusa)" if lang == "it" else "(4% V.A.T. included)"
    elif iva == IVAINCL10:
        istr = "(I.V.A. 10% inclusa)" if lang == "it" else "(10% V.A.T. included)"
    elif iva == IVAINCL22:
        istr = "(I.V.A. 22% inclusa)" if lang == "it" else "(22% V.A.T. included)"
    elif iva == IVA4:
        istr = "+ I.V.A. 4%" if lang == "it" else "+ 4% V.A.T."
    elif iva == IVA10:
        istr = "+ I.V.A. 10%" if lang == "it" else "+ 10% V.A.T."
    elif iva == IVA22:
        istr = "+ I.V.A. 22%" if lang == "it" else "+ 22% V.A.T."
    else:
        istr = ''
    return importo+" "+vstr+" "+istr

def stringa_costo(costo, lang):
    "Generazione della stringa per il costo del bene"
    ret = stringa_valore(costo[COSTO], lang)
    if costo[MODO_TRASP] == SPECIFICARE:
        trasp = "(più trasporto: " if lang == "it" else "(plus shipping: "
        ret += trasp+stringa_valore(costo["costo_trasporto"], lang)+")"
    elif costo[MODO_TRASP] == TRASP_INC:   # trasporto incluso
        ret += ", incluso trasporto" if lang == "it" else ', shipping included'
    return ret


def find_max_prat(year=None):
    "Cerca il massimo valore del numero pratica"
    if not year:
        year = thisyear()
    yys = '%d'%year
    dpath = os.path.join(datapath(), yys)
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
    yys = '%d'%year
    dpath = os.path.join(datapath(), yys)
    try:
        plist = os.listdir(dpath)
    except Exception:
        plist = []
    maxfld = 0
    prat = ''
    for nprat in plist:
        path = os.path.join(dpath, nprat)
        try:
            dati_pratica = jload((path, 'pratica.json'))
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

def find_max_det(year=None):
    "Cerca il massimo valore del numero determina"
    return _find_max_field("numero_determina", year)


def clean_locks(datadir):
    "Rimuove lock file 'zombi'"
    tree = os.walk(datadir)
    for dpath, _unused, fnames in tree:
        for name in fnames:
            if name[-5:] == '.lock':
                lockfile = os.path.join(dpath, name)
                os.unlink(lockfile)

########################################## Table support
class FTable(Table):
    "definizione tabelle con estensioni per rendering HTML"
    def __init__(self, path, header=None, sortable=()):
        Table.__init__(self, path, header)
        self.sortable = [x for x in sortable if x in self.header]

    def render_item_as_form(self, title, form, action,
                            nrow=0, ignore=()):
        "HTML rendering di un campo per uso in un form"
        html = [TABLE_HEADER]
        if title:
            html.append('<h1> %s </h1>'%title)
        html.append('<form method="POST" action="%s">'%action)
        if nrow > 0:
            html.append('<b>Record N. %d</b><p>'%nrow)
        html.append('<dl>')
        for fname in self.header[1:]:
            if fname in ignore:
                continue
            val = str(form[fname])
            html.append('<dt> %s <dd> %s'%(form[fname].label, val))
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
            html.append('<h1> %s </h1>'%title)
        if index:
            fields = self.header
        else:
            fields = self.header[1:]
        row = self.get_row(nrow, index=index, as_dict=True)
        html.append('<b>Record N. %d</b><p>'%nrow)
        html.append('<dl>')
        for fld in fields:
            val = row[fld]
            html.append('<dt> %s <dd> %s'%(fld, val))
        html.append('</dl>')
        return '\n'.join(html)

    def render(self, title=None, menu=(), select_url=(), sort_url=(),
               edit_symb=EDIT_SYMB, index=False, sort_on=1, footer='',
               select=None, messages=()):
        "HTML rendering della tabella"
        def _formrow(row):
            dname = row[0]
            ret = '<tr><td><a href="%s/%d">%s</a></td><td>'%(select_url[0], dname, edit_symb)
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
            html.append('<h1> %s </h1>'%title)
        if messages:
            html.append('<hr>')
            for msg in messages:
                html.append('<p> %s </p>'%msg)
            html.append('<hr>')
        render_menu = []
        for mnu in menu:
            render_menu.append('<a href="%s">%s</a>'%tuple(mnu))
        if render_menu:
            html.append('%s'%'&nbsp;|&nbsp'.join(render_menu))
        if select_url:
            html.append('<hr>%s'%select_url[1])
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
            html.append('<center><font size=1>%s</font></center>'%footer)

        return '\n'.join(html)

########################################## End table support

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
        parlist.append('%s="%s"'%(key, filt(value)))
    return ' '.join(parlist)

def login_check(session):
    "Verifica avvenuto login e set informazioni per logger"
    if 'userid' in session:
        user = get_user(session['userid'])
    else:
        return {}
    set_user_info(user.get('userid'))
    return user

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

NUMB_RE = re.compile("\\d+(,\\d+)?$")
def is_number(number):
    "Verifica che il campo sia un numero nella forma: 111[,222]"
    try:
        isnumb = NUMB_RE.match(number)
    except Exception:
        return False
    return isnumb

def internal_error(msg=''):
    "Riporta errore in formato HTML"
    ret = "<h1>Errore interno</h1>"
    if msg:
        ret += "<h3>%s</h3>"%msg
    return ret

def thisyear():
    "Riporta l'anno corrente"
    return time.localtime().tm_year

class Matchty:
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
    sbp = subprocess.Popen(command, stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdoutdata, stderrdata = sbp.communicate(inp)
    return (stdoutdata, stderrdata)

def procinfo():
    "Riporta informazioni sulprocesso"
    unm = os.uname()
    pyv = sys.version_info
    ret = [('User', pwd.getpwuid(os.getuid())[0]),
           ('PID', str(os.getpid())),
           ('OS', '%s-%s %s'%(unm[0], unm[4], unm[2])),
           ('Python', '%d.%d.%d'%(pyv[0], pyv[1], pyv[2]))]
    return ret

def swapname(name):
    "Scambia 'cognome, nome' e riporta 'nome, cognome'"
    spn = name.split(', ')
    if len(spn) == 2:
        ret = '%s %s'%(spn[1].strip(), spn[0].strip())
    else:
        ret = name
    return ret

def makepdf(pkg_root, destdir, templ_name, pdf_name, debug=False, include="", **data):
    "Crea documento PDF da template LaTeX e dict di termini"
    tfile = os.path.join(pkg_root, 'files', templ_name)+'.tex'
    pdfname = pdf_name+'.pdf'
    logging.info("Creazione documento da: %s come: %s/%s", tfile, destdir, pdfname)
    logging.info("Dati documento: %s", ', '.join(list(data.keys())))
    if  include:
        attach = os.path.join(destdir, include)
        logging.info("Includo file: %s", attach)
        attach_list = [attach]
    else:
        attach_list = None
    latex.makepdf(destdir, pdfname, tfile, attach=attach_list, debug=debug, **data)

def get_user(userid):
    "Riporta record di utente"
    usr = USERLIST.where('userid', userid, as_dict=True)
    if usr:
        ret = usr[0]
        ret['email'] = ret['email'].strip()
        return usr[0]
    return {}

def _fullname(email):
    "Riporta il nome completo di utente, dato indirizzo e-mail"
    rec = USERLIST.where('email', email)
    if rec:
        return rec[0][5]
    return 'Sconosciuto'

def _read_userlist():
    "Legge la lista utenti"
    global USERLIST
    USERLIST = FTable((datapath(), 'userlist.json'))
    if USERLIST.empty():
        logging.error("Errore lettura userlist: %s", USERLIST.filename)
    user_sn = USERLIST.columns((2, 3))
    user_fn = ['%s %s'%(x[0], x[1]) for x in user_sn]
    USERLIST.add_column(6, 'fullname', column=user_fn)
    logging.info("Lista utenti aggiornata")

def update_userlist():
    "Aggiorna la lista utenti"
    global USERLIST
    if not USERLIST:
        _read_userlist()
        return
    if USERLIST.needs_update():
        _read_userlist()

def _read_codflist():
    "Legge la lista dei codici fondo"
    global CODFLIST
    CODFLIST = FTable((datapath(), 'codf.json'))
    if CODFLIST.empty():
        logging.warning("Errore lettura lista codici fondi: %s", CODFLIST.filename)
                          # Integrazione codflist (aggiunge nome esteso)
    resp_em = CODFLIST.column(4)
    resp_names = [_fullname(x) for x in resp_em]
    CODFLIST.add_column(1, 'nome_Responsabile', column=resp_names)
    logging.info("Lista Codici fondo aggiornata")

def update_codflist():
    "Aggiorna la lista dei codici fondo"
    global CODFLIST
    if not CODFLIST:
        _read_codflist()
        return
    if CODFLIST.needs_update():
        _read_codflist()

def init_helplist():
    "Genera una lista dei files di nome 'help_*.html' nella directory dei file ausiliari"
    global HELPLIST
    _helpfilt = re.compile('help_.+[.]html')
    try:
        flst = os.listdir(filepath())
    except Exception:
        HELPLIST = []
    else:
        HELPLIST = [x[5:-5] for x in flst if _helpfilt.match(x)]

CHARS = string.ascii_letters+string.digits
def randstr(lng):
    "Genera stringa casuale di linghezzadata"
    return ''.join([random.choice(CHARS) for i in range(lng)])

ABILITATO = "Utente abilitato, "
NON_ABILITATO = "Utente non abilitato, "

def authenticate(userid, password, ldap_host, ldap_port):
    "Autenticazione utente. ldap: indirizzo IP server LDAP, o vuoto"
    user = get_user(userid)
    abilitato = bool(user)
    ret = ldap_authenticate(userid, password, ldap_host, ldap_port)
    if ret < 0:
        logging.error("Errore di connessione al server LDAP")
    elif ret > 0:
        auth_msg = "autenticazione LDAP OK"
        if abilitato:
            return True, ABILITATO+auth_msg
        return False, NON_ABILITATO+auth_msg
    if PAM_AUTH(userid, password):
        auth_msg = 'autenticazione PAM OK'
        if abilitato:
            return True, ABILITATO+auth_msg
        return False, NON_ABILITATO+auth_msg
    if abilitato:
        if crypt.crypt(password, userid) == user['pw']:
            return True, ABILITATO+'autenticazione locale OK'
        return False, ABILITATO+"ID/Password errati"
    return False, NON_ABILITATO+"ID/Password errati"

def checkdir():
    "Verifica esistenza della directory per dati e riporta il path"
    thedir = datapath()
    if not os.path.exists(thedir):
        print()
        print("Directory %s inesistente"%thedir)
        print("\nDevi creare le directory di lavoro\n")
        sys.exit()
    return thedir

def makeuser(userid):
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
        print(" -                    Nome: '%s'"%user[2])
        print(" -                 Cognome: '%s'"%user[1])
        print(" -                   Email: '%s'"%user[3])
        print(" - Password ('-': usa PAM): '%s'"%user[5])
        print(" -                   Flags: '%s'"%user[4])
        ans = input('Modificare/Cancellare utente [m/c]? ')
        ans = ans[:1].lower()
        if ans == "c":
            ans = input("Confermi cancellazione utente %s %s [%s]? "%(user[2], user[1], userid))
            ans = ans[:1].lower()
            if ans == "s":
                rec = uls.where('userid', userid, index=True)
                if rec:
                    pos = rec[0][0]
                    uls.delete_row(pos)
                    uls.save()
                    print("Record utente %s cancellato"%userid)
            return
        if ans != "m":
            return
    else:
        user = ["", "", "", "", "", ""]
        print("Definizione dati per utente:", userid)
    name = input(" -                      Nome [%s]: "%user[2])
    surname = input(" -                   Cognome [%s]: "%user[1])
    email = input(" -                     Email [%s]: "%user[3])
    while True:
        password = input(" - Password ('-': usa PAM/LDAP): ")
        if password:
            break
    flags = input(" -                     Flags (ALD) [%s]: "%user[4])
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
    print(" -   Userid:", userid)
    print(" -     Nome:", name)
    print(" -  Cognome:", surname)
    print(" -    Email:", email)
    print(" - Password:", password)
    print(" -    Flags:", flags)
    print()
    if password == "-":
        pwcrypt = '-'
    else:
        pwcrypt = crypt.crypt(password, userid)

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
        print("Record utente %s modificato"%userid)
    else:
        print("Nessuna modifica")

def signature(path):
    "Return sha256 signature for file"
    fname = os.path.join(*path)
    shsum = hashlib.sha256()
    try:
        fds = open(fname, mode='rb')
    except Exception:
        return ''
    shsum.update(fds.read())
    fds.close()
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
        print("Utente %s. campo %s fatto uguale a: %s"%(userid, field, str(value)))
    else:
        print("L'utente %s non esiste"%userid)

def setadmin():
    "assegna ad utente orivilegio di amministratore"
    thedir = checkdir()
    userid = input('Userid: ')
    if userid:
        setfield(thedir, userid, 'admin', 1)

def is_year(year):
    "verifica numero anno corretto"
    try:
        nyr = int(year)
    except Exception:
        return False
    return nyr > 2000 and nyr < 3000

def get_years(ddate):
    "trova elenco anni definiti"
    try:
        years = [x for x in os.listdir(ddate) if is_year(x)]
    except Exception:
        years = []
    return years

def namebasedir(anno, num):
    "genera path directory per nuova pratica"
    stanno = '%4.4d' % int(anno)
    stnum = '%6.6d' % int(num)
    basedir = os.path.join(datapath(), stanno, stanno+'_'+stnum)
    return basedir

IS_PRAT_DIR = re.compile(r'\d{4}_\d{6}')   #  Seleziona directory per pratica

class DocList:
    "definizione lista documenti"
    def __init__(self, thedir, fname,
                 year=None,
                 directory_filter=lambda x: True,
                 filename_filter=lambda x: True,
                 content_filter=lambda x: True,
                 sort=None,
                 extract=None):
        self.years = get_years(thedir)  # Rendi noto quali altri
        self.years.sort()           # anni sono disponibili
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
                    rec = jload(fnm)
                except tb.TableException:
                    self.errors.append(fnm)
                    continue
                if rec and content_filter(rec):
                    if extract:
                        rec = {key:value for key, value in rec.items() if key in extract}
                    self.records.append(rec)
        if sort:
            self.records.sort(key=sort)

class PratIterator:
    "Iteratore sulle pratiche dell'anno specificato"
    def __init__(self, year=None):
        if not year:
            year = thisyear()
        self.ydir = os.path.join(datapath(), str(year))
        self.pratdir = iter(os.listdir(self.ydir))

    def __iter__(self):
        return self

    def __next__(self):
        nextdir = self.pratdir.__next__()
        pratfile = os.path.join(self.ydir, nextdir, "pratica.json")
        try:
            prat = jload(pratfile)
        except tb.TableException:
            prat = {}
        return prat

def remove(path, show_error=True):
    "Remove files"
    fullname = getpath(path)
    try:
        os.unlink(fullname)
    except Exception as excp:
        if show_error:
            logging.error("Error removing file: %s [%s]", fullname, str(excp))
    else:
        logging.info("Removed file: %s", fullname)


def testlogin():
    "Test funzionamento login"
    from getpass import getpass
    print('Prova userid/password')
    userid = input("Userid: ")
    psw = getpass()
    thedir = checkdir()
    config = jload((thedir, 'config.json'))
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
        print(' - Accesso: OK [%s]'%why)
    else:
        print(' - Accesso: NO [%s]'%why)

def show64file(filename):
    "Mostra file json codificato"
    f64 = os.path.join(datapath(), filename)
    obj64 = jload_b64(f64)
    print()
    print(obj64)

def protect(fpath):
    "set proper mode bits on filepath"
    os.chmod(fpath, stat.S_IRUSR+stat.S_IWUSR)

def makepwfile(ldappw=False):
    "Crea file per password"
    pwpath = os.path.join(datapath(), 'pwfile.json')
    pop3pw = input('password per accesso POP3: ')
    if not pop3pw:
        return
    pwdict = {'pop3_pw': pop3pw, 'secret_key': randstr(30)}
    if ldappw:
        managerpw = input('password per LDAP manager (accesso R/W): ')
        anonymouspw = input('password per LDAP anonimo (accesso R): ')
        pwdict['manager_pw'] = managerpw
        pwdict['anonymous_pw'] = anonymouspw
    jsave_b64(pwpath, pwdict)
    protect(pwpath)

def input_anno():
    "Richiesta iterattiva anno"
    year = input('Anno: ')
    if year:
        year = int(year)
    else:
        year = thisyear()
    return year

def showmaxdet():
    "Trova massimo numero di determina"
    year = input_anno()
    ndet, prat = find_max_det(year)
    print()
    print("Ultima determina anno %d: %d (pratica: %s)"%(year, ndet, prat))

def showmaxprat():
    "Trova massimo numero di pratica"
    year = input_anno()
    prat = find_max_prat(year)
    print()
    print("Ultima pratica anno %d: %s"%(year, prat))

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
        fname = "%s, %s [%s]"%(usr[2], usr[3], usr[1])
        print("%-42s %-30s  %s"%(fname, usr[4], usr[5]))

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
    print("Elenco combinazioni valori nei campi: %s per l'anno %d"%(", ".join(fields), year))
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
        dati_pratica = jload((basedir, PRAT_JFILE))
        pprint(dati_pratica, indent=4)
    else:
        print()
        print("Errore numero pratica:", nprat)

def showpratiche():
    "Mostra elenco pratiche"
    year = input_anno()
    print("Elenco pratiche per l'anno", year)
    elenco = DocList(datapath(), 'pratica.json', year=year, extract=_EXTRACT)
    for rec in elenco.records:
        print(" - %s %s %s/%s"%(rec[NUMERO_PRATICA], rec[DATA_RICHIESTA],
                                rec[NOME_RICHIEDENTE], rec[NOME_RESPONSABILE]))
        print("   %s"%rec[DESCRIZIONE_ACQUISTO])
    if elenco.errors:
        print("Errori di accesso alle pratiche:")
        for err in elenco.errors:
            print("  ", err)

def main():
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
    elif verb == 'ad':
        setadmin()
    elif verb == 'al':
        showallfields()
    elif verb == 'nd':
        showmaxdet()
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
