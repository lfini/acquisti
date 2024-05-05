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
import constants as cs
from constants import CdP

#    cope with compatibility with older werkzeug versions
try:
    from werkzeug.utils import secure_filename
except ImportError:
    from werkzeug import secure_filename

#from constants import *          # pylint: disable=W0401, W0614
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
__version__ = '5.0.16'
__date__ = '05/05/2024'

__start__ = time.asctime(time.localtime())

MODALITA_IMPLEMENTATE = [cs.TRATT_MEPA_40]     # Lista modalità acquisto implementate

# stringhe per check_xxxxx
YES = 'SI'
NOT = 'NO'
NON_ADMIN = 'non sei amministratore'
NON_RICH = 'non sei richiedente'
NON_RESP = 'non sei responsabile dei fondi'
NON_RUP = 'non sei RUP'
NON_DIR = 'non sei Direttore'

NO_DECIS_INVIATA = 'NO: decisione di contrarre già inviata'
NO_DECIS_GENERATA = 'NO: decisione di contrarre già generata'
NO_NON_ADMIN = 'NO: '+NON_ADMIN
NO_NON_RICH = 'NO: '+NON_RICH
NO_NON_RESP = 'NO: '+NON_RESP
NO_NON_RUP = 'NO: '+NON_RUP
NO_NON_DIR = 'NO: '+NON_DIR
NO_PASSO_ERRATO = 'NO: operazione non prevista a questo passo'
NO_PDF_CIG = 'NO: Manca allegato CIG'
NO_PDF_RDO_MEPA = 'NO: Manca allegato RdO da MePA'
NO_PRATICA_CHIUSA = 'NO: Pratica chiusa'
NO_PRATICA_ANNULLATA = 'NO: Pratica annullata'
NO_PRATICA_GIA_ANNULLATA = 'NO: Pratica già annullata'
NO_PRATICA_APERTA = 'NO: Pratica aperta'
NO_PROGETTO_GEN = 'NO: Progetto non generato'
NO_PREV_MEPA = 'NO: manca preventivo MePA in allegato'
NO_PROGETTO_INV = 'NO: Progetto già inviato'
NO_PROGETTO_APPROV = 'NO: Progetto già approvato'
NO_PROGETTO_NON_APPROV = 'NO: progetto non ancora approvato'
NO_PROGETTO_AUTORIZ = 'NO: Progetto già autorizzato'
NO_PROGETTO_NON_AUTORIZ = 'NO: progetto non ancora autorizzato'
NO_RESP = "NO: Operazione consentita solo al resp. dei fondi"
NO_RESP_AMM = "NO: Operazione consentita solo al resp. dei fondi o all'Amministrazione"
NO_RICH_AMM = "NO: Operazione consentita solo al richiedente o all'Amministrazione"
NO_RICH_RESP_AMM = "NO: Operazione consentita solo al richiedente, " \
                   "al responsabile dei fondi o all'Amministrazione"
NO_RICH_INVIATA = "NO: Richiesta già inviata"
NO_RICH_RESP_AMM = "NO: Operazione consentita solo al richiedente, " \
                   "al responsabile dei fondi o all'Amministrazione"
NO_RUP_NON_NOMINATO = 'NO: RUP non nominato'
NO_RUP_GIA_NOMINATO = 'NO: RUP già nominato'
NO_RUP_DICH = 'NO: mancano dichiarazioni del RUP'
NO_TBD = 'NO: operazione da implementare'

INVIO_NON_AUTORIZZ = 'Invio non autorizzato: %s. Utente: %s pratica %s'

NOTA_ANNULLAMENTO = '''
<tr><td><b>Attenzione:</b> La pratica annullata in un qualunque
stato di avanzamento  non potrà più essere riaperta o riutilizzata.
<p>
Per procedere devi specificare una motivazione per l'annullamento
e premere "Conferma" </td></tr>
'''

class ToBeImplemented(RuntimeError):
    'Parte codice non implementata'

class CONFIG:                   # pylint: disable=R0903
    'Dati di configurazione'
    time = time.time()
    config = tb.jload(cs.CONFIG_FILE)

BASEDIR_STR = 'basedir'

START_YEAR = 0

class DEBUG:         # pylint: disable=R0903
    "Variabili di supporto per Debug"
    local = False
    email = ''

FASE_ERROR = Exception("Manca specifica fase")
NO_BASEDIR = Exception("Basedir non definita")
ILL_ATCH = Exception("Modello allegato non previsto")

def setdebug():
    "Determina modo DEBUG"
    DEBUG.local = True
    DEBUG.email = CONFIG.config[cs.EMAIL_WEBMASTER]
    fms.debug_enable()

def print_debug(*args):
    'scrive debug su stdout, solo in modo "locale"'
    if DEBUG.local:
        print('DBG ACQ>', *args)

def update_lists():
    "Riinizializza tabelle"
    ft.update_userlist()
    ft.update_codflist()

#  Utilities

def _test_admin(the_user) -> bool:
    return 'A' in the_user.get('flags')

def _test_developer(the_user) -> bool:
    return 'D' in the_user.get('flags')

def _test_richiedente(the_user, d_prat) -> bool:
    emailrich = d_prat.get(cs.EMAIL_RICHIEDENTE, "R").lower()
    emailuser = the_user.get("email", "U").lower()
    return emailuser == emailrich

def _test_responsabile(the_user, d_prat) -> bool:
    emailresp = d_prat.get(cs.EMAIL_RESPONSABILE, "R").lower()
    emailuser = the_user.get("email", "U").lower()
    return emailuser == emailresp

def _test_rup(the_user, d_prat) -> bool:
    emailrup = d_prat.get(cs.EMAIL_RUP, "R").lower()
    emailuser = the_user.get("email", "U").lower()
    return emailuser == emailrup

def _test_direttore(the_user) -> bool:
    emaildir = CONFIG.config[cs.EMAIL_DIRETTORE].lower()
    emailuser = the_user.get("email", "U").lower()
    return emailuser == emaildir

def _test_pdf_decisione(basedir) -> bool:
    "test: esistenza decisione di contrarre"
    if not basedir:
        raise NO_BASEDIR
    return os.path.exists(os.path.join(basedir, cs.DECIS_PDF_FILE))

def _test_all_prev_mepa(basedir, d_prat) -> bool:
    "test esistenza preventivo mepa"
    if d_prat[cs.MOD_ACQUISTO] == cs.TRATT_MEPA_40:
        return bool(ft.findfiles(basedir, cs.TAB_ALLEGATI[cs.ALL_PREV_MEPA][0]))
    return True

def _test_all_cv_rup(basedir) -> bool:
    "test esistenza CV RUP"
    return ft.findfiles(basedir, cs.TAB_ALLEGATI[cs.ALL_CV_RUP][0])

def _test_all_cig(basedir) -> bool:
    "test esistenza CIG in allegato"
    return ft.findfiles(basedir, cs.TAB_ALLEGATI[cs.ALL_CIG][0])

def _test_all_rdo(basedir) -> bool:
    "test esistenza CIG in allegato"
    return ft.findfiles(basedir, cs.TAB_ALLEGATI[cs.ALL_RDO][0])

def _test_all_dich_rup(basedir) -> bool:
    "test esistenza dichiarazione RUP"
    return ft.findfiles(basedir, cs.TAB_ALLEGATI[cs.ALL_DICH_RUP][0])

def _test_all_decis_firmata(basedir) -> bool:
    return ft.findfiles(basedir, cs.TAB_ALLEGATI[cs.ALL_DECIS_FIRMATA][0])

def _test_all_obblig_perf(basedir) -> bool:
    return ft.findfiles(basedir, cs.TAB_ALLEGATI[cs.ALL_OBBLIG][0])

def _test_pdf_progetto(basedir) -> bool:
    "test: esistenza documento progetto"
    if not basedir:
        raise NO_BASEDIR
    pdf_path = os.path.join(basedir, cs.PROG_PDF_FILE)
    return os.path.exists(pdf_path)

def _test_pdf_nominarup(basedir) -> bool:
    "test: esistenza documento autorizzazione"
    if not basedir:
        raise NO_BASEDIR
    pdf_path = os.path.join(basedir, cs.NOMINARUP_PDF_FILE)
    return os.path.exists(pdf_path)

def _test_pdf_rdo(basedir) -> bool:
    "test: esistenza documento autorizzazione"
    if not basedir:
        raise NO_BASEDIR
    pdf_path = os.path.join(basedir, cs.RDO_PDF_FILE)
    return os.path.exists(pdf_path)

def check_allegati_cancellabili(the_user, d_prat) -> str:
    "test: allegati cancellabili"
    if d_prat.get(cs.PRATICA_APERTA) != 1:
        return NO_PRATICA_CHIUSA
    if _test_admin(the_user):
        return YES
    ret = [NON_ADMIN]
    if _test_richiedente(the_user, d_prat):
        return YES
    ret.append(NON_RICH)
    if _test_responsabile(the_user, d_prat):
        return YES
    ret.append(NON_RESP)
    return 'NO: '+', '.join(ret)

def check_progetto_inviabile(the_user, basedir, d_prat) -> str:      # pylint: disable=R0911
    "test: progetto inviabile per approv. al resp. fondi"
    if not d_prat.get(cs.PRATICA_APERTA, 1):
        return NO_PRATICA_CHIUSA
    if not _test_pdf_progetto(basedir):
        return NO_PROGETTO_GEN
    if not _test_all_prev_mepa(basedir, d_prat):
        return NO_PREV_MEPA
    if not (_test_admin(the_user) or _test_richiedente(the_user, d_prat)):
        return NO_RICH_AMM
    if d_prat.get(cs.PROGETTO_INVIATO):
        return NO_PROGETTO_INV
    if d_prat.get(cs.FIRMA_APPROV_RESP):
        return NO_PROGETTO_APPROV
    return YES

def check_progetto_modificabile(user, _basedir, d_prat) -> str:            # pylint: disable=W0703,R0911
    "test: progetto modificabile"
    if CdP.INI <= d_prat[cs.PASSO] < CdP.PIR:
        if _test_admin(user) or \
           _test_richiedente(user, d_prat) or \
           _test_responsabile(user, d_prat):
            return YES
        return NO_RICH_RESP_AMM
    return NO_PASSO_ERRATO

def check_progetto_approvabile(user, _basedir, d_prat) -> str:
    "test: progetto approvabile"
    if CdP.PIR <= d_prat[cs.PASSO] < CdP.PAR:
        if _test_responsabile(user, d_prat):
            return YES
        return NO_RESP
    return NO_PASSO_ERRATO

def check_rup_cancellabile(the_user, _unused, d_prat) -> str:
    "test: è possibile nominare il RUP"
    if not _test_admin(the_user):
        return NO_NON_ADMIN
    if not d_prat.get(cs.NOME_RUP):
        return NO_RUP_NON_NOMINATO
    return NO_TBD

def check_rup_indicabile(user, d_prat) -> str:
    "test: è possibile nominare il RUP"
    if CdP.PAR <= d_prat[cs.PASSO] < CdP.RAL:
        if _test_admin(user):
            return YES
        return NO_NON_ADMIN
    return NO_PASSO_ERRATO

def check_autorizz_richiedibile(user, _basedir, d_prat) -> str:     #pylint: disable=R0911
    "test: il RUP può chiedere l'autorizzazione del direttore?"
    if CdP.RAL <= d_prat[cs.PASSO] < CdP.IRD:
        if _test_admin(user):
            return YES
        return NO_NON_ADMIN
    return NO_PASSO_ERRATO

def check_rich_rup_autorizzabile(user, _basedir, d_prat) -> str:
    "test: il direttore può autorizzare la richiesta del RUP?"
    if CdP.IRD <= d_prat[cs.PASSO] < CdP.AUD:
        if _test_direttore(user):
            return YES
        return NO_NON_DIR
    return NO_PASSO_ERRATO

def check_rollback(user, _basedir) -> str:
    "test: rollback attivabile"
    if _test_admin(user):
        return YES
    return NO_NON_ADMIN

def check_rdo_modificabile(user, _basedir, d_prat) -> str:
    "test: rdo modificabile"
    if CdP.AUD <= d_prat[cs.PASSO] < CdP.RFI:
        if _test_rup(user, d_prat):
            return YES
        return NO_NON_RUP
    return NO_PASSO_ERRATO

def check_decisione_modificabile(user, _basedir, d_prat) -> str:
    "test: decisione di contrarre modificabile"
    if CdP.RFI <= d_prat[cs.PASSO] < CdP.DCI:
        if _test_rup(user, d_prat):
            return YES
        return NO_NON_RUP
    return NO_PASSO_ERRATO

def check_decisione_inviabile(user, _basedir, d_prat) -> str:
    "test: decisione di contrarre inviabile"
    if CdP.DCG <= d_prat[cs.PASSO] < CdP.DCI:
        if _test_rup(user, d_prat):
            return YES
        return NO_NON_RUP
    return NO_PASSO_ERRATO

def check_decisione_cancellabile(_user, basedir, _d_prat) -> str:
    "test: decisione di contrarre cancellabile"
    if not _test_pdf_decisione(basedir):
        return NO_DECIS_GENERATA
    return NO_TBD

def check_pratica_chiudibile(user, _unused, d_prat) -> str:
    "test: pratica chiudibile"
    if CdP.OGP <= d_prat[cs.PASSO] < CdP.FIN:
        if _test_admin(user):
            return YES
        return NO_NON_RUP
    return NO_PASSO_ERRATO

def check_pratica_annullabile(user) -> str:
    "test: pratica annullabile"
    if _test_admin(user):
        return YES
    return NO_NON_ADMIN

def make_info(the_user, basedir, d_prat) -> dict:
    "Verifica lo stato della pratica e riporta un dict riassuntivo"
    info = {}
    info['debug'] = YES if bool(DEBUG.local) else NOT
    info['developer'] = YES if _test_developer(the_user) else NOT
    info['admin'] = YES if _test_admin(the_user) else NOT
    info['responsabile'] = YES if _test_responsabile(the_user, d_prat) else NOT
    info['direttore'] = YES if _test_direttore(the_user) else NOT
    info['all_prev_mepa'] = YES if _test_all_prev_mepa(basedir, d_prat) else NOT
    info['all_cv_rup'] = YES if _test_all_cv_rup(basedir) else NOT
    info['all_dich_rup'] = YES if _test_all_dich_rup(basedir) else NOT
    info['all_cig'] = YES if _test_all_cig(basedir) else NOT
    info['allegati_cancellabili'] = check_allegati_cancellabili(the_user, d_prat)
    info['autorizz_richiedibile'] = check_autorizz_richiedibile(the_user, basedir, d_prat)
    info['decis_modificabile'] = check_decisione_modificabile(the_user, basedir, d_prat)
    info['decis_cancellabile'] = check_decisione_cancellabile(the_user, basedir, d_prat)
    info['decis_inviabile'] = check_decisione_inviabile(the_user, basedir, d_prat)
    info['pratica_annullabile'] = check_pratica_annullabile(the_user)
    info['pratica_chiudibile'] = check_pratica_chiudibile(the_user, basedir, d_prat)
    info['progetto_approvabile'] = check_progetto_approvabile(the_user, basedir, d_prat)
    info['progetto_modificabile'] = check_progetto_modificabile(the_user, basedir, d_prat)
    info['progetto_inviabile'] = check_progetto_inviabile(the_user, basedir, d_prat)
    info['rich_rup_autorizzabile'] = check_rich_rup_autorizzabile(the_user, basedir, d_prat)
    info['rollback'] = check_rollback(the_user, basedir)
    info['rup_indicabile'] = check_rup_indicabile(the_user, d_prat)
    info['rup_cancellabile'] = check_rup_cancellabile(the_user, basedir, d_prat)
    info['rdo_modificabile'] = check_rdo_modificabile(the_user, basedir, d_prat)
    info[cs.PDF_PROGETTO] = YES if _test_pdf_progetto(basedir) else NOT
    info[cs.PDF_NOMINARUP] = YES if _test_pdf_nominarup(basedir) else NOT
    info[cs.PDF_DECISIONE] = YES if _test_pdf_decisione(basedir) else NOT
    info[cs.PDF_RDO] = YES if _test_pdf_rdo(basedir) else NOT
    return info

def check_all(the_user, basedir, d_prat) -> dict:
    "Verifica lo stato della pratica e riporta un dict con valori bool"
    info = make_info(the_user, basedir, d_prat)
    for key, val in info.items():
        info[key] = val.startswith(YES)
    return info

def nome_da_email(embody, prima_nome=True):
    "estrae nome da messaggio email"
    row = ft.GlobLists.USERLIST.where('email', embody.strip())
    if row:
        if prima_nome:
            return f'{row[0][2]} {row[0][1]}'
        return f'{row[0][1]}, {row[0][2]}'
    return '??, ??'

def storia(d_prat, user, text):
    'aggiunge record alla storia della pratica'
    line = f'{text} - {ft.today()} ({user["fullname"]})'
    d_prat[cs.STORIA_PRATICA].append(line)
    logging.info(text)

def send_email(eaddr, text, subj, attach=None):
    'invio mail a utente'
    sender = CONFIG.config[cs.EMAIL_UFFICIO]
    if DEBUG.local:
        recipients = [CONFIG.config[cs.EMAIL_WEBMASTER]]
    else:
        recipients = [eaddr]
    ret = ft.send_email(CONFIG.config.get(cs.SMTP_HOST), sender, recipients,
                        subj, text, attach=attach, debug_addr=DEBUG.email)
    if ret:
        logging.info('Inviato messaggio "%s" a: %s', subj, eaddr)
    else:
        logging.error('Invio messaggio "%s" a: %s', subj, eaddr)
    return ret

def _check_access(user_only=False):
    "Verifica accesso alla pratica"
    d_prat = None
    user = user_info()
    basedir = fk.session.get(BASEDIR_STR, '')
    err_msg = None
    if basedir:
        try:
            d_prat = tb.jload((basedir, cs.PRAT_JFILE))
        except tb.TableException:
            err_msg = _errore_accesso(basedir)
    else:
        err_msg = _errore_basedir(user)
    if not err_msg or user_only:
        return (user, basedir, d_prat)
    fk.flash(err_msg, category="error")
    logging.error(err_msg)
    return None

def word_match(ins, where):
    "funzione ausiliaria per ricerca di parole case insensitive"
    setins = frozenset((x.lower() for x in ins.split()))
    if setins:
        setwhr = frozenset((x.lower() for x in where.split()))
        return len(setins.intersection(setwhr)) == len(setins)
    return False

def sel_menu(tipo_allegato):
    "Genera voce di menu per allegati"
    return (tipo_allegato,)+cs.TAB_ALLEGATI[tipo_allegato][1:3]

def salvapratica(basedir, d_prat):
    'Salva pratica, rimuovendo campi provvisori'
    tb.jsave((basedir, cs.PRAT_JFILE), d_prat)
    logging.info('Salvati dati pratica: %s/%s', basedir, cs.PRAT_JFILE)

def da_allegare(basedir, d_prat, s_range, tipo):
    'verifica se la voce di menù allegati deve essere aggiunta'
    if s_range[0] <= d_prat[cs.PASSO] < s_range[1] and \
        not ft.findfiles(basedir, cs.TAB_ALLEGATI[tipo][0]):
        return sel_menu(tipo)
    return None

def menu_allegati(basedir, d_prat):
    "Genera lista allegati in funzione del tipo di acquisto e del passo"
    mod_acquisto = d_prat[cs.MOD_ACQUISTO]
    menu = []
    if mod_acquisto == cs.TRATT_MEPA_40:
        if voce_menu := da_allegare(basedir, d_prat, (CdP.GPA,CdP.PAR), cs.ALL_PREV_MEPA):
            menu.append(voce_menu)
        if voce_menu := da_allegare(basedir, d_prat, (CdP.RUI,CdP.DCI), cs.ALL_CV_RUP):
            menu.append(voce_menu)
        if voce_menu := da_allegare(basedir, d_prat, (CdP.RUI,CdP.DCI), cs.ALL_DICH_RUP):
            menu.append(voce_menu)
        if voce_menu := da_allegare(basedir, d_prat, (CdP.AUD,CdP.DCI), cs.ALL_CIG):
            menu.append(voce_menu)
        if voce_menu := da_allegare(basedir, d_prat, (CdP.ROG,CdP.RFI), cs.ALL_RDO):
            menu.append(voce_menu)
        if voce_menu := da_allegare(basedir, d_prat, (CdP.DCI,CdP.DCF), cs.ALL_DECIS_FIRMATA):
            menu.append(voce_menu)
        if voce_menu := da_allegare(basedir, d_prat, (CdP.DCF,CdP.OGP), cs.ALL_OBBLIG):
            menu.append(voce_menu)
    menu.append(sel_menu(cs.ALL_GENERICO))
    return menu

def clean_dict(adict):
    "Crea newdict rimuovendo da adict le chiavi che iniziano per T_"
    newdict = {}
    for key, value in adict.items():
        if not key.startswith(cs.TEMPORARY_KEY_PREFIX):
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
    for ditta in rdo_data[cs.LISTA_DITTE]:
        if ditta.get("T_cancella"):
            continue
        if bool(ditta[cs.NOME_DITTA]) or  bool(ditta[cs.SEDE_DITTA]):
            newlist.append(ditta)
    rdo_data[cs.LISTA_DITTE] = newlist

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

ALL_MATCH = re.compile(r"A\d\d_")

def pratica_common(user, basedir, d_prat):
    "parte comune alle pagine relative alla pratica"
    info = check_all(user, basedir, d_prat)
    upl = fms.MyUpload(menu_allegati(basedir, d_prat))
    pdf_files = ft.flist(basedir, filetypes=cs.UPLOAD_TYPES)
    info['attach'] = [(a, _clean_name(a), a.startswith('A99')) \
                           for a in pdf_files if ALL_MATCH.match(a)]
    info['allegati_mancanti'] = allegati_mancanti(basedir, d_prat)
    info['stato_pratica'] = cs.PASSI[d_prat.get(cs.PASSO, 0)][0]
    return fk.render_template('pratica.html', info=info,
                              pratica=d_prat, upload=upl,
                              sede=CONFIG.config[cs.SEDE])

def modifica_pratica(what):               # pylint: disable=R0912,R0915
    "parte comune alle pagine di modifica pratica"
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    if what[0].lower() == 'c':      # Chiudi pratica
        err = check_pratica_chiudibile(user, basedir, d_prat)
        if err.startswith(NOT):
            fk.flash(err, category="error")
            logging.warning('Chiusura pratica rifiutata: %s. Utente %s, pratica %s',
                            err, user['userid'], d_prat[cs.NUMERO_PRATICA])
        else:
            d_prat[cs.PRATICA_APERTA] = 0
            text = f'Pratica {d_prat[cs.NUMERO_PRATICA]} chiusa'
            storia(d_prat, user, text)
    return fk.redirect(fk.url_for('pratica1'))

def _mydel(key, d_prat):
    "Cancella un campo della pratica"
    try:
        del d_prat[key]
    except KeyError:
        pass

def _aggiornaformato():
    "Chiamata quando è richiesto aggiornamento del formato pratica"
    fk.flash("Per procedere alle modifiche è necessario "
             "l'aggiornamento del formato", category="info")
    return fk.redirect(fk.url_for('aggiornaformato'))

def allegati_mancanti(basedir, d_prat):
    "Genera lista allegati mancanti"
    ret = []
    if not _test_all_prev_mepa(basedir, d_prat):
        ret.append("prev. MePA")
    if d_prat.get(cs.PASSO, 0) >= CdP.RUI and not _test_all_cv_rup(basedir):
        ret.append("CV RUP")
    if d_prat.get(cs.PASSO, 0) >= CdP.RUI and not _test_all_dich_rup(basedir):
        ret.append("Dich. RUP")
    if d_prat.get(cs.PASSO, 0) >= CdP.AUD and not _test_all_cig(basedir):
        ret.append("CIG")
    if d_prat.get(cs.PASSO, 0) >= CdP.ROG and not _test_all_rdo(basedir):
        ret.append("RdO Firmata")
    if d_prat.get(cs.PASSO, CdP.INI) >= CdP.DCI and not _test_all_decis_firmata(basedir):
        ret.append("Decis. firmata")
    if d_prat.get(cs.PASSO, CdP.INI) >= CdP.DCF and not _test_all_obblig_perf(basedir):
        ret.append("Decis. firmata")
    return ', '.join(ret)

def _avvisi(_user, _basedir, d_prat, _fase, _level=0):
    "Genera messaggi di avviso per pagina pratica. level=0: tutti; level=1: errori"
#   if level < 1:
#       if d_prat[MOD_ACQUISTO] in (MEPA, CONSIP):
#           fk.flash("La Bozza d'ordine MEPA deve essere trasmessa "
#                    "al Punto Ordinante", category="info")
    if not d_prat.get(cs.FIRMA_APPROV_RESP):
        fk.flash("Occorre richiedere l'approvazione del responsabile dei fondi", category="info")

def _pratica_ascendente(item):
    "funzione ausiliaria per sort pratiche"
    nprat = item.get(cs.NUMERO_PRATICA, '0/0').split('/')[0]
    return int(nprat)

def _pratica_discendente(item):
    "funzione ausiliaria per sort pratiche"
    nprat = item.get(cs.NUMERO_PRATICA, '0/0').split('/')[0]
    return -int(nprat)

def _render_progetto(form, d_prat):
    "rendering del form progetto di acquisto"
    ddp = {'title': 'Progetto di acquisto',
           'subtitle': f"Pratica N. {d_prat['numero_pratica']}<br><br>"
                       f"Richiedente: {d_prat['nome_richiedente']}",
           'before': '<form method=POST action=/modificaprogetto '
                     'accept-charset="utf-8" novalidate>',
           'after': '</form>',
           'note': cs.OBBLIGATORIO,
           'body': form()}
    return fk.render_template("form_layout.html", sede=CONFIG.config[cs.SEDE], data=ddp)

def genera_pratica(user):
    "Genera pratica temporanea vuota"
    d_prat = {cs.VERSIONE: cs.FILE_VERSION,
              cs.NUMERO_PRATICA: '-------',
              cs.EMAIL_RICHIEDENTE: user['email'],
              cs.NOME_RICHIEDENTE: user['name']+' '+user['surname'],
              cs.DATA_RICHIESTA: ft.today(False),
              cs.PASSO: CdP.INI,
              cs.PRATICA_APERTA: 1}
    logging.info("Creata nuova pratica (temporanea)")
    return d_prat

def get_tipo_allegato():
    "Determina il tipo di allegato"
    allx = [k for k in fk.request.form.keys() if k.endswith(".x")]
    if allx:
        return allx[0][:-2]
    return ""

def filename_allegato(tipo, origname, ext, spec, d_prat):    # pylint: disable=R0913
    "Genera nomi file per allegati"
    prefix, model = (cs.TAB_ALLEGATI[tipo][0], cs.TAB_ALLEGATI[tipo][2])
    if model == cs.ALL_SING:
        return prefix+ext
    if model == cs.ALL_SPEC:
        if spec:
            cspec = spec.strip("/\\?!;,><|#*\"'$%&£()`§")
            cspec = cspec.replace(" ", "_")
            return f"{prefix}_({cspec}){ext}"
        return ""
    if model == cs.ALL_NAME:
        return prefix+origname+ext
    if model != cs.ALL_PRAT:
        raise ILL_ATCH
    nprat = d_prat[cs.NUMERO_PRATICA].replace("/", "-")
    return f"{prefix}_{nprat}{ext}"

def _rdo_validate(dati_pratica):
    "Verifica coerenza dati relativi a RDO su MEPA"
    errors = []
    vincitore = [x for x in dati_pratica[cs.LISTA_DITTE] if x.get("vincitore")]
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

def costo_voce(voce):
    'calcola importo netto e iva'
    importo = float(voce['importo']) if voce['importo'] else 0.0
    iva = importo*(int(voce['iva'])/100.) if voce['iva'] else 0.0
    return importo, iva

def costo_totale(costo):
    'calcola costi per elementi separati: importo, iva, totale'
    totimp = 0.0
    totiva = 0.0
    totbase = 0.0
    imp, iva = costo_voce(costo['voce_1'])
    totimp += imp
    totiva += iva
    totbase += imp if costo['voce_1']['inbase'] else 0
    imp, iva = costo_voce(costo['voce_2'])
    totimp += imp
    totiva += iva
    totbase += imp if costo['voce_2']['inbase'] else 0
    imp, iva = costo_voce(costo['voce_3'])
    totimp += imp
    totiva += iva
    totbase += imp if costo['voce_3']['inbase'] else 0
    imp, iva = costo_voce(costo['voce_4'])
    totimp += imp
    totiva += iva
    totbase += imp if costo['voce_4']['inbase'] else 0
    imp, iva = costo_voce(costo['voce_5'])
    totimp += imp
    totiva += iva
    totbase += imp if costo['voce_5']['inbase'] else 0
    totimp = round(totimp, 2)
    totiva = round(totiva, 2)
    totbase = round(totbase, 2)
    return totimp, totiva, totimp+totiva, totbase

def _voce(voce):
    'genera rappresentazione come lista di una voce di costo'
    s_desc = voce['descrizione'].strip()
    if not s_desc:
        return '', '', '', '', ''
    s_imp = voce['importo']
    s_iva = voce['iva']
    v_imp = round(float(s_imp), 2) if s_imp else 0.0
    v_ivap = int(s_iva) if s_iva else 0
    v_ivav = round(v_imp*v_ivap/100., 2)
    v_tot = v_imp+v_ivav
    return s_desc, f'{v_imp:.2f}', s_iva, f'{v_ivav:.2f}', f'{v_tot:.2f}'

def costo_dett(costo):
    'genera lista con i dettagli di corso'
    return [_voce(costo['voce_1']),
            _voce(costo['voce_2']),
            _voce(costo['voce_3']),
            _voce(costo['voce_4']),
            _voce(costo['voce_5']),
           ]

def login():
    "genera pagina di login"
    if os.stat(cs.CONFIG_FILE).st_mtime > CONFIG.time:
        CONFIG.time = time.time()
        CONFIG.config = tb.jload(cs.CONFIG_FILE)
        logging.info('Riletta configurazione aggiornata')
    uid = fk.request.form.get('userid')
    pwd = fk.request.form.get('password')
    form = fms.MyLoginForm(cs.DATADIR, uid, pwd, CONFIG.config.get(cs.LDAP_HOST),
                           CONFIG.config.get(cs.LDAP_PORT), formdata=fk.request.form)
    if fk.request.method == 'POST' and form.validate():
        ret, why = form.password_ok()
        if ret:
            fk.session['userid'] = fk.request.form['userid']
            return fk.redirect(fk.url_for('start'))
        logging.error('Accesso negato: userid: "%s" (%s)', uid, why)
        fk.flash(f'Accesso negato: {why}', category="error")
    return fk.render_template('login.html', form=form, sede=CONFIG.config[cs.SEDE],
                              title='Procedura per acquisti')

def update_costo(d_prat, spec):
    'Aggiorna dati relativi al costo (spec: costo, costo_decisione)'
    totimp, totiva, tottot, totbase = costo_totale(d_prat[spec])
    d_prat[cs.COSTO_NETTO] = f'{totimp:.2f}'
    d_prat[cs.COSTO_IVA] = f'{totiva:.2f}'
    d_prat[cs.COSTO_TOTALE] = f'{tottot:.2f}'
    d_prat[cs.COSTO_BASE] = f'{totbase:.2f}'
    d_prat[cs.COSTO_DETTAGLIO] = costo_dett(d_prat[spec])

ACQ = fk.Flask(__name__, template_folder=cs.FILEDIR, static_folder=cs.FILEDIR)

@ACQ.before_request
def before():
    "procedura da eseguire prima di ogni pagina"
    if CONFIG.config.get(cs.CONFIG_VERSION, -1) != cs.CONFIG_REQUIRED:
        raise RuntimeError('File configurazione incompatibile')
    logger = logging.getLogger()
    logger.host_info = fk.request.remote_addr
    if userid := fk.session.get('userid'):
        update_lists()
        logger.user_info = userid
        ret = None
    else:
        logger.user_info = '----------'
        ret = login()
    ft.setformatter()
    return ret

def user_info():
    'trova record utente'
    if userid := fk.session.get('userid'):
        return ft.get_user(userid)
    return {}

def set_passo(d_prat, user, nuovo_stato):
    'aggiorna passo pratica'
    print('set_passo(d_prat,user,',nuovo_stato,')')
    d_prat[cs.PASSO] = nuovo_stato
    text = cs.PASSI[nuovo_stato][0]
    storia(d_prat, user, text)

@ACQ.route("/")
def start():
    "pagina: iniziale"
    logging.info('URL: / (%s)', fk.request.method)
    user = user_info()
    fk.session[BASEDIR_STR] = ''
    rooturl = ft.host(fk.request.url_root)
    status = {'url0': rooturl, 'footer': 'Procedura '+long_version()}
    if _test_admin(user):
        status['admin'] = 1
    if _test_developer(user):
        status['developer'] = 1
    if _test_direttore(user):
        status['direttore'] = 1
    return fk.render_template('start_acquisti.html', sede=CONFIG.config[cs.SEDE],
                              user=user, status=status)

@ACQ.route("/about")
def about():                                 # pylint: disable=R0915
    "pagina: informazioni sulle procedure"
    logging.info('URL: /about (%s)', fk.request.method)
    user = user_info()
    html = []
    html.append('<table cellpadding=3 border=1>')
    html.append('<tr><th colspan=2> Parametri di sistema </th></tr>')
    pinfo = ft.procinfo()
    for pinf in pinfo:
        html.append(f'<tr><td><b>{pinf[0]}</b></td><td> {pinf[1]} </td></tr>')
    html.append(f'<tr><td><b>Root path</b></td><td> {cs.PKG_ROOT} </td></tr>')
    html.append(f'<tr><td><b>Start</b></td><td> {__start__} </td></tr>')
    html.append('</table></td></tr>')
    html.append('<tr><td><table cellpadding=3 border=1>')
    html.append('<tr><th colspan=4> Informazioni sui moduli </td></tr>')
    html.append('<tr><th>Modulo</th><th>Versione</th><th>Data</th><th>Autore</th></tr>')
    fmt = '<tr><td> <tt> {} </tt></td><td> {} </td><td>{}</td> <td> {} </td></tr>'
    html.append(fmt.format('acquisti.py', __version__, __date__, __author__))
    html.append(fmt.format('constants.py', cs.__version__, cs.__date__, cs.__author__))
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
        html.append(f'<tr><td><b>PKG_ROOT</b></td><td>{cs.PKG_ROOT}</td></tr>')
        html.append(f'<tr><td><b>DATADIR</b></td><td>{cs.DATADIR}</td></tr>')
        html.append(f'<tr><td><b>WORKDIR</b></td><td>{cs.WORKDIR}</td></tr>')
        html.append(f'<tr><td><b>FILEDIR</b></td><td>{cs.FILEDIR}</td></tr>')
        html.append('</table></td></tr>')

        cks = list(CONFIG.config.keys())
        cks.sort()
        html.append('<tr><td><table cellpadding=3 border=1>')
        config_spec = f'{cs.CONFIG_FILE}, letto: {time.asctime(time.localtime(CONFIG.time))}'
        html.append(f'<tr><th colspan=2> File di configurazione ({config_spec})  </th></tr>')
        for key in cks:
            html.append(f'<tr><td><b>{key}</b></td><td>{CONFIG.config[key]}</td></tr>')
        html.append('</table></td></tr>')

        html.append('<tr><td><table cellpadding=3 border=1>')
        html.append('<tr><th> Lista files di help </th></tr>')
        html.append('<tr><td>'+', '.join(ft.GlobLists.HELPLIST)+'</td></tr>')
        html.append('</table></td></tr>')

    body = '\n'.join(html)
    return fk.render_template('about.html', sede=CONFIG.config[cs.SEDE], data=body)

@ACQ.route("/clearsession")
def clearsession():
    "pagina: logout"
    logging.info('URL: /clearsession (%s)', fk.request.method)
    fk.session.clear()
    return login()

@ACQ.route('/modificaprogetto', methods=('GET', 'POST'))
def modificaprogetto():               # pylint: disable=R0912,R0915,R0911,R0914
    "pagina: modifica progetto"
    logging.info('URL: /modificaprogetto (%s)', fk.request.method)
    if not (ret := _check_access(user_only=True)):
        return fk.redirect(fk.url_for('start'))
    print_debug('_check_access:', ret)
    user, basedir, d_prat = ret
    if not d_prat:
        d_prat = genera_pratica(user)
    else:
        err = check_progetto_modificabile(user, basedir, d_prat)
        if err.startswith(NOT):
            fk.flash(err, category="error")
            logging.error('Modifica progetto non possibile: %s. Utente:%s pratica %s',
                          err, user['userid'], d_prat[cs.NUMERO_PRATICA])
            return fk.redirect(fk.url_for('pratica1'))
    if not d_prat.get(cs.VERSIONE):
        raise RuntimeError("Formato file pratica obsoleto in modificaprogetto")
    prog = fms.ProgettoAcquisto(fk.request.form, **d_prat)
    codfs = ft.GlobLists.CODFLIST.column('Codice', unique=True)
    codf_menu = list(zip(codfs, codfs))
    prog.lista_codf.choices = codf_menu
    prog.email_responsabile.choices = _menu_scelta_utente("Seleziona responsabile")
    if not prog.lista_codf.data:    # Workaroud per errore wtform (non aggiorna campo)
        prog.lista_codf.process_data(d_prat.get("lista_codf", []))
    if fk.request.method == 'POST':
        print_debug('Request data:', fk.request.form)
        if cs.ANNULLA in fk.request.form:
            fk.flash('Operazione annullata', category="info")
            if cs.SAVED in d_prat:
                return fk.redirect(fk.url_for('pratica1'))
            return fk.redirect(fk.url_for('start'))
        mod_acquisto = fk.request.form.get(cs.MOD_ACQUISTO)
        print_debug('Modalità acquisto:', mod_acquisto)
        if mod_acquisto not in MODALITA_IMPLEMENTATE:
            fk.flash('Modalità di acquisto non ancora implementata', category="error")
            return fk.redirect(fk.url_for('start'))
        if prog.validate():
            if cs.STORIA_PRATICA not in d_prat:
                d_prat[cs.STORIA_PRATICA] = []
                year = ft.thisyear()
                number = ft.find_max_prat(year)+1
                basedir = ft.namebasedir(year, number)
                fk.session[BASEDIR_STR] = basedir
                ft.newdir(basedir)
                d_prat.update({cs.NUMERO_PRATICA: f'{number}/{year:4d}',
                               cs.DATA_RICHIESTA: ft.today(False)})
                storia(d_prat, user, 0)
            else:
                storia(d_prat, user, 'Modificato progetto di acquisto')
            d_prat.update(clean_data(prog.data))
            d_prat[cs.STR_CODF] = ', '.join(d_prat[cs.LISTA_CODF])
            d_prat[cs.STR_MOD_ACQ] = _select(cs.MENU_MOD_ACQ, d_prat.get(cs.MOD_ACQUISTO))
            d_prat[cs.STR_CRIT_ASS] = _select(cs.MENU_CRIT_ASS, d_prat.get(cs.CRIT_ASS))
            d_prat[cs.NOME_RESPONSABILE] = nome_da_email(d_prat[cs.EMAIL_RESPONSABILE], True)
            d_prat[cs.SEDE] = CONFIG.config[cs.SEDE]
            d_prat[cs.CITTA] = CONFIG.config[cs.SEDE][cs.CITTA]
            d_prat[cs.PROGETTO_INVIATO] = 0
            d_prat[cs.FIRMA_APPROV_RESP] = ""
            set_passo(d_prat, user, CdP.GPA)
            update_costo(d_prat, cs.COSTO_PROGETTO)
            d_prat[cs.SAVED] = 1
            salvapratica(basedir, d_prat)
            prog_name = os.path.splitext(cs.PROG_PDF_FILE)[0]
            ft.makepdf(basedir, prog_name, prog_name, debug=DEBUG.local, pratica=d_prat,
                       sede=CONFIG.config[cs.SEDE], warning='da approvare da resp.fondi')
            ft.remove((basedir, cs.DECIS_PDF_FILE), show_error=False)
            logging.info('Generato progetto: %s/%s', basedir, cs.PROG_PDF_FILE)
            _avvisi(user, basedir, d_prat, "A")
            return fk.redirect(fk.url_for('pratica1'))
        errors = prog.get_errors()
        for err in errors:
            fk.flash(err, category="error")
        logging.debug("Errori form Progetto di acquisto: %s", "; ".join(errors))
    return _render_progetto(prog, d_prat)

@ACQ.route('/inviaprogetto')
def inviaprogetto():
    "pagina: invia progetto per approvazione resp. fondi"
    logging.info('URL: /inviaprogetto (%s)', fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    err = check_progetto_inviabile(user, basedir, d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        logging.error(INVIO_NON_AUTORIZZ, err, user['userid'],
                      d_prat[cs.NUMERO_PRATICA])
    else:
        testo = cs.TESTO_APPROVAZIONE.format(d_prat[cs.NUMERO_PRATICA], fk.request.root_url)+ \
                cs.DETTAGLIO_PRATICA.format(**d_prat)
        subj = 'Richiesta di approvazione progetto di acquisto.'
        ret = send_email(d_prat[cs.EMAIL_RESPONSABILE], testo, subj)
        if ret:
            if d_prat[cs.MOD_ACQUISTO] in (cs.MEPA, cs.CONSIP):
                fk.flash("Ricorda di trasmettere la bozza d'ordine MEPA al "
                         "\"Punto Ordinante\"", category="info")
            fk.flash("Richiesta di approvazione per  la pratica "
                     f"{d_prat[cs.NUMERO_PRATICA]} inviata a: "
                     f"{d_prat.get(cs.EMAIL_RESPONSABILE)}", category="info")
            set_passo(d_prat, user, CdP.PIR)
            d_prat[cs.PROGETTO_INVIATO] = 1
            salvapratica(basedir, d_prat)
        else:
            msg = "Invio per approvazione fallito"
            fk.flash(msg, category="error")
    return fk.redirect(fk.url_for('pratica1'))

@ACQ.route('/inviadecisione')
def inviadecisione():                    #pylint: disable=R0914
    "pagina: invia decisione di contrarre per firma digitale direttore"
    logging.info('URL: /inviadecisione (%s)', fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    err = check_decisione_inviabile(user, basedir, d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        logging.error(INVIO_NON_AUTORIZZ, err, user['userid'],
                      d_prat[cs.NUMERO_PRATICA])
    else:
        decis_template = ft.modello_decisione(d_prat[cs.MOD_ACQUISTO])
        decis_name = os.path.splitext(cs.DECIS_PDF_FILE)[0]
        firma_dir = CONFIG.config[cs.TITOLO_DIRETTORE]+' '+CONFIG.config[cs.NOME_DIRETTORE]
        ft.makepdf(basedir, decis_template, decis_name, sede=CONFIG.config[cs.SEDE],
                   debug=DEBUG.local, pratica=d_prat, user=user, il_direttore=firma_dir)
        testo = cs.TESTO_INVIA_DECISIONE.format(**d_prat)+ \
                cs.DETTAGLIO_PRATICA.format(**d_prat)
        subj = 'Decisione di contrarre da firmare'
        numdet = d_prat.get(cs.NUMERO_DECISIONE).split('/')[0]
        pdfname = f"decisione_{numdet}.pdf"
        recipient = CONFIG.config[cs.EMAIL_DIREZIONE]
        attach = (os.path.join(basedir, cs.DECIS_PDF_FILE), pdfname)
        ret = send_email(recipient, testo, subj, attach=attach)
        if ret:
            fk.flash("Richiesta di approvazione per  la pratica "
                     f"{d_prat[cs.NUMERO_PRATICA]} inviata a: "
                     f"{recipient}", category="info")
            d_prat[cs.DECIS_INVIATA] = 1
            set_passo(d_prat, user, CdP.DCI)
            salvapratica(basedir, d_prat)
        else:
            msg = "Invio per firma fallito"
            fk.flash(msg, category="error")
    return fk.redirect(fk.url_for('pratica1'))

@ACQ.route('/approvaprogetto')
def approvaprogetto():
    "pagina: resp.fondi approva progetto"
    logging.info('URL: /approvaprogetto (%s)', fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    err = check_progetto_approvabile(user, basedir, d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        logging.error('Approvazione non autorizzata: %s. Utente %s pratica %s',
                      err, user['userid'], d_prat[cs.NUMERO_PRATICA])
    else:
        prog_name = os.path.splitext(cs.PROG_PDF_FILE)[0]
        ft.makepdf(basedir, prog_name, prog_name, debug=DEBUG.local, pratica=d_prat,
                   sede=CONFIG.config[cs.SEDE], il_responsabile=True,
                   warning='in attesa autorizz. direttore')
        d_prat[cs.FIRMA_APPROV_RESP] = ft.signature((basedir, cs.PROG_PDF_FILE))
        set_passo(d_prat, user, CdP.PAR)
        salvapratica(basedir, d_prat)
        fk.flash(f"L'approvazione del progetto {d_prat[cs.NUMERO_PRATICA]} è stata"
                 " correttamente registrata", category="info")
        subj = 'Notifica approvazione progetto di acquisto. Pratica: '+d_prat[cs.NUMERO_PRATICA]
        body = cs.TESTO_NOTIFICA_APPROVAZIONE.format(**d_prat)

        if not _test_responsabile(user, d_prat):
            send_email(d_prat[cs.EMAIL_RICHIEDENTE], body, subj)
        send_email(CONFIG.config[cs.EMAIL_UFFICIO], body, subj)
    return fk.redirect(fk.url_for('pratica1'))

@ACQ.route('/indicarup', methods=('GET', 'POST'))
def indicarup():
    "pagina: indica RUP"
    logging.info('URL: /indicarup (%s)', fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    err = check_rup_indicabile(user, d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        logging.error('Indicazione RUP non autorizzata: %s. Utente %s pratica %s',
                      err, user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica1()
    if cs.ANNULLA in fk.request.form:
        fk.flash('Operazione annullata', category="info")
        return pratica1()
    rupf = fms.IndicaRUP(fk.request.form)
    rupf.email_rup.choices = _menu_scelta_utente("Seleziona RUP")
    if fk.request.method == 'POST':
        if rupf.validate():
            d_prat[cs.EMAIL_RUP] = rupf.email_rup.data
            d_prat[cs.INTERNO_RUP] = rupf.interno_rup.data
            d_prat[cs.NOME_RUP] = nome_da_email(d_prat[cs.EMAIL_RUP], True)
            nominarup_name = os.path.splitext(cs.NOMINARUP_PDF_FILE)[0]
            ft.makepdf(basedir, nominarup_name, nominarup_name, debug=DEBUG.local, pratica=d_prat,
                       sede=CONFIG.config[cs.SEDE], warning='in attesa firma direttore')
            set_passo(d_prat, user, CdP.RUI)
            text = cs.TESTO_INDICA_RUP.format(d_prat[cs.NUMERO_PRATICA], fk.request.root_url)
            send_email(d_prat[cs.EMAIL_RUP], text, "Indicazione come RUP")
            salvapratica(basedir, d_prat)
            msg = f"{d_prat[cs.NOME_RUP]} indicato come RUP per pratica {d_prat[cs.NUMERO_PRATICA]}"
            logging.info(msg)
            fk.flash(msg, category='info')
            return pratica1()
        for err in rupf.errlist:
            fk.flash(err, category="error")
    body = rupf()
    ddp = {'title': 'Indica RUP',
           'before': '<form method=POST action=/indicarup '
                     'accept-charset="utf-8" novalidate>',
           'after': '</form>',
           'note': 'Questa è una nota',
           'body': body}
    return fk.render_template('form_layout.html', sede=CONFIG.config[cs.SEDE], data=ddp)

@ACQ.route('/autorizza', methods=('GET', ))
def autorizza():
    "autorizzazione del direttore"
    logging.info('URL: /autorizza (%s)', fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    err = check_rich_rup_autorizzabile(user, basedir, d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        logging.error('Autorizzazione richiesta non consentita: %s. Utente %s pratica %s',
                      err, user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica1()
    prog_name = os.path.splitext(cs.PROG_PDF_FILE)[0]
    firma_dir = CONFIG.config[cs.TITOLO_DIRETTORE]+' '+CONFIG.config[cs.NOME_DIRETTORE]
    ft.makepdf(basedir, prog_name, prog_name, debug=DEBUG.local, pratica=d_prat,
               nominarup=True, il_direttore=firma_dir,
               il_responsabile=True, sede=CONFIG.config[cs.SEDE])
    d_prat[cs.FIRMA_APPROV_RESP] = ft.signature((basedir, cs.PROG_PDF_FILE))
    nominarup_name = os.path.splitext(cs.NOMINARUP_PDF_FILE)[0]
    ft.makepdf(basedir, nominarup_name, nominarup_name, debug=DEBUG.local, pratica=d_prat,
               il_direttore=firma_dir, sede=CONFIG.config[cs.SEDE])
    d_prat[cs.PDF_NOMINARUP] = cs.NOMINARUP_PDF_FILE
    d_prat[cs.FIRMA_AUTORIZZ_DIR] = ft.signature((basedir, cs.NOMINARUP_PDF_FILE))
    text = cs.TESTO_NOMINA_RUP.format(d_prat[cs.NUMERO_PRATICA])
    send_email(d_prat[cs.EMAIL_RUP], text, "Nomina RUP")
    set_passo(d_prat, user, CdP.AUD)
    salvapratica(basedir, d_prat)
    return pratica1()

@ACQ.route('/rich_autorizzazione', methods=('GET', ))
def rich_autorizzazione():
    "pagina: richiesta autorizzazione del direttore"
    logging.info('URL: /rich_autorizzazione (%s)', fk.request.method)     #pylint: disable=W1203
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    err = check_autorizz_richiedibile(user, basedir, d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        logging.error('Invio richiesta di autorizzazione non consentito: %s. Utente %s pratica %s',
                      err, user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica1()
    subj = 'Richiesta autorizzazione progetto di acquisto. Pratica: '+d_prat[cs.NUMERO_PRATICA]
    body = cs.TESTO_RICHIESTA_AUTORIZZAZIONE.format(url=fk.request.root_url, **d_prat)
    ret = send_email(CONFIG.config[cs.EMAIL_DIREZIONE], body, subj)
    if ret:
        msg = 'Richiesta di autorizzazione inviata al direttore'
        fk.flash(msg, category="info")
        logging.info(msg)
        set_passo(d_prat, user, CdP.IRD)
        salvapratica(basedir, d_prat)
        return pratica1()
    err = 'Invio richiesta di autorizzazione al direttore fallito'
    fk.flash(err, category="error")
    logging.error(err)
    return pratica1()

@ACQ.route('/rimuovirup', methods=('GET', ))
def rimuovirup():
    "pagina: rimuovi RUP"
    logging.info('URL: /rimuovirup (%s)', fk.request.method)
    raise RuntimeError("ritorno indietro da definire")
#   if not (ret := _check_access()):
#       return fk.redirect(fk.url_for('start'))
#   user, basedir, d_prat = ret
#   err = check_rup_cancellabile(user, basedir, d_prat)
#   if err.startswith(NOT):
#       fk.flash(err, category="error")
#       logging.error('Cancellazione RUP non autorizzata: %s. Utente %s pratica %s',
#                     err, user['userid'], d_prat[cs.NUMERO_PRATICA])
#       return pratica1()
#   msg = f"RUP: {d_prat[cs.NOME_RUP]} cancellato"
#   logging.info(msg)
#   _mydel(cs.EMAIL_RUP, d_prat)
#   _mydel(cs.NOME_RUP, d_prat)
#   d_prat[cs.PASSO] = 20
#   ft.remove((basedir, cs.NOMINARUP_PDF_FILE), show_error=False)
#   salvapratica(basedir, d_prat)
#   fk.flash(msg, category="info")
#   return pratica1()

@ACQ.route('/cancella/<name>', methods=('GET', 'POST'))
def cancella(name):
    "pagina: cancella allegato"
    logging.info('URL: /cancella/%s (%s)', name, fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    err = check_allegati_cancellabili(user, d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        logging.error('Rimozione allegato non autorizzata: %s. Utente %s pratica %s',
                      err, user['userid'], d_prat[cs.NUMERO_PRATICA])
    else:
        storia(d_prat, user, f'Rimosso allegato {name}')
        ft.remove((basedir, name))
    salvapratica(basedir, d_prat)
    return pratica1()

@ACQ.route('/vedicodf')
def vedicodf():
    "pagine: visualizza lista codici Fu.Ob."
    logging.info('URL: /vedicodf (%s)', fk.request.method)
    return ft.GlobLists.CODFLIST.render(title="Lista Codici Fu.Ob. e responsabili")

@ACQ.route('/vedifile/<filename>')
def vedifile(filename):
    "pagina: visualizza file PDF"
    logging.info('URL: /vedifile/%s (%s)', filename, fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    basedir = ret[1]
    return fk.send_from_directory(basedir, filename, as_attachment=True)

# Filtri applicabili:
#   RIC_A: pratica aperta come richiedente
#   RUP_A: pratica aperta come RUP
#   RES_0: pratica da approvare come responsabile dei fondi
#   DIR_0: pratica da approvare come direttore
#   RIC_C: pratica chiusa come richiedente
#   RUP_C: pratica chiusa come RUP
#   RES_1: pratica approvata come responsabile dei fondi
#   DIR_1: pratica approvata come direttore

PRAT_APE = 'Elenco pratiche aperte '
PRAT_CHI = 'Elenco pratiche chiuse '
PRAT_APP = 'Elenco pratiche approvate '
PRAT_DAP = 'Elenco pratiche da approvare '
PRAT_NOR = 'Elenco pratiche in attesa di indicazione del RUP'

@ACQ.route('/pratiche/<filtro>/<anno>/<ascendente>')
def lista_pratiche(filtro, anno, ascendente):            #pylint: disable=R0915,R0912,R0914
    "pagina: lista pratiche"
    logging.info('URL: /pratiche/%s/%s/%s (%s)', filtro, anno, ascendente, fk.request.method)
    user = user_info()
    fk.session[BASEDIR_STR] = ''
    anno = int(anno)
    if not anno:
        anno = ft.thisyear()
    if int(ascendente):
        sort_f = _pratica_ascendente
    else:
        sort_f = _pratica_discendente
    oper = filtro[:3]
    if oper == 'ALL':      # Lista praticahe aperte/chiuse
        if not _test_admin(user):
            logging.error('Visualizzazione pratiche come amministrativo non autorizzata. '\
                          'Utente: %s', user['userid'])
            fk.session.clear()
            return fk.render_template('noaccess.html', sede=CONFIG.config[cs.SEDE])
        ruolo = lambda x: True
        if filtro[-1] == 'A':
            stato = lambda x: x.get(cs.PRATICA_APERTA)
            title = PRAT_APE
        else:
            stato = lambda x: not x.get(cs.PRATICA_APERTA)
            title = PRAT_CHI
    elif oper == 'RIC':   # Lista pratiche aperte/chiuse come richiedente
        ruolo = lambda x, u=user: _test_richiedente(u, x)
        str_ruolo = 'come richiedente'
        if filtro[-1] == 'A':           # pratica aperta
            stato = lambda x: x.get(cs.PRATICA_APERTA)
            title = PRAT_APE+str_ruolo
        else:                           # pratica chiusa
            stato = lambda x: not x.get(cs.PRATICA_APERTA)
            title = PRAT_CHI+str_ruolo
    elif oper == 'RES':   # Lista pratiche da approvare/approvate come resp. fondi
        ruolo = lambda x, u=user: _test_responsabile(u, x)
        str_ruolo = 'come responsabile dei fondi'
        if filtro[-1] == '0':            # pratica da approvare
            stato = lambda x: not x.get(cs.FIRMA_APPROV_RESP)
            title = PRAT_DAP+str_ruolo
        else:                            # pratica approvata
            stato = lambda x: x.get(cs.FIRMA_APPROV_RESP)
            title = PRAT_APP+str_ruolo
    elif oper == 'RUP':   # Lista pratiche aperte/chiuse come RUP
        ruolo = lambda x, u=user: _test_rup(u, x)
        str_ruolo = 'come RUP'
        if filtro[-1] == 'A':
            stato = lambda x: x.get(cs.PRATICA_APERTA)
            title = PRAT_APE+str_ruolo
        else:
            stato = lambda x: not x.get(cs.PRATICA_APERTA)
            title = PRAT_CHI+str_ruolo
    elif oper == 'DIR':   # Lista pratiche da autorizzare/autorizzate come Direttore
        if not _test_direttore(user):
            logging.error('Visualizzazione pratiche come direttore non autorizzata. '\
                          'Utente: %s', user['userid'])
            fk.session.clear()
            return fk.render_template('noaccess.html', sede=CONFIG.config[cs.SEDE])
        ruolo = lambda x: True
        str_ruolo = 'come Direttore'
        if filtro[-1] == '1':
            stato = lambda x: bool(x.get(cs.FIRMA_AUTORIZZ_DIR))
            title = PRAT_APP+str_ruolo
        else:
            stato = lambda x: not x.get(cs.FIRMA_AUTORIZZ_DIR)
            title = PRAT_DAP+str_ruolo
    elif oper == 'NOR':    # Lista pratiche in attesa di indicazione del RUP
        if not _test_admin(user):
            logging.error('Visualizzazione pratiche come amministrativo non autorizzata. '\
                          'Utente: %s', user['userid'])
            fk.session.clear()
            return fk.render_template('noaccess.html', sede=CONFIG.config[cs.SEDE])
        ruolo = lambda x: True
        title = PRAT_NOR
        stato = lambda x: (not x.get(cs.EMAIL_RUP)) and x.get(cs.FIRMA_APPROV_RESP)
    else:
        err = f'Operazione non valida in lista pratiche ({oper})'
        raise RuntimeError(err)
    f_filter = lambda x: ruolo(x) and stato(x)
    try:
        doclist = ft.DocList(cs.DATADIR, cs.PRAT_JFILE, anno, content_filter=f_filter, sort=sort_f)
    except Exception:               # pylint: disable=W0703
        err_msg = _errore_doclist(anno)
        fk.flash(err_msg, category="error")
        logging.error(err_msg)
        return fk.redirect(fk.url_for('start'))
    theyear = int(anno)
    years = [int(y) for y in doclist.years]
    return fk.render_template('lista_pratiche_per_anno.html', filtro=filtro,
                              sede=CONFIG.config[cs.SEDE], years=years, year=theyear,
                              dlist=doclist.records, title=title)

@ACQ.route('/trovapratica', methods=('POST', 'GET'))
def trovapratica():               # pylint: disable=R0912,R0914,R0915
    "pagina: trova pratica"
    logging.info('URL: /trovapratica (%s)', fk.request.method)
    fk.session[BASEDIR_STR] = ''
    user = user_info()
    if not (_test_admin(user) or _test_direttore(user)):
        logging.error('Ricerca pratiche non autorizzata. Utente: %s', user['userid'])
        fk.session.clear()
        return fk.render_template('noaccess.html', sede=CONFIG.config[cs.SEDE])
    if cs.ANNULLA in fk.request.form:
        fk.flash('Operazione annullata', category="info")
        return fk.redirect(fk.url_for('start'))
    prf = fms.TrovaPratica(fk.request.form)
    user_menu = [(x[6], x[6]) for  x in ft.GlobLists.USERLIST.rows]
    user_menu.sort(key=lambda x: x[1])
    user_menu.insert(0, ('*', 'Tutti'))
    prf.trova_responsabile.choices = user_menu
    prf.trova_richiedente.choices = user_menu
    years = ft.get_years(cs.DATADIR)
    years.sort(reverse=True)
    year_menu = list(zip(years, years))
    prf.trova_anno.choices = year_menu
    if fk.request.method == 'POST':
        theyear = prf.data['trova_anno']
        ricerca = f" anno={prf.data['trova_anno']} + (pratiche "
        vaperta = int(prf.data.get('trova_prat_aperta', '-1'))
        if vaperta == 1:
            ricerca += 'aperte)'
            aperta_func = lambda x: x.get(cs.PRATICA_APERTA, False)
        elif vaperta == 0:
            ricerca += 'chiuse)'
            aperta_func = lambda x: not x.get(cs.PRATICA_APERTA, False)
        else:
            ricerca += 'aperte e chiuse)'
            aperta_func = lambda x: True
        if nome_resp := prf.data['trova_responsabile']:
            resp_func = lambda x: word_match(nome_resp, x.get(cs.NOME_RESPONSABILE, ''))
            ricerca += f' + (resp.={nome_resp})'
        else:
            resp_func = lambda x: True
        if nome_rup := prf.data['trova_rup']:
            rup_func = lambda x: word_match(nome_rup, x.get(cs.NOME_RUP, ''))
            ricerca += f' + (rup={nome_rup})'
        else:
            rup_func = lambda x: True
        if nome_rich := prf.data['trova_richiedente']:
            rich_func = lambda x: word_match(nome_rich, x.get(cs.NOME_RICHIEDENTE, ''))
            ricerca += f' + (richied.={nome_rich})'
        else:
            rich_func = lambda x: True
        if prf.data['trova_parola']:
            parola_func = lambda x: word_match(prf.data.get('trova_parola', ''),
                                               x.get(cs.DESCRIZIONE_ACQUISTO, ''))
            ricerca += f" + (contiene parola={prf.data['trova_parola']})"
        else:
            parola_func = lambda x: True
        selector = lambda x: aperta_func(x) and rich_func(x) and \
                             resp_func(x) and rup_func(x) and parola_func(x)
        if prf.data['elenco_ascendente']:
            sort_f = _pratica_ascendente
        else:
            sort_f = lambda x: -1*_pratica_ascendente(x)
        try:
            lista = ft.DocList(cs.DATADIR, cs.PRAT_JFILE, theyear,
                               content_filter=selector, sort=sort_f)
        except Exception:               # pylint: disable=W0703
            err_msg = _errore_doclist(theyear)
            fk.flash(err_msg, category="error")
            logging.error(err_msg)
            return fk.redirect(fk.url_for('start'))
        title = 'Trova Pratiche'
        subtitle = 'Risultato per ricerca: '+ricerca+'<br>'+ \
                   f'N. pratiche selezionate: {len(lista)}'
        return fk.render_template('lista_pratiche_per_anno.html', filtro='', pre=[],
                                  post=[], year=theyear, dlist=lista.records, title=title,
                                  sede=CONFIG.config[cs.SEDE], subtitle=subtitle)
    ddp = {'title': 'Trova pratiche',
           'subtitle': 'Specifica criteri di ricerca',
           'before': '<form method=POST action=/trovapratica '
                     'accept-charset="utf-8" novalidate>',
           'after': '</form>',
           'body': prf()}
    return fk.render_template('form_layout.html', sede=CONFIG.config[cs.SEDE], data=ddp)

@ACQ.route('/pratica0/<num>/<year>', methods=('GET', ))
def pratica0(num, year):
    "pagina: accesso a pratica indicata"
    logging.info('URL: /pratica0/%s/%s (%s)', num, year, fk.request.method)
    basedir = ft.namebasedir(year, num)
    fk.session[BASEDIR_STR] = basedir
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    return pratica_common(user, basedir, d_prat)

@ACQ.route('/pratica1', methods=('GET', 'POST'))
def pratica1():               # pylint: disable=R0914,R0911,R0912
    "pagina: pratica, modo 1 (iterazione modifica)"
    logging.info('URL: /pratica1 (%s)', fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    if fk.request.method == 'POST':
        if 'upload_file' in fk.request.files:
            try:
                fle = fk.request.files['upload_file']
            except Exception as exc:               # pylint: disable=W0703
                fk.flash(f"Errore caricamento file: {exc}", category="error")
                return pratica_common(user, basedir, d_prat)
            tipo_allegato = get_tipo_allegato()
            logging.info("Richiesta upload: %s (tipo: %s)", fle.filename, tipo_allegato)
            origname, ext = os.path.splitext(fle.filename)
            origname = secure_filename(origname)
            ext = ext.lower()
            if ext not in cs.UPLOAD_TYPES:
                fk.flash(f"Tipo allegato non valido: {fle.filename}", category="error")
                return pratica_common(user, basedir, d_prat)
            spec = fk.request.form.get(cs.SIGLA_DITTA, "")
            name = filename_allegato(tipo_allegato, origname, ext, spec, d_prat)
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
            ft.protect(fpath)
            text = 'Allegato ' + cs.TAB_ALLEGATI[tipo_allegato][1]
            storia(d_prat, user, text)
                                             # Aggiorna stato pratica
            if d_prat[cs.PASSO] == CdP.RUI:
                if _test_all_cv_rup(basedir) and _test_all_dich_rup(basedir):
                    set_passo(d_prat, user, CdP.RAL)
            elif d_prat[cs.PASSO] == CdP.AUD:
                if _test_all_cig(basedir):
                    set_passo(d_prat, user, CdP.ROG)
            elif d_prat[cs.PASSO] == CdP.ROG:
                if _test_all_rdo(basedir):
                    set_passo(d_prat, user, CdP.RFI)
            elif d_prat[cs.PASSO] == CdP.DCI:
                if _test_all_decis_firmata(basedir):
                    set_passo(d_prat, user, CdP.DCF)
            elif d_prat[cs.PASSO] == CdP.DCF:
                if _test_all_obblig_perf(basedir):
                    set_passo(d_prat, user, CdP.OGP)
            salvapratica(basedir, d_prat)
    return pratica_common(user, basedir, d_prat)

@ACQ.route('/togglestoria', methods=('GET', 'POST', ))
def togglestoria():
    "pagina: abilita/disabilita storia pratica"
    logging.info('URL: /togglestoria (%s)', fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    sst = d_prat.get(cs.VEDI_STORIA, 0)
    if sst:
        d_prat[cs.VEDI_STORIA] = 0
    else:
        d_prat[cs.VEDI_STORIA] = 1
    salvapratica(basedir, d_prat)
    return pratica_common(user, basedir, d_prat)

@ACQ.route('/modificardo', methods=('GET', 'POST'))
def modificardo():
    "Gestione form per produzione di RdO"
    logging.info('URL: /modificardo (%s)', fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    err = check_rdo_modificabile(user, basedir, d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        logging.error('Generazione/modifica rdo non autorizzata: %s. Utente %s, Pratica %s', \
                      err, user['userid'], d_prat.get(cs.NUMERO_PRATICA, 'N.A.'))
    else:
        if fk.request.method == 'POST':
            if cs.ANNULLA in fk.request.form:
                fk.flash('Operazione annullata', category="info")
                return fk.redirect(fk.url_for('pratica1'))
            rdo = fms.RdO(fk.request.form)
            if cs.AVANTI in fk.request.form:
                if rdo.validate():
                    rdo_data = rdo.data.copy()
                    d_prat.update(clean_data(rdo_data))
                    update_costo(d_prat, cs.COSTO_RDO)
                    logging.info('Genera rdo: %s/%s', basedir, cs.RDO_PDF_FILE)
                    rdo_template = os.path.splitext(cs.RDO_PDF_FILE)[0]
                    rdo_name = os.path.splitext(cs.RDO_PDF_FILE)[0]
                    ft.makepdf(basedir, rdo_template, rdo_name, sede=CONFIG.config[cs.SEDE],
                               debug=DEBUG.local, pratica=d_prat, user=user)
                    if _test_all_cig(basedir):
                        set_passo(d_prat,user, CdP.ROG)
                    salvapratica(basedir, d_prat)
                    return fk.redirect(fk.url_for('pratica1'))
                errors = rdo.get_errors()
                for err in errors:
                    fk.flash(err, category="error")
                logging.debug("Errori form RdO: %s", "; ".join(errors))
        else:
            d_prat[cs.COSTO_RDO] = d_prat[cs.COSTO_PROGETTO].copy()
            rdo = fms.RdO(**d_prat)
        ddp = {'title': 'Immissione dati per RDO su MePA',
               'subtitle': f"Pratica N. {d_prat['numero_pratica']}",
               'before': '<form method=POST action=/modificardo '\
                         'accept-charset="utf-8" novalidate>',
               'after': "</form>",
               'note': cs.OBBLIGATORIO,
               'body': rdo(**d_prat)}
    return fk.render_template('form_layout.html', sede=CONFIG.config[cs.SEDE], data=ddp)

@ACQ.route('/modificadecisione', methods=('GET', 'POST', ))
def modificadecisione():                     #pylint: disable=R0914
    "pagina: modifica decisione di contrarre"
    logging.info('URL: /modificadecisione (%s)', fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    if cs.ANNULLA in fk.request.form:
        fk.flash('Operazione annullata', category="info")
        return fk.redirect(fk.url_for('pratica1'))
    err = check_decisione_modificabile(user, basedir, d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        logging.error('Gestione decisione di contrarre non autorizzata: %s. Utente %s, pratica %s',
                     err, user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica1()
    if cs.NUMERO_DECISIONE not in d_prat:
        year = ft.thisyear()
        ndet = ft.find_max_decis(year)[0]+1
        d_prat[cs.NUMERO_DECISIONE] = f"{ndet}/{year:4d}"
        d_prat[cs.DATA_DECISIONE] = ft.today(False)
        logging.info("Nuovo num. decisione: %s", d_prat[cs.NUMERO_DECISIONE])
    det = fms.Decisione(fk.request.form, **d_prat)
    if fk.request.method == 'POST':
        if det.validate():
            d_prat.update(clean_data(det.data))
            update_costo(d_prat, cs.COSTO_RDO)
            logging.info('Genera decisione provvisoria: %s/%s', basedir, cs.DECIS_PDF_FILE)
            decis_template = ft.modello_decisione(d_prat[cs.MOD_ACQUISTO])
            decis_name = os.path.splitext(cs.DECIS_PDF_FILE)[0]
            ft.makepdf(basedir, decis_template, decis_name, sede=CONFIG.config[cs.SEDE],
                       debug=DEBUG.local, pratica=d_prat, user=user,
                       warning='P R O V V I S O R I O')
            d_prat[cs.PDF_DECISIONE] = cs.DECIS_PDF_FILE
            set_passo(d_prat, user, CdP.DCG)
            salvapratica(basedir, d_prat)
            url = fk.url_for('pratica1')
            return fk.redirect(url)
        errors = det.get_errors()
        for err in errors:
            fk.flash(err, category="error")
        logging.debug("Errori form Determina agg.: %s", "; ".join(errors))

    ddp = {'title': 'Immissione dati per decisione di contrarre',
           'subtitle': f"Pratica N. {d_prat['numero_pratica']}",
           'before': '<form method=POST action=/modificadecisione '
                     'accept-charset="utf-8" novalidate>',
           'after': "</form>",
           'note': cs.OBBLIGATORIO,
           'body': det(d_prat)}
    return fk.render_template('form_layout.html', sede=CONFIG.config[cs.SEDE], data=ddp)

@ACQ.route('/cancelladecisione', methods=('GET', ))
def cancelladecisione():
    "pagina: cancella decisione"
    logging.info('URL: /cancelladecisione (%s)', fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    err = check_decisione_cancellabile(user, basedir, d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        logging.error('cancellazione decisione non autorizzata: %s. Utente %s, pratica %s',
                      err, user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica1()
    ft.remove((basedir, cs.DECIS_PDF_FILE), show_error=False)
    hist = "Cancellata decisione di contrarre. " \
           f"Pratica N. {d_prat.get(cs.NUMERO_PRATICA, '')}"
    storia(d_prat, user, hist)
    salvapratica(basedir, d_prat)
    return pratica1()

@ACQ.route('/rollback', methods=('GET', 'POST'))
def rollback():                       #pylint: disable=R0914
    "Pagina: annulla ultimo passo"
    logging.info('URL: /rollback (%s)', fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    err = check_rollback(user, basedir)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        logging.error('annullamento ultimo passo non autorizzato: %s. Utente %s, pratica %s',
                      err, user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica1()
    passo = d_prat[cs.PASSO]
    passi = list(cs.PASSI.keys())
    precid = passi.index(passo)-1
    if precid < 0:
        err = 'Annullamento passo impossibile'
        fk.flash(err, category="error")
        return pratica1()
    prec = passi[precid]
    logging.debug('Al passo %s rolling back to %s', passo, prec)
    doc_to_remove = cs.PASSI[passo][1] if cs.PASSI[passo][1] else ''
    cod_all = cs.PASSI[passo][2]
    all_to_remove = [cs.TAB_ALLEGATI[x][0][4:] for x in cod_all]
    logging.debug('Documento da cancellare: %s', doc_to_remove)
    logging.debug('Allegati da cancellare: %s', str(all_to_remove))
    if 'annulla' in fk.request.form:
        logging.info('Operazione annullata')
        fk.flash('Operazione annullata', category="info")
        return pratica1()
    if 'conferma' in fk.request.form:
        logging.info('Annullamento confermato')
        if doc_to_remove:
            ft.remove((basedir, doc_to_remove))
            logging.info('Rimosso file {name}')
        for tipo in cod_all:
            name = filename_allegato(tipo, '', '.pdf', '', d_prat)
            ft.remove((basedir, name))
            logging.info('Rimosso file {name}')
        msg = "Annullato ultimo passo pratica"
        storia(d_prat, user, msg)
        set_passo(d_prat, user, prec)
        salvapratica(basedir, d_prat)
        fk.flash(msg, category="info")
        logging.info(msg)
        return pratica1()
    ddp = {'passo': cs.PASSI[passo][0],
           'prec': cs.PASSI[prec][0],
           'remove_doc': doc_to_remove,
           'remove_all': ', '.join(all_to_remove)}
    return fk.render_template('rollback.html', sede=CONFIG.config[cs.SEDE],
                              pratica=d_prat, data=ddp)

@ACQ.route('/chiudipratica')
def chiudipratica():
    "pagina: chiudi pratica"
    logging.info('URL: /chiudipratica (%s)', fk.request.method)
    raise ToBeImplemented()

@ACQ.route('/apripratica')
def apripratica():
    "pagina: apri pratica"
    logging.info('URL: /apripratica (%s)', fk.request.method)
    return modifica_pratica('apri')

@ACQ.route('/annullapratica', methods=('GET', 'POST'))
def annullapratica():
    "pagina: annulla pratica"
    logging.info('URL: /annullapratica (%s)', fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    if cs.ANNULLA in fk.request.form:
        fk.flash('Operazione annullata', category="info")
        return pratica1()
    annul = fms.AnnullaPratica(fk.request.form)
    if fk.request.method == 'POST':
        if annul.validate():
            d_prat[cs.MOTIVAZIONE_ANNULLAMENTO] = annul.motivazione_annullamento.data
            set_passo(d_prat, user, CdP.ANN)
            salvapratica(basedir, d_prat)
            msg = f"Pratica {d_prat[cs.NUMERO_PRATICA]} annullata"
            storia(d_prat, user, msg)
            logging.info(msg)
            fk.flash(msg, category='info')
            return pratica1()
        msg = "Motivazione annullamento non specificata"
        fk.flash(msg, category="error")
        logging.error(msg)
    body = annul()
    before_text = NOTA_ANNULLAMENTO + '''
<form method=POST action=/annullapratica 
accept-charset="utf-8" novalidate>
'''
    ddp = {'title': 'Annullamento pratica',
           'before': before_text,
           'after': '</form>',
           'note': 'Questa è una nota',
           'body': body}
    return fk.render_template('form_layout.html', sede=CONFIG.config[cs.SEDE], data=ddp)

@ACQ.route('/files/<name>')
def files(name):
    "download file"
    logging.info('URL: /files/%s (%s)', name, fk.request.method)     #pylint: disable=W1203
    return  ACQ.send_static_file(name)

@ACQ.route('/devel', methods=('GET', 'POST'))
def devel():                     #pylint: disable=R0915
    'operazioni per supporto sviluppo'
    logging.info('URL: /devel (%s)', fk.request.method)
    if not (ret := _check_access()):
        return fk.redirect(fk.url_for('start'))
    user, basedir, d_prat = ret
    if not _test_developer(user):
        fk.session.clear()
        raise RuntimeError("Accesso illegale")
    if 'vediinfo' in fk.request.form:
        text = '<h4>Info:</h4><pre>'
        keys = [x for x in fk.request.form.keys() if x.startswith('info.')]
        keys.sort()
        for key in keys:
            text += '   '+key+': '+fk.request.form.get(key)+'\n'
        text += '</blockquote>'
    elif 'vedichecks' in fk.request.form:
        info = make_info(user, basedir, d_prat)
        keys = list(info.keys())
        keys.sort()
        text = "<h4>Checks su pratica N. "+d_prat[cs.NUMERO_PRATICA]+"</h4><pre>\n"
        for  key in keys:
            text += f"  - {key} -> {info[key]}\n"
    elif 'vedipratica' in fk.request.form:
        ppath = os.path.join(basedir, cs.PRAT_JFILE)
        ppt = PrettyPrinter(indent=4)
        text = f'<h4>{ppath}</h4>'
        text += '<pre>'+ ppt.pformat(d_prat)+'</pre>'
    elif 'vediconfig' in fk.request.form:
        ppt = PrettyPrinter(indent=4)
        text = f'<h4>{cs.CONFIG_FILE}</h4>'
        text += '<pre>'+ ppt.pformat(CONFIG.config)+'</pre>'
    elif 'vedirequest' in fk.request.form:
        lines = ['<h4>Request (parziale):</h4><pre>']
        lines.append(f'application: {fk.request.application}')
        lines.append(f'base_url: {fk.request.base_url}')
        lines.append(f'full_path: {fk.request.full_path}')
        lines.append(f'host: {fk.request.host}')
        lines.append(f'host_url: {fk.request.host_url}')
        lines.append(f'path: {fk.request.path}')
        lines.append(f'remote_addr: {fk.request.remote_addr}')
        lines.append(f'remote_user: {fk.request.remote_user}')
        lines.append(f'root_path: {fk.request.root_path}')
        lines.append(f'root_url: {fk.request.root_url}')
        lines.append(f'server: {fk.request.server}')
        lines.append(f'url: {fk.request.url}')
        lines.append(f'url_root: {fk.request.url_root}')
        lines.append(f'url_rule: {fk.request.url_rule}')
        lines.append(f'user_agent: {fk.request.user_agent}')
        lines.append('</pre>')
        text = '\n'.join(lines)
    else:
        fk.session.clear()
        raise RuntimeError("Accesso illegale")
    return text

#############################################################################
################### Pagine housekeeping #####################################

@ACQ.route('/housekeeping')
def housekeeping():
    "Inizio procedura housekeeping"
    logging.info('URL: /housekeeping (%s)', fk.request.method)
    user = user_info()
    status = {'footer': f"Procedura housekeeping.py. Vers. {__version__} - " \
                        f"L. Fini, {__date__}",
              'host': ft.host(fk.request.url_root)}

    if _test_admin(user):
        return fk.render_template('start_housekeeping.html',
                                  user=user,
                                  sede=CONFIG.config[cs.SEDE],
                                  status=status).encode('utf8')
    fk.session.clear()
    return fk.render_template('noaccess.html')

@ACQ.route("/sortcodf/<field>")
def sortcodf(field):
    "Riporta codici Fu.Ob. con ordine specificato"
    logging.info('URL: /sortcodf/%s (%s)', field, fk.request.method)
    user = user_info()
    if not _test_admin(user):
        return fk.render_template('noaccess.html').encode('utf8')
    ncodf = ft.FTable((cs.DATADIR, 'codf.json'), sortable=('Codice', 'email_Responsabile'))
    msgs = fk.get_flashed_messages()
    return ncodf.render("Lista Codici Fu.Ob.",
                        select_url=("/editcodf",
                                    "Per modificare, clicca sul simbolo: "
                                    "<font color=red><b>&ofcir;</b></font>"),
                        sort_url=('/sortcodf', '<font color=red>&dtrif;</font>'),
                        menu=(('/addcodf', "Aggiungi Codice Fu.Ob."),
                              ('/downloadcodf', "Scarica CSV"),
                              ('/housekeeping', 'Torna')),
                        sort_on=field,
                        messages=msgs,
                        footer=f"Procedura housekeeping.py. Vers. {__version__}. "\
                               f"&nbsp;-&nbsp; L. Fini, {__date__}")

@ACQ.route("/codf")
def codf():
    "Riporta codici Fu.Ob."
    logging.info('URL: /codf (%s)', fk.request.method)
    return sortcodf('')


@ACQ.route('/addcodf', methods=('GET', 'POST'))
def addcodf():
    "Aggiungi codice Fu.Ob."
    logging.info('URL: /addcodf (%s)', fk.request.method)
    user = user_info()
    if not _test_admin(user):
        return fk.render_template('noaccess.html').encode('utf8')
    cfr = fms.CodfForm(formdata=fk.request.form)
    ulist = ft.FTable((cs.DATADIR, 'userlist.json')).as_dict('email', True)
    resp_menu = [(x, _nome_resp(ulist, x, False)) for  x in ulist]
    resp_menu.sort(key=lambda x: x[1])
    cfr.email_Responsabile.choices = resp_menu
    ncodf = ft.FTable((cs.DATADIR, 'codf.json'))
    if fk.request.method == 'POST':
        if 'annulla' in fk.request.form:
            fk.flash('Operazione annullata')
            return fk.redirect(fk.url_for('housekeeping'))
        if cfr.validate():
            data = ncodf.get_row(0, as_dict=True, default='') # get an empty row
            data.update(cfr.data)
            ncodf.insert_row(data)
            ncodf.save()
            msg = f"Aggiunto Codice Fu.Ob.: {data['Codice']}"
            logging.info(msg)
            fk.flash(msg)
            return fk.redirect(fk.url_for('codf'))
        logging.debug("Validation errors: %s", cfr.errlist)
    return ncodf.render_item_as_form('Aggiungi Codice Fu.Ob.', cfr,
                                     fk.url_for('addcodf'),
                                     errors=cfr.errlist)

@ACQ.route('/editcodf/<nrec>', methods=('GET', 'POST'))
def editcodf(nrec):
    "Modifica tabella codici Fu.Ob."
    logging.info('URL: /editcodf/%s (%s)', nrec, fk.request.method)
    nrec = int(nrec)
    user = user_info()
    if not _test_admin(user):
        return fk.render_template('noaccess.html').encode('utf8')
    ncodf = ft.FTable((cs.DATADIR, 'codf.json'))
    row = ncodf.get_row(nrec, as_dict=True)
    ulist = ft.FTable((cs.DATADIR, 'userlist.json')).as_dict('email')
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
            msg = "Cancellato Codice Fu.Ob.: " \
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
                msg = "Modificato Codice Fu.Ob.: " \
                      f"{row['Codice']} ({row['email_Responsabile']})"
                fk.flash(msg)
                logging.info(msg)
            return fk.redirect(fk.url_for('codf'))
        logging.debug("Validation errors: %s", cfr.errlist)
    return ncodf.render_item_as_form('Modifica Codice Fu.Ob.', cfr,
                                     fk.url_for('editcodf', nrec=str(nrec)),
                                     errors=cfr.errlist, nrow=nrec)

@ACQ.route('/downloadcodf', methods=('GET', 'POST'))
def downloadcodf():
    "Download tabella codici Fu.Ob."
    logging.info('URL: /downloadcodf (%s)', fk.request.method)
    return download('codf')

@ACQ.route('/downloadutenti', methods=('GET', 'POST'))
def downloadutenti():
    "Download tabella utenti"
    logging.info('URL: /downloadutenti (%s)', fk.request.method)
    return download('utenti')

def download(_unused):
    "Download"
    return fk.render_template('tbd.html', goto='/')

@ACQ.route("/utenti")
def utenti():
    "Genera lista utenti"
    logging.info('URL: /utenti (%s)', fk.request.method)
    user = user_info()
    if _test_admin(user):
        users = ft.FTable((cs.DATADIR, 'userlist.json'))
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


@ACQ.route('/adduser', methods=('GET', 'POST'))
def adduser():
    "Aggiungi utente"
    logging.info('URL: /adduser (%s)', fk.request.method)
    user = user_info()
    if _test_admin(user):
        cfr = fms.UserForm(formdata=fk.request.form)
        users = ft.FTable((cs.DATADIR, 'userlist.json'))
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

@ACQ.route('/edituser/<nrec>', methods=('GET', 'POST'))
def edituser(nrec):
    "Modifica dati utente"
    logging.info('URL: /edituser/%s (%s)', nrec, fk.request.method)
    nrec = int(nrec)
    user = user_info()
    if _test_admin(user):
        users = ft.FTable((cs.DATADIR, 'userlist.json'))
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

@ACQ.route('/environ', methods=('GET',))
def environ():
    "Mostra informazioni su environment"
    logging.info('URL: /environ (%s)', fk.request.method)
    user = user_info()
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
    return fk.render_template('environ.html', sede=CONFIG.config[cs.SEDE], request=req, environ=env)

@ACQ.route('/testmail', methods=('GET',))
def testmail():
    "Invia messaggio di prova all'indirizzo di webmaster"
    logging.info('URL: /testmail (%s)', fk.request.method)
    user = user_info()
    if not _test_developer(user):
        fk.session.clear()
        return fk.render_template('noaccess.html')
    thetime = time.asctime()
    if smtp := CONFIG.config.get(cs.SMTP_HOST) == '-':
        host = 'GMail API'
    else:
        host = f'SMTP server: {smtp}'
    recipient = [CONFIG.config.get(cs.EMAIL_WEBMASTER)]
    sender = CONFIG.config.get(cs.EMAIL_UFFICIO, "")
    subj = "Messaggio di prova da procedura 'acquisti'"
    body = cs.MESSAGGIO_DI_PROVA.format(host)
    ret = send_email(recipient, body, subj)
    succ = 'SI' if ret else 'NO'
    return fk.render_template('testmail.html', time=thetime, sender=sender,
                              recipients=recipient,
                              server=host, state=succ).encode('utf8')

@ACQ.route('/force_excp', methods=('GET',))
def force_excp():                       #pylint: disable=R1710
    "Causa una eccezione"
    logging.info('URL: /force_excp (%s)', fk.request.method)
    user = user_info()
    if not _test_developer(user):
        fk.session.clear()
        return fk.render_template('noaccess.html')
    1/0                                 # pylint: disable=W0104

#############################################################################
############################### Inizializzazioni ############################

def initialize_me():
    "inizializza tutto il necessario"
    logging.info('Starting %s', long_version())
    logging.info('PKG_ROOT: %s', cs.PKG_ROOT)
    logging.info('DATADIR: %s', cs.DATADIR)
    logging.info('WORKDIR: %s', cs.WORKDIR)

    configname = os.path.join(cs.DATADIR, 'config.json')
    logging.info('Config loaded from: %s', configname)

    ft.latex.set_path(CONFIG.config.get("latex_path", ""))
    logging.info("LaTeX path: %s", ft.latex.PDFLATEX.cmd)

    update_lists()
    ft.init_helplist()
    ACQ.secret_key = CONFIG.config[cs.FLASK_KEY]

    ft.clean_locks(cs.DATADIR)

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
    ft.set_mail_logger(CONFIG.config[cs.SMTP_HOST], CONFIG.config[cs.EMAIL_PROCEDURA],
                       CONFIG.config[cs.EMAIL_WEBMASTER], 'Notifica errore ACQUISTI (debug)')
    ACQ.run(host="0.0.0.0", port=4001, debug=True)

def production():
    "lancia la procedura in modo produzione (all'interno del web server)"
    logging.basicConfig(level=logging.INFO)    # Livello logging normale
#   logging.basicConfig(level=logging.DEBUG)   # Più verboso
    initialize_me()
    ft.set_file_logger((cs.WORKDIR, 'acquisti5.log'))
    ft.set_mail_logger(CONFIG.config[cs.SMTP_HOST], CONFIG.config[cs.EMAIL_PROCEDURA],
                       CONFIG.config[cs.EMAIL_WEBMASTER], 'Notifica errore ACQUISTI')

if __name__ == '__main__':
    localtest()
else:
    production()
