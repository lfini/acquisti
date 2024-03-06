"""
Genera tabella di conversione per passaggio a nomi INAF

L.Fini - Novembre 2020
"""

import sys, os
import json
import pickle
import ftools as ft
from ldapinaf import get_users

from newusers import newids, special

TEST = True
DEBUG = False

if TEST:
    DATADIR = "/home/lfini/py/acquisti/data"
else:
    DATADIR = "/home/public/acquisti/data"

ALLCHARS = "abcdefghijklmnopqrstuvwxyz"
TOREMOVE = "' "

TTABLE = "".maketrans(ALLCHARS, ALLCHARS, TOREMOVE)

INAF_EMAIL = "@inaf.it"

def clean(nome):
    "Elimina caratteri non alfabetici"
    ret = nome.lower()
    return ret.translate(TTABLE)

uconvert = {}
econvert = {}
thedir = ft.checkdir()
ulist = ft.Table((thedir, 'userlist.json'))
for user in ulist:
    idx, userid, surname, name, email, flags, pwd = user
    newuserid = clean(name)+"."+clean(surname)
    if newuserid not in newids:
        if newuserid in special:
            newuserid = special[newuserid]
        else:
            newuserid = None
            print("Utente non trovato: (ID=%s NEW=%s [%s %s])"%(userid, newuserid, name, surname))
    if newuserid:
        try:
            ldapuser = get_users(newuserid)
            newemail = ldapuser[0]["eduPersonPrincipalName"]
            newname = ldapuser[0]['givenName'][0]
            newsurname = ldapuser[0]['sn'][0]
            uconvert[userid] = newuserid, newemail, newname, newsurname
            econvert[email] = newemail
        except Exception as excp:
            print("Errore LDAP per utente:", userid, "->", newuserid, "EXC-", str(excp))
 
#   Ciclo di conversione

print("Conversione tabella utenti")
for oldid, newinfo in uconvert.items():
    rec = ulist.where("userid", oldid, as_dict=True, index=True)[0]
    print("  Converto", oldid, "in", newinfo[0], "-", newinfo[1])
    updater = {"userid": newinfo[0],
               "email": newinfo[1],
               "name": newinfo[2],
               "surname": newinfo[3]}
    rec.update(updater)
    pos = rec["_IND_"]
    del rec["_IND_"]
    ulist.insert_row(rec, pos)

outfile = "newuserlist.json"
ulist.save(outfile)
print("Creato file:", outfile)

userid_table = {x: y[0] for x,y in uconvert.items()}
tab_file = "convert_data.pkl"
with open(tab_file, "wb") as outp:
    pickle.dump({"email_table": econvert, "userid_table": userid_table}, outp)
print("Creato file:", tab_file)

