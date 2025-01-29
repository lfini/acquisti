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
from collections import UserDict
from pprint import PrettyPrinter
import traceback

import jinja2 as j2
import wtforms as wt
import flask as fk
import constants as cs
from constants import CdP
import latex

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

# Versione 5.0   3/2024:   Preparazione nuova versione 2024 con modifiche sostanziali
# Versione 5.1   10/2024:  Modifiche e correzioni dopo la messa in produzione della versione 5
# Versione 5.2   12/2024:  Bugfix: ritorno a procedura principale da housekeeping.
#                          Attivato flag per versione di test in configurazione
# Versione 5.3   1/2025:   Introdotta lista decisioni per anno e verifiche sulla duplicazione
#                          dei numeri di decisione
# Versione 5.3.1 1/2025:   Corretto ftools.py per bug in calcolo ultima pratica dell'anno
# Versione 5.3.2 1/2025:   Messo log invio mail
# Versione 5.4   1/2025:   Corretti errori nel form per Decisione

__author__ = 'Luca Fini'
__version__ = '5.4'
__date__ = '27/1/2025'

__start__ = time.asctime(time.localtime())

# stringhe per auth_xxxxx
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
NO_NON_PREV = 'NO: non prevista'
NO_NON_RICH = 'NO: '+NON_RICH
NO_NON_RESP = 'NO: '+NON_RESP
NO_NON_RUP = 'NO: '+NON_RUP
NO_NON_DIR = 'NO: '+NON_DIR
NO_NON_ADMIN_RUP = 'NO: non sei amministratore o RUP'
NO_NO_RDO = 'NO: RdO non richiesta'
NO_PASSO_ERRATO = 'NO: operazione non prevista a questo passo'
NO_PDF_CIG = 'NO: Manca allegato CIG'
NO_PDF_RDO_MEPA = 'NO: Manca allegato RdO da MePA'
NO_PRATICA_CHIUSA = 'NO: Pratica chiusa'
NO_PRATICA_ANNULLATA = 'NO: Pratica annullata'
NO_PRATICA_GIA_ANNULLATA = 'NO: Pratica già annullata'
NO_PRATICA_APERTA = 'NO: Pratica aperta'
NO_PROGETTO_GEN = 'NO: Progetto non generato'
NO_PREVENTIVO = 'NO: manca preventivo in allegato'
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

ILLEGAL_OP = 'Operazione non consentita'

INVIO_NON_AUTORIZZ = 'Invio non autorizzato: %s. Utente: %s pratica %s'

NOTA_ANNULLAMENTO = '''
<tr><td><b>Attenzione:</b> La pratica annullata in un qualunque
stato di avanzamento  non potrà più essere riaperta o riutilizzata.
<p>
Per procedere devi specificare una motivazione per l'annullamento
e premere "Conferma" </td></tr>
'''

def verifica_tabella_passi():
    'Verifica tabella passi'
    tab = cs.TABELLA_PASSI
    codes = list(cs.CdP)
    t_keys = list(tab.keys())
    some_err = False
    for code in codes:
        if code not in t_keys:
            ACQ.logger.error('Elemento CdP.%s non usato', code)
            some_err = True

    for key, value in tab.items():
        if len(value) != 5:
            ACQ.logger.error('Errore passo %s: lunghezza', key)
            some_err = True
        if not isinstance(value[0], str):
            ACQ.logger.error('Errore passo %s[0]: non stringa', key)
            some_err = True
        if not isinstance(value[1], list):
            ACQ.logger.error('Errore passo %s[1]: non lista', key)
            some_err = True
        if len(value[1]) not in (0, 2):
            ACQ.logger.error('Errore passo %s[1]: lunghezza diversa da 2', key)
            some_err = True
        if not isinstance(value[2], list):
            ACQ.logger.error('Errore passo %s[2]: non lista', key)
            some_err = True
        if not isinstance(value[3], list):
            ACQ.logger.error('Errore passo %s[3]: non lista', key)
            some_err = True
        if not isinstance(value[4], (dict, cs.CdP)):
            ACQ.logger.error('Errore passo %s[4]: non enum CdP', key)
            some_err = True
    if some_err:
        raise RuntimeError('Trovati errori in Tabella generale passi')

class ToBeImplemented(RuntimeError):
    'Parte codice non implementata'

class CONFIG:                   # pylint: disable=R0903
    'Dati di configurazione'
    time = time.time()
    config = tb.jload(cs.CONFIG_FILE)

def pass_info(passcode, what=''):      # pylint: disable=R0911
    'Riporta la descrizione del passo di dato codice'
    passo = cs.TABELLA_PASSI[passcode]
    if what.startswith('t'):
        return passo[0]
    if what.startswith('f'):
        return passo[1]
    if what.startswith('c'):
        return passo[2]
    if what.startswith('a'):
        return passo[3]
    if what.startswith('n'):
        return passo[4]
    if what.startswith('F'):
        return passo
    return passcode

class Pratica(UserDict):                  #pylint: disable=R0903
    'dati pratica'
    def __init__(self, init, basedir='', user=None):
        super().__init__(init)
        self.user = user if user else {}
        self.set_basedir(basedir)

    def __str__(self):
        ppt = PrettyPrinter(indent=4)
        return f'''
Pratica:
    data = {ppt.pformat(self.data)}
    basedir = {self.basedir}
    user = {ppt.pformat(self.user)}
    stato = {self.data[cs.TAB_PASSI]}'''

    def __repr__(self):
        return self.__str__()

    def set_basedir(self, basedir):
        'Imposta basedir'
        self.basedir = basedir

    def get_passo(self, what=''):
        'riporta passo corrente - what = "text", "file", "cmd", "alleg", "next", "Full"'
        passcode = self.data[cs.TAB_PASSI][-1]
        if not what:
            return passcode
        return pass_info(passcode, what)

    def get_back(self, what=''):
        'riporta passo precedente - what = "text", "file", "cmd", "alleg", "next", "Full"'
        try:
            passcode = self.data[cs.TAB_PASSI][-2]
        except IndexError:
            return None
        return pass_info(passcode, what)

    def check_next(self):
        'Verifica se passo successivo consentito'
        cpasso = self.data[cs.TAB_PASSI][-1]
        _, doc, _, alleg, npasso = cs.TABELLA_PASSI[cpasso]
        if isinstance(npasso, dict):
            npasso = npasso[self.data[cs.MOD_ACQUISTO]]
        if doc:
            fname = doc[0]
            if not ft.findfiles(self.basedir, fname):
                ACQ.logger.debug('Incremento non applicato - file mancante: %s', fname)
                return f'Documento mancante: {fname}', cpasso
        if alleg:
            for alg in alleg:
                if not ft.findfiles(self.basedir, cs.TAB_ALLEGATI[alg][0]):
                    ACQ.logger.debug('Incremento non applicato: allegato mancante')
                    return 'Allegato mancante', cpasso
        return '', npasso

    def next(self):
        'passa a passo successivo, se condizioni verificate'
        ret, npasso = self.check_next()
        if ret:
            return ret
        self.data[cs.TAB_PASSI].append(npasso)
        ACQ.logger.debug('Passo raggiunto: %s', str(npasso))
        return ''

    def back(self):
        'passa a passo precedente'
        if len(self.data[cs.TAB_PASSI]) < 2:
            return False
        cpasso = self.data[cs.TAB_PASSI].pop(-1)
        ppasso = self.data[cs.TAB_PASSI][-1]
        ACQ.logger.debug('back(), {%s} -> {%s}', cpasso, ppasso)
        alleg = self.get_passo('a')
        for alg in alleg:
            name = cs.TAB_ALLEGATI[alg][0]
            ret = ft.remove((self.basedir, name))
            if ret:
                ACQ.logger.info('Rimosso file: %s', ret)
        doc = self.get_passo('f')
        genera_documento(self, doc)
        return True

    def annulla(self, motivo):
        'annullamento pratica'
        self.data[cs.MOTIVAZIONE_ANNULLAMENTO] = motivo
        self.data[cs.TAB_PASSI].append(CdP.ANN)
        self.data[cs.PRATICA_APERTA] = False

START_YEAR = 0

class DEBUG:         # pylint: disable=R0903
    "Variabili di supporto per Debug"
    local = False
    email = ''

FASE_ERROR = Exception("Manca specifica fase")
NO_BASEDIR = Exception("Basedir non definita")
ILL_ATCH = Exception("Modello allegato non previsto")

def update_lists():
    "Riinizializza tabelle"
    ft.update_userlist()
    ft.update_codflist()

#  Utilities

def test_admin(user) -> bool:
    "test: l'utente è amministratore"
    if user:
        return 'A' in user.get('flags')
    return False

def test_developer(user) -> bool:
    "test: l'utente è developer"
    if user:
        return 'D' in user.get('flags')
    return False

def test_richiedente(d_prat: Pratica) -> bool:
    "test: l'utente è il richiedente"
    emailrich = d_prat.get(cs.EMAIL_RICHIEDENTE, "R").lower()
    emailuser = d_prat.user.get("email", "U").lower()
    return emailuser == emailrich

def test_responsabile(d_prat: Pratica) -> bool:
    "test: l'utente è il resp. fondi"
    emailresp = d_prat.get(cs.EMAIL_RESPONSABILE, "R").lower()
    emailuser = d_prat.user.get("email", "U").lower()
    return emailuser == emailresp

def test_rup(d_prat: Pratica) -> bool:
    "test: l'utente è il RUP della pratica"
    emailrup = d_prat.get(cs.EMAIL_RUP, "R").lower()
    emailuser = d_prat.user.get("email", "U").lower()
    return emailuser == emailrup

def test_direttore(user) -> bool:
    "test: l'utente è il direttore"
    emaildir = CONFIG.config[cs.EMAIL_DIRETTORE].lower()
    emailuser = user.get("email", "U").lower()
    return emailuser == emaildir

def test_vicario(user) -> bool:
    "test: l'utente è il direttore vicario"
    emaildir = CONFIG.config[cs.EMAIL_VICARIO].lower()
    emailuser = user.get("email", "U").lower()
    return emailuser == emaildir

def test_doc_decisione(d_prat: Pratica) -> bool:
    "test: esistenza decisione di contrarre"
    if not d_prat.basedir:
        return False
    return os.path.exists(os.path.join(d_prat.basedir, cs.DOC_DECISIONE))

def test_doc_ordine(d_prat: Pratica) -> bool:
    "test: esistenza ordine"
    if not d_prat.basedir:
        return False
    return os.path.exists(os.path.join(d_prat.basedir, cs.DOC_ORDINE))

def test_allegato(d_prat: Pratica, cod_allegato):
    "Test esistenza dell'allegato richiesto al dato passo"
    if cod_allegato in d_prat.get_passo(what='alleg'):
        return bool(ft.findfiles(d_prat.basedir, cs.TAB_ALLEGATI[cod_allegato][0]))
    return True

def test_doc_progetto(d_prat: Pratica) -> bool:
    "test: esistenza documento progetto"
    pdf_path = os.path.join(d_prat.basedir, cs.DOC_PROGETTO)
    return os.path.exists(pdf_path)

def test_doc_nominarup(d_prat: Pratica) -> bool:
    "test: esistenza documento autorizzazione"
    pdf_path = os.path.join(d_prat.basedir, cs.DOC_NOMINARUP)
    return os.path.exists(pdf_path)

def test_doc_rdo(d_prat: Pratica) -> bool:
    "test: esistenza documento autorizzazione"
    if not d_prat.basedir:
        return False
    pdf_path = os.path.join(d_prat.basedir, cs.DOC_RDO)
    return os.path.exists(pdf_path)

def test_rdo_richiesta(d_prat: Pratica) -> str:
    "True se la modalità di acquisto richiede RdO"
    return d_prat[cs.MOD_ACQUISTO] in (cs.TRATT_MEPA_40, cs.TRATT_UBUY_40,
                                       cs.TRATT_MEPA_143, cs.TRATT_UBUY_143)

def test_ordine_richiesto(d_prat: Pratica) -> str:
    "True se la modalità di acquisto richiede generazione dell'ordine"
    return d_prat.get(cs.MOD_ACQUISTO, '') in (cs.INFER_5000, cs.TRATT_UBUY_40,
                                               cs.TRATT_UBUY_143)

def auth_allegati_cancellabili(d_prat: Pratica) -> str:
    "test: allegati cancellabili"
    if not d_prat.get(cs.PRATICA_APERTA):
        return NO_PRATICA_CHIUSA
    if test_admin(d_prat.user):
        return YES
    ret = [NON_ADMIN]
    if test_richiedente(d_prat):
        return YES
    ret.append(NON_RICH)
    if test_responsabile(d_prat):
        return YES
    ret.append(NON_RESP)
    return 'NO: '+', '.join(ret)

def auth_progetto_inviabile(d_prat: Pratica) -> str:      # pylint: disable=R0911
    "test: progetto inviabile per approv. al resp. fondi"
    if not (test_admin(d_prat.user) or test_richiedente(d_prat)):
        return NO_RICH_AMM
    return YES

def auth_progetto_modificabile(d_prat: Pratica) -> str:            # pylint: disable=W0703,R0911
    "test: progetto modificabile"
    if test_admin(d_prat.user) or \
       test_richiedente(d_prat) or \
       test_responsabile(d_prat):
        return YES
    return NO_RICH_RESP_AMM

def auth_progetto_approvabile(d_prat: Pratica) -> str:
    "test: progetto approvabile"
    if test_responsabile(d_prat):
        return YES
    return NO_RESP

def auth_rup_indicabile(d_prat: Pratica) -> str:
    "test: è possibile indicare il RUP"
    return YES if test_admin(d_prat.user) else NO_NON_ADMIN

def auth_autorizz_richiedibile(d_prat: Pratica) -> str:     #pylint: disable=R0911
    "test: chi può chiedere l'autorizzazione del direttore?"
    return YES if test_admin(d_prat.user) else NO_NON_ADMIN

def auth_autorizzabile(d_prat: Pratica) -> str:
    "test: il direttore può autorizzare la richiesta del RUP?"
    if d_prat.get('rup_firma_vicario'):
        return YES if test_vicario(d_prat.user) else NO_NON_DIR
    return YES if test_direttore(d_prat.user) else NO_NON_DIR

def auth_rollback(d_prat: Pratica) -> str:
    "test: rollback attivabile"
    if test_admin(d_prat.user):
        return YES
    return NO_NON_ADMIN

def auth_rdo_modificabile(d_prat: Pratica) -> str:
    "test: rdo modificabile"
    if test_rup(d_prat) or test_admin(d_prat.user):
        return YES
    return NO_NON_ADMIN_RUP

def auth_decisione_modificabile(d_prat: Pratica) -> str:
    "test: decisione di contrarre modificabile"
    if test_rup(d_prat) or test_admin(d_prat.user):
        return YES
    return NO_NON_ADMIN_RUP

def auth_ordine_modificabile(d_prat: Pratica) -> str:
    "test: ordine modificabile"
    if test_rup(d_prat) or test_admin(d_prat.user):
        return YES
    return NO_NON_ADMIN_RUP

def auth_decisione_inviabile(d_prat: Pratica) -> str:
    "test: decisione di contrarre inviabile"
    if test_rup(d_prat) or test_admin(d_prat.user):
        return YES
    return NO_NON_ADMIN_RUP

def auth_decisione_cancellabile(d_prat: Pratica) -> str:
    "test: decisione di contrarre cancellabile"
    if test_rup(d_prat) or test_admin(d_prat.user):
        return YES
    return NO_NON_ADMIN_RUP

def auth_pratica_riapribile(d_prat: Pratica) -> str:
    "test: pratica chiudibile"
    if test_admin(d_prat.user):
        return YES
    return NO_NON_ADMIN

def auth_pratica_chiudibile(d_prat: Pratica) -> str:
    "test: pratica chiudibile"
    if test_admin(d_prat.user):
        return YES
    return NO_NON_ADMIN

def auth_pratica_annullabile(d_prat) -> str:
    "test: pratica annullabile"
    if test_admin(d_prat.user):
        return YES
    return NO_NON_ADMIN

def make_info(d_prat: Pratica) -> dict:
    "Verifica lo stato della pratica e riporta un dict riassuntivo"
    info = {}
    info['debug'] = YES if bool(DEBUG.local) else NOT
    info['developer'] = YES if test_developer(d_prat.user) else NOT
    info['admin'] = YES if test_admin(d_prat.user) else NOT
    info['responsabile'] = YES if test_responsabile(d_prat) else NOT
    info['direttore'] = YES if test_direttore(d_prat.user) else NOT
    info['all_preventivo'] = YES if test_allegato(d_prat, cs.ALL_PREV) else NOT
    info['all_cv_rup'] = YES if test_allegato(d_prat, cs.ALL_CV_RUP) else NOT
    info['all_dich_rup'] = YES if test_allegato(d_prat, cs.ALL_DICH_RUP) else NOT
    info['all_cig'] = YES if test_allegato(d_prat, cs.ALL_CIG) else NOT
    info['allegati_cancellabili'] = auth_allegati_cancellabili(d_prat)
    info['autorizz_richiedibile'] = auth_autorizz_richiedibile(d_prat)
    info['autorizzabile'] = auth_autorizzabile(d_prat)
    info['decis_modificabile'] = auth_decisione_modificabile(d_prat)
    info['decis_inviabile'] = auth_decisione_inviabile(d_prat)
    info['ordine_modificabile'] = auth_ordine_modificabile(d_prat)
    info['ordine'] = YES if test_ordine_richiesto(d_prat) else NOT
    info['pratica_annullabile'] = auth_pratica_annullabile(d_prat)
    info['progetto_approvabile'] = auth_progetto_approvabile(d_prat)
    info['pratica_chiudibile'] = auth_pratica_chiudibile(d_prat)
    info['pratica_riapribile'] = auth_pratica_riapribile(d_prat)
    info['progetto_modificabile'] = auth_progetto_modificabile(d_prat)
    info['progetto_inviabile'] = auth_progetto_inviabile(d_prat)
    info['rdo_richiesta'] = YES if test_rdo_richiesta(d_prat) else NOT
    info['rollback'] = auth_rollback(d_prat)
    info['rup_indicabile'] = auth_rup_indicabile(d_prat)
    info['rdo_modificabile'] = auth_rdo_modificabile(d_prat)
    info[cs.PDF_PROGETTO] = YES if test_doc_progetto(d_prat) else NOT
    info[cs.PDF_NOMINARUP] = YES if test_doc_nominarup(d_prat) else NOT
    info[cs.PDF_DECISIONE] = YES if test_doc_decisione(d_prat) else NOT
    info[cs.PDF_ORDINE] = YES if test_doc_ordine(d_prat) else NOT
    info[cs.PDF_RDO] = YES if test_doc_rdo(d_prat) else NOT
    return info

def check_all(d_prat: Pratica) -> dict:
    "Verifica lo stato della pratica e riporta un dict con valori bool"
    info = make_info(d_prat)
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

def storia(d_prat: Pratica, text: str):
    'aggiunge record alla storia della pratica'
    line = f'{text} - {ft.today()} ({d_prat.user["fullname"]})'
    d_prat[cs.STORIA_PRATICA].append(line)
    ACQ.logger.info(text)

def send_email(eaddr, text, subj, attach=None):
    'invio mail a utente'
    sender = CONFIG.config[cs.EMAIL_UFFICIO]
    if DEBUG.local:
        recipients = [CONFIG.config[cs.EMAIL_WEBMASTER]]
    else:
        if isinstance(eaddr, (list, tuple)):
            recipients = eaddr
        else:
            recipients = [eaddr]
    try:
        ft.send_email(CONFIG.config.get(cs.SMTP_HOST), sender, recipients,
                      subj, text, attach=attach, debug_addr=DEBUG.email)
    except Exception as excp:    #pylint: disable=W0718
        ACQ.logger.error('Invio messaggio "%s" a: %s (%s)', subj, eaddr, str(excp))
        return False
    ACQ.logger.debug('Inviato messaggio "%s" a: %s', subj, eaddr)
    return True

def check_access(new=False):
    "Verifica accesso alla pratica"
    user = user_info()
    if not user:
        err = 'utente non autorizzato'
        ACQ.logger.error(err)
        fk.flash(err, category="error")
        return None
    if new:
        fk.session[cs.BASEDIR] = ''
    basedir = fk.session.get(cs.BASEDIR, '')
    if basedir:
        d_prat = tb.jload((basedir, cs.PRAT_JFILE))
    else:
        d_prat = {cs.VERSIONE: cs.FILE_VERSION,
                  cs.NUMERO_PRATICA: '-------',
                  cs.EMAIL_RICHIEDENTE: user['email'],
                  cs.NOME_RICHIEDENTE: user['name']+' '+user['surname'],
                  cs.DATA_PRATICA: ft.today(fulltime=False),
                  cs.TAB_PASSI: [CdP.INI],
                  cs.PRATICA_APERTA: True}
    ACQ.logger.debug('Session: %s', str(fk.session))
    ACQ.logger.debug('Request form:')
    for key, val in fk.request.form.items():
        ACQ.logger.debug(' - %s: %s', key, val)
#   ACQ.logger.debug('Pratica: %s', str(d_prat))
    return Pratica(d_prat, user=user, basedir=basedir)

def status_not_ok(d_prat: Pratica, stati=()):
    "Verifica che l'operazione sia consentita nello stato corrente"
    passcode = d_prat.get_passo()
    text = cs.TABELLA_PASSI[passcode][0]
    ACQ.logger.info('Stato interno: %d - %s', passcode, text)
    if stati:
        return passcode not in stati
    return False

def menu_allegati(d_prat: Pratica, all_mancanti):
    'genera menù per allegati'
    def sel_menu(t_alleg):
        "Genera voce di menu per allegati"
        return (t_alleg,)+cs.TAB_ALLEGATI[t_alleg][1:3]
    menu = [sel_menu(x) for x in all_mancanti]
    if d_prat[cs.MOD_ACQUISTO] == cs.INFER_5000:
        menu.append(sel_menu(cs.ALL_LISTA_DETT))
    menu.append(sel_menu(cs.ALL_GENERICO))
    return menu

def salvapratica(d_prat: Pratica):
    'Salva pratica, rimuovendo campi provvisori'
    if not d_prat.basedir:
        raise RuntimeError(f'Manca basedir. Pratica: {d_prat[cs.NUMERO_PRATICA]}')
    tb.jsave((d_prat.basedir, cs.PRAT_JFILE), d_prat.data)
    ACQ.logger.info('Salvati dati pratica: %s/%s', d_prat.basedir, cs.PRAT_JFILE)

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
        if bool(ditta[cs.FORNITORE_NOME]) or  bool(ditta[cs.FORNITORE_SEDE]):
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

def pratica_common(d_prat: Pratica):
    "parte comune alle pagine relative alla pratica"
    info = check_all(d_prat)
    all_mancanti = allegati_mancanti(d_prat)
    menu = menu_allegati(d_prat, all_mancanti)
    upl = fms.MyUpload(menu)
    pdf_files = ft.flist(d_prat.basedir, filetypes=cs.UPLOAD_TYPES)
    info['attach'] = [(a, _clean_name(a), a.startswith('A99')) \
                           for a in pdf_files if ALL_MATCH.match(a)]
    info['allegati_mancanti'] = ', '.join(all_mancanti)
    info['stato_pratica'] = d_prat.get_passo('t')
    info['commands'] = d_prat.get_passo('cmd')
    return fk.render_template('pratica.html', info=info, test_mode=CONFIG.config.get(cs.TEST_MODE),
                              pratica=d_prat, upload=upl, sede=CONFIG.config[cs.SEDE])

def modifica_pratica(what):               # pylint: disable=R0912,R0915
    "parte comune alle pagine di modifica pratica"
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    if what[0].lower() == 'c':      # Chiudi pratica
        err = auth_pratica_chiudibile(d_prat)
        if err.startswith(NOT):
            fk.flash(err, category="error")
            ACQ.logger.warning('Chiusura pratica rifiutata: %s. Utente %s, pratica %s',
                            err, d_prat.user['userid'], d_prat[cs.NUMERO_PRATICA])
        else:
            d_prat[cs.PRATICA_APERTA] = False
            d_prat.next()
            text = f'Pratica {d_prat[cs.NUMERO_PRATICA]} chiusa'
            storia(d_prat, text)
            salvapratica(d_prat)
        return pratica_common(d_prat)
    if what[0].lower() == 'a':      # Riapri pratica
        err = auth_pratica_riapribile(d_prat)
        if err.startswith(NOT):
            fk.flash(err, category="error")
            ACQ.logger.warning('Riapertura pratica rifiutata: %s. Utente %s, pratica %s',
                            err, d_prat.user['userid'], d_prat[cs.NUMERO_PRATICA])
        else:
            d_prat.back()
            d_prat[cs.PRATICA_APERTA] = True
            text = f'Pratica {d_prat[cs.NUMERO_PRATICA]} riaperta'
            storia(d_prat, text)
            salvapratica(d_prat)
        return pratica_common(d_prat)
    msg = f'Errore interno - modifica_pratica: codice illegale ({what})'
    fk.flash(msg, category="error")
    ACQ.logger.error(msg)
    return fk.redirect(fk.url_for('start'))

def _mydel(key, d_prat):
    "Cancella un campo della pratica"
    try:
        del d_prat[key]
    except KeyError:
        pass

def allegati_mancanti(d_prat: Pratica):
    "Genera lista allegati mancanti (nuovo: da tabella passi)"
    alleg = d_prat.get_passo(what='alleg')
    return [a for a in alleg if not test_allegato(d_prat, a)]

def avvisi(d_prat: Pratica, _fase, _level=0):
    "Genera messaggi di avviso per pagina pratica. level=0: tutti; level=1: errori"
    if not d_prat.get(cs.FIRMA_APPROV_RESP):
        fk.flash("Occorre richiedere l'approvazione del responsabile dei fondi", category="info")

def _pratica_discendente(item):
    "funzione ausiliaria per sort pratiche"
    nprat = item.get(cs.NUMERO_PRATICA, '0/0').split('/')[0]
    return -int(nprat)

def render_progetto(form, d_prat: Pratica):
    "rendering del form progetto di acquisto"
    ddp = {'title': 'Progetto di acquisto',
           'subtitle': f"Pratica N. {d_prat['numero_pratica']}<br><br>"
                       f"Richiedente: {d_prat['nome_richiedente']}",
           'before': '<form method=POST action=/modificaprogetto '
                     'accept-charset="utf-8" novalidate>',
           'after': '</form>',
           'note': cs.OBBLIGATORIO,
           'body': form()}
    return fk.render_template("form_layout.html", sede=CONFIG.config[cs.SEDE],
                              test_mode=CONFIG.config.get(cs.TEST_MODE), data=ddp)

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

def genera_documento(d_prat: Pratica, spec: list, filenum=0):
    'genera un documento da template e opzioni'
    ACQ.logger.debug('Genera_documento - spec=%s, filenum=%s', str(spec), str(filenum))
    if not spec:
        return None
    nome_pdf, opts = spec
    noext = os.path.splitext(nome_pdf)[0]
    nome_tmpl = noext+'-'+cs.TAB_TEMPLATE[d_prat[cs.MOD_ACQUISTO]]+'.tex'
    template = os.path.join(cs.FILEDIR, nome_tmpl)
    if filenum:
        nome_pdf = f'{noext}_{filenum}.pdf'
    ndata = {x: 1 for x in opts}
    if cs.VICARIO in opts:
        ndata[cs.NOME_VICARIO] = CONFIG.config[cs.NOME_VICARIO]
    if d_prat.get(cs.EMAIL_RESPONSABILE, 'A') == d_prat.get(cs.EMAIL_RICHIEDENTE, 'B'):
        ndata['rich_is_rup'] = 1
    ndata[cs.SEDE] = CONFIG.config[cs.SEDE]
    ndata[cs.RICH_IS_RESP] = d_prat[cs.EMAIL_RICHIEDENTE] == d_prat[cs.EMAIL_RESPONSABILE]
    ndata["headerpath"] = os.path.join(cs.FILEDIR, "header.png")
    ndata["footerpath"] = os.path.join(cs.FILEDIR, "footer.png")
    ndata["dir_is_m"] = CONFIG.config['gender_direttore'].lower() == 'm'
    ACQ.logger.info('Generazione documento: %s/%s (template: %s)',
                 d_prat.basedir, nome_pdf, template)
    latex.makepdf(d_prat.basedir, nome_pdf, template,
                  debug=DEBUG.local, pratica=d_prat.data, **ndata)
    return nome_pdf

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
        ACQ.logger.info('Riletta configurazione aggiornata')
    uid = fk.request.form.get('userid')
    pwd = fk.request.form.get('password')
    form = fms.MyLoginForm(cs.DATADIR, uid, pwd, CONFIG.config.get(cs.LDAP_HOST),
                           CONFIG.config.get(cs.LDAP_PORT), formdata=fk.request.form)
    if fk.request.method == 'POST' and form.validate():
        ret, why = form.password_ok()
        if ret:
            fk.session['userid'] = fk.request.form['userid']
            return fk.redirect(fk.url_for('start'))
        ACQ.logger.error('Accesso negato: userid: "%s" (%s)', uid, why)
        fk.flash(f'Accesso negato: {why}', category="error")
    return fk.render_template('login.html', form=form,
                              sede=CONFIG.config[cs.SEDE],
                              test_mode=CONFIG.config.get(cs.TEST_MODE),
                              title='Procedura per acquisti')

def update_costo(d_prat: Pratica, spec):
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
    remote = fk.request.remote_addr
    if userid := fk.session.get('userid'):
        update_lists()
        ret = None
    else:
        userid = '-'
        ret = login()
    ft.set_log_context(remote, userid)
    return ret

def user_info():
    'trova record utente'
    if userid := fk.session.get('userid'):
        return ft.get_user(userid)
    ACQ.logger.error('user_info() called with userid: %s', userid)
    return {}

@ACQ.route("/")
def start():
    "pagina: iniziale"
    ACQ.logger.info('URL: / (%s)', fk.request.method)
    user = user_info()
    if not user:
        return login()
    fk.session[cs.BASEDIR] = ''
    rooturl = ft.host(fk.request.url_root)
    status = {'url0': rooturl, 'footer': 'Procedura '+long_version()}
    if test_admin(user):
        status['admin'] = 1
    if test_developer(user):
        status['developer'] = 1
    if test_direttore(user):
        status['direttore'] = 1
    if test_vicario(user):
        status['vicario'] = 1
    anno = ft.thisyear()
    doclist, _ = ft.trova_pratiche_1(anno, 'NOR', user['email'])
    status['no_rup'] = len(doclist)
    return fk.render_template('start_acquisti.html', sede=CONFIG.config[cs.SEDE],
                              test_mode=CONFIG.config.get(cs.TEST_MODE), user=user, status=status)

@ACQ.route("/about")
def about():                                 # pylint: disable=R0915
    "pagina: informazioni sulle procedure"
    ACQ.logger.info('URL: /about (%s)', fk.request.method)
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
    html.append(fmt.format('latex.py', latex.__version__,
                           latex.__date__, latex.__author__))
    html.append(fmt.format('table.py', ft.tb.__version__, ft.tb.__date__, ft.tb.__author__))
    html.append(fmt.format('Flask', fk.__version__, '-',
                           'Vedi: <a href=http://flask.pocoo.org>Flask home</a>'))
    html.append(fmt.format('Jinja2', j2.__version__, '-',
                           'Vedi: <a href=https://jinja.palletsprojects.com>Jinja2 home</a>'))
    html.append(fmt.format('WtForms', wt.__version__, '-',
                           'Vedi: <a href=https://wtforms.readthedocs.org>WtForms home</a>'))
    html.append('</table></td></tr>')
    if test_admin(user):
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
    return fk.render_template('about.html', sede=CONFIG.config[cs.SEDE],
                              test_mode=CONFIG.config.get(cs.TEST_MODE), data=body)

@ACQ.route("/clearsession")
def clearsession():
    "pagina: logout"
    ACQ.logger.info('URL: /clearsession (%s)', fk.request.method)
    fk.session.clear()
    return login()

@ACQ.route('/procedi', methods=('GET', ))
def procedi():
    "pagina per avanzamento generico"
    ACQ.logger.info('URL: /procedi (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat, (CdP.AUD, CdP.DCI, CdP.ORD, CdP.ALS, CdP.OGP)):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    ret = d_prat.next()
    if ret:
        fk.flash(ret, category="error")
    else:
        salvapratica(d_prat)
    return pratica_common(d_prat)

@ACQ.route('/modificaprogetto', methods=('GET', 'POST'))
def modificaprogetto():               # pylint: disable=R0912,R0915,R0911,R0914
    "pagina: modifica progetto"
    ACQ.logger.info('URL: /modificaprogetto (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat, (CdP.INI, )):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    if cs.ANNULLA in fk.request.form:
        fk.flash('Operazione annullata', category="info")
        if d_prat.get(cs.NUMERO_PRATICA, '-').startswith('-'):
            return fk.redirect(fk.url_for('start'))
        return pratica_common(d_prat)
    err = auth_progetto_modificabile(d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        ACQ.logger.error('Modifica progetto non possibile: %s. Utente:%s pratica %s',
                      err, d_prat.user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica_common(d_prat)
    if mod_acquisto := fk.request.form.get(cs.MOD_ACQUISTO):
        d_prat[cs.MOD_ACQUISTO] = mod_acquisto
    ACQ.logger.debug('Modalità acquisto: %s', mod_acquisto)
    prog = fms.ProgettoAcquisto(fk.request.form, **d_prat)
    codfs = ft.GlobLists.CODFLIST.column('Codice', unique=True)
    codf_menu = list(zip(codfs, codfs))
    prog.lista_codf.choices = codf_menu
    prog.email_responsabile.choices = _menu_scelta_utente("Seleziona responsabile")
    if not prog.lista_codf.data:    # Workaround per errore wtform (non aggiorna campo)
        prog.lista_codf.process_data(d_prat.get("lista_codf", []))
    if mod_acquisto:
        if not cs.TAB_TEMPLATE.get(mod_acquisto):
            err = 'Modalità di acquisto non ancora implementata'
            fk.flash(err, category="error")
            ACQ.logger.error(err)
            return fk.redirect(fk.url_for('start'))
    if fk.request.method == 'GET':
        return render_progetto(prog, d_prat)
    if prog.validate():
        if cs.STORIA_PRATICA not in d_prat:
            d_prat[cs.STORIA_PRATICA] = []
            year = ft.thisyear()
            number = ft.find_max_prat(year)+1
            basedir = ft.namebasedir(year, number)
            fk.session[cs.BASEDIR] = basedir
            thedir = ft.newdir(basedir)
            ACQ.logger.info("Creata directory: %s", thedir)
            d_prat.update({cs.NUMERO_PRATICA: f'{number}/{year:4d}',
                           cs.DATA_PRATICA: ft.today(False)})
            d_prat.set_basedir(basedir)
            storia(d_prat, f'Aperta pratica: {d_prat[cs.NUMERO_PRATICA]}')
        d_prat.update(clean_data(prog.data))
        d_prat[cs.STR_CODF] = ', '.join(d_prat[cs.LISTA_CODF])
        d_prat[cs.STR_MOD_ACQ] = _select(cs.MENU_MOD_ACQ, d_prat.get(cs.MOD_ACQUISTO))
        d_prat[cs.STR_CRIT_ASS] = _select(cs.MENU_CRIT_ASS, d_prat.get(cs.CRIT_ASS))
        d_prat[cs.NOME_RESPONSABILE] = nome_da_email(d_prat[cs.EMAIL_RESPONSABILE], True)
        d_prat[cs.NOME_DIRETTORE] = CONFIG.config[cs.NOME_DIRETTORE]
        d_prat[cs.SEDE] = CONFIG.config[cs.SEDE]
        d_prat[cs.CITTA] = CONFIG.config[cs.SEDE][cs.CITTA]
        d_prat[cs.FIRMA_APPROV_RESP] = ""
        update_costo(d_prat, cs.COSTO_PROGETTO)
        doc = d_prat.get_passo('f')
        d_prat[cs.SAVED] = 1
        storia(d_prat, 'Generato/modificato progetto di acquisto')
        salvapratica(d_prat)
        genera_documento(d_prat, doc)
        avvisi(d_prat, "A")
        return pratica_common(d_prat)
    errors = prog.get_errors()
    for err in errors:
        fk.flash(err, category="error")
    ACQ.logger.debug("Errori form Progetto di acquisto: %s", "; ".join(errors))
    return render_progetto(prog, d_prat)

@ACQ.route('/inviaprogetto')
def inviaprogetto():
    "pagina: invia progetto per approvazione resp. fondi"
    ACQ.logger.info('URL: /inviaprogetto (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat, (CdP.INI, )):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    err = auth_progetto_inviabile(d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        ACQ.logger.error(INVIO_NON_AUTORIZZ, err, d_prat.user['userid'],
                      d_prat[cs.NUMERO_PRATICA])
        return pratica_common(d_prat)
    cannot_go = d_prat.check_next()[0]
    if cannot_go:
        fk.flash(cannot_go, category="error")
        return pratica_common(d_prat)
    testo = cs.TESTO_APPROVAZIONE.format(d_prat[cs.NUMERO_PRATICA], fk.request.root_url)+ \
            cs.DETTAGLIO_PRATICA.format(**d_prat)
    subj = 'Richiesta di approvazione progetto di acquisto.'
    ret = send_email(d_prat[cs.EMAIL_RESPONSABILE], testo, subj)
    if ret:
        fk.flash("Richiesta di approvazione per  la pratica "
                 f"{d_prat[cs.NUMERO_PRATICA]} inviata a: "
                 f"{d_prat.get(cs.EMAIL_RESPONSABILE)}", category="info")
        d_prat.next()
        storia(d_prat, 'Progetto inviato al resp. dei fondi per approvazione')
        salvapratica(d_prat)
    else:
        msg = "Invio per approvazione fallito"
        fk.flash(msg, category="error")
    return pratica_common(d_prat)

@ACQ.route('/inviadecisione')
def inviadecisione():                    #pylint: disable=R0914
    "pagina: invia decisione di contrarre per firma digitale direttore"
    ACQ.logger.info('URL: /inviadecisione (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat, (CdP.ROG, CdP.DEC)):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    err = auth_decisione_inviabile(d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        ACQ.logger.error(INVIO_NON_AUTORIZZ, err, d_prat.user['userid'],
                      d_prat[cs.NUMERO_PRATICA])
        return pratica_common(d_prat)
    cannot_go = d_prat.check_next()[0]
    if cannot_go:
        fk.flash(cannot_go, category="error")
        return pratica_common(d_prat)
    numdec = d_prat.get(cs.NUMERO_DECISIONE).split('/')[0]
    doc_opts = [cs.DIRETTORE]
    if d_prat.get(cs.DEC_FIRMA_VICARIO):
        chifirma = "Dir. Vicario"
        doc_opts.append(cs.VICARIO)
    else:
        chifirma = "Direttore"
    doc_pdf = genera_documento(d_prat, (cs.DOC_DECISIONE, doc_opts), filenum=numdec)
    d_prat[cs.DECIS_DA_FIRMARE] = doc_pdf
    testo = cs.TESTO_INVIA_DECISIONE.format(**d_prat)+ \
            cs.DETTAGLIO_PRATICA.format(**d_prat)
    subj = f'Decisione di contrarre da inviare al {chifirma} per firma'
    recipient = (d_prat[cs.EMAIL_RUP], CONFIG.config[cs.EMAIL_SERVIZIO])
    attach = (os.path.join(d_prat.basedir, doc_pdf), doc_pdf)
    ret = send_email(recipient, testo, subj, attach=attach)
    if ret:
        msg = f"Decisione da firmare digitalmente dal {chifirma} inviata a: {recipient}"
        fk.flash(msg, category="info")
        storia(d_prat, msg)
        d_prat.next()
        salvapratica(d_prat)
    else:
        fk.flash("Invio e-mail per firma fallito", category="error")
    genera_documento(d_prat, (cs.DOC_DECISIONE, doc_opts))  # Elimina barra "provvisorio"
    return pratica_common(d_prat)

@ACQ.route('/approvaprogetto')
def approvaprogetto():
    "pagina: resp.fondi approva progetto"
    ACQ.logger.info('URL: /approvaprogetto (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat, (CdP.PIR, )):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    err = auth_progetto_approvabile(d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        ACQ.logger.error('Approvazione non autorizzata: %s. Utente %s pratica %s',
                      err, d_prat.user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica_common(d_prat)
    d_prat[cs.DATA_RESP_APPROVA] = ft.today()
    d_prat.next()
    genera_documento(d_prat, (cs.DOC_PROGETTO, [cs.RESPONSABILE]))
    storia(d_prat, 'Progetto approvato da resp. fondi.')
    salvapratica(d_prat)
    subj = 'Notifica approvazione progetto di acquisto. Pratica: '+d_prat[cs.NUMERO_PRATICA]
    body = cs.TESTO_NOTIFICA_APPROVAZIONE.format(**d_prat)
    if not test_responsabile(d_prat):
        if send_email(d_prat[cs.EMAIL_RICHIEDENTE], body, subj):
            fk.flash(f"L'approvazione del progetto {d_prat[cs.NUMERO_PRATICA]} è stata"
                     " correttamente registrata", category="info")
    send_email(CONFIG.config[cs.EMAIL_UFFICIO], body, subj)
    return pratica_common(d_prat)

@ACQ.route('/indicarup', methods=('GET', 'POST'))
def indicarup():
    "pagina: indica RUP"
    ACQ.logger.info('URL: /indicarup (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat, (CdP.PAR, )):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    err = auth_rup_indicabile(d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        ACQ.logger.error('Indicazione RUP non autorizzata: %s. Utente %s pratica %s',
                      err, d_prat.user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica_common(d_prat)
    if cs.ANNULLA in fk.request.form:
        fk.flash('Operazione annullata', category="info")
        return pratica_common(d_prat)
    rupf = fms.IndicaRUP(fk.request.form)
    rupf.email_rup.choices = _menu_scelta_utente("Seleziona RUP")
    if fk.request.method == 'POST':
        if rupf.validate():
            d_prat[cs.EMAIL_RUP] = rupf.email_rup.data
            d_prat[cs.INTERNO_RUP] = rupf.interno_rup.data
            d_prat[cs.NOME_RUP] = nome_da_email(d_prat[cs.EMAIL_RUP], True)
            d_prat[cs.RUP_FIRMA_VICARIO] = 1 if rupf.rup_firma_vicario.data else 0
            doc = d_prat.get_passo('f')
            genera_documento(d_prat, doc)
            d_prat.next()
            text = cs.TESTO_INDICA_RUP.format(d_prat[cs.NUMERO_PRATICA], fk.request.root_url)
            send_email(d_prat[cs.EMAIL_RUP], text, "Indicazione come RUP")
            msg = f"{d_prat[cs.NOME_RUP]} indicato come RUP"
            fk.flash(msg, category='info')
            storia(d_prat, msg)
            salvapratica(d_prat)
            return pratica_common(d_prat)
        for err in rupf.errlist:
            fk.flash(err, category="error")
    body = rupf()
    ddp = {'title': 'Indica RUP',
           'before': '<form method=POST action=/indicarup '
                     'accept-charset="utf-8" novalidate>',
           'after': '</form>',
           'note': 'Questa è una nota',
           'body': body}
    return fk.render_template('form_layout.html', sede=CONFIG.config[cs.SEDE],
                              test_mode=CONFIG.config.get(cs.TEST_MODE), data=ddp)

@ACQ.route('/autorizza', methods=('GET', ))
def autorizza():
    "autorizzazione del direttore"
    ACQ.logger.info('URL: /autorizza (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat, (CdP.IRD, )):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    err = auth_autorizzabile(d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        ACQ.logger.error('Autorizzazione richiesta non consentita: %s. Utente %s pratica %s',
                      err, d_prat.user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica_common(d_prat)
    text = cs.TESTO_NOMINA_RUP.format(d_prat[cs.NUMERO_PRATICA])
    send_email(d_prat[cs.EMAIL_RUP], text, "Nomina RUP")
    d_prat.next()
    storia(d_prat, "Autorizzazione concessa dal direttore")
    doc_opts = [cs.RESPONSABILE, cs.DIRETTORE]
    if d_prat.get(cs.RUP_FIRMA_VICARIO):
        doc_opts.append(cs.VICARIO)
    d_prat[cs.DATA_DIR_AUTORIZZA] = ft.today()
    genera_documento(d_prat, (cs.DOC_PROGETTO, doc_opts))
    genera_documento(d_prat, (cs.DOC_NOMINARUP, doc_opts))   # genera versione definitiva
    salvapratica(d_prat)
    return pratica_common(d_prat)

@ACQ.route('/rich_autorizzazione', methods=('GET', ))
def rich_autorizzazione():
    "pagina: richiesta autorizzazione del direttore"
    ACQ.logger.info('URL: /rich_autorizzazione (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat, (CdP.RUI, )):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    err = auth_autorizz_richiedibile(d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        ACQ.logger.error('Invio richiesta di autorizzazione non consentito: '\
                         '%s. Utente %s pratica %s',
                         err, d_prat.user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica_common(d_prat)
    cannot_go = d_prat.check_next()[0]
    if cannot_go:
        fk.flash(cannot_go, category="error")
        return pratica_common(d_prat)
    subj = 'Richiesta autorizzazione progetto di acquisto. Pratica: '+d_prat[cs.NUMERO_PRATICA]
    body = cs.TESTO_RICHIESTA_AUTORIZZAZIONE.format(url=fk.request.root_url, **d_prat)
    ret = send_email(CONFIG.config[cs.EMAIL_DIREZIONE], body, subj)
    if ret:
        msg = 'Richiesta di autorizzazione inviata alla direzione'
        fk.flash(msg, category="info")
        d_prat.next()
        storia(d_prat, msg)
        salvapratica(d_prat)
        return pratica_common(d_prat)
    err = 'Invio richiesta di autorizzazione alla direzione fallito'
    fk.flash(err, category="error")
    ACQ.logger.error(err)
    return pratica_common(d_prat)

@ACQ.route('/modificardo', methods=('GET', 'POST'))
def modificardo():
    "Gestione form per produzione di RdO"
    ACQ.logger.info('URL: /modificardo (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat, (CdP.AUD, )):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    err = auth_rdo_modificabile(d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        ACQ.logger.error('Generazione/modifica rdo non autorizzata: %s. Utente %s, Pratica %s', \
                      err, d_prat.user['userid'],
                      d_prat.get(cs.NUMERO_PRATICA, 'N.A.'))
        return pratica_common(d_prat)
    if fk.request.method == 'POST':
        rdo = fms.RdO(fk.request.form)
        if cs.ANNULLA in fk.request.form:
            fk.flash('Operazione annullata', category="info")
            return pratica_common(d_prat)
        if cs.AVANTI in fk.request.form:
            if rdo.validate():
                rdo_data = rdo.data.copy()
                d_prat.update(clean_data(rdo_data))
                update_costo(d_prat, cs.COSTO_RDO)
                genera_documento(d_prat, (cs.DOC_RDO, [cs.DIRETTORE]))
#               d_prat.next()
                storia(d_prat, 'Generata/modificata RdO')
                salvapratica(d_prat)
                return pratica_common(d_prat)
            errors = rdo.get_errors()
            for err in errors:
                fk.flash(err, category="error")
            ACQ.logger.debug("Errori form RdO: %s", "; ".join(errors))
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
    return fk.render_template('form_layout.html', sede=CONFIG.config[cs.SEDE],
                              test_mode=CONFIG.config.get(cs.TEST_MODE), data=ddp)

@ACQ.route('/modificaordine', methods=('GET', 'POST', ))
def modificaordine():                     #pylint: disable=R0914
    "pagina: modifica ordine (sopl per acquyisti inf. 5k)"
    ACQ.logger.info('URL: /modificaordine (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat, (CdP.ORD, )):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    if cs.ANNULLA in fk.request.form:
        fk.flash('Operazione annullata', category="info")
        return pratica_common(d_prat)
    err = auth_ordine_modificabile(d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        ACQ.logger.error('Gestione ordine non autorizzata: %s. Utente %s, pratica %s',
                     err, d_prat.user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica_common(d_prat)
    if cs.COSTO_RDO not in d_prat:
        d_prat[cs.COSTO_RDO] = d_prat[cs.COSTO_PROGETTO].copy()
    ordn = fms.Ordine(fk.request.form, **d_prat)
    if fk.request.method == 'POST':
        if ordn.validate():
            d_prat.update(clean_data(ordn.data))
            update_costo(d_prat, cs.COSTO_RDO)
            doc = d_prat.get_passo('f')
            genera_documento(d_prat, doc)
            storia(d_prat, f'Generato/modificato ordine N. {d_prat.get(cs.NUMERO_DECISIONE, "")}')
            salvapratica(d_prat)
            return pratica_common(d_prat)
        errors = ordn.get_errors()
        for err in errors:
            fk.flash(err, category="error")
        ACQ.logger.debug("Errori form Ordine: %s", "; ".join(errors))

    ddp = {'title': 'Immissione dati per ordine',
           'subtitle': f"Pratica N. {d_prat['numero_pratica']}",
           'before': '<form method=POST action=/modificaordine '
                     'accept-charset="utf-8" novalidate>',
           'after': "</form>",
           'note': cs.OBBLIGATORIO,
           'body': ordn(d_prat)}
    return fk.render_template('form_layout.html', sede=CONFIG.config[cs.SEDE],
                              test_mode=CONFIG.config.get(cs.TEST_MODE), data=ddp)

@ACQ.route('/modificadecisione', methods=('GET', 'POST', ))
def modificadecisione():                     #pylint: disable=R0914
    "pagina: modifica decisione di contrarre"
    ACQ.logger.info('URL: /modificadecisione (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat, (CdP.ROG, CdP.DEC)):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    if cs.ANNULLA in fk.request.form:
        fk.flash('Operazione annullata', category="info")
        return pratica_common(d_prat)
    err = auth_decisione_modificabile(d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        ACQ.logger.error('Gestione decisione di contrarre non autorizzata: ' \
                         '%s. Utente %s, pratica %s',
                          err, d_prat.user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica_common(d_prat)
    if cs.COSTO_RDO not in d_prat:
        d_prat[cs.COSTO_RDO] = d_prat[cs.COSTO_PROGETTO].copy()
    decis = fms.Decisione(fk.request.form, **d_prat)
    if fk.request.method == 'POST':
        if decis.validate(d_prat):
            d_prat.update(clean_data(decis.data))
            if not d_prat[cs.NUMERO_DECISIONE]:
                year = ft.thisyear()
                ndecis = ft.find_max_decis(year)[0]+1
                d_prat[cs.NUMERO_DECISIONE] = f"{ndecis}/{year:4d}"
                d_prat[cs.DATA_DECISIONE] = ft.today(fulltime=False)
                what = "Generata"
            else:
                what = "Modificata"
            update_costo(d_prat, cs.COSTO_RDO)
            doc = d_prat.get_passo('f')
            genera_documento(d_prat, doc)
            storia(d_prat, what+' decisione a contrarre N. '
                           f'{d_prat[cs.NUMERO_DECISIONE]}')
            ndecis = int(d_prat[cs.NUMERO_DECISIONE].split('/')[0])
            if ft.check_dupl_decis(ndecis):
                fk.flash("Il numero di decisione " \
                         f"{d_prat[cs.NUMERO_DECISIONE]} risulta duplicato",
                         category="info")
            salvapratica(d_prat)
            return pratica_common(d_prat)
        errors = decis.get_errors()
        for err in errors:
            fk.flash(err, category="error")
        ACQ.logger.debug("Errori form Decisione: %s", "; ".join(errors))
    ddp = {'title': 'Immissione dati per decisione di contrarre',
           'subtitle': f"Pratica N. {d_prat['numero_pratica']}",
           'before': '<form method=POST action=/modificadecisione '
                     'accept-charset="utf-8" novalidate>',
           'after': "</form>",
           'note': cs.OBBLIGATORIO,
           'body': decis(d_prat)}
    return fk.render_template('form_layout.html', sede=CONFIG.config[cs.SEDE],
                              test_mode=CONFIG.config.get(cs.TEST_MODE), data=ddp)

@ACQ.route('/upload', methods=('POST', ))
def upload():               # pylint: disable=R0914,R0911,R0912
    "pagina per upload di file"
    ACQ.logger.info('URL: /upload (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    try:
        fle = fk.request.files['upload_file']
    except Exception as exc:               # pylint: disable=W0703
        fk.flash(f"Errore caricamento file: {exc}", category="error")
        return pratica_common(d_prat)
    if status_not_ok(d_prat):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    tipo_allegato = get_tipo_allegato()
    ACQ.logger.info("Richiesta upload: %s (tipo: %s)", fle.filename, tipo_allegato)
    origname, ext = os.path.splitext(fle.filename)
    origname = secure_filename(origname)
    ext = ext.lower()
    if ext not in cs.UPLOAD_TYPES:
        fk.flash(f"Tipo allegato non valido: {fle.filename}", category="error")
        return pratica_common(d_prat)
    spec = fk.request.form.get(cs.SIGLA_DITTA, "")
    name = filename_allegato(tipo_allegato, origname, ext, spec, d_prat)
    if not name:
        fk.flash("Devi specificare una sigla per la ditta!", category="error")
        return pratica_common(d_prat)
    fpath = os.path.join(d_prat.basedir, name)
    if os.path.exists(fpath):
        fk.flash(f'File "{name}" già esistente!', category='error')
        fk.flash('Devi modificare il nome del file '
                 '(o rimuovere quello esistente)', category="error")
        return pratica_common(d_prat)
    fle.save(fpath)        # Archivia file da upload
    ft.protect(fpath)
    text = 'Allegato ' + cs.TAB_ALLEGATI[tipo_allegato][1]
    storia(d_prat, text)
    salvapratica(d_prat)
    return pratica_common(d_prat)

##################################################################  Operazioni di supporto
@ACQ.route('/cancella/<name>', methods=('GET', 'POST'))
def cancella(name):
    "pagina: cancella allegato"
    ACQ.logger.info('URL: /cancella/%s (%s)', name, fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    err = auth_allegati_cancellabili(d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        ACQ.logger.error('Rimozione allegato non autorizzata: %s. Utente %s pratica %s',
                      err, d_prat.user['userid'], d_prat[cs.NUMERO_PRATICA])
    else:
        storia(d_prat, f'Rimosso allegato {name}')
        ret = ft.remove((d_prat.basedir, name))
        if ret:
            ACQ.logger.info('Rimosso file: %s', ret)
    salvapratica(d_prat)
    return pratica_common(d_prat)

@ACQ.route('/vedicodf')
def vedicodf():
    "pagine: visualizza lista codici Fu.Ob."
    ACQ.logger.info('URL: /vedicodf (%s)', fk.request.method)
    return ft.GlobLists.CODFLIST.render(title="Lista Codici Fu.Ob. e responsabili")

@ACQ.route('/vedifile/<filename>')
def vedifile(filename):
    "pagina: visualizza file PDF"
    ACQ.logger.info('URL: /vedifile/%s (%s)', filename, fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    return fk.send_from_directory(d_prat.basedir, filename, as_attachment=True)

#pylint: disable=C3001
@ACQ.route('/pratiche/<filtro>/<anno>/<ascendente>')
def lista_pratiche(filtro, anno, ascendente):            #pylint: disable=R0915,R0912,R0914
    "pagina: lista pratiche"
    ACQ.logger.info('URL: /pratiche/%s/%s/%s (%s)', filtro, anno, ascendente,
                                                 fk.request.method)
    user = user_info()
    fk.session[cs.BASEDIR] = ''
    anno = int(anno)
    if not anno:
        anno = ft.thisyear()
    ascendente = bool(int(ascendente))
    oper = filtro[:3]
    if oper == ('ALL', 'NOR'):
        if not test_admin(user):
            ACQ.logger.error('Operazione non autorizzata. '\
                          'Utente: %s', user['userid'])
            fk.session.clear()
            return fk.render_template('noaccess.html', test_mode=CONFIG.config.get(cs.TEST_MODE),
                                      sede=CONFIG.config[cs.SEDE])
    elif oper == 'DIR':   # Lista pratiche da autorizzare/autorizzate dal Direttore
        if not (test_direttore(user) or test_admin(user)):
            ACQ.logger.error('Operazione non autorizzata '\
                          'Utente: %s', user['userid'])
            fk.session.clear()
            return fk.render_template('noaccess.html', test_mode=CONFIG.config.get(cs.TEST_MODE),
                                      sede=CONFIG.config[cs.SEDE])
    try:
        doclist, title = ft.trova_pratiche_1(anno, filtro, user['email'], ascendente)
    except Exception:                      # pylint: disable=W0703
        errlog = traceback.format_exc(limit=3)
        ACQ.logger.error(errlog)
        err_msg = 'Errore sistema'
        fk.flash(err_msg, category="error")
        return fk.redirect(fk.url_for('start'))
    theyear = int(anno)
    years = [int(y) for y in doclist.years]
    return fk.render_template('lista_pratiche_per_anno.html', filtro=filtro,
                              test_mode=CONFIG.config.get(cs.TEST_MODE),
                              sede=CONFIG.config[cs.SEDE],
                              years=years, year=theyear,
                              dlist=doclist.records, title=title)

@ACQ.route('/trovapratica', methods=('POST', 'GET'))
def trovapratica():               # pylint: disable=R0912,R0914,R0915
    "pagina: trova pratica"
    ACQ.logger.info('URL: /trovapratica (%s)', fk.request.method)
    fk.session[cs.BASEDIR] = ''
    if cs.ANNULLA in fk.request.form:
        fk.flash('Operazione annullata', category="info")
        return fk.redirect(fk.url_for('start'))
    user = user_info()
    if not (test_admin(user) or test_direttore(user)):
        ACQ.logger.error('Ricerca pratiche non autorizzata. Utente: %s', user['userid'])
        fk.session.clear()
        return fk.render_template('noaccess.html', test_mode=CONFIG.config.get(cs.TEST_MODE),
                                  sede=CONFIG.config[cs.SEDE])
    prf = fms.TrovaPratica(fk.request.form)
    years = ft.get_years(cs.DATADIR)
    years.sort(reverse=True)
    year_menu = list(zip(years, years))
    prf.trova_anno.choices = year_menu
    if fk.request.method == 'POST':
        try:
            anno = int(prf.data['trova_anno'])
        except ValueError:
            anno = ft.thisyear()
        vaperta = int(prf.data.get('trova_prat_aperta', '-1'))
        if vaperta == 0:
            stato = 'a'
        elif vaperta == 1:
            stato = 'c'
        elif vaperta == 2:
            stato = 'n'
        else:
            stato = ''
        asc = prf.data['elenco_ascendente']
        match_rich = prf.data['trova_richiedente'].strip()
        match_resp = prf.data['trova_responsabile'].strip()
        match_rup = prf.data['trova_rup'].strip()
        match_descr = prf.data['trova_parola'].strip()
        ACQ.logger.debug('trova - anno: %d, rich. %s, resp: %s, rup: %s, descriz: %s',
                      anno, match_rich, match_resp, match_rup, match_descr)
        try:
            lista, expr = ft.trova_pratiche_2(anno, stato, match_rich, match_resp,
                                              match_rup, match_descr, ascendente=asc)
        except Exception:            # pylint: disable=W0703
            errlog = traceback.format_exc(limit=3)
            ACQ.logger.error(errlog)
            err_msg = 'Errore sistema'
            fk.flash(err_msg, category="error")
            return fk.redirect(fk.url_for('start'))
        title = 'Trova Pratiche'
        subtitle = 'Risultato per ricerca: '+expr+'<br>'+ \
                   f'N. pratiche selezionate: {len(lista)}'
        return fk.render_template('lista_pratiche_per_anno.html', filtro='',
                                  test_mode=CONFIG.config.get(cs.TEST_MODE), pre=[],
                                  post=[], year=anno, dlist=lista.records, title=title,
                                  sede=CONFIG.config[cs.SEDE], subtitle=subtitle)
    ddp = {'title': 'Trova pratiche',
           'subtitle': 'Specifica criteri di ricerca',
           'before': '<form method=POST action=/trovapratica '
                     'accept-charset="utf-8" novalidate>',
           'after': '</form>',
           'body': prf()}
    return fk.render_template('form_layout.html', sede=CONFIG.config[cs.SEDE],
                              test_mode=CONFIG.config.get(cs.TEST_MODE), data=ddp)

@ACQ.route('/pratica0/<num>/<year>', methods=('GET', ))
def pratica0(num, year):
    "pagina: accesso a pratica indicata"
    ACQ.logger.info('URL: /pratica0/%s/%s (%s)', num, year, fk.request.method)
    basedir = ft.namebasedir(year, num)
    fk.session[cs.BASEDIR] = basedir
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    return pratica_common(d_prat)

@ACQ.route('/togglestoria', methods=('GET', 'POST', ))
def togglestoria():
    "pagina: abilita/disabilita storia pratica"
    ACQ.logger.info('URL: /togglestoria (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    sst = d_prat.get(cs.VEDI_STORIA, 0)
    if sst:
        d_prat[cs.VEDI_STORIA] = 0
    else:
        d_prat[cs.VEDI_STORIA] = 1
    salvapratica(d_prat)
    return pratica_common(d_prat)
@ACQ.route('/rollback', methods=('GET', 'POST'))
def rollback():                       #pylint: disable=R0914
    "Pagina: annulla ultimo passo"
    ACQ.logger.info('URL: /rollback (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    err = auth_rollback(d_prat)
    if err.startswith(NOT):
        fk.flash(err, category="error")
        ACQ.logger.error('annullamento ultimo passo non autorizzato: %s. Utente %s, pratica %s',
                      err, d_prat.user['userid'], d_prat[cs.NUMERO_PRATICA])
        return pratica_common(d_prat)
    passcode = d_prat.get_passo()
    prevcode = d_prat.get_back()
    ACQ.logger.debug('Al passo %s rolling back to %s', passcode, prevcode)
    doc_to_remove = pass_info(passcode, what='file')
    doc_to_remove_str = doc_to_remove[0] if doc_to_remove else 'Nessuno'
    cod_all = pass_info(passcode, what='alleg')
    all_to_remove = [cs.TAB_ALLEGATI[x][0][4:] for x in cod_all]
    ACQ.logger.debug('Documento da cancellare: %s', doc_to_remove_str)
    ACQ.logger.debug('Allegati da cancellare: %s', ', '.join(all_to_remove))
    if 'annulla' in fk.request.form:
        ACQ.logger.info('Operazione annullata')
        fk.flash('Operazione annullata', category="info")
        return pratica_common(d_prat)
    if 'conferma' in fk.request.form:
        ACQ.logger.info('Annullamento confermato')
        if doc_to_remove:
            ret = ft.remove((d_prat.basedir, doc_to_remove[0]))
            if ret:
                ACQ.logger.info('Rimosso file: %s', ret)
        for tipo in cod_all:
            name = filename_allegato(tipo, '', '.pdf', '', d_prat)
            ret = ft.remove((d_prat.basedir, name))
            if ret:
                ACQ.logger.info('Rimosso file: %s', ret)
        msg = "Annullato ultimo passo pratica"
        storia(d_prat, msg)
        d_prat.back()
        storia(d_prat, f'Passo corrente: {d_prat.get_passo("text")}')
        salvapratica(d_prat)
        fk.flash(msg, category="info")
        ACQ.logger.info(msg)
        return pratica_common(d_prat)
    ddp = {'passo': pass_info(passcode, 'text'),
           'prec': pass_info(prevcode, 'text'),
           'remove_doc': doc_to_remove,
           'remove_all': ', '.join(all_to_remove)}
    return fk.render_template('rollback.html', sede=CONFIG.config[cs.SEDE],
                              test_mode=CONFIG.config.get(cs.TEST_MODE), pratica=d_prat, data=ddp)

@ACQ.route('/chiudipratica')
def chiudipratica():
    "pagina: chiudi pratica"
    ACQ.logger.info('URL: /chiudipratica (%s)', fk.request.method)
    return modifica_pratica('chiudi')

@ACQ.route('/apripratica')
def apripratica():
    "pagina: apri pratica"
    ACQ.logger.info('URL: /apripratica (%s)', fk.request.method)
    return modifica_pratica('apri')

@ACQ.route('/annullapratica', methods=('GET', 'POST'))
def annullapratica():
    "pagina: annulla pratica"
    ACQ.logger.info('URL: /annullapratica (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if status_not_ok(d_prat):
        fk.flash(ILLEGAL_OP, category="error")
        return pratica_common(d_prat)
    if cs.ANNULLA in fk.request.form:
        fk.flash('Operazione annullata', category="info")
        return pratica_common(d_prat)
    annul = fms.AnnullaPratica(fk.request.form)
    if fk.request.method == 'POST':
        if annul.validate():
            d_prat.annulla(annul.motivazione_annullamento.data)
            salvapratica(d_prat)
            msg = f"Pratica {d_prat[cs.NUMERO_PRATICA]} annullata"
            storia(d_prat, msg)
            ACQ.logger.info(msg)
            fk.flash(msg, category='info')
            return pratica_common(d_prat)
        msg = "Motivazione annullamento non specificata"
        fk.flash(msg, category="error")
        ACQ.logger.error(msg)
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
    return fk.render_template('form_layout.html', sede=CONFIG.config[cs.SEDE],
                              test_mode=CONFIG.config.get(cs.TEST_MODE), data=ddp)

@ACQ.route('/files/<name>')
def files(name):
    "download file"
#   ACQ.logger.info('URL: /files/%s (%s)', name, fk.request.method)
    return  ACQ.send_static_file(name)

@ACQ.route('/devel', methods=('GET', 'POST'))
def devel():                     #pylint: disable=R0915
    'operazioni per supporto sviluppo'
    ACQ.logger.info('URL: /devel (%s)', fk.request.method)
    if not (d_prat := check_access()):
        return fk.redirect(fk.url_for('start'))
    if not test_developer(d_prat.user):
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
        info = make_info(d_prat)
        keys = list(info.keys())
        keys.sort()
        text = "<h4>Checks su pratica N. "+d_prat[cs.NUMERO_PRATICA]+"</h4><pre>\n"
        for  key in keys:
            text += f"  - {key} -> {info[key]}\n"
    elif 'vedipratica' in fk.request.form:
        ppath = os.path.join(d_prat.basedir, cs.PRAT_JFILE)
        text = f'<h4>{ppath}</h4>'
        text += '<pre>'+str(d_prat)+'</pre>'
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
    ACQ.logger.info('URL: /housekeeping (%s)', fk.request.method)
    user = user_info()
    status = {'footer': f"Procedura housekeeping.py. Vers. {__version__} - " \
                        f"L. Fini, {__date__}",
              'url_root': fk.request.url_root}

    if test_admin(user):
        return fk.render_template('start_housekeeping.html',
                                  user=user, test_mode=CONFIG.config.get(cs.TEST_MODE),
                                  sede=CONFIG.config[cs.SEDE],
                                  status=status).encode('utf8')
    fk.session.clear()
    return fk.render_template('noaccess.html', test_mode=CONFIG.config.get(cs.TEST_MODE))

@ACQ.route("/sortcodf/<field>")
def sortcodf(field):
    "Riporta codici Fu.Ob. con ordine specificato"
    ACQ.logger.info('URL: /sortcodf/%s (%s)', field, fk.request.method)
    user = user_info()
    if not test_admin(user):
        return fk.render_template('noaccess.html',
                                  test_mode=CONFIG.config.get(cs.TEST_MODE)).encode('utf8')
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
    ACQ.logger.info('URL: /codf (%s)', fk.request.method)
    return sortcodf('')


@ACQ.route('/addcodf', methods=('GET', 'POST'))
def addcodf():
    "Aggiungi codice Fu.Ob."
    ACQ.logger.info('URL: /addcodf (%s)', fk.request.method)
    user = user_info()
    if not test_admin(user):
        return fk.render_template('noaccess.html',
                                  test_mode=CONFIG.config.get(cs.TEST_MODE)).encode('utf8')
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
            ACQ.logger.info(msg)
            fk.flash(msg)
            return fk.redirect(fk.url_for('codf'))
        ACQ.logger.debug("Validation errors: %s", cfr.errlist)
    return ncodf.render_item_as_form('Aggiungi Codice Fu.Ob.', cfr,
                                     fk.url_for('addcodf'),
                                     errors=cfr.errlist)

@ACQ.route('/editcodf/<nrec>', methods=('GET', 'POST'))
def editcodf(nrec):
    "Modifica tabella codici Fu.Ob."
    ACQ.logger.info('URL: /editcodf/%s (%s)', nrec, fk.request.method)
    nrec = int(nrec)
    user = user_info()
    if not test_admin(user):
        return fk.render_template('noaccess.html',
                                  test_mode=CONFIG.config.get(cs.TEST_MODE)).encode('utf8')
    ncodf = ft.FTable((cs.DATADIR, 'codf.json'))
    row = ncodf.get_row(nrec, as_dict=True)
    ulist = ft.FTable((cs.DATADIR, 'userlist.json')).as_dict('email')
    resp_menu = [(x, _nome_resp(ulist, x, False)) for  x in ulist]
    resp_menu.sort(key=lambda x: x[1])
    if fk.request.method == 'GET':
        ACQ.logger.debug("Codice row=%s", row)
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
            ACQ.logger.info(msg)
            return fk.redirect(fk.url_for('codf'))
        if 'annulla' in fk.request.form:
            fk.flash('Operazione annullata')
            return fk.redirect(fk.url_for('housekeeping'))
        if cfr.validate():
            if 'avanti' in fk.request.form:
                row.update(cfr.data)
                ncodf.insert_row(row, nrec)
                ncodf.save()
                msg = "Modificato Codice Fu.Ob.: " \
                      f"{row['Codice']} ({row['email_Responsabile']})"
                fk.flash(msg)
                ACQ.logger.info(msg)
            return fk.redirect(fk.url_for('codf'))
        ACQ.logger.debug("Validation errors: %s", cfr.errlist)
    return ncodf.render_item_as_form('Modifica Codice Fu.Ob.', cfr,
                                     fk.url_for('editcodf', nrec=str(nrec)),
                                     errors=cfr.errlist, nrow=nrec)

@ACQ.route('/downloadcodf', methods=('GET', 'POST'))
def downloadcodf():
    "Download tabella codici Fu.Ob."
    ACQ.logger.info('URL: /downloadcodf (%s)', fk.request.method)
    return download('codf')

@ACQ.route('/downloadutenti', methods=('GET', 'POST'))
def downloadutenti():
    "Download tabella utenti"
    ACQ.logger.info('URL: /downloadutenti (%s)', fk.request.method)
    return download('utenti')

def download(_unused):
    "Download"
    return fk.render_template('tbd.html', test_mode=CONFIG.config.get(cs.TEST_MODE), goto='/')

@ACQ.route("/utenti")
def utenti():
    "Genera lista utenti"
    ACQ.logger.info('URL: /utenti (%s)', fk.request.method)
    user = user_info()
    if test_admin(user):
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
    return fk.render_template('noaccess.html',
                              test_mode=CONFIG.config.get(cs.TEST_MODE)).encode('utf8')


@ACQ.route('/adduser', methods=('GET', 'POST'))
def adduser():
    "Aggiungi utente"
    ACQ.logger.info('URL: /adduser (%s)', fk.request.method)
    user = user_info()
    if test_admin(user):
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
                ACQ.logger.info(msg)
                fk.flash(msg)
                return fk.redirect(fk.url_for('utenti'))
            ACQ.logger.debug("Validation errors: %s", cfr.errlist)
        return users.render_item_as_form('Aggiungi utente', cfr,
                                         fk.url_for('adduser'),
                                         errors=cfr.errlist,
                                         ignore=('pw', 'flags'))
    return fk.render_template('noaccess.html',
                              test_mode=CONFIG.config.get(cs.TEST_MODE)).encode('utf8')

@ACQ.route('/edituser/<nrec>', methods=('GET', 'POST'))
def edituser(nrec):
    "Modifica dati utente"
    ACQ.logger.info('URL: /edituser/%s (%s)', nrec, fk.request.method)
    nrec = int(nrec)
    user = user_info()
    if test_admin(user):
        users = ft.FTable((cs.DATADIR, 'userlist.json'))
        users.sort(3)
        row = users.get_row(nrec, as_dict=True)
        if fk.request.method == 'GET':
            ACQ.logger.debug("Userlist row=%s", row)
            cfr = fms.UserForm(**row)
            ACQ.logger.debug("UserForm inizializzato: %s", cfr.data)
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
                ACQ.logger.info(msg)
                fk.flash(msg)
                return fk.redirect(fk.url_for('utenti'))
            if cfr.validate():
                if 'avanti' in fk.request.form:
                    ACQ.logger.debug("Pressed: avanti. Modifica utente")
                    row.update(cfr.data)
                    users.insert_row(row, nrec)
                    users.sort(3)
                    users.save()
                    msg = f"Modificato utente: {row['name']} {row['surname']}"
                    ACQ.logger.info(msg)
                    fk.flash(msg)
                return fk.redirect(fk.url_for('utenti'))
            ACQ.logger.debug("Validation errors: %s", cfr.errlist)
        return users.render_item_as_form('Modifica utente', cfr,
                                         fk.url_for('edituser', nrec=str(nrec)),
                                         nrow=nrec, errors=cfr.errlist,
                                         ignore=('pw', 'flags'))
    return fk.render_template('noaccess.html',
                              test_mode=CONFIG.config.get(cs.TEST_MODE)).encode('utf8')

@ACQ.route('/environ', methods=('GET',))
def environ():
    "Mostra informazioni su environment"
    ACQ.logger.info('URL: /environ (%s)', fk.request.method)
    user = user_info()
    if not test_developer(user):
        fk.session.clear()
        return fk.render_template('noaccess.html', test_mode=CONFIG.config.get(cs.TEST_MODE))
    html = ["<ul>"]
    keys = list(os.environ.keys())
    keys.sort()
    for key in keys:
        html.append(f"<li><b>{key}</b>: {os.environ[key]}")
    html.append("</ul>")
    env = '\n'.join(html)
    html = ["<ul>"]
    args = list(fk.request.args)
    html.append(f"<li><b>args</b>: {args}")
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
    return fk.render_template('environ.html', sede=CONFIG.config[cs.SEDE],
                              test_mode=CONFIG.config.get(cs.TEST_MODE), request=req, environ=env)

@ACQ.route('/testmail', methods=('GET',))
def testmail():
    "Invia messaggio di prova all'indirizzo di webmaster"
    ACQ.logger.info('URL: /testmail (%s)', fk.request.method)
    user = user_info()
    if not test_developer(user):
        fk.session.clear()
        return fk.render_template('noaccess.html', test_mode=CONFIG.config.get(cs.TEST_MODE))
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
                              recipients=recipient, test_mode=CONFIG.config.get(cs.TEST_MODE),
                              server=host, state=succ).encode('utf8')

@ACQ.route('/force_excp', methods=('GET',))
def force_excp():                       #pylint: disable=R1710
    "Causa una eccezione"
    ACQ.logger.info('URL: /force_excp (%s)', fk.request.method)
    user = user_info()
    if not test_developer(user):
        fk.session.clear()
        return fk.render_template('noaccess.html', test_mode=CONFIG.config.get(cs.TEST_MODE))
    1/0                                 # pylint: disable=W0104

#############################################################################
############################### Inizializzazioni ############################

def initialize_me():
    "inizializza tutto il necessario"
    ACQ.logger.info('Starting %s', long_version())
    ACQ.logger.info('PKG_ROOT: %s', cs.PKG_ROOT)
    ACQ.logger.info('DATADIR: %s', cs.DATADIR)
    ACQ.logger.info('WORKDIR: %s', cs.WORKDIR)

    configname = os.path.join(cs.DATADIR, 'config.json')
    ACQ.logger.info('Config loaded from: %s', configname)

    latex.set_path(CONFIG.config.get("latex_path", ""), ACQ.logger)
    ACQ.logger.info("LaTeX path: %s", latex.PDFLATEX.cmd)

    update_lists()
    ft.init_helplist()
    ACQ.secret_key = CONFIG.config[cs.FLASK_KEY]

    ft.clean_locks(cs.DATADIR)

    ACQ.logger.info('Inizializzazione terminata correttamente')

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

    DEBUG.local = True
    DEBUG.email = CONFIG.config[cs.EMAIL_WEBMASTER]
    fms.debug_enable()

    ACQ.logger.setLevel(logging.DEBUG)
    fk.logging.default_handler.setLevel(logging.DEBUG)
    ft.set_logger(ACQ.logger, (cs.WORKDIR, 'acquisti.log'),
                  CONFIG.config[cs.EMAIL_PROCEDURA],
                  CONFIG.config[cs.EMAIL_WEBMASTER],
                  f'Notifica errore ACQUISTI v. {__version__} (debug)')
    verifica_tabella_passi()
    initialize_me()
    ACQ.run(host="0.0.0.0", port=4001, debug=True)

def production():
    "lancia la procedura in modo produzione (all'interno del web server)"
    ACQ.logger.setLevel(logging.INFO)
    ft.set_logger(ACQ.logger, (cs.WORKDIR, 'acquisti.log'),
                  CONFIG.config[cs.EMAIL_PROCEDURA],
                  CONFIG.config[cs.EMAIL_WEBMASTER],
                  f'Notifica errore ACQUISTI v. {__version__}')
    ACQ.logger.removeHandler(fk.logging.default_handler)
    fms.debug_enable()
    initialize_me()

if __name__ == '__main__':
    localtest()
else:
    production()
