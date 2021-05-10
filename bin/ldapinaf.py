"""
ldapinaf.py    Vers. %s    - %s %s

Estrazione dati da tabelle LDAP di INAF (seleziona dipendenti di Arcetri)

Uso:
     python ldapinaf.py [-a] [-h] [filt]

dove:
     -a         Limita ricerca ad Arcetri
     filt       Filtro selezione (es: \\*fini\\*)
                Default: tabella completa
"""

# NOTA: richiede il package: python-ldap3

import sys
from ldap3 import Server, Connection

__author__ = 'Luca Fini'
__version__ = '1.0'
__date__ = '28/11/2020'

#### Parameters for LDAP test ###
LDAP_SERVER_IP = 'ldap.ced.inaf.it'
PEOPLE_DN = 'ou=people,dc=inaf,dc=it'
FILT_ARCETRI = "(&(uid=%s)(ou=*Arcetri*))"
FILT_INAF = "(uid=%s)"

def usage():
    "Print usage message"
    print(__doc__ % (__version__, __author__, __date__))
    sys.exit()

class HOOK:                    #pylint: disable=R0903
    "Parametri di connessione"
    server = None
    connection = None

def _init():
    if not HOOK.server:
        HOOK.server = Server(LDAP_SERVER_IP)
        HOOK.connection = Connection(HOOK.server, auto_bind=True)

def get_users(select=None, arcetri=True):
    "Estrae nomi da tabella people da LDAP"
    _init()
    if arcetri:
        basefilt = FILT_ARCETRI
    else:
        basefilt = FILT_INAF
    if select:
        filt = basefilt%select
    else:
        filt = basefilt%"*"
    if HOOK.connection.search(PEOPLE_DN, filt, attributes="*"):
        return [x['attributes'] for x in HOOK.connection.response]
    return []

def show_users(filt, arcetri):
    "Print user's data"
    users = get_users(filt, arcetri)
    if users:
        for user in users:
            print("-----------------------")
            keys = list(user.keys())
            keys.sort()
            for key in keys:
                print(" %s:"%key, user[key])
    else:
        print('No user matching: %s' % filt)

def main():
    "Test procedure"
    if "-h" in sys.argv:
        usage()
        sys.exit()
    arcetri = bool("-a" in sys.argv)

    if not sys.argv[-1].startswith("-"):
        filt = sys.argv[-1]
    else:
        filt = None
    show_users(filt, arcetri)

if __name__ == '__main__':
    main()
