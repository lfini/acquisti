"""
Questa procedura deve essere lanciata da CRON dell'account dedicato alle
procedure degli acquisti, tipicamente ogni 5 minuti.

Il comando relativo e':

   python bin/email_fetcher.py filter

La procedura utilizza POP3 per estrarre i messaggi dalla mailbox e genera
le necessarie transazioni HTTP quando trova un messaggio relativo ad
una approvazione.

La procedura puo' essere utilizzata in modo interattivo per verificare
la presenza di messaggi sul server, senza effettuare l'estrazione:

   python bin/email_fetcher.py count

Per test:

    python bin/email_fetcher.py test

"""
import sys
import os
import re
import poplib
import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
import requests
import ftools
from table import jload

__author__ = 'Luca Fini'
__version__ = '3.0.2'
__date__ = '21/8/2019'

IDENT = "EMAIL_FETCHER. Vers. %s. %s, %s" % (__version__, __author__, __date__)

DATADIR = ftools.datapath()
WORKDIR = ftools.workpath()

LOGFILE = os.path.join(WORKDIR, 'email_fetcher.log')
CONFIG = jload((DATADIR, 'config.json'))

def make_url(code):
    "Genera la URL per invio autorizzazione"
    return "http://{}:{}/email_approv/{}".format(CONFIG["web_host"], CONFIG["web_port"], code)

def send_http(code, sender, mailhost):
    "Invio richiesta HTTP per approvazione"
    header = {'Identity': 'Email-Fetcher',
              'Sender-Email': sender,
              'Mail-Host': mailhost}

    url = make_url(code)
    response = requests.get(url, headers=header, timeout=2)
    if response.status_code != requests.codes.ok:
        raise RuntimeError("send_http returned: "+str(response.status_code))

RE_SUBJ = re.compile(r'Subject:\s(.+)')
RE_CODE = re.compile(r'Code:([A-Za-z0-9]{10}):')
RE_SENDER = re.compile(r'From:\s(.+)')
RE_MAILHOST = re.compile(r'Received: from .*[(]([^)]+)[)]')

def getitem(line, regexp):
    "Generica estrazione di parte di linea"
    match = regexp.match(line)
    if match:
        return match.group(1)
    return ''

def getcode(line):
    "Estrai codice di apporovazione"
    match = RE_CODE.search(line)
    if match:
        return match.group(1)
    return ''

def parsesubject(lines):
    "Estrai codice approvazione da linea Subject"
    subj = ''
    for line in lines:
        subj = getitem(line, RE_SUBJ)
        if subj:
            break
    if subj:
        subject = subj
        code = getcode(subject)
    else:
        subject = 'No subject'
        code = ''
    return subject, code

def parsesender(lines):
    "Estrai mittente"
    sender = ''
    for line in lines:
        sender = getitem(line, RE_SENDER)
        if sender:
            break
    return sender

def parsemailhost(lines):
    "Estrai mailhost da messaggio"
    mhost = ''
    for line in lines:
        mhost = getitem(line, RE_MAILHOST)
        if mhost:
            break
    return mhost


def do_message(lines):
    "Analizza messaggio"
    subject, code = parsesubject(lines)
    sender = parsesender(lines)
    mailhost = parsemailhost(lines)

    ret = True
    if code:
        try:
            send_http(code, sender, mailhost)
        except Exception as excp:
            LOGGER.warning("Errore messaggio HTTP (%s):  code:%s, sender:%s, mailhost:%s",
                           str(excp), code, sender, mailhost)
            ret = False
        else:
            LOGGER.info("Ricevuta approvazione. Mail-Host: %s. From: %s. Code: %s",
                        mailhost, sender, code)
    else:
        LOGGER.warning("Ricevuto messaggio illegale. Mail-Host: %s. From: %s. Subject: %s",
                       mailhost, sender, subject)
        maxlines = 200
        nline = 0
        for line in lines:
            LOGGER.warning("> %s", line.strip())
            nline += 1
            if nline > maxlines:
                LOGGER.warning("> .... removed %d lines", len(lines)-maxlines)
                break
    return ret

def fetchmail(server, user, pwd, processor):
    "Recupera messaggio da mail server"
    popconn = poplib.POP3_SSL(server)
    popconn.user(user)
    popconn.pass_(pwd)
    n_messages = len(popconn.list()[1])
    for i in range(n_messages):
#     m = M.retr(i+1)
        reply = popconn.top(i+1, 4)
        message = [x.decode("utf8") for x in reply[1]]
        ret = processor(message)
        if ret:
            popconn.dele(i+1)
    popconn.quit()

def countmail(server, user, pwd):
    "Conta messaggi in attesa sul server"
    popconn = poplib.POP3_SSL(server)
    popconn.user(user)
    popconn.pass_(pwd)
    n_messages = len(popconn.list()[1])
    popconn.quit()
    return n_messages

if 'filter' in sys.argv:
    LOGGER = logging.getLogger()
    for h in LOGGER.handlers:
        LOGGER.removeHandler(h)       # Per rimuovere lo StreamHandler di default
    LOGGER.setLevel(logging.INFO)
    FORMATTER = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    HNDL = RotatingFileHandler(LOGFILE, maxBytes=10000000, backupCount=3, encoding='utf8')
    HNDL.setFormatter(FORMATTER)
    LOGGER.addHandler(HNDL)

    EHNDL = SMTPHandler(CONFIG["smtp_host"], CONFIG["email_responder"],
                        [CONFIG["email_webmaster"]], 'Errore procedura EMAIL_FETCHER')
    EHNDL.setLevel(logging.ERROR)
    LOGGER.addHandler(EHNDL)

    LOGGER.info(IDENT)
    PASSWD = ftools.decrypt(CONFIG["pop3_pw"])
    fetchmail(CONFIG["pop3_host"], CONFIG["pop3_user"], PASSWD, do_message)
    sys.exit()

if 'help' in sys.argv:
    print()
    print(IDENT)
    print()
    print(__doc__)
    sys.exit()

if 'count' in sys.argv:
    PASSWD = ftools.decrypt(CONFIG["pop3_pw"])
    N_MSG = countmail(CONFIG["pop3_host"], CONFIG["pop3_user"], PASSWD)
    print()
    print(IDENT)
    print()
    print("Messages ready at %s: %d"  % (CONFIG["pop3_host"], N_MSG))
    sys.exit()

TEST_MSG = """
Nota: questo test, se l'invio della richiesta è corretto, deve causare un
log nel server della procedura acquisti con l'indicazione che la richiesta
è illegale
"""

if 'test' in sys.argv:
    print(TEST_MSG)
    CODE = "12345678"
    print("URL:", make_url(CODE))
    try:
        send_http(CODE, "lfini@inaf.it", "193.206.155.7")
    except Exception as excp:
        print("Errore:", excp)
    else:
        print("Richiesta inviata")
    sys.exit()

print()
print(IDENT)
print()
print("Uso:")
print("      python bin/email_fetcher help     -- Descrizione procedura")
print("      python bin/email_fetcher filter   -- Processa messaggi")
print("      python bin/email_fetcher count    -- Numero messaggi in attesa")
print("      python bin/email_fetcher test     -- Invia richiesta al server HTTP")
print()

sys.exit()
