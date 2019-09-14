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
import readline

import ftools

__version__ = "1.0"

SEDE = OrderedDict([("sede_it", "Identificazione sede INAF\n[es: INAF - Osservatorio Astrofisico di Arcetri]"),
                    ("sede_uk", "Identificazione della sede per documenti in inglese\n[es: INAF - Arcetri Astrophysical Observatory]"),
                    ("indirizzo", "Indirizzo postale della sede (una linea)\n[es: L.go Enrico Fermi, 5. 50125 Firenze (Italia)]"),
                    ("citta", "Città\n[es: Firenze]"),
                    ("website", "URL completa del sito web della sede\n[es: http://www.arcetri.inaf.it]")])

PARAMS = OrderedDict([("nome_webmaster", "Nome del web master\n[es: Luca Fini]"),
                      ("email_webmaster", "Indirizzo e-mail del web master\n(a cui saranno mandati i messaggi di errore)\n[es: lfini@arcetri.inaf.it]"),
                      ("nome_direttore", "Nome del direttore\n[es: Maria Sofia Randich]"),
                      ("email_direttore", "Indirizzo e-mail del direttore\n[es: luca.fini@inaf.it]"),
                      ("titolo_direttore", "Titolo del direttore\n[es: Dott.ssa]"),
                      ("email_ufficio", "Indirizzo EMail dell'ufficio ordini\nA questo indirizzo sono inviati i messaggi automatici\ngenerati dalla procedura [es: ordini@arcetri.inaf.it]"),
                     ])

TECH = OrderedDict([("web_host", "Indirizzo IP del server che ospita la procedura\n[es: www.arcetri.inaf.it]"),
                    ("web_port", "Port IP assegnato alla procedura\n[es: 4000)"),
                    ("smtp_host", "Indirizzo IP del server SMTP\nIndirizzo del server SMTP utilizzato dalla procedura\nper inviare i messaggi automatici [es: smtp.arcetri.astro.it]"),
                    ("email_responder", "Indirizzo EMail valido per il responder automatico\n[es: acquisti@arcetri.inaf.it]"),
                    ("ldap_host", "Indirizzo del server LDAP per autenticazione utenti\n[es: ldap.ced.inaf.it]\n(Usa '-' per disabilitare autenticazione LDAP)"),
                    ("ldap_port", "IP port del server LDAP per autenticazione utenti\n[es: 389]"),
                    ("pop3_host", "Indirizzo del server POP3 del responder\n[es: pop3.arcetri.inaf.it]"),
                    ("pop3_user", "Username POP3 per accesso ai mail del responder\n[es: acquisti]"),
                    ("pop3_pw", "Password POP3 per accesso ai mail del responder"),
                    ("approval_host", "Indirizzo IP per le richieste del responder\nSi tratta dell'indirizzo IP (numerico) del server sul quale\ngira la procedura del responder automatico [es: 193.206.154.33]"),
                   ]
                  )

def creadirs():
    "Crea struttura directory di lavoro"
    datadir = ftools.datapath()
    workdir = ftools.workpath()
    approvdir = os.path.join(datadir, 'approv')

    print()
    if os.path.exists(datadir):
        print("Directory %s già esistente"%datadir)
    else:
        os.makedirs(datadir)
        print("Creata directory %s"%datadir)

    if os.path.exists(approvdir):
        print("Directory %s già esistente"%approvdir)
    else:
        os.makedirs(approvdir)
        print("Creata directory %s"%approvdir)

    if os.path.exists(workdir):
        print("Directory %s già esistente"%workdir)
    else:
        os.makedirs(workdir)
        print("Creata directory %s"%workdir)
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

    cfile_name = os.path.join(ftools.datapath(), "config.json")
    cfile_save = os.path.join(ftools.datapath(), "config.save")

    if os.path.exists(cfile_name):
        old_config = ftools.jload(cfile_name)
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
        ftools.jsave(cfile_name, new_config)

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
