"""
Gestione dati utenti via LDAP
"""

import logging
import time
import flask as fk
import wtforms as wt
import ldaparcetri as ll
import ftools as ft
import table as tb
from forms import MyTextField, MySelectField, MyLoginForm, render_field
from constants import *     # pylint: disable=W0401

#  VERSION  1.0  30/01/2015: Prima versione
#  VERSION  1.1  30/01/2015: Modificato metodo controllo password
#  VERSION  1.2  30/01/2015: Inseguimento modifiche ldaplib
#  VERSION  1.3  31/03/2015: Modificato controllo permessi
#  VERSION  1.4  20/05/2016: Modificato password_ok
#  VERSION  1.5  10/10/2016: Update per inseguimento modifiche ftools.py
#  VERSION  2.0  05/10/2018: Conversione a python 3
#  VERSION  2.1  12/03/2019: Bug fix
#  VERSION  2.2  26/03/2019: Bug fix
#  VERSION  2.3  10/12/2020: Un po' di pulizia nel codice

__author__ = 'Luca Fini'
__version__ = '2.3'
__date__ = '10/12/2020'

ALLPEOPLE = ll.get_people_table(real=False)
PEOPLE = [x for x in ALLPEOPLE if x.get('employeeType')]


SELECTOR_EMPL = list({x.get('employeeType')[0] for x in PEOPLE})
SELECTOR_EMPL.sort()

HEADER_ABOUT = """<!DOCTYPE html>
<html>
<head>
<title>About procedura ldapserver</title>
</head>
<body>"""

__start__ = time.asctime(time.localtime())

CONFIG = tb.jload((DATADIR, 'config.json'))
PWFILE = tb.jload_b64((DATADIR, 'pwfile.json'))

class LdapForm(wt.Form):
    "Form per modifica LDAP"
    ldap_tel = MyTextField('Numero telefonico (completo di prefisso internazionale)', False)
    ldap_stanza = MyTextField('Numero di stanza', False)

    ldap_posizione = MySelectField('Posizione', True,
                                   [wt.validators.Required()],
                                   choices=list(zip(SELECTOR_EMPL, SELECTOR_EMPL)))

    avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def render(self):
        "Rendering del form"
        html = []
        html.append('<tr><td>'+render_field(self.ldap_tel)+'</td></tr>')
        html.append('<tr><td>'+render_field(self.ldap_stanza)+'</td></tr>')
        html.append('<tr><td>'+render_field(self.ldap_posizione)+'</td></tr>')
        html.append('<tr><td>'+self.annulla()+' &nbsp; '+self.avanti()+'</td></tr>')
        return '\n'.join(html)

MLP = fk.Flask(__name__, template_folder='../files', static_folder='../files')
MLP.secret_key = PWFILE['secret_key']

def _test_authorization(user):
    return 'L' in user.get('flags')

def test_people(people):
    "Verifica correttezza campi"
    ret = []
    for pers in people:
        anlist = []
        if not pers.get('roomNumber'):
            anlist.append('N.stanza mancante')
        if not pers.get('telephoneNumber'):
            anlist.append('N.tel. mancante')
        etype = pers.get('employeeType')
        if etype:
            if not etype in SELECTOR_EMPL:
                anlist.append('Posizione errata')
        else:
            anlist.append('Posizione mancante')
        if anlist:
            ret.append((pers['uid'],
                        '%s, %s'%(pers['sn'], pers.get('givenName', '~')),
                        ', '.join(anlist)))
    return ret

@MLP.route("/clearsession")
def clearsession():
    "Clear sessione e ritorno a login"
    fk.session.clear()
    return fk.redirect(fk.url_for('login'))


@MLP.route("/login", methods=['GET', 'POST'])
def login():
    "Accesso login"
    usr = fk.request.form.get('userid')
    pwd = fk.request.form.get('password')
    form = MyLoginForm(DATADIR, usr, pwd, CONFIG.get("ldap_host"),
                       CONFIG.get("ldap_port"), formdata=fk.request.form)
    if fk.request.method == 'POST' and form.validate():
        ret, why = form.password_ok()
        if ret:
            fk.session['userid'] = fk.request.form['userid']
            return fk.redirect(fk.url_for('start'))
        msg = 'Login negato per %s (%s)' % (usr, why)
        fk.flash(msg)
        logging.error(msg)
    return fk.render_template('login.html', form=form,
                              sede=CONFIG['sede'], title='Modifica dati utenti') # .encode('utf8')

@MLP.route('/modificaldap/<uid>', methods=['GET', 'POST'])
def modifica_ldap(uid):
    "Modifica dati utente"
    user = ft.login_check(fk.session)
    if user:
        if _test_authorization(user):
            try:
                urecord = ll.get_people_record(uid)
            except Exception as excp:                # pylint: disable=W0703
                msg = "Errore: %s"%str(excp)
                fk.flash(msg)
                logging.error(msg)
                return fk.redirect(fk.url_for("start"))
            udata = {'ldap_tel': urecord.get('telephoneNumber', [''])[0],
                     'ldap_stanza': urecord.get('roomNumber', [''])[0],
                     'ldap_posizione': urecord.get('employeeType', [''])[0]}
            fullname = '%s, %s' % (urecord.get('sn')[0], urecord.get('givenName')[0])
            cform = LdapForm(formdata=fk.request.form, **udata)
            if fk.request.method == 'POST':
                if 'annulla' in fk.request.form:
                    fk.flash('Operazione annullata')
                    return fk.redirect(fk.url_for('start'))
                if 'avanti' in fk.request.form and cform.validate():
                    update = [('employeeType', cform.ldap_posizione.data)]
                    posizione = cform.ldap_posizione.data.strip()
                    if not posizione:
                        posizione = None
                    update = [('employeeType', posizione)]
                    stanza = cform.ldap_stanza.data.strip()
                    update.append(('roomNumber', stanza))
                    tel = cform.ldap_tel.data.strip()
                    if not tel:
                        tel = 0
                    update.append(('telephoneNumber', tel))
                    ll.update_people_items(uid, update, PWFILE['manager_pw'])
                    fk.flash('Aggiornato utente: %s' % fullname)
                    return fk.redirect(fk.url_for('start'))
            ddd = {'title': 'Aggiornamento dati utente: %s' % fullname,
                   'before':"<form method=POST action=/modificaldap/%s>" % uid,
                   'after':"</form>",
                   'note':'<b>N.B.:</b> I campi sottolineati sono obbligatori',
                   'body': cform.render()}
            return fk.render_template('form_layout.html', data=ddd,
                                      sede=CONFIG["sede"]).encode('utf8')
        return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))

@MLP.route('/')
def start():
    "Start da qui"
    user = ft.login_check(fk.session)
    if user:
        if _test_authorization(user):
            people = [p for p in ll.get_people_table(real=True) \
                      if (p.get('sn') and p.get('givenName'))]
            page_data = ft.byinitial(people,
                                     key=lambda x: x.get('sn')[0].lower()+ \
                                                   x.get('givenName')[0].lower())
            initials = list(page_data.keys())
            initials.sort()
            return fk.render_template('lista_people.html',
                                      title='Elenco generale utenti', initials=initials,
                                      data=page_data, sede=CONFIG["sede"]).encode('utf8')
        return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))

@MLP.route('/anomalie')
def anomalie():
    "Riporta lista utenti con anomalie"
    user = ft.login_check(fk.session)
    if user:
        if _test_authorization(user):
            people = ll.get_people_table(real=True)
            lista_anomalie = test_people(people)
            return fk.render_template('lista_anomalie.html',
                                      title='Utenti con anomalie',
                                      sede=CONFIG["sede"],
                                      data=lista_anomalie).encode('utf8')
        return fk.render_template('noaccess.html').encode('utf8')
    return fk.redirect(fk.url_for('login'))



####################################################################################

def initialize_me():
    "Inizializzations"
    logging.info("Starting manageldap.py - Vers. %s, %s. %s", __version__, __date__, __author__)
    ft.update_userlist()
    ft.init_helplist()
    logging.info("Initialization complete")

def localtest():
    "Start in local mode (for debug)"
    logging.basicConfig(level=logging.DEBUG)
    initialize_me()
    logging.info("Waiting for clients on port: 4010")
    MLP.run(host="0.0.0.0", port=4010, debug=True)

def production():
    "Start in production mode"
    logging.basicConfig(level=logging.INFO)
    ft.set_file_logger((WORKDIR, 'ldap.log'))
    ft.set_mail_logger(CONFIG[SMTP_HOST], CONFIG[EMAIL_PROCEDURA],
                       CONFIG[EMAIL_WEBMASTER], 'Notifica errore LDAP manager')
    initialize_me()

if __name__ == '__main__':
    print("Starting in local mode")
    localtest()
else:
    production()
