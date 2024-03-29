"""
Procedura CGI per gestione acquisti

Uso:
    python acquisti.py [-h] [-v] [-V]

Dove:
    -h   mostra aiuto
    -v   mostra numero di versione (MAJ.min) ed esce
    -V   mostra versione  in formato completo ed esce

Lanciato senza argomenti, attiva il modo debug
"""

import sys
import time
import os
import re
import logging
from pprint import PrettyPrinter

import wtforms as wt
import flask as fk
import constants as const    #  Mantenere: serve per about()

#    cope with compatibility with older werkzeug versions
try:
    from werkzeug.utils import secure_filename
except ImportError:
    from werkzeug import secure_filename

from constants import *          # pylint: disable=W0401
import forms as fms
import ftools as ft
import table as tb

# pylint: disable=C0302

# Versione 1.0   10/10/2014-28/10/2014  Prima release
#
# Versione 2.0   20/08/2016: Revisione completa per inseguimento normativa
#                            Corretti numerosi bug
#                            Introdotto support utf-8
#                            Ripulito con pylint

# Versione 2.2   01/2018:    Modificato testo determine

# Versione 3.0   10/2018:    Rivisto layout complessivo, aggiunte funzioni
#                            e portato a python 3
# Versione 3.1   3/2019:     Risistemate varie modalità di acquisto

# Versione 3.2   7/2019:     Nuova versione stabile (dopo 2 mesi di on-line)

# Versione 3.3  10/2019:     Aggiunta gestione RDO su MEPA (preliminare)

# Versione 3.4  12/2019:     Completata gestione RDO su MEPA

# Versione 3.5   5/2020:     Corretto testo di Richiesta e determine nei casi RDO
#                            e manifestazione di interesse.
# Versione 3.6   9/2020:     Corretto testo di ordine inglese

# Versione 4.1  11/2020:     Integrate le funzione di housekeeping in acquisti
#                            la procedura Housekeeping viene eliminata
# Versione 4.2  11/2020:     Lista utenti convertita a nomi INAF
# Versione 4.3  11/2020:     Modificato pannello per ricerca pratiche
# Versione 4.4  12/2020:     Corretto errore nella selezione pratiche per richiedente/responsabile
# Versione 4.5  12/2020:     Aggiunto supporto per invio mail con GMail API
# Versione 4.6   4/2021:     Aggiunto supporto per inclusione logo in testa ai documenti
# Versione 4.7   5/2021:     Rimossa approvazione per e-mail e sostituito mailserver
#                            con server google
# Versione 4.8   6/2021:     Corretto bug nella generazione dei messaggi di richiesta approvazione
# Versione 4.9  11/2021:     Modificato layout pagine PDF generate (per effetto "carta intestata")
# Versione 4.10  11/2023:    introdotto logging delle URL. Passato con pylint
# Versione 4.10.1  11/2023:  Corretto bug alla linea 1525

# Versione 5.0   3/2024:  Preparazione nuova versione 2024 con modifiche sostanziali

__author__ = 'Luca Fini'
__version__ = '5.0.4'
__date__ = '16/03/2024'

__start__ = time.asctime(time.localtime())

CONFIG_FILE = os.path.join(DATADIR, CONFIG_NAME)

MODALITA_IMPLEMENTATE = [TRATT_MEPA_40]     # Lista modalità acquisto implementate

class ToBeImplemented(RuntimeError):
    'Eccezione per parti da implementare'

class CONFIG:                   # pylint: disable=R0903
    'Dati di configurazione'
    time = time.time()
    config = tb.jload(CONFIG_FILE)

THIS_URL = os.environ.get("REQUEST_SCHEME", "???")+"://"+ \
           os.environ.get("SERVER_NAME", "??.??.??")+":"+ \
           os.environ.get("SERVER_PORT", "?")

BASEDIR_STR = 'basedir'

FILE_VERSION = 3    # Versione file pratica.json

MAX_DETERMINA = 0
START_YEAR = 0

class DEBUG:         # pylint: disable=R0903
    "Variabili di supporto per Debug"
    local = False
    email = ''

FASE_ERROR = Exception("Manca specifica fase")
NO_BASEDIR = Exception("Basedir non definita")
ILL_ATCH = Exception("Modello allegato non previsto")

MANCA_PREV_MEPA = "Manca preventivo MePA in allegato"

def setdebug():
    "Determina modo DEBUG"
    DEBUG.local = True
    DEBUG.email = CONFIG.config[EMAIL_WEBMASTER]

def print_debug(*args):
    'scrive debug su stdout, solo in modo "locale"'
    if DEBUG.local:
        print('LOC_DBG>', *args)

def update_lists():
    "Riinizializza tabelle"
    ft.update_userlist()
    ft.update_codflist()

#  Utilities

def _test_admin(the_user):
    return 'A' in the_user.get('flags')

def _test_developer(the_user):
    return 'D' in the_user.get('flags')

def _test_richiedente(the_user, d_prat):
    emailrich = d_prat.get(EMAIL_RICHIEDENTE, "R").lower()
    emailuser = the_user.get("email", "U").lower()
    return emailuser == emailrich

def _test_responsabile(the_user, d_prat):
    emailresp = d_prat.get(EMAIL_RESPONSABILE, "R").lower()
    emailuser = the_user.get("email", "U").lower()
    return emailuser == emailresp

def _test_rup(the_user, d_prat):
    emailrup = d_prat.get(EMAIL_RUP, "R").lower()
    emailuser = the_user.get("email", "U").lower()
    return emailuser == emailrup

def _test_pdf_determina(basedir, _unused, fase):
    "test: esistenza determina"
    if not basedir:
        raise NO_BASEDIR
    if fase == "B":
        pdf_path = os.path.join(basedir, DETB_PDF_FILE)
    elif fase == "A":
        pdf_path = os.path.join(basedir, DETA_PDF_FILE)
    else:
        raise FASE_ERROR
    return os.path.exists(pdf_path)

def _test_pdf_preventivo_mepa(basedir, d_prat, fase):
    "test esistenza preventivo mepa"
    if fase == "A":
        if d_prat[MOD_ACQUISTO] == TRATT_MEPA_40:
            return ft.findfiles(basedir, TAB_ALLEGATI[PREV_TRATT_MEPA][0])
        return True
    if fase == "B":
        return True
    raise FASE_ERROR

def _test_pdf_ordine(basedir, d_prat, fase):
    "test esistenza ordine nella fase data"
    if not basedir:
        raise NO_BASEDIR
    if fase == "A":
        if d_prat[MOD_ACQUISTO] == TRATT_MEPA_40:
            return True
    elif fase == "B":
        return True
    else:
        raise FASE_ERROR
    pdf_path = os.path.join(basedir, ORD_PDF_FILE)
    return os.path.exists(pdf_path)

def _test_pdf_progetto(basedir, _unused1, _unused2):
    "test: esistenza progetto"
    if not basedir:
        raise NO_BASEDIR
    pdf_path = os.path.join(basedir, PROG_PDF_FILE)
    return os.path.exists(pdf_path)

def _test_pdf_ordine_mepa(basedir, d_prat, fase):
    "test: esistenza ordine mepa"
    if not basedir:
        raise NO_BASEDIR
    if fase == "A":
        if d_prat[MOD_ACQUISTO] == TRATT_MEPA_40:
            return True
        return False
    if fase == "B":
        return True
    raise FASE_ERROR

def _test_pdf_trattativa_mepa(basedir, d_prat, fase):
    "test: esistenza trattativa diretta mepa"
    raise ToBeImplemented("_test_pdf_trattativa_mepa")
#   if fase == "A":
#       if d_prat[MOD_ACQUISTO] == TRATT_MEPA_40:
#           return ft.findfiles(basedir, TAB_ALLEGATI[DOCUM_STIPULA][0])
#       return True
#   if fase == "B":
#       return True
#   raise FASE_ERROR

def _test_pdf_offerta_ditta(basedir, d_prat, fase):
    "test: esistenza offerte da ditte"
    raise ToBeImplemented("_test_pdf_offerta_ditta")
#   if fase == "A":
#       if d_prat[MOD_ACQUISTO] in (INFER_5000, SUPER_5000, INFER_1000, SUPER_1000, PROC_NEG):
#           return bool(len(ft.findfiles(basedir, TAB_ALLEGATI[OFFERTA_DITTA_A][0])))
#       return True
#   if fase == "B":
#       if d_prat.get(MOD_ACQUISTO_B, "") in (PROC_NEG, SUPER_5000, SUPER_1000):
#           return bool(len(ft.findfiles(basedir, TAB_ALLEGATI[OFFERTA_DITTA_B][0])))
#       return True
#   raise FASE_ERROR

def _test_pdf_lettera_invito(basedir, d_prat, fase):
    "test: esistenza lettere di invito"
    raise ToBeImplemented("_test_pdf_lettera_invito")
#   if fase == "A":
#       if d_prat[MOD_ACQUISTO] == PROC_NEG:
#           return bool(len(ft.findfiles(basedir, TAB_ALLEGATI[LETT_INVITO_A][0])))
#       return True
#   if fase == "B":
#       if d_prat[MOD_ACQUISTO] in (PROC_NEG, MANIF_INT):
#           return bool(len(ft.findfiles(basedir, TAB_ALLEGATI[LETT_INVITO_B][0])))
#       return True
#   raise FASE_ERROR

def _test_pdf_capitolato_rdo(basedir, d_prat, fase):
    "test: esistenza capitolato RDO"
    raise ToBeImplemented("_test_pdf_capitolato_rdo")
#   if fase == "A":
#       if d_prat[MOD_ACQUISTO] in (RDO_MEPA, ):
#           return len(ft.findfiles(basedir, TAB_ALLEGATI[CAPITOLATO_RDO][0]))
#       return True
#   if fase == "B":
#       return True
#   raise FASE_ERROR

def _test_pdf_lista_ditte_invitate(basedir, d_prat, fase):
    "test: esistenza lista ditte invitate"
    raise ToBeImplemented("_test_pdf_lista_ditte_invitate")
#   if fase == "A":
#       if d_prat[MOD_ACQUISTO] == RDO_MEPA:
#           return len(ft.findfiles(basedir, TAB_ALLEGATI[LISTA_DITTE_INV][0]))
#       return True
#   if fase == "B":
#       return True
#   raise FASE_ERROR

def check_allegati_allegabili(d_prat):
    "test: allegati allegabili"
    if d_prat[PRATICA_APERTA] != 1:
        return 'Pratica chiusa'
    return ''

def check_allegati_cancellabili(the_user, d_prat):
    "test: allegati cancellabili"
    if d_prat.get(PRATICA_APERTA) != 1:
        return 'Pratica chiusa'
    if _test_admin(the_user):
        return ''
    ret = ['Non admin']
    if _test_richiedente(the_user, d_prat):
        return ''
    ret.append('Non richiedente')
    if _test_responsabile(the_user, d_prat):
        return ''
    ret.append('Non responsabile')
    return ', '.join(ret)

def check_progetto_inviabile(the_user, basedir, d_prat):               # pylint: disable=R0911
    "test: progetto inviabile"
    if not d_prat.get(PRATICA_APERTA, 1):
        return 'Pratica chiusa'
    if not _test_pdf_progetto(basedir, d_prat, "A"):
        return 'Progetto non generato'
    if not _test_pdf_preventivo_mepa(basedir, d_prat, "A"):
        return MANCA_PREV_MEPA
    if not (_test_admin(the_user) or _test_richiedente(the_user, d_prat)):
        return "Operazione consentita solo al richiedente o all'Amministrazione"
    if d_prat.get(PROGETTO_INVIATO):
        return 'Progetto già inviato'
    if d_prat.get(FIRMA_APPROVAZIONE):
        return 'Progetto già approvato'
    return ''

def check_progetto_modificabile(the_user, basedir, d_prat):               # pylint: disable=W0703,R0911
    "test: progetto modificabile"
    if d_prat.get(PRATICA_APERTA) != 1:  # NO: La pratica e' chiusa
        return 'Pratica chiusa'
    if _test_pdf_determina(basedir, d_prat, "A"):
        return 'Determina generata'
    if _test_admin(the_user):
        return  ''
    if _test_responsabile(the_user, d_prat):
        return ''
    if _test_richiedente(the_user, d_prat):
        if d_prat.get(PROGETTO_INVIATO, 0):
            return """Progetto in approvazione. Operazione consentita solo
al responsabile dei fondi o all'Amministrazione"""
        return ''
    return """Operazione consentita solo al richiedente,
al responsabile dei fondi o all'Amministrazione"""

def check_progetto_approvabile(the_user, basedir, d_prat):
    "test: progetto approvabile"
    if not d_prat[PRATICA_APERTA]:
        return 'Pratica chiusa'
    if not _test_responsabile(the_user, d_prat):
        return "Operazione consentita solo al responsabile dei fondi"
    if d_prat.get(FIRMA_APPROVAZIONE):
        return 'Progetto già approvato'
    if not _test_pdf_preventivo_mepa(basedir, d_prat, "A"):
        return MANCA_PREV_MEPA
    return ''

#def check_rup_nominabile(the_user, _unused, d_prat):
#    "test: è possibile nominare il RUP"
#    if not d_prat[PRATICA_APERTA]:
#        return 'Pratica chiusa'
#    if not _test_admin(the_user):
#        return OPER_SOLO_AMMINISTRAZIONE
#    if not d_prat.get(FIRMA_APPROVAZIONE):
#        return 'Progetto non ancora approvato'
#    if d_prat.get(EMAIL_RUP):
#        return 'RUP già nominato'
#    return ''

def check_determina_modificabile(the_user, basedir, d_prat, fase):
    "test: determina a modificabile"
    if d_prat.get(PRATICA_APERTA) != 1:
        return 'Pratica chiusa'
    if not _test_admin(the_user):
        return OPER_SOLO_AMMINISTRAZIONE
    if fase == "A" and _test_pdf_determina(basedir, d_prat, "B"):
        return "Determina aggiudicazione generata"
    return ''

def check_determina_cancellabile(the_user, basedir, d_prat, fase):
    "test: determina cancellabile"
    if not _test_pdf_determina(basedir, d_prat, fase):
        return 'La determina non è stata generata'
    return check_determina_modificabile(the_user, basedir, d_prat, fase)

def check_ordine_modificabile(the_user, basedir, d_prat, fase):
    "test: ordine modificabile"
    if d_prat.get(PRATICA_APERTA) != 1:
        return 'Pratica chiusa'
    if not _test_admin(the_user):
        return OPER_SOLO_AMMINISTRAZIONE
    if not _test_pdf_determina(basedir, d_prat, fase):
        return 'La determina non è stata generata'
    return ''

def check_pratica_chiudibile(the_user, _unused, d_prat):
    "test: pratica chiudibile"
    if d_prat.get(PRATICA_APERTA) != 1:
        return 'Pratica chiusa'
    if not _test_admin(the_user):
        return OPER_SOLO_AMMINISTRAZIONE
    return ''

def check_chiudibile_davvero(the_user, basedir, d_prat):
    "test: pratica chiudibile dopo conferma"
    ret = check_pratica_chiudibile(the_user, basedir, d_prat)
    if ret:
        return ret
    if d_prat.get(CONF_CHIUSURA, 0):
        return ''
    avv = _avvisi_allegati(basedir, d_prat, "A")
    avv += _avvisi_allegati(basedir, d_prat, "B")
    if avv:
        return avv
    return ''

def check_pratica_apribile(the_user, d_prat):
    "test: pratica apribile"
    if d_prat.get(PRATICA_APERTA, 0) != 0:
        return 'Pratica aperta'
    if d_prat.get(PRATICA_ANNULLATA, 0):
        return 'Pratica annullata'
    if _test_admin(the_user):
        return ''
    return OPER_SOLO_AMMINISTRAZIONE

def check_pratica_annullabile(the_user, d_prat):
    "test: pratica annullabile"
    if d_prat.get(PRATICA_ANNULLATA, 0) == 1:
        return 'Pratica già annullata'
    if _test_admin(the_user):
        return ''
    return OPER_SOLO_AMMINISTRAZIONE

def check_rdo_modificabile(_the_user, _basedir, d_prat):
    "test: rdo modificabile"
    if d_prat.get(PRATICA_APERTA) != 1:
        return 'Pratica chiusa'
    return ''

def check_all(the_user, basedir, d_prat):
    "Verifica lo stato della pratica e riporta un dict riassuntivo"
    info = {}
    info['debug'] = bool(DEBUG.local)
    info['developer'] = _test_developer(the_user)
    info['admin'] = _test_admin(the_user)
    info[PDF_PROGETTO] = _test_pdf_progetto(basedir, d_prat, "")
    info[PDF_DETERMINA_A] = _test_pdf_determina(basedir, d_prat, "A")
    info[PDF_DETERMINA_B] = _test_pdf_determina(basedir, d_prat, "B")
    info[PDF_ORDINE] = _test_pdf_ordine(basedir, d_prat, "A")
    info['allegati_cancellabili'] = not check_allegati_cancellabili(the_user, d_prat)
    info['det_a_cancellabile'] = not check_determina_cancellabile(the_user, basedir, d_prat, "A")
    info['det_a_modificabile'] = not check_determina_modificabile(the_user, basedir, d_prat, "A")
    info['det_b_cancellabile'] = not check_determina_cancellabile(the_user, basedir, d_prat, "B")
    info['det_b_modificabile'] = not check_determina_modificabile(the_user, basedir, d_prat, "B")
    info['ord_a_modificabile'] = not check_ordine_modificabile(the_user, basedir, d_prat, "A")
    info['ord_b_modificabile'] = not check_ordine_modificabile(the_user, basedir, d_prat, "B")
    info['rdo_modificabile'] = not check_rdo_modificabile(the_user, basedir, d_prat)
    info['pratica_annullabile'] = not check_pratica_annullabile(the_user, d_prat)
    info['pratica_apribile'] = not check_pratica_apribile(the_user, d_prat)
    info['pratica_chiudibile'] = not check_pratica_chiudibile(the_user, basedir, d_prat)
    info['progetto_approvabile'] = not check_progetto_approvabile(the_user, basedir, d_prat)
    info['progetto_modificabile'] = not check_progetto_modificabile(the_user, basedir, d_prat)
    info['progetto_inviabile'] = not check_progetto_inviabile(the_user, basedir, d_prat)
    if info['progetto_approvabile']:
        info['progetto_inviabile'] = False
#   info['rup_nominabile'] = not check_rup_nominabile(the_user, basedir, d_prat)
    return info

def show_ordine(d_prat):               # pylint: disable=W0703,R0911
    "Stabilisce se la parte ordine deve comparire nella prima fase della pratica"
    mod_acquisto = d_prat[MOD_ACQUISTO]
    if mod_acquisto in (TRATT_MEPA_40, ):
        return 0
#   if mod_acquisto == INFER_5000:
#       return 1
#   if mod_acquisto == INFER_1000:
#       return 1
#   if mod_acquisto == SUPER_5000:
#       return 1
#   if mod_acquisto == SUPER_1000:
#       return 1
#   if mod_acquisto == RDO_MEPA:
#       return 2
#   if mod_acquisto == PROC_NEG:
#       return 2
#   if mod_acquisto == MANIF_INT:
#       return ""
    return ""

def show_faseb(_basedir, _d_prat):
    "Stabilisce se la seconda parte della pratica deve comparire sulla pagina della pratica"
    return ""
#   mod_acquisto = d_prat[MOD_ACQUISTO]
#   if mod_acquisto in (MANIF_INT, PROC_NEG, RDO_MEPA) and \
#      _test_pdf_determina(basedir, d_prat, "A"):
#       return "s"
#   return ""

def _nome_da_email(embody, prima_nome=True):
    "estrae nome da messaggio email"
    row = ft.GlobLists.USERLIST.where('email', embody.strip())
    if row:
        if prima_nome:
            return f'{row[0][2]} {row[0][1]}'
        return f'{row[0][1]}, {row[0][2]}'
    return '??, ??'

def _hrecord(username, rec):
    "generazione line di storia della pratica"
    return f'{rec} il {ft.today()} ({username})'

def _email_approv(d_prat, ritrasm):
    "Invio mail di richiesta approvazione"
    ret = ''
    if ritrasm:
        sender = CONFIG.config[EMAIL_UFFICIO]
    else:
        sender = d_prat[EMAIL_RICHIEDENTE]
    eresp = d_prat.get(EMAIL_RESPONSABILE)
    prat = d_prat[NUMERO_PRATICA]
    if eresp:
        if ritrasm:
            subj = 'Ritrasmissione progetto di acquisto.'
        else:
            subj = 'Trasmissione progetto di acquisto.'
        testo = TESTO_APPROVAZIONE%fk.request.host_url + DETTAGLIO_PRATICA
        body = testo.format(**d_prat)
        if DEBUG.local:
            webm = CONFIG.config[EMAIL_WEBMASTER]
            recipients = [webm]
            info = f"Modo debug: invio e-mail a: {webm}. Pratica {prat}"
        else:
            recipients = [eresp]
            info = f"Invio richiesta approvazione a: {eresp}. " \
                   f"Pratica {prat}. Subj: {subj}"
        ret = ft.send_email(CONFIG.config.get(SMTP_HOST), sender, recipients,
                            subj, body, debug_addr=DEBUG.email)
        if ret:
            logging.info(info)
        else:
            logging.error(info)
    else:
        logging.error("Indirizzo responsabile non disponibile. Pratica %s", prat)
    return ret

def _check_access(user_only=False):
    "Verifica accesso alla pratica"
    user = ft.login_check(fk.session)
    if not user:
        return fk.redirect(fk.url_for('login'))
    d_prat = None
    basedir = fk.session.get(BASEDIR_STR)
    err_msg = None
    if basedir:
        try:
            d_prat = tb.jload((basedir, PRAT_JFILE))
        except tb.TableException:
            err_msg = _errore_accesso(basedir)
    else:
        err_msg = _errore_basedir(user)
    if not err_msg or user_only:
        return (user, basedir, d_prat)
    fk.flash(err_msg, category="error")
    logging.error(err_msg)
    return fk.redirect(fk.url_for('start'))

def _approva_progetto(username, basedir, d_prat, sgn):
    "funzione ausiliaria per approvazione progetto"
    d_prat[FIRMA_APPROVAZIONE] = sgn
    hist = 'Progetto approvato'
    d_prat[STATO_PRATICA] = hist
    d_prat[STORIA_PRATICA].append(_hrecord(username, hist))
    tb.jsave((basedir, PRAT_JFILE), d_prat)
    fk.flash(f"L'approvazione del progetto {d_prat[NUMERO_PRATICA]} è stata"
             " correttamente registrata", category="info")

    sender = d_prat[EMAIL_RESPONSABILE]
    prat = d_prat[NUMERO_PRATICA]
    if sender:
        subj = 'Notifica approvazione progetto di acquisto. Pratica: '+prat
        body = TESTO_NOTIFICA_APPROVAZIONE.format(**d_prat)
        if DEBUG.local:
            isdebug = 'Modo debug. '
        else:
            isdebug = ''
        recipients = [CONFIG.config[EMAIL_UFFICIO]]
        if d_prat.get(EMAIL_RICHIEDENTE, '-') != d_prat.get(EMAIL_RESPONSABILE, ''):
            recipients.append(d_prat[EMAIL_RICHIEDENTE])
        ret = ft.send_email(CONFIG.config.get(SMTP_HOST), CONFIG.config.get(EMAIL_UFFICIO),
                            recipients, subj, body, debug_addr=DEBUG.email)
        if ret:
            logging.info("Inviata richiesta approvazione a %s. "
                         "Pratica %s", ', '.join(recipients), prat)
        subj = 'Conferma ricevimento approvazione progetto di acquisto. Pratica: '+prat
        hdr0 = HEADER_NOTIFICA_RESPONSABILE_WEB
        body = (hdr0+DETTAGLIO_PRATICA).format(**d_prat)

        recipients = [sender]
        ret = ft.send_email(CONFIG.config.get(SMTP_HOST), sender, recipients,
                            subj, body, debug_addr=DEBUG.email)
        if ret:
            logging.info("%sInviata conferma approvazione a %s. "
                         "Pratica %s", isdebug, ','.join(recipients), prat)
    else:
        logging.error("Indirizzo email responsabile non disponibile. Pratica %s", prat)

def word_match(ins, where):
    "funzione ausiliaria per ricerca di parole case insensitive"
    setins = frozenset((x.lower() for x in ins.split()))
    if setins:
        setwhr = frozenset((x.lower() for x in where.split()))
        return len(setins.intersection(setwhr)) == len(setins)
    return False

def sel_menu(tipo_allegato):
    "Genera voce di menu per allegati"
    return (tipo_allegato,)+TAB_ALLEGATI[tipo_allegato][1:3]

def menu_allegati_fasea(pratica):
    "Genera lista allegati in funzione del tipo di acquisto (fase A)"
    mod_acquisto = pratica[MOD_ACQUISTO]
    menu = []
#   if mod_acquisto in (MEPA, CONSIP):
#       menu.append(sel_menu(ORDINE_MEPA))
    if mod_acquisto == TRATT_MEPA_40:
        menu.append(sel_menu(PREV_TRATT_MEPA))
#   if mod_acquisto == RDO_MEPA:
#       menu = [sel_menu(LETT_INVITO_MEPA), sel_menu(LISTA_DITTE_INV)]
#   if mod_acquisto in (MEPA, RDO_MEPA, INFER_5000, SUPER_5000,
#                       INFER_1000, SUPER_1000, PROC_NEG, MANIF_INT):
#       menu.append(sel_menu(DICH_IMPOSTA_BOLLO))
#   if mod_acquisto in (INFER_5000, SUPER_5000, INFER_1000, SUPER_1000):
#       menu.append(sel_menu(OFFERTA_DITTA_A))
#       menu.append(sel_menu(LISTA_DETTAGLIATA_A))

#   menu.append(sel_menu(ALLEGATO_CIG))
    menu.append(sel_menu(ALLEGATO_GENERICO_A))
    return menu

def menu_allegati_faseb(_pratica):
    "Genera lista allegati in funzione del tipo di acquisto (fase B)"
#   mod_acquisto = pratica[MOD_ACQUISTO]
    menu = []
#   if mod_acquisto == MANIF_INT:
#       menu = [sel_menu(LETT_INVITO_B),
#               sel_menu(OFFERTA_DITTA_B),
#               sel_menu(VERBALE_GARA),
#               sel_menu(LISTA_DETTAGLIATA_B)]
#   elif mod_acquisto == RDO_MEPA:
#       menu.append(sel_menu(CAPITOLATO_RDO))
    menu.append(sel_menu(ALLEGATO_GENERICO_B))
    return menu

def _clear_conferma_chiusura(basedir, d_prat, save=True):
    "Rimuove flag conferma chiusura"
    if d_prat and CONF_CHIUSURA in d_prat:
        del d_prat[CONF_CHIUSURA]
        if save:
            tb.jsave((basedir, PRAT_JFILE), d_prat)

def clean_dict(adict):
    "Crea newdict rimuovendo da adict le chiavi che iniziano per T_"
    newdict = {}
    for key, value in adict.items():
        if not key.startswith(TEMPORARY_KEY_PREFIX):
            newdict[key] = clean_data(value)
    return newdict

def clean_list(alist):
    "Ripulisce lista"
    newlist = []
    for value in alist:
        newlist.append(clean_data(value))
    return newlist

def clean_data(somedata):
    "Ripulisce dato generico"
    if isinstance(somedata, dict):
        return clean_dict(somedata)
    if isinstance(somedata, (tuple, list)):
        return clean_list(somedata)
    return somedata

def clean_lista(rdo_data):
    "Rimuove elementi vuoti o cancellati da lista ditte"
    newlist = []
    for ditta in rdo_data[LISTA_DITTE]:
        if ditta.get("T_cancella"):
            continue
        if bool(ditta[NOME_DITTA]) or  bool(ditta[SEDE_DITTA]):
            newlist.append(ditta)
    rdo_data[LISTA_DITTE] = newlist

def _clean_name(name):
    "Pulisce nome file (rimuove '_' e estensione)"
    cleaned = name[4:]
    cleaned = os.path.splitext(cleaned)[0]
    return cleaned.replace("_", " ")

def _select(menu, key):
    "estrae dal menu la descrizione relativa a key"
    ret = ""
    for item in menu:
        if item[0] == key:
            ret = item[1]
            break
    return ret

ALL_A_MATCH = re.compile(r"A\d\d_")
ALL_B_MATCH = re.compile(r"B\d\d_")

def pratica_common(user, basedir, d_prat):
    "parte comune alle pagine relative alla pratica"
    info = check_all(user, basedir, d_prat)
    upla = fms.MyUpload(menu_allegati_fasea(d_prat))
    uplb = fms.MyUpload(menu_allegati_faseb(d_prat))
    # Workaround per aggiornare il formato dati pratica vers. 2
    if not d_prat.get(STR_MOD_ACQ) or STR_CRIT_ASS not in d_prat:
        d_prat[STR_MOD_ACQ] = _select(MENU_MOD_ACQ, d_prat.get(MOD_ACQUISTO))
        d_prat[STR_CRIT_ASS] = _select(MENU_CRIT_ASS, d_prat.get(CRIT_ASS))
        tb.jsave((basedir, PRAT_JFILE), d_prat)
    if info.get(PDF_PROGETTO):
        firma = d_prat.get(FIRMA_APPROVAZIONE)
        if firma:
            firma_file = ft.signature((basedir, PROG_PDF_FILE))
            if firma_file != firma:
                d_prat[STATO_PRATICA] = 'Approvazione non valida'
                info['alarm'] = 1
    atch_files = ft.flist(basedir, filetypes=UPLOAD_TYPES,
                          exclude=(PROG_PDF_FILE, DETA_PDF_FILE, DETB_PDF_FILE, ORD_PDF_FILE))
    info['attachA'] = [(a, _clean_name(a)) for a in atch_files if ALL_A_MATCH.match(a)]
    info['attachB'] = [(a, _clean_name(a)) for a in atch_files if ALL_B_MATCH.match(a)]
    info['faseB'] = show_faseb(basedir, d_prat)
    info['ordine'] = show_ordine(d_prat)
    info['rdo'] = 0
#   info['rdo'] = 1 if d_prat.get(MOD_ACQUISTO) == RDO_MEPA else 0
    return fk.render_template('pratica.html', info=info,
                              pratica=d_prat, uploadA=upla,
                              uploadB=uplb, sede=CONFIG.config[SEDE])

def _modifica_pratica(what):               # pylint: disable=R0912,R0915
    "parte comune alle pagine di modifica pratica"
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    user, basedir, d_prat = ret
    if what[0].lower() == 'c':      # Chiudi pratica
        is_chiud, msg = check_chiudibile_davvero(user, basedir, d_prat)
        if is_chiud:
            d_prat[STATO_PRATICA] = 'Chiusa'
            d_prat[STORIA_PRATICA].append(_hrecord(user['fullname'], 'Pratica chiusa'))
            d_prat[PRATICA_APERTA] = 0
            _clear_conferma_chiusura(basedir, d_prat, save=False)
            logging.info('Pratica %s chiusa', d_prat[NUMERO_PRATICA])
        else:
            for amsg in msg:
                fk.flash(amsg, category="chiusura")
            logging.warning('Chiusura pratica richiede conferma: %s. Utente %s, pratica %s',
                            "; ".join(msg), user['userid'], d_prat[NUMERO_PRATICA])
            d_prat[CONF_CHIUSURA] = 1
    elif what[0].lower() == 'a':     # Apri pratica
        _clear_conferma_chiusura(basedir, d_prat, save=False)
        err = check_pratica_apribile(user, d_prat)
        if err:
            fk.flash(err, category="error")
            logging.error('Apertura pratica non autorizzata: %s. Utente %s, pratica %s',
                          "; ".join(msg), user['userid'], d_prat[NUMERO_PRATICA])
        else:
            d_prat[STATO_PRATICA] = 'Aperta'
            d_prat[STORIA_PRATICA].append(_hrecord(user['fullname'], 'Pratica riaperta'))
            d_prat[PRATICA_APERTA] = 1
            logging.info('Pratica %s riaperta', d_prat[NUMERO_PRATICA])
    elif what[0].lower() == 'r':    # Invio progetto per approvazione
        _clear_conferma_chiusura(basedir, d_prat, save=False)
        err = check_progetto_inviabile(user, basedir, d_prat)
        if err:
            fk.flash(msg, category="error")
            logging.error('Invio progetto non autorizzato: %s. Utente %s, pratica %s',
                          msg, user['userid'], d_prat[NUMERO_PRATICA])
        else:
            d_prat[FIRMA_APPROVAZIONE] = ""
            ret = _email_approv(d_prat, True)
            if ret:
                d_prat[STATO_PRATICA] = ATTESA_APPROVAZIONE
                d_prat[STORIA_PRATICA].append(_hrecord(user['fullname'],
                                                       'Progetto inviato per approvazione'))
                d_prat[PROGETTO_INVIATO] = 1
                msg = 'Inviata richiesta approvazione pratica ' \
                      f'{d_prat[NUMERO_PRATICA]} a: {d_prat[NOME_RESPONSABILE]}'
                logging.info(msg)
                fk.flash(msg, category='info')
    elif what[0].lower() == 'n':    # Annulla pratica
        _clear_conferma_chiusura(basedir, d_prat, save=False)
        err = check_pratica_annullabile(user, d_prat)
        if err:
            fk.flash(err, category="error")
            logging.error('Annullamento pratica non autorizzato: %s. Utente %s, pratica %s',
                          "; ".join(msg), user['userid'], d_prat[NUMERO_PRATICA])
        else:
            d_prat[PRATICA_ANNULLATA] = 1
            d_prat[STATO_PRATICA] = 'Annullata'
            d_prat[STORIA_PRATICA].append(_hrecord(user['fullname'],
                                                   'Pratica annullata e chiusa'))
            d_prat[CONF_CHIUSURA] = 0
            d_prat[PRATICA_APERTA] = 0
            logging.info('Pratica %s annullata', d_prat[NUMERO_PRATICA])
    tb.jsave((basedir, PRAT_JFILE), d_prat)
    return fk.redirect(fk.url_for('pratica1'))

def _delete_field(d_prat, field):
    "Cancella un campo della pratica"
    try:
        del d_prat[field]
    except KeyError:
        pass

def _aggiornaformato():
    "Chiamata quando è richiesto aggiornamento del formato pratica"
    fk.flash("Per procedere alle modifiche è necessario "
             "l'aggiornamento del formato", category="info")
    return fk.redirect(fk.url_for('aggiornaformato'))

def _avvisi_allegati(basedir, d_prat, fase):
    "Genera elenco avvisi relativi agli allegati"
    ret = []
    if not _test_pdf_preventivo_mepa(basedir, d_prat, fase):
        ret.append("Manca allegato preventivo MePA")
#   if not _test_pdf_lista_ditte_invitate(basedir, d_prat, fase):
#       ret.append("Manca Lista ditte invitate")
#   if not _test_pdf_capitolato_rdo(basedir, d_prat, fase):
#       ret.append("Manca capitolato per RDO")
#   if not _test_pdf_offerta_ditta(basedir, d_prat, fase):
#       ret.append("Mancano offerte")
#   if not _test_pdf_lettera_invito(basedir, d_prat, fase):
#       ret.append("Mancano lettere invito")
#   if not _test_pdf_ordine_mepa(basedir, d_prat, fase):
#       ret.append("Manca Bozza d'ordine MEPA")
#   if not _test_pdf_trattativa_mepa(basedir, d_prat, fase):
#       ret.append("Manca offerta da trattativa diretta su MEPA")
    return ret

def _avvisi(_unused, basedir, d_prat, fase, level=0):
    "Genera messaggi di avviso per pagina pratica. level=0: tutti; level=1: errori"
    avvisi = _avvisi_allegati(basedir, d_prat, fase)
    ret = len(avvisi)
    for avviso in avvisi:
        fk.flash(avviso, category="error")
    if level < 1:
        if d_prat[MOD_ACQUISTO] in (MEPA, CONSIP):
            fk.flash("La Bozza d'ordine MEPA deve essere trasmessa "
                     "al Punto Ordinante", category="info")
        fk.flash("Occorre richiedere l'approvazione del responsabile dei fondi", category="info")
    return ret

def _pratica_ascendente(item):
    "funzione ausiliaria per sort pratiche"
    nprat = item.get(NUMERO_PRATICA, '0/0').split('/')[0]
    return int(nprat)

def _render_progetto(form, d_prat):
    "rendering del form progetto di acquisto"
    ddp = {'title': 'Progetto di acquisto',
           'subtitle': f"Pratica N. {d_prat['numero_pratica']}<br><br>"
                       f"Richiedente: {d_prat['nome_richiedente']}",
           'before': '<form method=POST action=/modificaprogetto '
                     'accept-charset="utf-8" novalidate>',
           'after': '</form>',
           'note': OBBLIGATORIO,
           'body': form.renderme()}
    return fk.render_template("form_layout.html", sede=CONFIG.config[SEDE], data=ddp)

def _genera_pratica(user):
    "Genera pratica temporanea vuota"
    d_prat = {VERSIONE: FILE_VERSION,
              NUMERO_PRATICA: '-------',
              EMAIL_RICHIEDENTE: user['email'],
              NOME_RICHIEDENTE: user['name']+' '+user['surname'],
              DATA_RICHIESTA: ft.today(False),
              PRATICA_APERTA: 1}
    logging.info("Creata nuova pratica (temporanea)")
    return d_prat

def filename_allegato(model, prefix, origname, ext, spec, d_prat):    # pylint: disable=R0913
    "Genera nomi file per allegati"
    if model == ALL_SING:
        name = prefix+ext
    elif model == ALL_SPEC:
        if spec:
            cspec = spec.strip("/\\?!;,><|#*\"'$%&£()`§")
            cspec = cspec.replace(" ", "_")
            name = f"{prefix}_({cspec}){ext}"
        else:
            name = ""
    elif model == ALL_NAME:
        name = prefix+origname+ext
    elif model == ALL_PRAT:
        nprat = d_prat[NUMERO_PRATICA].replace("/", "-")
        name = f"{prefix}_{nprat}{ext}"
    else:
        raise ILL_ATCH
    return name

def _rdo_validate(dati_pratica):
    "Verifica coerenza dati relativi a RDO su MEPA"
    errors = []
    vincitore = [x for x in dati_pratica[LISTA_DITTE] if x.get("vincitore")]
    if vincitore:
        if len(vincitore) > 1:
            errors.append("Sono state indicate più ditte vincitrici")
            vincitore = {}
        else:
            vincitore = vincitore[0]
    else:
        vincitore = {}
    return errors, vincitore

def _errore_basedir(user):
    "Segnala errore sessione"
    return "basedir assente in sessione. User: "+user['userid']

def _errore_accesso(basedir):
    "Segnala errore di accesso"
    return "Errore accesso alla directory: "+basedir

def _errore_doclist(anno):
    "segnala errore lista documenti"
    return f"Errore DocList, anno {anno}. Forse una directory per pratica vuota?"

def _menu_scelta_utente(topline):
    "genera menù per acelta utente"
    menulist = [(x[4], x[6]) for  x in ft.GlobLists.USERLIST.rows]
    menulist.sort(key=lambda x: x[1])
    menulist.insert(0, ('', f'-- {topline} --'))
    return menulist

def _nome_resp(ulist, eaddr, prima_nome=True):
    if prima_nome:
        return f"{ulist.get(eaddr, ['', '', '??', '??'])[3]} " \
               f"{ulist.get(eaddr, ['', '??', '??'])[2]}"
    return f"{ulist.get(eaddr, ['', '', '??', '??'])[2]}, " \
           f"{ulist.get(eaddr, ['', '??', '??'])[3]}"

def modificadetermina_a(user, basedir, d_prat):
    "pagina: modifica determina fase A"
    if NUMERO_DETERMINA_A not in d_prat:
        year = ft.thisyear()
        ndet = ft.find_max_det(year)[0]+1
        d_prat[NUMERO_DETERMINA_A] = f"{ndet}/{year:4d}"
        d_prat[DATA_DETERMINA_A] = ft.today(False)
        d_prat[NOME_DIRETTORE] = CONFIG.config[NOME_DIRETTORE]
        d_prat[DIRETTORE_M] = CONFIG.config[GENDER_DIRETTORE][:1].lower() == 'm'
        logging.info("Nuovo num. determina: %s", d_prat[NUMERO_DETERMINA_A])
    det = fms.DeterminaA(fk.request.form, **d_prat)
    det.email_rup.choices = _menu_scelta_utente("Seleziona RUP")
    if fk.request.method == 'POST':
        if det.validate():
            d_prat.update(clean_data(det.data))
            d_prat[NOME_RUP] = _nome_da_email(d_prat[EMAIL_RUP], True)
            d_prat[TITOLO_DIRETTORE] = CONFIG.config[TITOLO_DIRETTORE]
            logging.info('Genera determina: %s/%s', basedir, DETA_PDF_FILE)
            det_template = ft.modello_determinaa(d_prat[MOD_ACQUISTO])
            det_name = os.path.splitext(DETA_PDF_FILE)[0]
            ft.makepdf(basedir, det_template, det_name, sede=CONFIG.config[SEDE],
                       debug=DEBUG.local, pratica=d_prat, user=user)
            d_prat[STORIA_PRATICA].append(_hrecord(user['fullname'],
                                                   'Determina generata'))
            ft.remove((basedir, ORD_PDF_FILE), show_error=False)
            d_prat[PDF_ORDINE] = ''
            d_prat[PDF_DETERMINA_A] = DETA_PDF_FILE
            tb.jsave((basedir, PRAT_JFILE), d_prat)
            url = fk.url_for('pratica1')
            return fk.redirect(url)
        errors = det.get_errors()
        for err in errors:
            fk.flash(err, category="error")
        logging.debug("Errori form DeterminaA: %s", "; ".join(errors))

    ddp = {'title': 'Immissione dati per determina',
           'subtitle': f"Pratica N. {d_prat['numero_pratica']}",
           'before': '<form method=POST action=/modificadetermina/A '
                     'accept-charset="utf-8" novalidate>',
           'after': "</form>",
           'note': OBBLIGATORIO,
           'body': det.renderme(d_prat)}
    return fk.render_template('form_layout.html', sede=CONFIG.config[SEDE], data=ddp)

def modificadetermina_b(user, basedir, d_prat):
    "pagina: modifica determina fase B"
    errors, vincitore = _rdo_validate(d_prat)
    if errors:
        for err in errors:
            fk.flash(err, category="error")
        logging.debug("Pratica RDO non completa: %s", "; ".join(errors))
        return fk.redirect(fk.url_for('pratica1'))
    d_prat[VINCITORE] = vincitore
    if NUMERO_DETERMINA_B not in d_prat:
        year = ft.thisyear()
        ndet = ft.find_max_det(year)[0]+1
        d_prat[NUMERO_DETERMINA_B] = f"{ndet}/{year:4d}"
        d_prat[DATA_DETERMINA_B] = ft.today(False)
        d_prat[NOME_DIRETTORE_B] = d_prat[NOME_DIRETTORE]
        logging.info("Nuovo num. determina B: %s", d_prat[NUMERO_DETERMINA_B])
    det = fms.DeterminaB(fk.request.form, vincitore=bool(vincitore), **d_prat)
    if fk.request.method == 'POST':
        if det.validate():
            d_prat.update(clean_data(det.data))
            ft.remove((basedir, ORD_PDF_FILE), show_error=False)
            d_prat[PDF_ORDINE] = ''
            d_prat[PDF_DETERMINA_B] = DETB_PDF_FILE
            d_prat[FINE_GARA_GIORNO], d_prat[FINE_GARA_ORE] = d_prat[FINE_GARA].split()
            d_prat[STR_PREZZO_GARA] = ft.stringa_costo(d_prat.get(PREZZO_GARA), "it")
            d_prat[STR_ONERI_IT] = ft.stringa_valore(d_prat.get(ONERI_SIC_GARA), "it")
            tb.jsave((basedir, PRAT_JFILE), d_prat)
            logging.info('Genera determina: %s/%s', basedir, DETB_PDF_FILE)
            det_template = os.path.splitext(DETB_PDF_FILE)[0]
            det_name = det_template
            ft.makepdf(basedir, det_template, det_name, sede=CONFIG.config[SEDE],
                       debug=DEBUG.local, pratica=d_prat, user=user)
            d_prat[STORIA_PRATICA].append(_hrecord(user['fullname'],
                                                   'Generata determina B'))
            return fk.redirect(fk.url_for('pratica1'))
        errors = det.get_errors()
        for err in errors:
            fk.flash(err, category="error")
        logging.debug("Errori form DeterminaB: %s", "; ".join(errors))

    ddp = {'title': 'Immissione dati per determina',
           'subtitle': f"Pratica N. {d_prat['numero_pratica']}",
           'before': '<form method=POST action=/modificadetermina/B '
                     'accept-charset="utf-8" novalidate>',
           'after': "</form>",
           'note': OBBLIGATORIO,
           'body': det.renderme(d_prat)}
    return fk.render_template('form_layout.html', sede=CONFIG.config[SEDE], data=ddp)


ACQ = fk.Flask(__name__, template_folder=FILEDIR, static_folder=FILEDIR)

@ACQ.before_request
def before():
    "procedura da eseguire prima di ogni pagina"
    ft.set_host_info(fk.request.remote_addr)
    update_lists()

@ACQ.route("/")
def start():
    "pagina: iniziale"
    logging.info('URL: / (%s)', fk.request.method)
    user = ft.login_check(fk.session)
    if not user:
        return fk.redirect(fk.url_for('login'))
    fk.session[BASEDIR_STR] = ''
    rooturl = ft.host(fk.request.url_root)
    status = {'url0': rooturl, 'footer': 'Procedura '+long_version()}
    if _test_admin(user):
        status['admin'] = 1
    if _test_developer(user):
        status['developer'] = 1
    return fk.render_template('start_acquisti.html', sede=CONFIG.config[SEDE],
                              user=user, status=status)

@ACQ.route("/about")
def about():                                 # pylint: disable=R0915
    "pagina: informazioni sulle procedure"
    logging.info('URL: /about (%s)', fk.request.method)
    user = ft.login_check(fk.session)
    if not user:
        return fk.redirect(fk.url_for('login'))
    html = []
    html.append('<table cellpadding=3 border=1>')
    html.append('<tr><th colspan=2> Parametri di sistema </th></tr>')
    pinfo = ft.procinfo()
    for pinf in pinfo:
        html.append(f'<tr><td><b>{pinf[0]}</b></td><td> {pinf[1]} </td></tr>')
    html.append(f'<tr><td><b>Root path</b></td><td> {PKG_ROOT} </td></tr>')
    html.append(f'<tr><td><b>Start</b></td><td> {__start__} </td></tr>')
    html.append('</table></td></tr>')
    html.append('<tr><td><table cellpadding=3 border=1>')
    html.append('<tr><th colspan=4> Informazioni sui moduli </td></tr>')
    html.append('<tr><th>Modulo</th><th>Versione</th><th>Data</th><th>Autore</th></tr>')
    fmt = '<tr><td> <tt> {} </tt></td><td> {} </td><td>{}</td> <td> {} </td></tr>'
    html.append(fmt.format('acquisti.py', __version__, __date__, __author__))
    html.append(fmt.format('constants.py', const.__version__, const.__date__, const.__author__))
    html.append(fmt.format('forms.py', fms.__version__, fms.__date__, fms.__author__))
    html.append(fmt.format('ftools.py', ft.__version__, ft.__date__, ft.__author__))
    html.append(fmt.format('latex.py', ft.latex.__version__,
                           ft.latex.__date__, ft.latex.__author__))
    html.append(fmt.format('table.py', ft.tb.__version__, ft.tb.__date__, ft.tb.__author__))
    html.append(fmt.format('Flask', fk.__version__, '-',
                           'Vedi: <a href=http://flask.pocoo.org>Flask home</a>'))
    html.append(fmt.format('WtForms', wt.__version__, '-',
                           'Vedi: <a href=https://wtforms.readthedocs.org>WtForms home</a>'))
    html.append('</table></td></tr>')
    if _test_admin(user):
        html.append('<tr><td><table cellpadding=3 border=1>')
        html.append('<tr><th colspan=2> Path rilevanti </th></tr>')
        html.append(f'<tr><td><b>PKG_ROOT</b></td><td>{PKG_ROOT}</td></tr>')
        html.append(f'<tr><td><b>DATADIR</b></td><td>{DATADIR}</td></tr>')
        html.append(f'<tr><td><b>WORKDIR</b></td><td>{WORKDIR}</td></tr>')
        html.append(f'<tr><td><b>FILEDIR</b></td><td>{FILEDIR}</td></tr>')
        html.append('</table></td></tr>')

        cks = list(CONFIG.config.keys())
        cks.sort()
        html.append('<tr><td><table cellpadding=3 border=1>')
        config_spec = f'{CONFIG_FILE}, letto: {time.asctime(time.localtime(CONFIG.time))}'
        html.append(f'<tr><th colspan=2> File di configurazione ({config_spec})  </th></tr>')
        for key in cks:
            html.append(f'<tr><td><b>{key}</b></td><td>{CONFIG.config[key]}</td></tr>')
        html.append('</table></td></tr>')

        html.append('<tr><td><table cellpadding=3 border=1>')
        html.append('<tr><th> Lista files di help </th></tr>')
        html.append('<tr><td>'+', '.join(ft.GlobLists.HELPLIST)+'</td></tr>')
        html.append('</table></td></tr>')

    body = '\n'.join(html)
    return fk.render_template('about.html', sede=CONFIG.config[SEDE], data=body)

@ACQ.route("/clearsession")
def clearsession():
    "pagina: logout"
    logging.info('URL: /clearsession (%s)', fk.request.method)
    fk.session.clear()
    return fk.redirect(fk.url_for('login'))

@ACQ.route("/login", methods=['GET', 'POST'])
def login():
    "pagina: login"
    logging.info('URL: /login (%s)', fk.request.method)
    if os.stat(CONFIG_FILE).st_mtime > CONFIG.time:
        CONFIG.time = time.time()
        CONFIG.config = tb.jload(CONFIG_FILE)
        logging.info('Riletta configurazione aggiornata')
    uid = fk.request.form.get('userid')
    pwd = fk.request.form.get('password')
    form = fms.MyLoginForm(DATADIR, uid, pwd, CONFIG.config.get(LDAP_HOST),
                           CONFIG.config.get(LDAP_PORT), formdata=fk.request.form)
    if fk.request.method == 'POST' and form.validate():
        ret, why = form.password_ok()
        if ret:
            fk.session['userid'] = fk.request.form['userid']
            return fk.redirect(fk.url_for('start'))
        logging.error('Accesso negato: userid: "%s" (%s)', uid, why)
        fk.flash(f'Accesso negato: {why}', category="error")
    return fk.render_template('login.html', form=form, sede=CONFIG.config[SEDE],
                              title='Procedura per acquisti')

@ACQ.route('/modificaprogetto', methods=('GET', 'POST'))
def modificaprogetto():               # pylint: disable=R0912,R0915,R0911
    "pagina: modifica progetto"
    logging.info('URL: /modificaprogetto (%s)', fk.request.method)
    ret = _check_access(user_only=True)
    if not isinstance(ret, tuple):
        return ret
    user, basedir, d_prat = ret
    _clear_conferma_chiusura(basedir, d_prat)
    if not d_prat:
        print_debug('Genera nuova pratica per:', user['userid'])
        d_prat = _genera_pratica(user)
    else:
        err = check_progetto_modificabile(user, basedir, d_prat)
        if err:
            fk.flash(err, category="error")
            logging.error('Modifica progetto non possibile: %s. Utente:%s pratica %s',
                          err, user['userid'], d_prat[NUMERO_PRATICA])
            return fk.redirect(fk.url_for('pratica1'))
    if d_prat.get(VERSIONE, 0) == 0:
        raise RuntimeError("Formato file pratica obsoleto in modificaprogetto")
    racq = fms.ProgettoAcquisto(fk.request.form, **d_prat)
    codfs = ft.GlobLists.CODFLIST.column('Codice', unique=True)
    codf_menu = list(zip(codfs, codfs))
    racq.lista_codf.choices = codf_menu
    racq.email_responsabile.choices = _menu_scelta_utente("Seleziona responsabile")
    if not racq.lista_codf.data:    # Workaroud per errore wtform (non aggiorna campo)
        racq.lista_codf.process_data(d_prat.get("lista_codf", []))
    if fk.request.method == 'POST':
        print_debug('Request data:', fk.request.form)
        if ANNULLA in fk.request.form:
            fk.flash('Operazione annullata', category="info")
            if SAVED in d_prat:
                return fk.redirect(fk.url_for('pratica1'))
            return fk.redirect(fk.url_for('start'))
        mod_acquisto = fk.request.form.get(MOD_ACQUISTO)
        print_debug('Modalità acquisto:', mod_acquisto)
        if mod_acquisto not in MODALITA_IMPLEMENTATE:
            fk.flash('Modalità di acquisto non ancora implementata', category="error")
            return fk.redirect(fk.url_for('start'))
        if racq.validate():
            if STORIA_PRATICA not in d_prat:
                year = ft.thisyear()
                number = ft.find_max_prat(year)+1
                basedir = ft.namebasedir(year, number)
                fk.session[BASEDIR_STR] = basedir
                ft.newdir(basedir)
                d_prat.update({NUMERO_PRATICA: f'{number}/{year:4d}',
                               STORIA_PRATICA: [_hrecord(user['fullname'],
                                                         'Progetto generato')],
                               DATA_RICHIESTA: ft.today(False)})
            else:
                d_prat[STORIA_PRATICA].append(_hrecord(user['fullname'],
                                                       'Progetto modificato'))
            d_prat.update(clean_data(racq.data))
            d_prat[STR_CODF] = ', '.join(d_prat[LISTA_CODF])
            d_prat[STR_COSTO_IT] = ft.stringa_costo(d_prat.get(COSTO), "it")
            d_prat[STR_COSTO_UK] = ft.stringa_costo(d_prat.get(COSTO), "uk")
            d_prat[STR_ONERI_IT] = ft.stringa_valore(d_prat.get(ONERI_SICUREZZA), "it")
            d_prat[STR_ONERI_UK] = ft.stringa_valore(d_prat.get(ONERI_SICUREZZA), "uk")
            d_prat[STR_MOD_ACQ] = _select(MENU_MOD_ACQ, d_prat.get(MOD_ACQUISTO))
            d_prat[STR_CRIT_ASS] = _select(MENU_CRIT_ASS, d_prat.get(CRIT_ASS))
            d_prat[NOME_RESPONSABILE] = _nome_da_email(d_prat[EMAIL_RESPONSABILE], True)
            d_prat[SEDE] = CONFIG.config[SEDE]
            d_prat[CITTA] = CONFIG.config[SEDE][CITTA]
            d_prat[STATO_PRATICA] = ATTESA_APPROVAZIONE
            d_prat[PROGETTO_INVIATO] = 0
            d_prat[FIRMA_APPROVAZIONE] = ""
            d_prat[SAVED] = 1
            d_prat[CONF_CHIUSURA] = 0
            tb.jsave((basedir, PRAT_JFILE), d_prat)
            logging.info('Salvati dati pratica: %s/%s', basedir, PRAT_JFILE)
            prog_name = os.path.splitext(PROG_PDF_FILE)[0]
            ft.makepdf(basedir, prog_name, prog_name,
                       debug=DEBUG.local, pratica=d_prat, sede=CONFIG.config[SEDE])
            ft.remove((basedir, DETA_PDF_FILE), show_error=False)
            ft.remove((basedir, DETB_PDF_FILE), show_error=False)
            ft.remove((basedir, ORD_PDF_FILE), show_error=False)
            logging.info('Generato progetto: %s/%s', basedir, PROG_PDF_FILE)
            _avvisi(user, basedir, d_prat, "A")
            return fk.redirect(fk.url_for('pratica1'))
        errors = racq.get_errors()
        for err in errors:
            fk.flash(err, category="error")
        logging.debug("Errori form Progetto di acquisto: %s", "; ".join(errors))
    return _render_progetto(racq, d_prat)

@ACQ.route('/verificaallegati/<fase>')
def verificaallegati(fase):
    "Emette avviso sullo stato degli allegati"
    logging.info('URL: /verificaallegati/{fase} ({fk.request.method})')     #pylint: disable=W1203
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    user, basedir, d_prat = ret
    _clear_conferma_chiusura(basedir, d_prat)
    if not _avvisi(user, basedir, d_prat, fase, level=1):
        fk.flash("Allegati OK", category="info")
    return pratica_common(user, basedir, d_prat)

@ACQ.route('/inviaprogetto')
def inviaprogetto():
    "pagina: invia progetto"
    logging.info('URL: /inviaprogetto (%s)', fk.request.method)
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    user, basedir, d_prat = ret
    _clear_conferma_chiusura(basedir, d_prat)
    err = check_progetto_inviabile(user, basedir, d_prat)
    if err:
        fk.flash(err, category="error")
        logging.error('Invio fallito: %s. Utente: %s pratica %s', err,
                      user['userid'], d_prat[NUMERO_PRATICA])
    else:
        ret = _email_approv(d_prat, False)
        if ret:
            if d_prat[MOD_ACQUISTO] in (MEPA, CONSIP):
                fk.flash("Ricorda di trasmettere la bozza d'ordine MEPA al "
                         "\"Punto Ordinante\"", category="info")
            fk.flash("Richiesta di approvazione per  la pratica "
                     f"{d_prat[NUMERO_PRATICA]} inviata a: "
                     f"{d_prat.get(EMAIL_RESPONSABILE, 'IND.NON DISPONIBILE')}", category="info")
            d_prat[PROGETTO_INVIATO] = 1
            d_prat[STATO_PRATICA] = ATTESA_APPROVAZIONE
            d_prat[STORIA_PRATICA].append(_hrecord(user['fullname'],
                                                   'Inviata richiesta approvazione'))
            tb.jsave((basedir, PRAT_JFILE), d_prat)
        else:
            msg = "Invio per approvazione fallito"
            fk.flash(msg, category="error")
            logging.error("Errore invio approvazione - Pratica: %s, EMail resp: %s",
                          d_prat[NUMERO_PRATICA], d_prat[EMAIL_RESPONSABILE])
    return fk.redirect(fk.url_for('pratica1'))

@ACQ.route('/approvaprogetto')
def approvaprogetto():
    "pagina: approva progetto"
    logging.info('URL: /approvaprogetto (%s)', fk.request.method)
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    user, basedir, d_prat = ret
    _clear_conferma_chiusura(basedir, d_prat)
    sgn = ft.signature((basedir, PROG_PDF_FILE))
    err = check_progetto_approvabile(user, basedir, d_prat)
    if err:
        fk.flash(err, category="error")
        logging.error('Approvazione non autorizzata: %s. Utente %s pratica %s',
                      err, user['userid'], d_prat[NUMERO_PRATICA])
    else:
        _approva_progetto(user.get('fullname'), basedir, d_prat, sgn)
    return fk.redirect(fk.url_for('pratica1'))

#@ACQ.route('/rup/<oper>', methods=('GET', 'POST'))
#def rup(oper):
#    "pagina: nomina/cancella RUP"
#    logging.info(f'URL: /rup/{oper} ({fk.request.method})')     #pylint: disable=W1203
#    ret = _check_access()
#    if not isinstance(ret, tuple):
#        return ret
#    user, basedir, d_prat = ret
#    _clear_conferma_chiusura(basedir, d_prat)
#    if oper == 'cancella':
#        err = check_rup_cancellabile(user, d_prat)
#        if err:
#            fk.flash(err, category="error")
#            logging.error('Cancellazione RUP non autorizzata: %s. Utente %s pratica %s',
#                          err, user['userid'], d_prat[NUMERO_PRATICA])
#            return pratica1()
#        if EMAIL_RUP in d_prat:
#            msg = f"RUP: {d_prat[NOME_RUP]} cancellato"
#            logging.info(msg)
#            del d_prat[EMAIL_RUP]
#            del d_prat[NOME_RUP]
#            tb.jsave((basedir, PRAT_JFILE), d_prat)
#            fk.flash(msg, category="info")
#        return pratica1()
#    if oper == 'nomina':
##        rupf = fms.NominaRUP(fk.request.form)
#        rupf.email_rup.choices = _menu_scelta_utente("Seleziona RUP")
#        if fk.request.method == 'POST':
#            if rupf.validate():
#                d_prat[EMAIL_RUP] = rupf.email_rup.data
#                d_prat[NOME_RUP] = _nome_da_email(d_prat[EMAIL_RUP], True)
#                tb.jsave((basedir, PRAT_JFILE), d_prat)
#                msg = f"{d_prat[NOME_RUP]} nominato RUP per pratica {d_prat[NUMERO_PRATICA]}"
#                logging.info(msg)
#                fk.flash(msg, category='info')
#                return pratica1()
#            fk.flash('Scelta RUP non valida', category="error")
#        ddp = {'title': 'Nomina RUP',
#               'before': '<form method=POST action=/rup/nomina '
#                         'accept-charset="utf-8" novalidate>',
#               'after': '</form>',
#               'note': 'QUesta è una nota',
#               'body': rupf.renderme()}
#        return fk.render_template('form_layout.html', sede=CONFIG.config[SEDE], data=ddp)
#    raise RuntimeError('rup: operazione errata')

@ACQ.route('/cancella/<name>', methods=('GET', 'POST'))
def cancella(name):
    "pagina: cancella allegato"
    logging.info(f'URL: /cancella/{name} ({fk.request.method})')     #pylint: disable=W1203
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    user, basedir, d_prat = ret
    _clear_conferma_chiusura(basedir, d_prat)
    err = check_allegati_cancellabili(user, d_prat)
    if err:
        fk.flash(err, category="error")
        logging.error('Rimozione allegato non autorizzata: %s. Utente %s pratica %s',
                      err, user['userid'], d_prat[NUMERO_PRATICA])
    else:
        d_prat[STORIA_PRATICA].append(_hrecord(user['fullname'], f'Rimosso allegato {name}'))
        ft.remove((basedir, name))
    tb.jsave((basedir, PRAT_JFILE), d_prat)
    return pratica1()

@ACQ.route('/vedicodf')
def vedicodf():
    "pagine: visualizza lista codici fondo"
    logging.info('URL: /vedicodf (%s)', fk.request.method)
    return ft.GlobLists.CODFLIST.render(title="Lista Codici fondi e responsabili")

@ACQ.route('/vedifile/<filename>')
def vedifile(filename):
    "pagina: visualizza file PDF"
    logging.info('URL: /vedifile/{filename} ({fk.request.method})')     #pylint: disable=W1203
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    basedir, d_prat = ret[1:]
    _clear_conferma_chiusura(basedir, d_prat)
    return fk.send_from_directory(basedir, filename, as_attachment=True)

@ACQ.route('/pratiche/<stato>/<anno>/<ascendente>')
def lista_pratiche(stato, anno, ascendente):
    "pagina: lista pratiche"
    logging.info('URL: /pratiche/{stato}/{anno}/{ascendente} ({fk.request.method})')     #pylint: disable=W1203
    user = ft.login_check(fk.session)
    if not user:
        return fk.redirect(fk.url_for('login'))
    fk.session[BASEDIR_STR] = ''
    anno = int(anno)
    if not anno:
        anno = ft.thisyear()

    if int(ascendente):
        sort_funct = _pratica_ascendente
    else:
        sort_funct = lambda x: -1*_pratica_ascendente(x)

    if stato[:3] == 'ALL' and not _test_admin(user):
        logging.error('Visualizzazione pratiche non autorizzata. Utente: %s', user['userid'])
        fk.session.clear()
        return fk.render_template('noaccess.html', sede=CONFIG.config[SEDE])
    if stato[-1] == 'A':
        filtac = lambda x: x.get(PRATICA_APERTA)
        title = 'Elenco pratiche aperte'
    else:
        filtac = lambda x: not x.get(PRATICA_APERTA)
        title = 'Elenco pratiche chiuse'
    if stato[:3] == 'RIC':
        filtsb = lambda x: _test_richiedente(user, x)
        title += ' come richiedente'
    elif stato[:3] == 'RES':
        filtsb = lambda x: _test_responsabile(user, x)
        title += ' come resp. dei fondi'
    elif stato[:3] == 'RUP':
        filtsb = lambda x: _test_rup(user, x)
        title += ' come RUP'
    else:
        filtsb = lambda x: True
    filt = lambda x: filtac(x) and filtsb(x)
    try:
        doclist = ft.DocList(DATADIR, PRAT_JFILE, anno, content_filter=filt, sort=sort_funct)
    except Exception:               # pylint: disable=W0703
        err_msg = _errore_doclist(anno)
        fk.flash(err_msg, category="error")
        logging.error(err_msg)
        return fk.redirect(fk.url_for('start'))
    theyear = int(anno)
    years = [int(y) for y in doclist.years]
    return fk.render_template('lista_pratiche_per_anno.html', stato=stato,
                              sede=CONFIG.config[SEDE], years=years, year=theyear,
                              dlist=doclist.records, title=title)

@ACQ.route('/trovapratica', methods=('POST', 'GET'))
def trovapratica():               # pylint: disable=R0912,R0914,R0915
    "pagina: trova pratica"
    logging.info('URL: /trovapratica (%s)', fk.request.method)
    user = ft.login_check(fk.session)
    if not user:
        return fk.redirect(fk.url_for('login'))
    fk.session[BASEDIR_STR] = ''
    if _test_admin(user):
        if ANNULLA in fk.request.form:
            fk.flash('Operazione annullata', category="info")
            return fk.redirect(fk.url_for('start'))
        prf = fms.TrovaPratica(fk.request.form)
        user_menu = [(x[6], x[6]) for  x in ft.GlobLists.USERLIST.rows]
        user_menu.sort(key=lambda x: x[1])
        user_menu.insert(0, ('*', 'Tutti'))
        prf.trova_responsabile.choices = user_menu
        prf.trova_richiedente.choices = user_menu
        years = ft.get_years(DATADIR)
        years.sort(reverse=True)
        year_menu = list(zip(years, years))
        prf.trova_anno.choices = year_menu
        if fk.request.method == 'POST':
            theyear = prf.data['trova_anno']
            ricerca = f" anno={prf.data['trova_anno']} + (pratiche "
            vaperta = int(prf.data.get('trova_prat_aperta', '-1'))
            if vaperta == 1:
                ricerca += 'aperte)'
                aperta_func = lambda x: x.get(PRATICA_APERTA, 0) == 1
            elif vaperta == 0:
                ricerca += 'chiuse)'
                aperta_func = lambda x: x.get(PRATICA_APERTA, 1) == 0
            else:
                ricerca += 'aperte e chiuse)'
                aperta_func = lambda x: True
            nome_resp = prf.data['trova_responsabile']
            if nome_resp:
                resp_func = lambda x: word_match(nome_resp,
                                                 x.get(NOME_RESPONSABILE, ''))
                ricerca += f' + (resp.={nome_resp})'
            else:
                resp_func = lambda x: True
            nome_rich = prf.data['trova_richiedente']
            if nome_rich:
                rich_func = lambda x: word_match(nome_rich,
                                                 x.get(NOME_RICHIEDENTE, ''))
                ricerca += f' + (richied.={nome_rich})'
            else:
                rich_func = lambda x: True
            if prf.data['trova_parola']:
                parola_func = lambda x: word_match(prf.data.get('trova_parola', ''),
                                                   x.get(DESCRIZIONE_ACQUISTO, ''))
                ricerca += f" + (contiene parola={prf.data['trova_parola']})"
            else:
                parola_func = lambda x: True
            selector = lambda x: aperta_func(x) and rich_func(x) and resp_func(x) and parola_func(x)
            if prf.data['elenco_ascendente']:
                sort_func = _pratica_ascendente
            else:
                sort_func = lambda x: -1*_pratica_ascendente(x)

            try:
                lista = ft.DocList(DATADIR, PRAT_JFILE, theyear,
                                   content_filter=selector, sort=sort_func)
            except Exception:               # pylint: disable=W0703
                err_msg = _errore_doclist(theyear)
                fk.flash(err_msg, category="error")
                logging.error(err_msg)
                return fk.redirect(fk.url_for('start'))
            title = 'Trova Pratiche'
            subtitle = 'Risultato per ricerca: '+ricerca+'<br>'+ \
                       f'N. pratiche selezionate: {len(lista)}'
            return fk.render_template('lista_pratiche_per_anno.html', stato='', pre=[],
                                      post=[], year=theyear, dlist=lista.records, title=title,
                                      sede=CONFIG.config[SEDE], subtitle=subtitle)
        ddp = {'title': 'Trova pratiche',
               'subtitle': 'Specifica criteri di ricerca',
               'before': '<form method=POST action=/trovapratica '
                         'accept-charset="utf-8" novalidate>',
               'after': '</form>',
               'body': prf.renderme()}
        return fk.render_template('form_layout.html', sede=CONFIG.config[SEDE], data=ddp)
    logging.error('Ricerca pratiche non autorizzata. Utente: %s', user['userid'])
    fk.session.clear()
    return fk.render_template('noaccess.html', sede=CONFIG.config[SEDE])

@ACQ.route('/pratica0/<num>/<year>', methods=('GET', ))
def pratica0(num, year):
    "pagina: accesso a pratica indicata"
    logging.info('URL: /pratica0/{num}/{year} ({fk.request.method})')     #pylint: disable=W1203
    basedir = ft.namebasedir(year, num)
    fk.session[BASEDIR_STR] = basedir
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    user, basedir, d_prat = ret
    _clear_conferma_chiusura(basedir, d_prat)
    return pratica_common(user, basedir, d_prat)

def get_tipo_allegato():
    "Determina il tipo di allegato"
    allx = [k for k in fk.request.form.keys() if k.endswith(".x")]
    if allx:
        return allx[0][:-2]
    return ""

@ACQ.route('/pratica1', methods=('GET', 'POST'))
def pratica1():               # pylint: disable=R0914
    "pagina: pratica, modo 1 (iterazione modifica)"
    logging.info('URL: /pratica1 (%s)', fk.request.method)
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    user, basedir, d_prat = ret
    if fk.request.method == 'POST':
        try:
            fle = fk.request.files['upload_file']
        except Exception:               # pylint: disable=W0703
            fk.flash("Errore caricamento file!", category="error")
        else:
            _clear_conferma_chiusura(basedir, d_prat)
            tipo_allegato = get_tipo_allegato()
            logging.info("Richiesta upload: %s (tipo: %s)", fle.filename, tipo_allegato)
            err = check_allegati_allegabili(d_prat)
            if err:
                fk.flash(err, category="error")
                logging.error(err)
                return pratica_common(user, basedir, d_prat)
            origname, ext = os.path.splitext(fle.filename)
            origname = secure_filename(origname)
            ext = ext.lower()
            if ext not in UPLOAD_TYPES:
                fk.flash(f"Tipo allegato non valido: {fle.filename}", category="error")
            elif tipo_allegato in (LISTA_DETTAGLIATA_A, LISTA_DETTAGLIATA_B) and \
                 ext not in PDF_TYPES:
                fk.flash(f"L'allegato non è in formato PDF: {fle.filename}", category="error")
            else:
                prefix, mod_allegato = (TAB_ALLEGATI[tipo_allegato][0],
                                        TAB_ALLEGATI[tipo_allegato][2])
                spec = fk.request.form.get(SIGLA_DITTA, "")
                name = filename_allegato(mod_allegato, prefix, origname, ext, spec, d_prat)
                if not name:
                    fk.flash("Devi specificare una sigla per la ditta!", category="error")
                    return pratica_common(user, basedir, d_prat)
                fpath = os.path.join(basedir, name)
                if os.path.exists(fpath):
                    fk.flash(f'File "{name}" già esistente!', category='error')
                    fk.flash('Devi modificare il nome del file '
                             '(o rimuovere quello esistente)', category="error")
                    return pratica_common(user, basedir, d_prat)

                fle.save(fpath)        # Archivia file da upload
                msg = 'Allegato file '+name
                d_prat[STORIA_PRATICA].append(_hrecord(user['fullname'], msg))
                tb.jsave((basedir, PRAT_JFILE), d_prat)
                ft.protect(fpath)
                logging.info('Allegato file %s', fpath)
    return pratica_common(user, basedir, d_prat)

@ACQ.route('/togglestoria', methods=('GET', 'POST', ))
def togglestoria():
    "pagina: abilita/disabilita storia pratica"
    logging.info('URL: /togglestoria (%s)', fk.request.method)
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    user, basedir, d_prat = ret
    _clear_conferma_chiusura(basedir, d_prat, save=False)
    sst = d_prat.get(VEDI_STORIA, 0)
    if sst:
        d_prat[VEDI_STORIA] = 0
    else:
        d_prat[VEDI_STORIA] = 1
    tb.jsave((basedir, PRAT_JFILE), d_prat)
    return pratica_common(user, basedir, d_prat)

@ACQ.route('/modificadetermina/<fase>', methods=('GET', 'POST', ))
def modificadetermina(fase):
    "pagina: modifica determina"
    logging.info('URL: /modificadetermina/{fase} ({fk.request.method})')     #pylint: disable=W1203
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    user, basedir, d_prat = ret
    _clear_conferma_chiusura(basedir, d_prat)
    if ANNULLA in fk.request.form:
        fk.flash('Operazione annullata', category="info")
        return fk.redirect(fk.url_for('pratica1'))
    if d_prat.get(VERSIONE, 0) == 0:
        return _aggiornaformato()
    err = check_determina_modificabile(user, basedir, d_prat, fase)
    if err:
        fk.flash(err, category="error")
        logging.error('Gestione determina non autorizzata: %s. Utente %s, pratica %s',
                     err, user['userid'], d_prat[NUMERO_PRATICA])
    else:
        if fase == "A":
            return modificadetermina_a(user, basedir, d_prat)
        if fase == "B":
            return modificadetermina_b(user, basedir, d_prat)
        raise FASE_ERROR
    return pratica1()

@ACQ.route('/cancelladetermina/<fase>', methods=('GET', ))
def cancelladetermina(fase):
    "pagina: cancella determina"
    logging.info('URL: /cancelladetermina/{fase} ({fk.request.method})')     #pylint: disable=W1203
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    user, basedir, d_prat = ret
    _clear_conferma_chiusura(basedir, d_prat)
    err = check_determina_cancellabile(user, basedir, d_prat, fase)
    if err:
        fk.flash(err, category="error")
        logging.error('cancellazione determina non autorizzata: %s. Utente %s, pratica %s',
                      err, user['userid'], d_prat[NUMERO_PRATICA])
    else:
        if fase == "A":
            ft.remove((basedir, DETA_PDF_FILE), show_error=False)
            ft.remove((basedir, DETB_PDF_FILE), show_error=False)
            ft.remove((basedir, ORD_PDF_FILE), show_error=False)
            d_prat[STORIA_PRATICA].append(_hrecord(user['fullname'],
                                                   'Cancellati determine e ordine'))
            logging.info("Cancellati determine e ordine. Pratica N. %s",
                         d_prat.get(NUMERO_PRATICA, ''))
        else:
            ft.remove((basedir, DETB_PDF_FILE), show_error=False)
            ft.remove((basedir, ORD_PDF_FILE), show_error=False)
            d_prat[STORIA_PRATICA].append(_hrecord(user['fullname'],
                                                   'Cancellati determina agg. e ordine'))
            logging.info("Cancellati determina agg. e ordine. Pratica N. %s",
                         d_prat.get(NUMERO_PRATICA, ''))
        tb.jsave((basedir, PRAT_JFILE), d_prat)
    return pratica1()

@ACQ.route('/modificaordine/<fase>', methods=('GET', 'POST'))
def modificaordine(fase):               # pylint: disable=R0912,R0914
    "pagina: modifica ordine"
    logging.info('URL: /modificaordine/{fase} ({fk.request.method})')     #pylint: disable=W1203
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    user, basedir, d_prat = ret
    _clear_conferma_chiusura(basedir, d_prat)
    if DATA_ORDINE not in d_prat:
        d_prat[DATA_ORDINE] = ft.today(False)
    err = check_ordine_modificabile(user, basedir, d_prat, fase)
    if err:
        fk.flash(err, category="error")
        logging.error('Modifica ordine non autorizzata: %s. Utente %s, Pratica %s', \
                      err, user['userid'], d_prat.get(NUMERO_PRATICA, 'N.A.'))
        url = fk.url_for('pratica1')
        return fk.redirect(url)
    if d_prat.get(VERSIONE, 0) == 0:
        return _aggiornaformato()
    if not d_prat.get(DESCRIZIONE_ORDINE):
        d_prat[DESCRIZIONE_ORDINE] = d_prat[DESCRIZIONE_ACQUISTO]
    if not d_prat.get(COSTO_ORDINE):
        d_prat[COSTO_ORDINE] = d_prat[COSTO]
    orn = fms.Ordine(fk.request.form, **d_prat)
    if fk.request.method == 'POST':
        if ANNULLA in fk.request.form:
            fk.flash('Operazione annullata', category="info")
            return fk.redirect(fk.url_for('pratica1'))
        if orn.validate():
            d_prat.update(clean_data(orn.data))
            if d_prat.get(LINGUA_ORDINE, '') == 'EN':
                ord_name = ORD_NAME_EN
            else:
                ord_name = ORD_NAME_IT
            d_prat[STR_COSTO_ORD_IT] = ft.stringa_costo(d_prat.get(COSTO_ORDINE), "it")
            d_prat[STR_COSTO_ORD_UK] = ft.stringa_costo(d_prat.get(COSTO_ORDINE), "uk")
            d_prat[TITOLO_DIRETTORE_UK] = CONFIG.config[TITOLO_DIRETTORE_UK]
            logging.info('Genera ordine [%s]: %s/%s', ord_name, basedir, ORD_PDF_FILE)
            file_lista_dettagliata = filename_allegato(ALL_SING,
                                                       TAB_ALLEGATI[LISTA_DETTAGLIATA_A][0],
                                                       "", ".pdf", "", d_prat)
            if ft.findfiles(basedir, file_lista_dettagliata):
                include = file_lista_dettagliata
                d_prat[DETTAGLIO_ORDINE] = 1
            else:
                include = ""
                d_prat[DETTAGLIO_ORDINE] = 0
            pdf_name = os.path.splitext(ORD_PDF_FILE)[0]
            ft.makepdf(basedir, ord_name, pdf_name, debug=DEBUG.local,
                       include=include, pratica=d_prat, sede=CONFIG.config[SEDE])
            d_prat[PDF_ORDINE] = ORD_PDF_FILE
            d_prat[STORIA_PRATICA].append(_hrecord(user['fullname'], 'Ordine generato'))
            tb.jsave((basedir, PRAT_JFILE), d_prat)
            url = fk.url_for('pratica1')
            return fk.redirect(url)
        errors = orn.get_errors()
        for err in errors:
            fk.flash(err, category="error")
        logging.debug("Errori form Ordine: %s", "; ".join(errors))
    ddp = {'title': 'Immissione dati per ordine',
           'subtitle': f"Pratica N. {d_prat['numero_pratica']}",
           'before': f'<form method=POST action=/modificaordine/{fase} ' \
                     'accept-charset="utf-8" novalidate>',
           'after': "</form>",
           'note': OBBLIGATORIO,
           'body': orn.renderme(d_prat)}
    return fk.render_template('form_layout.html', sede=CONFIG.config[SEDE], data=ddp)

@ACQ.route('/chiudipratica')
def chiudipratica():
    "pagina: chiudi pratica"
    logging.info('URL: /chiudipratica ({fk.request.method})')
    return _modifica_pratica('chiudi')

@ACQ.route('/apripratica')
def apripratica():
    "pagina: apri pratica"
    logging.info('URL: /apripratica (%s)', fk.request.method)
    return _modifica_pratica('apri')

@ACQ.route('/annullapratica')
def annullapratica():
    "pagina: annulla pratica"
    logging.info('URL: /annullapratica (%s)', fk.request.method)
    return _modifica_pratica('null')

@ACQ.route('/vedijson/<fname>')
def vedijson(fname):
    "pagina: mostra contenuto di file json"
    logging.info('URL: /vedijson/{fname} ({fk.request.method})')     #pylint: disable=W1203
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    user, basedir = ret[:2]
    if _test_developer(user):
        ffn = fname+'.json'
        data = tb.jload((basedir, ffn), {})
        text = f'<h4>{os.path.join(basedir, ffn)}</h4>'
        ppt = PrettyPrinter(indent=4)
        text += '<pre>'+ ppt.pformat(data)+'</pre>'
        return text
    logging.error('Visualizzazione JSON non autorizzata. Utente: %s', user['userid'])
    fk.session.clear()
    return fk.render_template('noaccess.html', sede=CONFIG.config[SEDE])

@ACQ.route('/files/<name>')
def files(name):
    "download file"
    logging.info('URL: /files/%s (%s)', name, fk.request.method)     #pylint: disable=W1203
    return  ACQ.send_static_file(name)

@ACQ.route('/show_checks')
def show_checks():
    "Mostra risultato checks"
    logging.info('URL: /show_checks (%s)', fk.request.method)
    def addsi(text):
        return "NO: "+text+"\n" if text else "SI\n"
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    the_user, basedir, d_prat = ret
    if _test_developer(the_user):
        text = "<h4>Checks su pratica N. "+d_prat[NUMERO_PRATICA]+"</h4>\n"
        text = "<h4>Checks su pratica N. "+d_prat[NUMERO_PRATICA]+"</h4><pre>\n"
        text += "  - pratica apribile: "+addsi(check_pratica_apribile(the_user, d_prat))
        text += "  - pratica annullabile: "+addsi(check_pratica_annullabile(the_user, d_prat))
        text += "  - pratica chiudibile: "+ \
                addsi(check_pratica_chiudibile(the_user, basedir, d_prat))
        text += "  - progetto approvabile: "+ \
                addsi(check_progetto_approvabile(the_user, basedir, d_prat))
        text += "  - progetto modificabile: "+ \
                addsi(check_progetto_modificabile(the_user, basedir, d_prat))
        text += "  - progetto inviabile: "+ \
                addsi(check_progetto_inviabile(the_user, basedir, d_prat))
        text += "  - rdo modificabile: "+addsi(check_rdo_modificabile(the_user, basedir, d_prat))
#       text += "  - RUP nominabile: "+addsi(check_rup_nominabile(the_user, basedir, d_prat))
        text += "  - determina (fase A) cancellabile: "+ \
                addsi(check_determina_cancellabile(the_user, basedir, d_prat, "A"))
        text += "  - determina (fase B) cancellabile: "+ \
                addsi(check_determina_cancellabile(the_user, basedir, d_prat, "B"))
        text += "  - determina (fase A) modificabile: "+ \
                addsi(check_determina_modificabile(the_user, basedir, d_prat, "A"))
        text += "  - determina (fase B) modificabile: "+ \
                addsi(check_determina_modificabile(the_user, basedir, d_prat, "B"))
        text += "  - allegati allegabili: "+addsi(check_allegati_allegabili(d_prat))
        text += "  - allegati cancellabili: "+addsi(check_allegati_cancellabili(the_user, d_prat))
        text += "  - ordine (fase A) modificabile: "+ \
                addsi(check_ordine_modificabile(the_user, basedir, d_prat, "A"))
        text += "  - ordine (fase B) modificabile: "+ \
                addsi(check_ordine_modificabile(the_user, basedir, d_prat, "B"))
        text += "</pre>"
        return text
    logging.error('Visualizzazione checks() non autorizzata. Utente: %s', the_user['userid'])
    fk.session.clear()
    return fk.render_template('noaccess.html', sede=CONFIG.config[SEDE])

@ACQ.route('/user')
def user_tbd():
    "pagina T.B.D."
    logging.info('URL: /user (%s)', fk.request.method)
    return fk.render_template('tbd.html', goto='/', sede=CONFIG.config[SEDE])

def remove_prefix(adict, prefix):
    "rimuove da dict tutte le chiavi che inizino per la stringa data"
    toremove = []
    for key in adict:
        if key.startswith(prefix):
            toremove.append(key)
    for key in toremove:
        del adict[key]

@ACQ.route('/procedura_rdo', methods=('GET', 'POST'))
def procedura_rdo():
    "Trattamento pagina per procedura RDO"
    logging.info('URL: /procedura_rdo (%s)', fk.request.method)
    ret = _check_access()
    if not isinstance(ret, tuple):
        return ret
    user, basedir, d_prat = ret
    _clear_conferma_chiusura(basedir, d_prat)
    err = check_rdo_modificabile(user, basedir, d_prat)
    if err:
        fk.flash(err, category="error")
        logging.error('Modifica ordine non autorizzata: %s. Utente %s, Pratica %s', \
                      err, user['userid'], d_prat.get(NUMERO_PRATICA, 'N.A.'))
    else:
        if fk.request.method == 'POST':
            if ANNULLA in fk.request.form:
                fk.flash('Operazione annullata', category="info")
                return fk.redirect(fk.url_for('pratica1'))
            rdo = fms.PraticaRDO(fk.request.form)
            if MORE in fk.request.form:
                m_entries = len(rdo.data[LISTA_DITTE])+2
# Trucco per rendere variabile la dimensione del form per lista ditte
                class LocalForm(fms.PraticaRDO): pass     # pylint: disable=C0115,C0321,R0903
                LocalForm.lista_ditte = fms.new_lista_ditte("Lista ditte", m_entries)
# Fine trucco
                logging.debug("Richiesto incremento numero ditte: %d", m_entries)
                rdo = LocalForm(fk.request.form)
            elif AVANTI in fk.request.form:
                if rdo.validate():
                    if LISTA_DITTE in d_prat:
                        del d_prat[LISTA_DITTE]
                    rdo_data = rdo.data.copy()
                    clean_lista(rdo_data)
                    d_prat.update(clean_data(rdo_data))
                    tb.jsave((basedir, PRAT_JFILE), d_prat)
                    ft.remove((basedir, DETB_PDF_FILE), show_error=False)
                    ft.remove((basedir, ORD_PDF_FILE), show_error=False)
                    logging.debug("Aggiornata pratica con dati RDO")
                    return fk.redirect(fk.url_for('pratica1'))
                errors = rdo.get_errors()
                for err in errors:
                    fk.flash(err, category="error")
                logging.debug("Errori form PraticaRDO: %s", "; ".join(errors))
        else:
            rdo = fms.PraticaRDO(**d_prat)
        ddp = {'title': 'Immissione dati per RDO su MEPA',
               'subtitle': f"Pratica N. {d_prat['numero_pratica']}",
               'before': '<form method=POST action=/procedura_rdo '\
                         'accept-charset="utf-8" novalidate>',
               'after': "</form>",
               'note': OBBLIGATORIO,
               'body': rdo.renderme(**d_prat)}
    return fk.render_template('form_layout.html', sede=CONFIG.config[SEDE], data=ddp)

#############################################################################
################### Pagine housekeeping #####################################

@ACQ.route('/housekeeping')
def housekeeping():
    "Inizio procedura housekeeping"
    logging.info('URL: /housekeeping (%s)', fk.request.method)
    user = ft.login_check(fk.session)
    if user:
        status = {'footer': f"Procedura housekeeping.py. Vers. {__version__} - " \
                            f"L. Fini, {__date__}",
                  'host': ft.host(fk.request.url_root)}

        if _test_admin(user):
            return fk.render_template('start_housekeeping.html',
                                      user=user,
                                      sede=CONFIG.config[SEDE],
                                      status=status).encode('utf8')
        fk.session.clear()
        return fk.render_template('noaccess.html')
    return fk.redirect(fk.url_for('login'))

@ACQ.route("/sortcodf/<field>")
def sortcodf(field):
    "Riporta codici fondi con ordine specificato"
    logging.info('URL: /sortcodf/{field} ({fk.request.method})')     #pylint: disable=W1203
    user = ft.login_check(fk.session)
    if user:
        if _test_admin(user):
            ncodf = ft.FTable((DATADIR, 'codf.json'), sortable=('Codice', 'email_Responsabile'))
            msgs = fk.get_flashed_messages()
            return ncodf.render("Lista Codici fondi",
                                select_url=("/editcodf",
                                            "Per modificare, clicca sul simbolo: "
                                            "<font color=red><b>&ofcir;</b></font>"),
                                sort_url=('/sortcodf', '<font color=red>&dtrif;</font>'),
                                menu=(('/addcodf', "Aggiungi Codice fondo"),
                                      ('/downloadcodf', "Scarica CSV"),
                                      ('/housekeeping', 'Torna')),
                                sort_on=field,
                                messages=msgs,
                                footer=f"Procedura housekeeping.py. Vers. {__version__}. "\
                                       f"&nbsp;-&nbsp; L. Fini, {__date__}")
        return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))


@ACQ.route("/codf")
def codf():
    "Riporta codici fondi"
    logging.info('URL: /codf (%s)', fk.request.method)
    return sortcodf('')


@ACQ.route('/addcodf', methods=('GET', 'POST'))
def addcodf():
    "Aggiungi codice fondo"
    logging.info('URL: /addcodf (%s)', fk.request.method)
    user = ft.login_check(fk.session)
    if user:
        if _test_admin(user):
            cfr = fms.CodfForm(formdata=fk.request.form)
            ulist = ft.FTable((DATADIR, 'userlist.json')).as_dict('email', True)
            resp_menu = [(x, _nome_resp(ulist, x, False)) for  x in ulist]
            resp_menu.sort(key=lambda x: x[1])
            cfr.email_Responsabile.choices = resp_menu
            ncodf = ft.FTable((DATADIR, 'codf.json'))
            if fk.request.method == 'POST':
                if 'annulla' in fk.request.form:
                    fk.flash('Operazione annullata')
                    return fk.redirect(fk.url_for('housekeeping'))
                if cfr.validate():
                    data = ncodf.get_row(0, as_dict=True, default='') # get an empty row
                    data.update(cfr.data)
                    ncodf.insert_row(data)
                    ncodf.save()
                    msg = f"Aggiunto Codice fondo: {data['Codice']}"
                    logging.info(msg)
                    fk.flash(msg)
                    return fk.redirect(fk.url_for('codf'))
                logging.debug("Validation errors: %s", cfr.errlist)
            return ncodf.render_item_as_form('Aggiungi Codice fondo', cfr,
                                             fk.url_for('addcodf'),
                                             errors=cfr.errlist)
        return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))

@ACQ.route('/editcodf/<nrec>', methods=('GET', 'POST'))
def editcodf(nrec):
    "Modifica tabella codici fondi"
    logging.info('URL: /editcodf/{nrec} ({fk.request.method})')     #pylint: disable=W1203
    nrec = int(nrec)
    user = ft.login_check(fk.session)
    if user:
        if _test_admin(user):
            ncodf = ft.FTable((DATADIR, 'codf.json'))
            row = ncodf.get_row(nrec, as_dict=True)
            ulist = ft.FTable((DATADIR, 'userlist.json')).as_dict('email')
            resp_menu = [(x, _nome_resp(ulist, x, False)) for  x in ulist]
            resp_menu.sort(key=lambda x: x[1])
            if fk.request.method == 'GET':
                logging.debug("Codice row=%s", row)
                cfr = fms.CodfForm(**row)
                cfr.email_Responsabile.choices = resp_menu
            else:
                cfr = fms.CodfForm(formdata=fk.request.form)
                cfr.email_Responsabile.choices = resp_menu
                if 'cancella' in fk.request.form:
                    ncodf.delete_row(nrec)
                    ncodf.sort(1)
                    ncodf.save()
                    msg = "Cancellato Codice fondo: " \
                          f"{row['Codice']} ({row['email_Responsabile']})"
                    fk.flash(msg)
                    logging.info(msg)
                    return fk.redirect(fk.url_for('codf'))
                if 'annulla' in fk.request.form:
                    fk.flash('Operazione annullata')
                    return fk.redirect(fk.url_for('housekeeping'))
                if cfr.validate():
                    if 'avanti' in fk.request.form:
                        row.update(cfr.data)
                        ncodf.insert_row(row, nrec)
                        print("row:", row, "   nrec:", nrec)
                        ncodf.save()
                        msg = "Modificato Codice fondo: " \
                              f"{row['Codice']} ({row['email_Responsabile']})"
                        fk.flash(msg)
                        logging.info(msg)
                    return fk.redirect(fk.url_for('codf'))
                logging.debug("Validation errors: %s", cfr.errlist)
            return ncodf.render_item_as_form('Modifica Codice fondo', cfr,
                                             fk.url_for('editcodf', nrec=str(nrec)),
                                             errors=cfr.errlist, nrow=nrec)
        return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))

@ACQ.route('/downloadcodf', methods=('GET', 'POST'))
def downloadcodf():
    "Download tabella codici fondi"
    logging.info('URL: /downloadcodf (%s)', fk.request.method)
    return download('codf')

@ACQ.route('/downloadutenti', methods=('GET', 'POST'))
def downloadutenti():
    "Download tabella utenti"
    logging.info('URL: /downloadutenti (%s)', fk.request.method)
    return download('utenti')

def download(_unused):
    "Download"
    user = ft.login_check(fk.session)
    if user:
        return fk.render_template('tbd.html', goto='/')
    return fk.redirect(fk.url_for('login'))

@ACQ.route("/utenti")
def utenti():
    "Genera lista utenti"
    logging.info('URL: /utenti (%s)', fk.request.method)
    user = ft.login_check(fk.session)
    if user:
        if _test_admin(user):
            users = ft.FTable((DATADIR, 'userlist.json'))
            msgs = fk.get_flashed_messages()
            return users.render("Lista utenti",
                                select_url=("/edituser",
                                            "Per modificare, clicca sul simbolo: "\
                                            "<font color=red><b>&ofcir;</b></font>"),
                                menu=(('/adduser', "Aggiungi utente"),
                                      ('/downloadutenti', "Scarica CSV"),
                                      ('/housekeeping', 'Torna')),
                                sort_on="surname",
                                messages=msgs,
                                footer=f"Procedura housekeeping.py. Vers. {__version__} "\
                                       f"- L. Fini, {__date__}")
        return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))


@ACQ.route('/adduser', methods=('GET', 'POST'))
def adduser():
    "Aggiungi utente"
    logging.info('URL: /adduser ({fk.request.method})')
    user = ft.login_check(fk.session)
    if user:
        if _test_admin(user):
            cfr = fms.UserForm(formdata=fk.request.form)
            users = ft.FTable((DATADIR, 'userlist.json'))
            if fk.request.method == 'POST':
                if 'annulla' in fk.request.form:
                    fk.flash('Operazione annullata')
                    return fk.redirect(fk.url_for('housekeeping'))
                if cfr.validate():
                    data = users.get_row(0, as_dict=True, default='') # get an empty row
                    data.update(cfr.data)
                    data['pw'] = '-'
                    users.insert_row(data)
                    users.save()
                    msg = f"Aggiunto Utente: {data['surname']} {data['name']}"
                    logging.info(msg)
                    fk.flash(msg)
                    return fk.redirect(fk.url_for('utenti'))
                logging.debug("Validation errors: %s", cfr.errlist)
            return users.render_item_as_form('Aggiungi utente', cfr,
                                             fk.url_for('adduser'),
                                             errors=cfr.errlist,
                                             ignore=('pw', 'flags'))
        return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))

@ACQ.route('/edituser/<nrec>', methods=('GET', 'POST'))
def edituser(nrec):
    "Modifica dati utente"
    logging.info('URL: /edituser/{nrec} ({fk.request.method})')     #pylint: disable=W1203
    nrec = int(nrec)
    user = ft.login_check(fk.session)
    if user:
        if _test_admin(user):
            users = ft.FTable((DATADIR, 'userlist.json'))
            users.sort(3)
            row = users.get_row(nrec, as_dict=True)
            if fk.request.method == 'GET':
                logging.debug("Userlist row=%s", row)
                cfr = fms.UserForm(**row)
                logging.debug("UserForm inizializzato: %s", cfr.data)
            else:
                cfr = fms.UserForm(formdata=fk.request.form)
                if 'annulla' in fk.request.form:
                    fk.flash('Operazione annullata')
                    return fk.redirect(fk.url_for('housekeeping'))
                if 'cancella' in fk.request.form:
                    row = users.get_row(nrec, as_dict=True)
                    users.delete_row(nrec)
                    users.sort(3)
                    users.save()
                    msg = f"Cancellato utente N. {nrec}: {row['name']} {row['surname']}"
                    logging.info(msg)
                    fk.flash(msg)
                    return fk.redirect(fk.url_for('utenti'))
                if cfr.validate():
                    if 'avanti' in fk.request.form:
                        logging.debug("Pressed: avanti. Modifica utente")
                        row.update(cfr.data)
                        users.insert_row(row, nrec)
                        users.sort(3)
                        users.save()
                        msg = f"Modificato utente: {row['name']} {row['surname']}"
                        logging.info(msg)
                        fk.flash(msg)
                    return fk.redirect(fk.url_for('utenti'))
                logging.debug("Validation errors: %s", cfr.errlist)
            return users.render_item_as_form('Modifica utente', cfr,
                                             fk.url_for('edituser', nrec=str(nrec)),
                                             nrow=nrec, errors=cfr.errlist,
                                             ignore=('pw', 'flags'))
        return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))

@ACQ.route('/environ', methods=('GET',))
def environ():
    "Mostra informazioni su environment"
    logging.info('URL: /environ (%s)', fk.request.method)
    user = ft.login_check(fk.session)
    if user:
        if not _test_developer(user):
            fk.session.clear()
            return fk.render_template('noaccess.html')
    html = ["<ul>"]
    keys = list(os.environ.keys())
    keys.sort()
    for key in keys:
        html.append(f"<li><b>{key}</b>: {os.environ[key]}")
    html.append("</ul>")
    env = '\n'.join(html)
    html = ["<ul>"]
    html.append(f"<li><b>args</b>: {fk.request.args}")
    html.append(f"<li><b>base_url</b>: {fk.request.base_url}")
    html.append(f"<li><b>date</b>: {fk.request.date}")
    html.append(f"<li><b>endpoint</b>: {fk.request.endpoint}")
    html.append(f"<li><b>full_path</b>: {fk.request.full_path}")
    html.append(f"<li><b>host</b>: {fk.request.host}")
    html.append(f"<li><b>host_url</b>: {fk.request.host_url}")
    html.append(f"<li><b>method</b>: {fk.request.method}")
    html.append(f"<li><b>remote_addr</b>: {fk.request.remote_addr}")
    html.append(f"<li><b>remote_user</b>: {fk.request.remote_user}")
    html.append(f"<li><b>scheme</b>: {fk.request.scheme}")
    html.append(f"<li><b>url</b>: {fk.request.url}")
    html.append(f"<li><b>url_root</b>: {fk.request.url_root}")
    html.append(f"<li><b>user_agent</b>: {fk.request.user_agent}")
    req = '\n'.join(html)
    return fk.render_template('environ.html', sede=CONFIG.config[SEDE], request=req, environ=env)

@ACQ.route('/testmail', methods=('GET',))
def testmail():
    "Invia messaggio di prova all'indirizzo di webmaster"
    logging.info('URL: /testmail (%s)', fk.request.method)
    user = ft.login_check(fk.session)
    if user:
        if not _test_developer(user):
            fk.session.clear()
            return fk.render_template('noaccess.html')
        thetime = time.asctime()
        host = CONFIG.config.get(SMTP_HOST)
        recipients = [CONFIG.config.get(EMAIL_WEBMASTER)]
        sender = CONFIG.config.get(EMAIL_UFFICIO, "")
        subj = "Messaggio di prova da procedura 'acquisti'"
        body = f"""
Invio messaggio di prova per verifica funzionamento del server.

Messaggio inviato all'indirizzo corrispondente al Webmaster tramite
server: {host} (se indicato come "-", l'invio avviene tramite GMail API)
"""
        ret = ft.send_email(host, sender, recipients, subj, body)
        return fk.render_template('testmail.html', time=thetime, sender=sender,
                                  recipients=", ".join(recipients),
                                  server=host, state=ret).encode('utf8')
    return fk.redirect(fk.url_for('login'))

@ACQ.route('/force_excp', methods=('GET',))
def force_excp():
    "Causa una eccezione"
    logging.info('URL: /force_excp (%s)', fk.request.method)
    user = ft.login_check(fk.session)
    if user:
        if not _test_developer(user):
            fk.session.clear()
            return fk.render_template('noaccess.html')
        1/0                                 # pylint: disable=W0104
    return fk.redirect(fk.url_for('login'))

#############################################################################
############################### Inizializzazioni ############################

def initialize_me():
    "inizializza tutto il necessario"
    logging.info('Starting %s', long_version())
    logging.info('PKG_ROOT: %s', PKG_ROOT)
    logging.info('DATADIR: %s', DATADIR)
    logging.info('WORKDIR: %s', WORKDIR)
    logging.info("URL: %s", THIS_URL)

    configname = os.path.join(DATADIR, 'config.json')
    logging.info('Config loaded from: %s', configname)

    ft.latex.set_path(CONFIG.config.get("latex_path", ""))
    logging.info("LaTeX path: %s", ft.latex.PDFLATEX.cmd)

    update_lists()
    ft.init_helplist()
    ACQ.secret_key = CONFIG.config[FLASK_KEY]

    ft.clean_locks(DATADIR)

    logging.info('Inizializzazione terminata correttamente')

def short_version():
    "riporta numero di versione (major.minor)"
    vvv = __version__.split('.')
    return '.'.join(vvv[:2])

def long_version():
    'riporta versione'
    return f'acquisti.py. Vers. {__version__} - L. Fini, {__date__}'

def localtest():
    "lancia la procedura come test in locale"
    if '-h' in sys.argv:
        print(__doc__)
        sys.exit()
    if '-v' in sys.argv:
        print(short_version(), end='')
        sys.exit()
    if '-V' in sys.argv:
        print(long_version())
        sys.exit()
    logging.basicConfig(level=logging.DEBUG)
    initialize_me()
    setdebug()
    ft.set_mail_logger(CONFIG.config[SMTP_HOST], CONFIG.config[EMAIL_PROCEDURA],
                       CONFIG.config[EMAIL_WEBMASTER], 'Notifica errore ACQUISTI (debug)')
    ACQ.run(host="0.0.0.0", port=4001, debug=True)

def production():
    "lancia la procedura in modo produzione (all'interno del web server)"
    logging.basicConfig(level=logging.INFO)    # Livello logging normale
#   logging.basicConfig(level=logging.DEBUG)   # Più verboso
    initialize_me()
    ft.set_file_logger((WORKDIR, 'acquisti5.log'))
    ft.set_mail_logger(CONFIG.config[SMTP_HOST], CONFIG.config[EMAIL_PROCEDURA],
                       CONFIG.config[EMAIL_WEBMASTER], 'Notifica errore ACQUISTI')

if __name__ == '__main__':
    localtest()
else:
    production()
