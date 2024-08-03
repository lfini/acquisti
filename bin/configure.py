"""
Mostra/Crea/modifica il file di configurazione

Uso:
       python configure.py [-c] [-h]
Dove:
       -c    crea/modifica file
"""

import sys
import os
from collections import OrderedDict
import readline                         # pylint: disable=W0611

import ftools
import constants as cs
from table import jload, jsave

__version__ = "1.5"

MY_VERSION = 4

LDAP_PORT_DESC = """IP port del server LDAP per autenticazione utenti
[es: 389]
"""

LDAP_HOST_DESC = """Indirizzo del server LDAP per autenticazione utenti
[es: ldap.ced.inaf.it]

(Specifica: '-' per disabilitare autenticazione LDAP)
"""

SMTP_HOST_DESC = """Indirizzo IP del server SMTP
Indirizzo del server SMTP utilizzato dalla procedura
per inviare i messaggi automatici [es: smtp.arcetri.astro.it]
************************************************************************
NOTA: specificare "-" se si utilizza GMail API per  l'invio di messaggi.
      altrimenti usare un indirizzo IP valido per il server SMTP)
************************************************************************
"""

LATEX_PATH_DESC = """Path del programma pdflatex [es: /usr/local/bin/pdflatex]
"""

CUU_DESC = """Codice Unico dell'ufficio (CUU)
[es: 14CVDG]
"""

EMAIL_UFFICIO_DESC = """Indirizzo e-mail dell'ufficio ordini.
A questo indirizzo sono inviati i messaggi automatici
generati dalla procedura [es: ordini.oaa@inaf.it]
"""

EMAIL_SERVIZIO_DESC = """Indirizzo e-mail di servizio.
A questo indirizzo sono inviati  i documenti da trasmettere
al direttore per la firma elettronica.

Se non è necessaria una differenziazione, può essere specificato
l'indirizzo e-mail dell'ufficio ordini. [es.: proc-acquisti.oaa@inaf.it]
"""

TITOLO_DIRETTORE_DESC = """Titolo del direttore [es: Dott.ssa]
"""

TITOLO_DIRETTORE_UK_DESC = """Titolo del direttore per ordini in inglese [es: Dr.]
"""

EMAIL_DIRETTORE_DESC = """Indirizzo e-mail personale del direttore

****************************************************************
NOTA: è NECESSARIO usare lo stesso indirizzo e-mail specificato
nella lista degli utenti della procedura.
****************************************************************
[es: luca.fini@inaf.it]
"""

EMAIL_DIREZIONE_DESC = """Indirizzo e-mail generico della direzione

Se tale indirizzo non esiste, specificare l'indirizzo personale
del direttore. [es: direttore.oaa@inaf.it]
"""

NOME_DIRETTORE_DESC = """Nome del direttore [es: Simone Esposito]
"""

GENDER_DIRETTORE_DESC = """Genere direttore (per la personalizzazione dei testi)
(indicare M o F) [es: M]
"""

EMAIL_WEBMASTER_DESC = """Indirizzo e-mail del web master
(a questo indirizzo saranno mandati i messaggi di errore)
[es: luca.fini@inaf.it]
"""

NOME_WEBMASTER_DESC = """Nome del web master [es: Luca Fini]
"""

WEBSITE_DESC = """URL completa del sito web della sede [es: http://www.arcetri.inaf.it]
"""

CITTA_DESC = """Città [es: Firenze]
"""

INDIRIZZO_DESC = """Indirizzo postale della sede (una linea)
[es: L.go Enrico Fermi, 5. 50125 Firenze (Italia)
"""

SEDE_UK_DESC = """Identificazione della sede per documenti in inglese
[es: INAF - Arcetri Astrophysical Observatory
"""

SEDE_DESC = """Identificazione sede INAF
[es: INAF - Osservatorio Astrofisico di Arcetri
"""

PART_IVA_DESC = """Partita I.V.A. dell'ente
[es: 97220210583]
"""

COD_FISC_DESC = """Codice fiscale dell'ente
[es: 97220210583]
"""

TEL_DESC = """Numero telefonico
[es: 0552752265]
"""

PEC_DESC = """Indirizzo PEC
[es: inafoaarcetri@pcert.postecert.it]
"""

EMAIL_PROCEDURA_DESC = """Indirizzo e-mail da cui provengono i messaggi tecnici.
Dovrebbe corrispondere all'identità GMail utilizzata per l'invio di messaggi.
[Es.: acquisti.oaa@gmail.com]
"""

SEDE = OrderedDict([(cs.SEDE_IT, SEDE_DESC),
                    (cs.SEDE_UK, SEDE_UK_DESC),
                    (cs.INDIRIZZO, INDIRIZZO_DESC),
                    (cs.CITTA, CITTA_DESC),
                    (cs.WEBSITE, WEBSITE_DESC),
                    (cs.COD_FISC, COD_FISC_DESC),
                    (cs.PART_IVA, PART_IVA_DESC),
                    (cs.PEC_OSS, PEC_DESC),
                    (cs.TEL_OSS, TEL_DESC),
                    (cs.CUU, CUU_DESC),
                   ])

PARAMS = OrderedDict([(cs.NOME_WEBMASTER, NOME_WEBMASTER_DESC),
                      (cs.EMAIL_WEBMASTER, EMAIL_WEBMASTER_DESC),
                      (cs.NOME_DIRETTORE, NOME_DIRETTORE_DESC),
                      (cs.GENDER_DIRETTORE, GENDER_DIRETTORE_DESC),
                      (cs.EMAIL_DIRETTORE, EMAIL_DIRETTORE_DESC),
                      (cs.TITOLO_DIRETTORE, TITOLO_DIRETTORE_DESC),
                      (cs.TITOLO_DIRETTORE_UK, TITOLO_DIRETTORE_UK_DESC),
                      (cs.EMAIL_UFFICIO, EMAIL_UFFICIO_DESC),
                      (cs.EMAIL_DIREZIONE, EMAIL_DIREZIONE_DESC),
                      (cs.EMAIL_SERVIZIO, EMAIL_SERVIZIO_DESC),
                      (cs.LATEX_PATH, LATEX_PATH_DESC),
                     ])

TECH = OrderedDict([(cs.SMTP_HOST, SMTP_HOST_DESC),
                    (cs.EMAIL_PROCEDURA, EMAIL_PROCEDURA_DESC),
                    (cs.LDAP_HOST, LDAP_HOST_DESC),
                    (cs.LDAP_PORT, LDAP_PORT_DESC),
                   ]
                  )

def creadirs():
    "Crea struttura directory di lavoro"
    approvdir = os.path.join(cs.DATADIR, 'approv')

    print()
    if os.path.exists(cs.DATADIR):
        print(f"Directory {cs.DATADIR} già esistente")
    else:
        os.makedirs(cs.DATADIR)
        print(f"Creata directory {cs.DATADIR}")

    if os.path.exists(approvdir):
        print(f"Directory {approvdir} già esistente")
    else:
        os.makedirs(approvdir)
        print(f"Creata directory {approvdir}")

    if os.path.exists(cs.WORKDIR):
        print(f"Directory {cs.WORKDIR} già esistente")
    else:
        os.makedirs(cs.WORKDIR)
        print(f"Creata directory {cs.WORKDIR}")
    print()

def ask_one(name, old_config, new_config, help_text):
    "Chiede valore di un parametro"
    print("\n\n\n\n\n---------")
    print(help_text)
    old_val = old_config.get(name)
    if old_val:
        if "_pw" in name:
            old_val = ftools.decrypt(old_val)
        print(" - Valore attuale:", old_val)
        new_val = input(" - Nuovo valore (se non specificato usa valore attuale) ").strip()
    else:
        print(" - Valore attuale: non definito")
        new_val = None
        while not new_val:
            new_val = input(" - Nuovo valore? ").strip()
    if not new_val:
        new_val = old_val
    if "_pw" in name:
        new_val = ftools.encrypt(new_val)
    new_config[name] = new_val

def ask_dict(questions, old_dict):
    "Gestione richieste interattive"
    new_dict = {}
    for key, value in questions.items():
        ask_one(key, old_dict, new_dict, value)
    return new_dict

def show(config, filename):
    "Mostra file di configurazione"
    print()
    print("File di configurazione:", filename)
    def showdict(adict, title, indent=''):
        print(indent, title)
        indent += '  '
        keys = list(adict.keys())
        keys.sort()
        for key in keys:
            val = adict[key]
            if isinstance(val, dict):
                showdict(val, key, indent)
            else:
                print(indent, f'{key}: {val}')
    showdict(config, filename)

def main():
    "Procedura"
    if "-h" in sys.argv:
        print(__doc__)
        sys.exit()

    cfile_name = os.path.join(cs.DATADIR, cs.CONFIG_NAME)
    cfile_save = os.path.join(cs.DATADIR, cs.CONFIG_SAVE)

    if os.path.exists(cfile_name):
        old_config = jload(cfile_name)
    else:
        old_config = {}

    if "-c" in sys.argv:
        creadirs()
        old_sede = old_config.get(cs.SEDE, {})
        if not isinstance(old_sede, dict):
            old_sede = {}

        new_sede = ask_dict(SEDE, old_sede)
        new_params = ask_dict(PARAMS, old_config)
        new_tech = ask_dict(TECH, old_config)

        new_config = {cs.CONFIG_VERSION: MY_VERSION, cs.SEDE: new_sede}
        new_config.update(new_params)
        new_config.update(new_tech)
        new_config[cs.FLASK_KEY] = ftools.randstr(30)

        print()
        print()
        if old_config:
            os.rename(cfile_name, cfile_save)
        jsave(cfile_name, new_config)

        if old_config:
            print("La configurazione precedente si trova nel file:", cfile_save)
        print("Creata nuova configurazione:", cfile_name)
    else:
        if old_config:
            show(old_config, cfile_name)
        else:
            print("Configurazione non definita.")
        print()
        print('Usa "-c" per creare/modificare la configurazione')
        print()

if __name__ == "__main__":
    main()
