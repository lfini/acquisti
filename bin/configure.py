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
from constants import *                 # pylint: disable=W0401
from table import jload, jsave

__version__ = "1.2"

LDAP_PORT_DESC = """IP port del server LDAP per autenticazione utenti
[es: 389]
"""

LDAP_HOST_DESC = """Indirizzo del server LDAP per autenticazione utenti
[es: ldap.ced.inaf.it]
(Usa '-' per disabilitare autenticazione LDAP)
"""

SMTP_HOST_DESC = """Indirizzo IP del server SMTP
Indirizzo del server SMTP utilizzato dalla procedura
per inviare i messaggi automatici [es: smtp.arcetri.astro.it]
(usare "-" se si utilizza GMail API per  l'invio di messaggi.
altrimenti usare un indirizzo e-mail valido per il server SMTP)
"""

WEB_PORT_DESC = """Port IP assegnato alla procedura
[es: 4000)
"""

WEB_HOST_DESC = """Indirizzo IP del server che ospita la procedura
[es: www.arcetri.inaf.it]
"""

LATEX_PATH_DESC = """Directory di installazione di pdflatex
[es: /usr/local/bin]
"""

EMAIL_UFFICIO_DESC = """Indirizzo EMail dell'ufficio ordini.
A questo indirizzo sono inviati i messaggi automatici
generati dalla procedura [es: ordini.oaa@inaf.it]
"""

TITOLO_DIRETTORE_DESC = """Titolo del direttore
[es: Dott.ssa]
"""

TITOLO_DIRETTORE_UK_DESC = """Titolo del direttore per ordini in inglese
[es: Dr.]
"""

EMAIL_DIRETTORE_DESC = """Indirizzo e-mail del direttore
[es: luca.fini@inaf.it]
"""

NOME_DIRETTORE_DESC = """Nome del direttore
[es: Maria Sofia Randich
"""

EMAIL_WEBMASTER_DESC = """Indirizzo e-mail del web master
(a questo indirizzo saranno mandati i messaggi di errore)
[es: luca.fini@inaf.it]
"""

NOME_WEBMASTER_DESC = """Nome del web master
[es: Luca Fini]
"""

WEBSITE_DESC = """URL completa del sito web della sede
[es: http://www.arcetri.inaf.it]
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

EMAIL_PROCEDURA_DESC = """Indirizzo e-mail da cui provengono i messaggi tecnici.
Dovrebbe corrispondere all'identità GMail utilizzata per l'invio di messaggi.
(Es.: acquisti.oaa@gmail.com)
"""

SEDE = OrderedDict([(SEDE_IT, SEDE_DESC),
                    (SEDE_UK, SEDE_UK_DESC),
                    (INDIRIZZO, INDIRIZZO_DESC),
                    (CITTA, CITTA_DESC),
                    (WEBSITE, WEBSITE_DESC),
                   ])

PARAMS = OrderedDict([(NOME_WEBMASTER, NOME_WEBMASTER_DESC),
                      (EMAIL_WEBMASTER, EMAIL_WEBMASTER_DESC),
                      (NOME_DIRETTORE, NOME_DIRETTORE_DESC),
                      (EMAIL_DIRETTORE, EMAIL_DIRETTORE_DESC),
                      (TITOLO_DIRETTORE, TITOLO_DIRETTORE_DESC),
                      (TITOLO_DIRETTORE_UK, TITOLO_DIRETTORE_UK_DESC),
                      (EMAIL_UFFICIO, EMAIL_UFFICIO_DESC),
                      (LATEX_PATH, LATEX_PATH_DESC),
                     ])

TECH = OrderedDict([(WEB_HOST, WEB_HOST_DESC),
                    (WEB_PORT, WEB_PORT_DESC),
                    (SMTP_HOST, SMTP_HOST_DESC),
                    (EMAIL_PROCEDURA, EMAIL_PROCEDURA_DESC),
                    (LDAP_HOST, LDAP_HOST_DESC),
                    (LDAP_PORT, LDAP_PORT_DESC),
                   ]
                  )

def creadirs():
    "Crea struttura directory di lavoro"
    approvdir = os.path.join(DATADIR, 'approv')

    print()
    if os.path.exists(DATADIR):
        print("Directory %s già esistente"%DATADIR)
    else:
        os.makedirs(DATADIR)
        print("Creata directory %s"%DATADIR)

    if os.path.exists(approvdir):
        print("Directory %s già esistente"%approvdir)
    else:
        os.makedirs(approvdir)
        print("Creata directory %s"%approvdir)

    if os.path.exists(WORKDIR):
        print("Directory %s già esistente"%WORKDIR)
    else:
        os.makedirs(WORKDIR)
        print("Creata directory %s"%WORKDIR)
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
    keys = list(config.keys())
    keys.sort()
    print()
    print("File di configurazione:", filename)
    for key in keys:
        print("   %s:"%key, config[key])

def main():
    "Procedura"
    if "-h" in sys.argv:
        print(__doc__)
        sys.exit()

    cfile_name = os.path.join(DATADIR, "config.json")
    cfile_save = os.path.join(DATADIR, "config.save")

    if os.path.exists(cfile_name):
        old_config = jload(cfile_name)
    else:
        old_config = {}

    if "-c" in sys.argv:
        creadirs()
        old_sede = old_config.get("sede", {})
        if not isinstance(old_sede, dict):
            old_sede = {}

        new_sede = ask_dict(SEDE, old_sede)
        new_params = ask_dict(PARAMS, old_config)
        new_tech = ask_dict(TECH, old_config)

        new_config = {"sede": new_sede}
        new_config.update(new_params)
        new_config.update(new_tech)
        new_config["flask_key"] = ftools.randstr(30)

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
            print()
            print("Configurazione non definita. Usa '-h' per istruzioni")
            print()

if __name__ == "__main__":
    main()
