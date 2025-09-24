"""
Supporto per l'invio di messaggi e-mail con vari metodi

1. Uso per test del mailserver non autenticato:

    python send_mail.py [-t attach.pdf] -n <mailserver> <indirizzo destinatario>

2. Uso per test del mailserver con autenticazione

    python send_mail.py [-t attach.pdf] -a <mailserver> <user-id> <passwd> <indirizzo destinatario>

3. Uso per test e generazione del token per API GMail:

    python send_mail.py [-t attach.pdf] -g <indirizzo destinatario>

NOTA: il Token viene generato a partire dal file credentials.json e richiede l'accesso
      autenticato ad una pagina di Google (attivato automaticamente dalla procedura di
      generazione).  Per generare il token per xxx@inaf.it ocorre fare l'operazione
      all'interno dell'organizzazione.
"""

import sys
import os.path
import smtplib
from email.message import EmailMessage
import base64
import getopt
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from constants import DATADIR


class EmailError(Exception):
    "Errori da email"


TOKEN_FILE = os.path.join(DATADIR, "GMailToken.json")
CREDS_FILE = os.path.join(DATADIR, "credentials.json")


############################################################### Codice per uso di GMail API
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
# Nota: quando si cambia questa linea, occorre cancellare il file GMailToken.json,
#       e rigenerarlo lanciando questa procedura in modo tst con messaggio inviato
#       via GMail


def get_credentials():
    "Riporta (o genera) il file per credenziali API di GMail"
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    # Se il file di credenziali non esiste, deve essere generato
    # lanciando questa procedura da linea di comando
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if __name__ != "__main__":
                raise EmailError("Non è stato generato il token per GMail API")
            if not os.path.exists(CREDS_FILE):
                raise EmailError(
                    f"Manca il file di credenziali per GMail API ({CREDS_FILE})"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w", encoding="utf8") as token:  # Salva le credenziali
            token.write(creds.to_json())
    return creds


def _send_via_gmail(message):
    "Invia un messaggio tramite API di GMail"
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)
    user_id = "me"
    msg = {
        "raw": base64.urlsafe_b64encode(message.as_string().encode("utf8")).decode(
            "ascii"
        )
    }
    service.users().messages().send(       # pylint: disable=E1101
        userId=user_id, body=msg
    ).execute()  # pylint: disable=E1101


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
        raise EmailError("[SMTP]") from excp
    smtp.close()


def send(  # pylint: disable=R0913, R0917
    mailhost, auth, sender, recipients, subj, message, attach=None
):
    "composizione ed invio messaggio"
    emsg = EmailMessage()
    emsg["to"] = ", ".join(recipients)
    emsg["subject"] = subj
    emsg["from"] = sender
    emsg.set_content(message)
    if attach:
        pdfpath, pdfname = attach
        with open(pdfpath, "rb") as pdf:
            emsg.add_attachment(
                pdf.read(), maintype="application", subtype="pdf", filename=pdfname
            )
    if mailhost:
        _send_smtp(mailhost, auth, sender, recipients, emsg)
    else:
        _send_via_gmail(emsg)


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

ARGERR = "Errore argomenti. Usa -h per aiuto"


def main():  # pylint: disable=R0912
    "Uso diretto per attivazione token GMail e test"
    if "-h" in sys.argv:
        print(__doc__)
        sys.exit()
    try:
        opts, args = getopt.getopt(sys.argv[1:], "gnat:")
    except getopt.error:
        print(ARGERR)
        sys.exit()
    attach = None
    oper = 0
    dest, mailserv, auth = (None, None, None)
    for opt, val in opts:
        if opt == "-g":
            if len(args) == 1:
                dest = args[0]
                oper = 1
            else:
                print(ARGERR)
                sys.exit()
        elif opt == "-n":
            if len(args) == 2:
                dest, mailserv = args
                oper = 2
        elif opt == "-a":
            if len(args) == 4:
                dest, mailserv = args[:2]
                auth = args[2:]
                oper = 3
        elif opt == "-t":
            filepath = val
            filename = os.path.basename(val)
            attach = (filepath, filename)

    if oper == 1:
        print("Invio messaggio di prova tramite GMail a:", dest)
        send("", None, SENDER, [dest], SUBJECT, GMAIL_MESSAGE, attach)
    elif oper == 2:
        print(f"Invio messaggio di prova tramite server {mailserv} a: ", dest)
        send(mailserv, None, SENDER, [dest], SUBJECT, SMTP_MESSAGE % mailserv, attach)
    elif oper == 3:
        print(f"Invio messaggio di prova tramite server {mailserv} a: ", dest)
        send(mailserv, auth, SENDER, [dest], SUBJECT, SMTP_MESSAGE % mailserv, attach)
    else:
        print(ARGERR)
    sys.exit()


if __name__ == "__main__":
    main()
