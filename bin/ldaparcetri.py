# -*- coding: utf-8 -*-
"""
ldaplib.py    Vers. %s    - %s %s

  Test MODE usage:
     python ldaplib.py anonymous      Test login as anonymous
     python ldaplib.py aliases        Read aliases records
     python ldaplib.py employeeType   Print all employeeType values
     python ldaplib.py hosts          Read hosts records
     python ldaplib.py manager passwd Test login as manager with given password
     python ldaplib.py modif          Modify test
     python ldaplib.py people         Read people records
     python ldaplib.py user name      Show record for given uid
"""

# NOTA: richiede il package: python-ldap3

# VERSION 2.0      10/01/2018   Nuova versione basata su ldap3
#                               Compatibile python 2 e 3

from __future__ import print_function

import pprint
import sys
from ldap3 import Server, Connection, MODIFY_REPLACE

__author__ = 'Luca Fini'
__version__ = '2.0'
__date__ = '10/01/2018'

#### Parameters for LDAP test ###
LDAP_SERVER_IP = 'polluce.arcetri.astro.it'
PEOPLE_DN = 'ou=people,dc=arcetri,dc=astro,dc=it'
ALIASES_DN = 'ou=aliases,dc=arcetri,dc=astro,dc=it'
HOSTS_DN = 'ou=hosts,dc=arcetri,dc=astro,dc=it'
ANON_DN = "cn=anonymous,ou=admins,dc=arcetri,dc=astro,dc=it"
ANON_PW = 'arcetri'
MANAG_DN = "cn=manager,dc=arcetri,dc=astro,dc=it"

def __convert2__(obj):
    "Convert data retrieved from LDAP database (python 2 only)"
    if isinstance(obj, str):
        return obj.decode('utf8').strip()
    if isinstance(obj, (list, tuple)):
        ret = []
        for i in obj:
            ret.append(convert(i))
        return ret
    if isinstance(obj, dict):
        for k in obj:
            obj[k] = convert(obj[k])
        return obj
    return obj

def __convert3__(obj):
    "Dummy convert for python 3"
    return obj

def usage():
    "Print usage message"
    print(__doc__ % (__version__, __author__, __date__))
    sys.exit()

if sys.version_info.major > 2:
    input23 = input
    convert = __convert3__
else:
    input23 = raw_input
    convert = __convert2__

SERVER = None
CON = None

def _init():
    global SERVER
    if not SERVER:
        SERVER = Server(LDAP_SERVER_IP)

def make_connection(dn, pwd):
    "Open connection with server"
    global CON
    CON = Connection(SERVER, dn, pwd, auto_bind=True)

def as_anonymous(pwd=None):
    "Esegue bind come anonymous"
    _init()
    if not pwd:
        pwd = ANON_PW
    make_connection(ANON_DN, pwd)

def as_manager(pwd):
    "Esegue bind come manager"
    _init()
    make_connection(MANAG_DN, pwd)


def get_ldap_table(dnm, filt, bind_dn=None, bind_pw=None):
    "Legge una tabella da LDAP"
    _init()
    if bind_dn:
        make_connection(bind_dn, bind_pw)  # Login
    else:
        as_anonymous()                     # Default Login

    ret = []
    if CON.search(dnm, filt, attributes="*"):
        ret = convert([x['attributes'] for x in CON.response])
    else:
        raise Exception("LDAP server not replying")
    return ret

def get_people_table(real=False):
    "retrieve People table"
    def get_gid(tab_item):
        gid0 = tab_item.get('gidNumber', 0)
        if isinstance(gid0, (list, tuple)):
            gid0 = gid0[0]
        return int(gid0)

    as_anonymous()
    tab = get_ldap_table(PEOPLE_DN, '(uid=*)')
    if real:
        tab = [x for x in tab if get_gid(x) == 100]
    return tab

def get_people_record(uid):
    "Get a record from People table"
    as_anonymous()
    filt = '(uid=%s)' % uid
    tab = get_ldap_table(PEOPLE_DN, filt)
    if tab:
        result = tab[0]
    else:
        result = None
    return result

def update_people_item(uid, field, value, pwd):
    "Modifica un campo di un record people"
    fieldvalues = [(field, value)]
    update_people_items(uid, fieldvalues, pwd)

def update_people_items(uid, fieldvalues, pwd):
    "Modifies several fields of a LDAP record."
    _init()
    as_manager(pwd)
    update_dn = "uid=%s,ou=people,dc=arcetri,dc=astro,dc=it" % uid
    to_modify = {}
    for fname, value in fieldvalues:
        fname = str(fname).strip()
        value = str(value).strip()
        if not value:
            value = ' '
        to_modify[fname] = [(MODIFY_REPLACE, [value])]
    if to_modify:
        CON.modify(update_dn, to_modify)

def get_aliases_table():
    "Retrieve aliases table"
    as_anonymous()
    tabs = get_ldap_table(ALIASES_DN, '(cn=*)')
    return tabs

def get_hosts_table():
    "Retrieve hosts table"
    as_anonymous()
    tabs = get_ldap_table(HOSTS_DN, '(cn=*)')
    out = []
    for tab in tabs:
        for ipn in tab.get('ipHostNumber', []):
            descr = tab.get('description', [])
            rcsed = ', '.join(descr)
            descr = ' '.join(rcsed.split())
            item = (tab['cn'][0], ipn, descr)
            out.append(item)
    return out

def _cleandict(toclean):
    "Convert value field of dictionary from list[1] to simple value"
    for key in toclean:
        toclean[key] = toclean[key][0]

def readpeople():
    "Print People table"
    readp = get_people_table(real=True)
    pprint.pprint(readp)

def readaliases():
    "Retrieve aliases table"
    reada = get_aliases_table()
    pprint.pprint(reada)

def readhosts():
    "read host table"
    table = get_hosts_table()
    table.sort(key=lambda x: x[1])
    for tab in table:
        print(tab[1], '      ', tab[0], '        #', tab[2])

def testmodif():
    "Test user data modification"
    uid = input23('Utente da modificare (uid): ')
    print("Il test modifica i campi roomNumber  e telephoneNumber dell'utente:", uid)
    rnumb = input23('Nuovo roomNumber: ')
    tnumb = input23('Nuovo telephoneNumber: ')
    fieldvalues = [('roomNumber', rnumb), ('telephoneNumber', tnumb)]
    pwd = input23('Password per manager: ')
    update_people_items(uid, fieldvalues, pwd)

def get_employee_type(record):
    etype = record.get('employeeType')
    if isinstance(etype, (list, tuple)):
        etype = etype[0]
    return etype

def all_employeetypes():
    "Print all employee types"
    allusers = get_people_table(real=False)
    empl = [get_employee_type(x) for x in allusers]
    types = list(set([x for x in empl if x]))
    types.sort()
    print()
    print("N. People Items: %d" % len(allusers))
    print("Employee types:")
    for typ in types:
        print(' -', typ)

def show_user(uid):
    "Print user's data"
    user = get_people_record(uid)
    if user:
        pprint.pprint(user, indent=4, width=80)
    else:
        print('No user with uid: %s' % uid)

def main():
    "Test procedure"
    if len(sys.argv) < 2:
        usage()
        sys.exit()

    cmd = sys.argv[1].lower()+'  '
    cmd = cmd[:2]

    if cmd == 'al':
        readaliases()
    elif cmd == 'an':
        try:
            as_anonymous()
        except:
            print("Anonymous login failed")
        else:
            print("Anonymous login OK")
    elif cmd == 'em':
        all_employeetypes()
    elif cmd == 'ho':
        readhosts()
    elif cmd == 'ma':
        if len(sys.argv) < 3:
            print("Missing password!")
            sys.exit()
        try:
            as_manager(sys.argv[2])
        except:
            print("Manager login failed")
        else:
            print("Manager login OK")
    elif cmd == 'mo':
        testmodif()
    elif cmd == 'pe':
        readpeople()
    elif cmd == 'us':
        show_user(sys.argv[2])
    else:
        usage()

if __name__ == '__main__':
    main()
