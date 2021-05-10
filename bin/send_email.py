"""
Supporto per l'invio di messaggi e-mail con vari metodi

1. Uso per test del mailserver non autenticato:

    python send_mail.py -n <mailserver> <indirizzo destinatario>

2. Uso per test del mailserver con autenticazione

    python send_mail.py -a <mailserver> <user-id> <passwd> <indirizzo destinatario>

3. Uso per test e generazione del token per API GMail:

    python send_mail.py -g <indirizzo destinatario>

"""

import sys
import pickle
import os.path
import smtplib
from email.mime.text import MIMEText
import base64
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from constants import DATADIR

class EmailError(Exception):
    "Errori da email"

TOKEN_FILE = os.path.join(DATADIR, "GMailToken.pkl")
CREDS_FILE = os.path.join(DATADIR, "credentials.json")


############################################################### Codice per uso di GMail API
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_credentials():
    "Riporta (o genera) il file per credenziali API di GMail"
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    # Se il file di credenziali non esiste, deve essere generato
    # lanciando questa procedura da linea di comando
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if __name__ != "__main__":
                raise EmailError("Non è stato generato il token per GMail API")
            if not os.path.exists(CREDS_FILE):
                raise EmailError("Manca il file di credenziali per GMail API (%s)"%CREDS_FILE)
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:      # Salva le credenziali
            pickle.dump(creds, token)
    return creds

def _send_via_gmail(message):
    "Invia un messaggio tramite API di GMail"
    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)
    user_id = "me"
    msg = {'raw': base64.urlsafe_b64encode(message.as_string().encode("utf8")).decode("ascii")}
    service.users().messages().send(userId=user_id, body=msg).execute() # pylint: disable=E1101

####################################################################### Fine codice per GMail API

def _send_smtp(mailhost, auth, sender, dest, msg):
    "Invio messaggio e-mail usando un server SMTP con o senza autenticazione"
    smtp = None
    try:
        smtp = smtplib.SMTP(mailhost)
        if auth:
            smtp.starttls()
            smtp.login(auth[0], auth[1])
        smtp.sendmail(sender, dest, msg.as_string())
    except Exception as excp:
        raise EmailError("[SMTP] "+str(excp))
    smtp.close()

def send(mailhost, auth, sender, recipients, subj, message):     # pylint: disable=R0913
    "Invia messaggio e-mail"
    try:
        msg = MIMEText(message.encode('utf8'), 'plain', 'utf8')
        msg['to'] = ', '.join(recipients)
        msg['subject'] = subj
        msg['from'] = sender
    except Exception as excp:
        errmsg = str(excp)+" [Recip.:%s]"%",".join(recipients)
        raise EmailError(errmsg)
    if mailhost:
        _send_smtp(mailhost, auth, sender, recipients, msg)
    else:
        _send_via_gmail(msg)

GMAIL_MESSAGE = """
In seguito all'invio del messaggio è stato anche generato il
token per l'accesso alla API di GMail
"""

SMTP_MESSAGE = """
Messaggio inviato tramite server: %s
per verifica di funzionamento
"""

SUBJECT = "Messaggio di prova"

SENDER = "test.acquisti@inaf.it"

def main():
    "Uso diretto per attivazione token GMail e test"
    if "-g" in sys.argv and len(sys.argv) == 3:
        dest = sys.argv[2]
        print("Invio messaggio di prova tramite GMail a: %s"%dest)
        send("", None, SENDER, [dest], SUBJECT, GMAIL_MESSAGE)
        sys.exit()
    if "-n" in sys.argv and len(sys.argv) == 4:
        dest = sys.argv[3]
        mailserv = sys.argv[2]
        print("Invio messaggio di prova tramite server %s a: %s"%(mailserv, dest))
        send(mailserv, None, SENDER, [dest], SUBJECT, SMTP_MESSAGE%mailserv)
        sys.exit()
    if "-a" in sys.argv and len(sys.argv) == 6:
        dest = sys.argv[5]
        mailserv = sys.argv[2]
        auth = (sys.argv[3], sys.argv[4])
        print("Invio messaggio di prova tramite server %s a: %s"%(mailserv, dest))
        send(mailserv, auth, SENDER, [dest], SUBJECT, SMTP_MESSAGE%mailserv)
        sys.exit()
    print(__doc__)

if __name__ == "__main__":
    main()
