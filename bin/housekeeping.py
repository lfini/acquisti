#!/usr/bin/env python3
"""
Modulo per gestione tabelle
"""

# VERSION=3.0    08/01/2018
#  - Versione python 3

__author__ = 'Luca Fini'
__version__ = '3.0'
__date__ = '08/01/2018'

import time
import logging

import flask as fk
import wtforms as wt

import ftools as ft
from forms import MyTextField, MyTextAreaField, MySelectField, MyBooleanField, MyLoginForm

from constants import *

PKG_ROOT = ft.pkgroot()
DATADIR = ft.datapath()
WORKDIR = ft.workpath()

HEADER_ABOUT = """<!DOCTYPE html>
<html>
<head>
<title>About procedura housekeeping</title>
</head>
<body>"""

CONFIG = ft.jload((DATADIR, 'config.json'))
IS_ARCETRI = 1 if "arcetri" in CONFIG[WEB_HOST] else 0

__start__ = time.asctime(time.localtime())

def reinit():
    "Aggiorna tabelle"
    ft.update_userlist()
    ft.update_codflist()

class CodfForm(wt.Form):
    "Modulo per modifica codici fondi"
    Codice = MyTextField('Codice', True, [wt.validators.Required()])
    Titolo = MyTextField('Titolo', True, [wt.validators.Required()])
    CUP = MyTextField('CUP', False)
    email_Responsabile = MySelectField('Responsabile', True, [wt.validators.Required()])

    Commenti = MyTextAreaField('Commenti', False)
    avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])
    cancella = wt.SubmitField('Cancella record', [wt.validators.Optional()])

class UserForm(wt.Form):
    "Form per modifica dati utente"
    userid = MyTextField('username',
                         [wt.validators.Required(message="Devi specificare l'username")])
    name = MyTextField('Nome',
                       [wt.validators.Required(message="Devi specificare il nome")])
    surname = MyTextField('Cognome',
                          [wt.validators.Required(message="Devi specificare il cognome")])

    email = MyTextField('e-mail', True, [wt.validators.Email()])
    amministratore = MyBooleanField('Funzioni di amministrazione', False)
    avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])
    cancella = wt.SubmitField('Cancella record', [wt.validators.Optional()])

def _nome_resp(ulist, eaddr, prima_nome=True):
    if prima_nome:
        return '%s %s'%(ulist.get(eaddr, ['', '', '??', '??'])[3],
                        ulist.get(eaddr, ['', '??', '??'])[2])
    return '%s, %s'%(ulist.get(eaddr, ['', '', '??', '??'])[2],
                     ulist.get(eaddr, ['', '??', '??'])[3])

def _test_admin(user):
    return 'A' in user.get('flags')

HSK = fk.Flask(__name__, template_folder='../files', static_folder='../files')

@HSK.before_request
def before():
    "Codice da eseguire prima di ogni accesso"
    ft.set_host_info(fk.request.host)
    reinit()

@HSK.route('/')
def start():
    "Start da qui"
    user = ft.login_check(fk.session)
    if user:
        status = {'footer': "Procedura housekeeping.py. Vers. %s - "
                            "L. Fini, %s"%(__version__, __date__),
                  'host': ft.host(fk.request.url_root)}

        if _test_admin(user):
            print("is_arcetri", IS_ARCETRI)
            return fk.render_template('start_housekeeping.html',
                                      is_arcetri=IS_ARCETRI,
                                      user=user,
                                      sede=CONFIG[SEDE],
                                      status=status).encode('utf8')
        fk.session.clear()
        return fk.render_template('noaccess.html')
    return fk.redirect(fk.url_for('login'))

@HSK.route("/clearsession")
def clearsession():
    "Clear sessione e torna a login"
    fk.session.clear()
    return fk.redirect(fk.url_for('login'))


@HSK.route("/login", methods=['GET', 'POST'])
def login():
    "Accesso iniziale"
    usr = fk.request.form.get('userid')
    psw = fk.request.form.get('password')
    form = MyLoginForm(DATADIR, usr, psw, CONFIG.get(LDAP_HOST),
                       CONFIG.get(LDAP_PORT), formdata=fk.request.form)
    if fk.request.method == 'POST' and form.validate():
        ret, why = form.password_ok()
        if ret:
            fk.session['userid'] = fk.request.form['userid']
            return fk.redirect(fk.url_for('start'))
        else:
            msg = 'Login negato per %s (%s)  ' % (usr, why)
            logging.error(msg)
            fk.flash(msg)
    return fk.render_template('login.html', form=form, sede=CONFIG[SEDE],
                              title='Modifica tabelle').encode('utf8')

@HSK.route('/about')
def about():
    "Riporta informazioni generali sulla procedura"
    user = ft.login_check(fk.session)
    if user:
        if _test_admin(user):
            fmt = '<tr><td> <tt> %s </tt></td><td> %s </td><td>%s</td> <td> %s </td></tr>'
            html = [HEADER_ABOUT]
            html.append('<h2>Informazioni su procedura housekeeping.py</h2>')
            html.append('<h4>Ultimo restart: %s </h4>' % __start__)
            html.append('<blockquote><table cellpadding=3 border=1>')
            html.append('<tr><th>Modulo</th><th>Autore</th><th>Versione</th><th>Data</th></tr>')
            html.append(fmt%('housekeeping.py', __author__, __version__, __date__))
            html.append(fmt%('ftools.py', ft.__author__, ft.__version__, ft.__date__))
            html.append(fmt%('table.py', ft.tb.__author__, ft.tb.__version__, ft.tb.__date__))
            html.append(fmt%('Flask', 'Vedi: <a href=http://flask.pocoo.org>Flask home</a>',
                             fk.__version__, '-'))
            html.append(fmt%('WtForms',
                             'Vedi: <a href=https://wtforms.readthedocs.org>WtForms home</a>',
                             wt.__version__, '-'))
            html.append('</table></blockquote>')
            html.append('<hr>&rightarrow; <a href=/>Torna</a>')

            html.append('</body></html>')
            return '\n'.join(html)
        fk.session.clear()
        return fk.render_template('noaccess.html')
    return fk.redirect(fk.url_for('login'))


@HSK.route("/sortcodf/<field>")
def sortcodf(field):
    "Riporta codici fondi con ordine specificato"
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
                                      ('/', 'Torna')),
                                sort_on=field,
                                messages=msgs,
                                footer="Procedura housekeeping.py. Vers. %s. &nbsp;-&nbsp; "
                                       "L. Fini, %s" % (__version__, __date__))
        return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))


@HSK.route("/codf")
def codf():
    "Riporta codici fondi"
    return sortcodf('')


@HSK.route('/addcodf', methods=('GET', 'POST'))
def addcodf():
    "Aggiungi codice fondo"
    user = ft.login_check(fk.session)
    if user:
        if _test_admin(user):
            cfr = CodfForm(formdata=fk.request.form)
            ulist = ft.FTable((DATADIR, 'userlist.json')).as_dict('email', True)
            resp_menu = [(x, _nome_resp(ulist, x, False)) for  x in ulist]
            resp_menu.sort(key=lambda x: x[1])
            cfr.email_Responsabile.choices = resp_menu
            ncodf = ft.FTable((DATADIR, 'codf.json'))
            if fk.request.method == 'POST':
                if 'annulla' in fk.request.form:
                    fk.flash('Operazione annullata')
                    return fk.redirect(fk.url_for('start'))
                if cfr.validate():
                    data = ncodf.get_row(0, as_dict=True, default='') # get an empty row
                    data.update(cfr.data)
                    ncodf.insert_row(data)
                    ncodf.save()
                    msg = 'Aggiunto Codice fondo: %s' % data['Codice']
                    HSK.logger.info(msg)
                    fk.flash(msg)
                    return fk.redirect(fk.url_for('codf'))
            return ncodf.render_item_as_form('Aggiungi Codice fondo', cfr, fk.url_for('addcodf'))
        else:
            return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))

@HSK.route('/editcodf/<nrec>', methods=('GET', 'POST'))
def editcodf(nrec):
    "Modifica tabella codici fondi"
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
                HSK.logger.debug("Codice row=%s", row)
                cfr = CodfForm(**row)
                cfr.email_Responsabile.choices = resp_menu
            else:
                cfr = CodfForm(formdata=fk.request.form)
                cfr.email_Responsabile.choices = resp_menu
                if 'cancella' in fk.request.form:
                    ncodf.delete_row(nrec)
                    ncodf.sort(1)
                    ncodf.save()
                    msg = 'Cancellato Codice fondo: %s (%s)'%(row['Codice'],
                                                              row['email_Responsabile'])
                    fk.flash(msg)
                    HSK.logger.info(msg)
                    return fk.redirect(fk.url_for('codf'))
                if 'annulla' in fk.request.form:
                    fk.flash('Operazione annullata')
                    return fk.redirect(fk.url_for('start'))
                if cfr.validate():
                    if 'avanti' in fk.request.form:
                        row.update(cfr.data)
                        ncodf.insert_row(row, nrec)
                        print("row:", row, "   nrec:", nrec)
                        ncodf.save()
                        msg = 'Modificato Codice fondo: %s (%s)'%(row['Codice'],
                                                                  row['email_Responsabile'])
                        fk.flash(msg)
                        HSK.logger.info(msg)
                    return fk.redirect(fk.url_for('codf'))
            return ncodf.render_item_as_form('Modifica Codice fondo', cfr,
                                             fk.url_for('editcodf', nrec=str(nrec)), nrow=nrec)
        else:
            return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))

@HSK.route('/downloadcodf', methods=('GET', 'POST'))
def downloadcodf():
    "Download tabella codici fondi"
    return download('codf')

@HSK.route('/downloadutenti', methods=('GET', 'POST'))
def downloadutenti():
    "Download tabella utenti"
    return download('utenti')

def download(_unused):
    "Download"
    user = ft.login_check(fk.session)
    if user:
#       table = ft.FTable((DATADIR, what+'.json'))
        return fk.render_template('tbd.html', goto='/')
    return fk.redirect(fk.url_for('login'))

@HSK.route("/utenti")
def utenti():
    "Genera lista utenti"
    user = ft.login_check(fk.session)
    if user:
        if _test_admin(user):
            users = ft.FTable((DATADIR, 'userlist.json'))
            msgs = fk.get_flashed_messages()
            return users.render("Lista utenti",
                                select_url=("/edituser",
                                            "Per modificare, clicca sul simbolo: "
                                            "<font color=red><b>&ofcir;</b></font>"),
                                menu=(('/adduser', "Aggiungi utente"),
                                      ('/downloadutenti', "Scarica CSV"),
                                      ('/', 'Torna')),
                                sort_on="surname",
                                messages=msgs,
                                footer="Procedura housekeeping.py. Vers. %s "
                                       "- L. Fini, %s"%(__version__, __date__))
        return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))


@HSK.route('/adduser', methods=('GET', 'POST'))
def adduser():
    "Aggiungi utente"
    user = ft.login_check(fk.session)
    if user:
        if _test_admin(user):
            cfr = UserForm(formdata=fk.request.form)
            users = ft.FTable((DATADIR, 'userlist.json'))
            if fk.request.method == 'POST':
                if 'annulla' in fk.request.form:
                    fk.flash('Operazione annullata')
                    return fk.redirect(fk.url_for('start'))
                if cfr.validate():
                    data = users.get_row(0, as_dict=True, default='') # get an empty row
                    data.update(cfr.data)
                    data['pw'] = '-'
                    users.insert_row(data)
                    users.save()
                    msg = 'Aggiunto Utente: %s %s' % (data['surname'], data['name'])
                    HSK.logger.info(msg)
                    fk.flash(msg)
                    return fk.redirect(fk.url_for('utenti'))
                else:
                    HSK.logger.debug("Validation errors: %s", cfr.errors)
            return users.render_item_as_form('Aggiungi utente', cfr,
                                             fk.url_for('adduser'), ignore=('pw', 'flags'))
        else:
            return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))

@HSK.route('/edituser/<nrec>', methods=('GET', 'POST'))
def edituser(nrec):
    "Modifica dati utente"
    nrec = int(nrec)
    user = ft.login_check(fk.session)
    if user:
        if _test_admin(user):
            users = ft.FTable((DATADIR, 'userlist.json'))
            users.sort(3)
            row = users.get_row(nrec, as_dict=True)
            if fk.request.method == 'GET':
                HSK.logger.debug("Userlist row=%s", row)
                cfr = UserForm(**row)
                HSK.logger.debug("UserForm inizializzato: %s", cfr.data)
            else:
                cfr = UserForm(formdata=fk.request.form)
                if 'annulla' in fk.request.form:
                    fk.flash('Operazione annullata')
                    return fk.redirect(fk.url_for('start'))
                if 'cancella' in fk.request.form:
                    row = users.get_row(nrec, as_dict=True)
                    users.delete_row(nrec)
                    users.sort(3)
                    users.save()
                    msg = "Cancellato utente N. %d: %s %s" %(nrec, row['name'], row['surname'])
                    HSK.logger.info(msg)
                    fk.flash(msg)
                    return fk.redirect(fk.url_for('utenti'))
                if cfr.validate():
                    if 'avanti' in fk.request.form:
                        HSK.logger.debug("Pressed: avanti. Modifica utente")
                        row.update(cfr.data)
                        users.insert_row(row, nrec)
                        users.sort(3)
                        users.save()
                        msg = 'Modificato utente: %s %s' % (row['name'], row['surname'])
                        HSK.logger.info(msg)
                        fk.flash(msg)
                    return fk.redirect(fk.url_for('utenti'))
            return users.render_item_as_form('Modifica utente', cfr,
                                             fk.url_for('edituser', nrec=str(nrec)),
                                             nrow=nrec, ignore=('pw', 'flags'))
        else:
            return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))

@HSK.route('/files/<fname>')
def files(fname):
    "Accesso a file HTML"
    return HSK.send_static_file(fname)

####################################################################################

HSK.secret_key = CONFIG[FLASK_KEY]

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Server housekeeping attivo su porta: 4101")
    reinit()
    ft.init_helplist()
    HSK.run(port=4101, debug=True)
else:                         # In production mode, add log handler to sys.stderr.
    EMAIL = {'mailhost': CONFIG[SMTP_HOST],
             'fromaddr': CONFIG[EMAIL_UFFICIO],
             'toaddrs': [CONFIG[EMAIL_WEBMASTER]],
             'subject': 'Notifica errore HOUSEKEEPING'}
    logging.basicConfig(level=logging.INFO)
    ft.set_file_logger((WORKDIR, 'housekeeping.log'), email=EMAIL)
    reinit()
    ft.init_helplist()
