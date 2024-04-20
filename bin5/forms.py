"""
Definizione forms per procedura acquisti
"""

import wtforms as wt
import flask as fk
from markupsafe import Markup

import ftools as ft
import constants as cs

__version__ = "2.2"
__date__ = "01/04/2024"
__author__ = "Luca Fini"

class DEBUG:             #pylint: disable=R0903
    'debug flag'
    enable = False

def debug_enable(enable=True):
    'abilita/disabilita printout di debug'
    DEBUG.enable = enable

def _debug(*f):
    print('DBG FORMS>', *f)

def radio_widget(field, **kwargs):
    "La mia versione del RadioWidget"
    kwargs.setdefault('type', 'radio')
    field_id = kwargs.pop('id', field.id)
    html = []
    for value, label, checked, _ in field.iter_choices():
        choice_id = f'{field_id}-{value}'
        options = dict(kwargs, name=field.name, value=value, id=choice_id)
        if checked:
            options['checked'] = 'checked'
        html.append(f'<input {ft.html_params(options)} />')
        html.append(f'<label for="{field_id}">{label}</label><br>')
    return ''.join(html)

def _has(hspec):
    if hspec in ft.GlobLists.HELPLIST:
        return 'help_'+hspec+'.html'
    return ''

def popup(url, text, size=(700, 500)):
    "Genera codice HTML per popup"
    return f'<a href="{url}"  onclick="window.open(\'{url}\', \'newwindow\', \'width={size[0]}, '\
           f'height={size[1]}, scrollbars=yes\'); return false;">{text}</a>'

def render_field(field, sameline=False, **kw):
    "Rendering di un campo"
    if field.help_spec:
        help_url = Markup(f'/files/{field.help_spec}')
        hlink = popup(help_url, '<sup><img src=/files/qm-12.png></sup>', size=(640, 480))
    else:
        hlink = ''
    if sameline:
        sep = "&nbsp;&nbsp;&nbsp;"
    else:
        sep = "<br />"
    if field.is_required:
        lab = Markup(f'<u>{field.a_label:s}</u>{hlink}{sep}')
    else:
        lab = Markup(f'{field.a_label}{hlink}{sep}')
    if isinstance(field, MyFormField):
        ret = Markup(field.form.renderme(**kw))
    else:
        ret = Markup(field(**kw))
    return lab+ret

B_TRTD = Markup('<tr><td>')
E_TRTD = Markup('</td></tr>')
BRK = Markup("<br />")
NBSP = Markup(" &nbsp; ")

class MyBooleanField(wt.BooleanField):
    "La mia versione del BooleanField"
    def __init__(self, label, required, *f, **kw):
        super().__init__(label, *f, **kw)
        self.help_spec = _has(self.short_name)
        self.is_required = required
        self.a_label = label

class MyRadioField(wt.RadioField):
    "La mia versione del RadioField"
    def __init__(self, label, required, *f, **kw):
        super().__init__(label, *f, **kw)
        self.help_spec = _has(self.short_name)
        self.is_required = required
        self.a_label = label
    def pre_validate(self, form):
        "Override la pre validation per modificare il messaggio"
        return True

class MyTextField(wt.StringField):
    "La mia versione del StringField"
    def __init__(self, label, required, *f, **kw):
        super().__init__(label, *f, **kw)
        self.help_spec = _has(self.short_name)
        self.is_required = required
        self.a_label = label

class MyTextAreaField(wt.TextAreaField):
    "La mia versione del TextAreaField"
    def __init__(self, label, required, *f, **kw):
        super().__init__(label, *f, **kw)
        self.help_spec = _has(self.short_name)
        self.is_required = required
        self.a_label = label

class MySelectMultipleField(wt.SelectMultipleField):
    "La mia versione del SelectMultipleField"
    def __init__(self, label, required, *f, **kw):
        super().__init__(label, *f, **kw)
        self.help_spec = _has(self.short_name)
        self.is_required = required
        self.a_label = label

class MySelectField(wt.SelectField):
    "La mia versione del SelectField"
    def __init__(self, label, required, *f, **kw):
        super().__init__(label, *f, **kw)
        self.help_spec = _has(self.short_name)
        self.is_required = required
        self.a_label = label

ATTACH_BUTTON = '<td><input type="image" name="%s" src="/files/attach.png" border="0" '\
                'alt="Allega" style="width: 20px;" /></td><td> %s %s</td></tr>\n'

class MyAttachField(wt.Field):
    "Field per attachments"
    def set(self, choices):
        "Imposta scelte del menù"
        self.choices = choices             #pylint: disable=W0201

    def __call__(self, **_unused):
        "rendering del form"
        ret = "<table><tr>"
        for atch in self.choices:
            if atch[2] == cs.ALL_SPEC:
                spec = (atch[0], atch[1], "&nbsp;(<input type=text name=sigla_ditta size=5>)")
            else:
                spec = (atch[0], atch[1], "&nbsp;")
            ret += ATTACH_BUTTON % spec
        return Markup(ret+"</table>")

class MyFormField(wt.FormField):
    "La mia versione del FormField"
    def __init__(self, fclass, label, required, *f, **kw):
        super().__init__(fclass, *f, **kw)
        self.errlist = []
        self.help_spec = None
        self.is_required = required
        self.a_label = label

    def validate(self, *_unused):
        "Validazione modificata"
        _debug('MyFormField.validate')
        if not self.form.validate():
            self.errlist.extend(self.form.errlist)
        return len(self.errlist) == 0

class MyFieldList(wt.FieldList):
    "FieldList, versione mia"
    def __init__(self, fclass, label, required, *f, **kw):
        super().__init__(fclass, *f, **kw)
        self.errlist = []
        self.help_spec = None
        self.is_required = required
        self.a_label = label

    def renderme(self, **kw):
        "rendering del form"
        for item in self:
            return render_field(item, **kw)

class FormWErrors(wt.Form):
    "Form modificato per gestione errori"
    def __init__(self, *f, **w):
        super().__init__(*f, **w)
        self.errlist = []

    def get_errors(self):
        "Riporta elenco errori"
        return self.errlist

class MyUpload(FormWErrors):
    "Form per upload di files"
    upload_file = wt.FileField('Aggiungi allegato', [wt.validators.Optional()])
    tipo_allegato = MyAttachField()
    sigla_ditta = wt.StringField('')

    def __init__(self, choices, *p, **kw):
        super().__init__(*p, **kw)
        self.tipo_allegato.set(choices)

class ImportoPiuIva(wt.Form):
    "Form per importo più I.V.A."
    importo = wt.StringField(render_kw={'size': 8})
    iva = wt.StringField(render_kw={'size': 2})
    descrizione = wt.StringField("", render_kw={'size': 30})

    def __init__(self, *pargs, **kwargs):
        super().__init__(*pargs, **kwargs)

    def __call__(self, **_unused):
        "Rendering del form"
        ret = Markup('<td>')+self.descrizione()+Markup('</td><td align=right>')+ \
              self.importo()+Markup('&nbsp;</td><td align=right>')+self.iva()+Markup('&nbsp;</td>')
        return ret

    def validate(self, *_unused1, **_unused2):
        "Validazione dati"
        if self.importo.data:    # campo importo specificato
            try:
                self.importo.data = f'{float(self.importo.data):.2f}'
            except ValueError:
                return False
        else:                    # Campo importo bianco
            if self.iva.data:
                return False
            return True
        if self.iva.data:        # campo IVA specificato
            try:
                self.iva.data = f'{int(self.iva.data)}'
            except ValueError:
                return False
        return True

class Costo(FormWErrors):
    "Form per costo del bene"
    valuta = wt.SelectField("Valuta", choices=cs.MENU_VALUTA)
    voce_1 = wt.FormField(ImportoPiuIva)
    voce_2 = wt.FormField(ImportoPiuIva)
    voce_3 = wt.FormField(ImportoPiuIva)
    voce_4 = wt.FormField(ImportoPiuIva)
    voce_5 = wt.FormField(ImportoPiuIva)

    def __init__(self, *pargs, **kwargs):
        super().__init__(*pargs, **kwargs)
        self.v_importo = 0
        self.v_iva = 0
        self.v_totale = 0

    def renderme(self, **_unused):
        "Rendering del form"
        ret = Markup('&nbsp;&nbsp; Valuta: ')+self.valuta()+Markup('\n<table>')
        ret += Markup('<r><td> &nbsp; </td><td align=center>Descrizione</td>')
        ret += Markup('<td align=center> Importo </td><td align=center> I.V.A. % </td></tr>\n')
        ret += Markup('<tr><td>voce&nbsp;1:</td>')+self.voce_1.form()+Markup('</tr>\n')
        ret += Markup('<tr><td>voce&nbsp;2:</td>')+self.voce_2.form()+Markup('</tr>\n')
        ret += Markup('<tr><td>voce&nbsp;3:</td>')+self.voce_3.form()+Markup('</tr>\n')
        ret += Markup('<tr><td>voce&nbsp;4:</td>')+self.voce_4.form()+Markup('</tr>\n')
        ret += Markup('<tr><td>voce&nbsp;5:</td>')+self.voce_5.form()+Markup('</tr>\n')
        ret += Markup('</table>\n')
#       ret += Markup('<tr><td>')+Markup(f'<b>Totale<b></td><td><b>{self.totale:.2f}</b></td></tr>')
        return ret

    def validate(self, *_unused1, **_unused2):
        "Validazione del form"
        self.errlist = []
        if not self.voce_1.validate(self):
            self.errlist.append('Errore alla voce 1')
        if not self.voce_2.validate(self):
            self.errlist.append('Errore alla voce 2')
        if not self.voce_3.validate(self):
            self.errlist.append('Errore alla voce 3')
        if not self.voce_4.validate(self):
            self.errlist.append('Errore alla voce 4')
        if not self.voce_5.validate(self):
            self.errlist.append('Errore alla voce 5')
        return len(self.errlist) == 0

class MyLoginForm(FormWErrors):
    "Form per login"
    userid = wt.StringField('Username')
    password = wt.PasswordField('Password')

    def __init__(self, thedir, us, pw, ldap_host, ldap_port, **kwargs):    #pylint: disable=R0913
        "Costruttore"
        self._dd = thedir
        self._us = us
        self._pw = pw
        self._ldap_host = ldap_host
        self._ldap_port = ldap_port
        super().__init__(**kwargs)

    def validate(self, extra_validators=None):
        "Validazione specifica"
        if not self.userid.data:
            self.errlist.append("Devi specificare il nome utente")
        if not self.password.data:
            self.errlist.append("Devi specificare la password")
        return len(self.errlist) == 0

    def password_ok(self):
        "Verifica password"
        return ft.authenticate(self._us, self._pw, self._ldap_host, self._ldap_port)

class NominaRUP(FormWErrors):
    'Form per nomina RUP'
    email_rup = MySelectField('', True, [])
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __call__(self):
        "rendering del form"
        html = B_TRTD+render_field(self.email_rup, size=15)+E_TRTD
        html += B_TRTD+self.T_annulla()+NBSP+self.T_avanti()+E_TRTD
        return html

class ProgettoAcquisto(FormWErrors):
    "Form per richiesta acquisto"
    data_richiesta = MyTextField('Data richiesta (g/m/aaaa)', True)
    descrizione_acquisto = MyTextField('Descrizione', True)
    descrizione_ordine = MyTextAreaField('Descrizione per ordine '\
                                         '(Solo se diversa dalla precedente)', False)
    motivazione_acquisto = MyTextAreaField('Motivazione acquisto', True)
    lista_codf = MySelectMultipleField('Codice Fondo', True,
                                       [wt.validators.InputRequired("Manca codice Fu.Ob.")])
    email_responsabile = MySelectField('Responsabile', True,
                                       [wt.validators.InputRequired("Manca responsabile acquisto")])
    modalita_acquisto = MyRadioField('Modalit&agrave; di acquisto', True,
                                     choices=cs.MENU_MOD_ACQ,
                                     widget=radio_widget)
    criterio_assegnazione = MyRadioField("Criterio di assegnazione", True,
                                         choices=cs.MENU_CRIT_ASS,
                                         widget=radio_widget)
    giustificazione = MyTextAreaField('Giustificazione procedura', True)
    fornitore_nome = MyTextField('Denominazione fornitore', True)
    fornitore_sede = MyTextField('Indirizzo fornitore', True)
    fornitore_codfisc = MyTextField('Codice Fiscale', True)
    fornitore_partiva = MyTextField('Partita Iva', True)
    rif_offerta = MyTextField('Riferimento offerta', True)
    costo = MyFormField(Costo, 'Costo del bene', True)
    oneri_sicurezza = MyFormField(ImportoPiuIva, "Oneri sicurezza", True)
    newform = wt.HiddenField()

    note_richiesta = MyTextAreaField('Note', False, [wt.validators.Optional()])
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __call__(self):
        "rendering del form"
        html = B_TRTD+render_field(self.data_richiesta, sameline=True, size=15)+E_TRTD
        html += B_TRTD+render_field(self.modalita_acquisto)+E_TRTD
        if self.modalita_acquisto.data is not None and self.modalita_acquisto.data != 'None':
            html += B_TRTD+render_field(self.descrizione_acquisto, size=50)+E_TRTD
#           if self.modalita_acquisto.data in (INFER_5000, SUPER_5000,
#                                              INFER_1000, SUPER_1000, PROC_NEG):
#               html += B_TRTD+render_field(self.descrizione_ordine, rows=3, cols=80)+E_TRTD
#           if self.modalita_acquisto.data in (SUPER_5000, SUPER_1000, PROC_NEG):
#               html += B_TRTD+render_field(self.giustificazione, rows=3, cols=80)+E_TRTD
            html += B_TRTD+render_field(self.motivazione_acquisto, rows=10, cols=80)+E_TRTD
            pop =popup(fk.url_for('vedicodf'),
                       'Vedi lista Codici fondi e responsabili', size=(1100, 900))
            html += B_TRTD+Markup(f'<div align=right> &rightarrow; {pop}</div>')
            html += render_field(self.email_responsabile, sameline=True)
            html += BRK+render_field(self.lista_codf)+E_TRTD

#           if self.modalita_acquisto.data not in (RDO_MEPA, PROC_NEG, MANIF_INT):
            if True:               # provvisoriamente al posto delle linea sopra
                html += B_TRTD+render_field(self.fornitore_nome, size=50)+BRK
                html += render_field(self.fornitore_sede, sep='', size=50)+BRK
                html += render_field(self.fornitore_codfisc)+BRK
                html += render_field(self.fornitore_partiva)+E_TRTD
#               html += render_field(self.rif_offerta, sep='', size=50)+E_TRTD
            html += B_TRTD+render_field(self.costo, sameline=True)+E_TRTD

#           if self.modalita_acquisto.data in (RDO_MEPA, PROC_NEG):
#               html += B_TRTD+render_field(self.criterio_assegnazione)+E_TRTD
#               html += B_TRTD+render_field(self.oneri_sicurezza)+E_TRTD
            html += B_TRTD+render_field(self.note_richiesta, rows=10, cols=80)+E_TRTD
        html += B_TRTD+self.T_annulla()+NBSP+self.T_avanti()+E_TRTD
        html += self.newform()
        return html

    def validate(self, extra_validators=None):                                   #pylint: disable=R0912
        if not ft.date_to_time(self.data_richiesta.data):
            self.errlist.append("Errore specifica data")
        if not self.descrizione_acquisto.data:
            self.errlist.append("Manca descrizione acquisto")
        if not self.motivazione_acquisto.data:
            self.errlist.append("Manca motivazione acquisto")
#       if not self.rif_offerta.data:
#           self.errlist.append("Manca il riferimento all'offerta")
        if not self.lista_codf.data:
            self.errlist.append("Manca codice Fu.Ob.")
        if not self.email_responsabile.data:
            self.errlist.append("Manca responsabile acquisto")
        if not self.modalita_acquisto.data:
            self.errlist.append("Specificare modalit&agrave; di acquisto")
#       if not self.giustificazione.data and self.modalita_acquisto.data == SUPER_5000:
#           self.errlist.append('Manca giustificazione per '\
#                               'affidamento diretto ed importo sup. a 5000 €')
#       if not self.giustificazione.data and self.modalita_acquisto.data == SUPER_1000:
#           self.errlist.append('Manca giustificazione per '\
#                               'affidamento diretto ed importo sup. a 1000 €')
#       if self.modalita_acquisto.data not in (RDO_MEPA, PROC_NEG, MANIF_INT):
#           if not (self.fornitore_nome.data and self.fornitore_sede.data):
#               self.errlist.append("Dati fornitore incompleti")
        if not self.costo.validate():
            self.errlist.append("Costo: "+", ".join(self.costo.errlist))
#       if self.modalita_acquisto.data == RDO_MEPA:
#           if self.criterio_assegnazione.data not in (PREZ_PIU_BASSO, OFF_PIU_VANT):
#               self.errlist.append("Specificare criterio di assegnazione")
#           if not self.oneri_sicurezza.validate():
#               self.errlist.append("Oneri sicurezza: "+", ".join(self.oneri_sicurezza.errlist))
        return len(self.errlist) == 0

class Decisione(FormWErrors):
    "form per definizione decisione di contrarre"
    numero_decisione = MyTextField('Numero decisione', True,
                                   [wt.validators.InputRequired("Manca numero decisione")])
    data_decisione = MyTextField('Data (g/m/aaaa)', True,
                                 [wt.validators.Optional("Manca data decisione")])
    capitolo = MyTextField('Capitolo', True,
                           [wt.validators.InputRequired("Manca indicazione capitolo")])
    numero_cup = MyTextField('CUP', True, [wt.validators.InputRequired()])
    numero_cig = MyTextField('CIG', True, [wt.validators.InputRequired()])
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __call__(self, d_prat):
        "rendering del form"
        html = B_TRTD+Markup(f'Richiesta del {d_prat[cs.DATA_RICHIESTA]}. '\
                                f'Resp.Fondi: {d_prat[cs.NOME_RESPONSABILE]}. '\
                                f'Richiedente: {d_prat[cs.NOME_RICHIEDENTE]}')
        html += Markup(f'<p><b>{d_prat[cs.DESCRIZIONE_ACQUISTO]}')+E_TRTD
        html += B_TRTD+render_field(self.numero_decisione)+BRK
        html += render_field(self.data_decisione)+BRK
        html += B_TRTD+Markup(f"Fu. Ob.: {d_prat[cs.STR_CODF]}<p>")
        html += render_field(self.capitolo)+BRK
        html += render_field(self.numero_cup)+BRK
        html += render_field(self.numero_cig)+BRK
        html += B_TRTD+self.T_annulla()+NBSP+self.T_avanti()+E_TRTD
        return html

    def validate(self, extra_validators=None):
        "Validazione specifica per il form"
        if not self.numero_decisione.data:
            self.errlist.append("Manca numero decisione")
        if not self.data_decisione.data:
            self.errlist.append("Manca data decisione")
        if not self.capitolo.data:
            self.errlist.append("Manca indicazione capitolo")
        if not self.numero_cup.data:
            self.errlist.append("Manca indicazione numero CUP")
        if not self.numero_cig.data:
            self.errlist.append("Manca indicazione numero CIG")
        return len(self.errlist) == 0

class DeterminaB(FormWErrors):
    "form per definizione determina fase B"
    numero_determina_b = MyTextField('Numero determina', True,
                                     [wt.validators.InputRequired("Manca numero determina")])
    data_determina_b = MyTextField('Data (g/m/aaaa)', True,
                                   [wt.validators.Optional("Manca data determina")])
    nome_direttore_b = MyTextField('Direttore', True,
                                   [wt.validators.Optional("Manca nome direttore")])
    art_2 = MyTextAreaField('Testo per articolo 2', False)
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __init__(self, *pw, vincitore=False, **kw):
        super().__init__(*pw, **kw)
        self._vinc = vincitore

    def __call__(self, d_prat):
        "rendering del form"
        html = B_TRTD+Markup(f'Richiesta del {d_prat[cs.DATA_RICHIESTA]}. '\
                                f'Resp.Fondi: {d_prat[cs.NOME_RESPONSABILE]}. '\
                                f'Richiedente: {d_prat[cs.NOME_RICHIEDENTE]}')
        html += Markup(f'<p><b>{d_prat[cs.DESCRIZIONE_ACQUISTO]}')+E_TRTD
        html += B_TRTD+render_field(self.numero_determina_b)+BRK
        html += render_field(self.data_determina_b)+BRK
        html += render_field(self.nome_direttore_b)+E_TRTD
        html += B_TRTD+Markup(f"<b>Modalità acquisto:</b> {d_prat[cs.STR_MOD_ACQ]}<br>")
        html += Markup(f"<b>Criterio di assegnazione:</b> {d_prat[cs.STR_CRIT_ASS]}<br>")
        html += Markup(f"<b>Codici Fondi:</b> {d_prat[cs.STR_CODF]}<br>")
        html += Markup(f"<b>Capitolo:</b> {d_prat[cs.CAPITOLO]}<br>")
        cup = d_prat.get(cs.CUP).strip()
        if cup:
            html += Markup(f"<b>CUP:</b> {cup}<br>")
        html += Markup(f"<b>RUP:</b> {d_prat[cs.RUP]}<br>")
        if self._vinc:
            html += Markup(f"<b>Vincitore:</b> {d_prat[cs.VINCITORE][cs.NOME_DITTA]} "\
                              f"- {d_prat[cs.VINCITORE][cs.SEDE_DITTA]}")+E_TRTD
        else:
            html += Markup('<b>Vincitore:</b> nessun vincitore')+E_TRTD
            html += B_TRTD+render_field(self.art_2, cols=100)+E_TRTD
        html += B_TRTD+self.T_annulla()+NBSP+self.T_avanti()+E_TRTD
        return html

    def validate(self, extra_validators=None):
        "Validazione specifica per il form"
        if not self.numero_determina_b.data:
            self.errlist.append("Manca numero determina")
        if not self.data_determina_b.data:
            self.errlist.append("Manca data determina")
        if not self.nome_direttore_b.data:
            self.errlist.append("Manca nome direttore")
        return len(self.errlist) == 0

class Ordine(FormWErrors):
    "form per definizione ordine"
    lingua_ordine = MySelectField('', True, choices=(('IT', 'Italiano'), ('EN', 'Inglese')))
    numero_ordine = MyTextField('Numero ordine', True,
                                [wt.validators.InputRequired("Manca numero ordine")])
    data_ordine = MyTextField('Data (g/m/aaaa)', True,
                              [wt.validators.InputRequired("Manca data ordine")])
    descrizione_ordine = MyTextAreaField('Descrizione', True,
                                         [wt.validators.InputRequired("Manca descrizione ordine")])
    costo_ordine = MyFormField(Costo, "Costo per Ordine", True)
    cig = MyTextField('CIG', True, [wt.validators.InputRequired("Manca specifica CIG")])
    note_ordine = MyTextAreaField('Note', False, [wt.validators.Optional()])

    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __call__(self, d_prat):
        "rendering del form"
        html = B_TRTD+Markup(f'Richiesta del {d_prat[cs.DATA_RICHIESTA]}. '\
                                f'Resp.Fondi: {d_prat[cs.NOME_RESPONSABILE]}. '\
                                f'Richiedente: {d_prat[cs.NOME_RICHIEDENTE]}')
        html += Markup(f'<p><b>{d_prat[cs.DESCRIZIONE_ACQUISTO]}')
        html += Markup(f'<p>Presso la ditta:<blockquote>{d_prat[cs.FORNITORE_NOME]}<br>'\
                          f'{d_prat[cs.FORNITORE_SEDE]}</blockquote>')+E_TRTD
        html += B_TRTD+Markup('<table width=100%><tr><td align=left>')+ \
                    render_field(self.numero_ordine)+Markup('</td>')
        html += Markup('<td align=right>')+render_field(self.lingua_ordine)+ \
                          E_TRTD+Markup('</table></br>')
        html += render_field(self.data_ordine)+BRK
        html += render_field(self.cig)+E_TRTD
        html += B_TRTD+render_field(self.descrizione_ordine, rows=3, cols=80)+E_TRTD
        html += B_TRTD+self.costo_ordine.renderme()+E_TRTD
        html += B_TRTD+render_field(self.note_ordine, rows=10, cols=80)+E_TRTD
        html += B_TRTD+self.T_annulla()+NBSP+self.T_avanti()+E_TRTD
        return html

    def validate(self, extra_validators=None):
        "Validazione specifica per il form"
        if not self.numero_ordine.data:
            self.errlist.append("Manca numero ordine")
        if not self.data_ordine.data:
            self.errlist.append("Manca data ordine")
        if not self.descrizione_ordine.data:
            self.errlist.append("Manca descrizione ordine")
        if not self.costo_ordine.validate():
            self.errlist.append("Costoper ordine: "+", ".join(self.costo_ordine.errlist))
        if not self.cig.data:
            self.errlist.append("Manca specifica CIG")
        return len(self.errlist) == 0

class AggiornaFormato(FormWErrors):
    "Classe per aggiornamento formato pratiche vers.0/1"
    nuovo_costo = MyFormField(Costo, "Costo", True)
    nuova_modalita_acquisto = MyRadioField('Modalit&agrave; di acquisto', True,
                                           choices=cs.MENU_MOD_ACQ,
                                           widget=radio_widget)
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __call__(self, d_prat):
        "rendering del form"
        html = B_TRTD+Markup('Vedi richiesta originale: <a href=/vedifile/richiesta.pdf>'\
                'richiesta.pdf</a>')+E_TRTD
        html += B_TRTD+Markup('Costo: '+d_prat.get("costo", ""))+BRK+ \
                render_field(self.nuovo_costo)+E_TRTD
        html += B_TRTD+render_field(self.nuova_modalita_acquisto)+E_TRTD
        html += B_TRTD+self.T_annulla()+NBSP+self.T_avanti()+E_TRTD
        return html

class TrovaPratica(FormWErrors):
    "form per ricerca pratiche"
    trova_prat_aperta = MySelectField('Stato pratica: ', False,
                                      choices=((-1, 'Tutte'), (1, 'Aperta'), (0, 'Chiusa')))
    trova_richiedente = MyTextField('Richiedente: ', False)
    trova_responsabile = MyTextField('Responsabile: ', False)
    trova_anno = MySelectField('Anno: ', False)
    trova_parola = MyTextField('Parola nella descrizione: ', False)
    elenco_ascendente = MyBooleanField('Ordine ascendente', False)
    T_avanti = wt.SubmitField('Trova', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __call__(self):
        "Rendering del form"
        html = B_TRTD+render_field(self.trova_prat_aperta, sameline=True)+BRK+BRK
        html += render_field(self.trova_richiedente, sameline=True)+BRK+BRK
        html += render_field(self.trova_responsabile, sameline=True)+BRK+BRK
        html += render_field(self.trova_anno, sameline=True)+BRK+BRK
        html += render_field(self.trova_parola, sameline=True)+BRK+BRK
        html += render_field(self.elenco_ascendente, sameline=True)+E_TRTD
        html += B_TRTD+self.T_annulla()+NBSP+self.T_avanti()+E_TRTD
        return html

B_TD = Markup("<td>")
E_TD = Markup("</td>")

class Ditta(FormWErrors):
    "form per singola ditta"
    nome_ditta = MyTextField('', True)
    sede_ditta = MyTextField('', True)
    codfisc_ditta = MyTextField('', True)
    partiva_ditta = MyTextField('', True)
    vincitore = wt.BooleanField()
    T_cancella = wt.BooleanField()

    def __call__(self, **_unused):
        "Rendering del form"
        html = B_TD+render_field(self.nome_ditta)+E_TD
        html += B_TD+render_field(self.sede_ditta)+E_TD
        html += B_TD+Markup('Cod.Fisc.: ')+render_field(self.codfisc_ditta)+E_TD
        html += B_TD+Markup('Part.IVA: ')+render_field(self.partiva_ditta)+E_TD
        if hasattr(self, "offerta"):
            html += B_TD+self.offerta()+E_TD
        html += B_TD+self.vincitore()+E_TD
        html += B_TD+self.T_cancella()+E_TD
        return html

class DittaExt(Ditta):
    "Form per ditta con offerta"
    offerta = wt.BooleanField()

def new_lista_ditte(label, m_entries=5):
    "Instanzia una lista ditte con dato numero di campi"
    return MyFieldList(wt.FormField(Ditta), label, True, min_entries=m_entries)

class PraticaRDO(FormWErrors):
    "form per specifiche della pratica RDO"
    inizio_gara = MyTextField('Data inizio (g/m/aaaa)', True)
    fine_gara = MyTextField('Data/ora fine (g/m/aaaa ora:min)', True)
    lista_ditte = new_lista_ditte("Elenco ditte che hanno presentato offerta")
    prezzo_gara = MyFormField(Costo, "Prezzo di gara", True)
    oneri_sic_gara = MyFormField(ImportoPiuIva, "Oneri sicurezza", True)
    T_more = wt.SubmitField("+Ditte")
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __init__(self, *pw, **kw):
        super().__init__(*pw, **kw)
        self.min_entries = 2

    def __call__(self, **kw):
        "Rendering del form"
        html = B_TRTD+render_field(self.inizio_gara)+BRK
        html += render_field(self.fine_gara)+E_TRTD
        html += B_TRTD+Markup(f"<b>{self.lista_ditte.a_label}</b><br>")
        html += Markup("<table border=1><tr><th>n.</th><th>Denominazione</th>"\
                          "<th>Indirizzo</th><th>Vincitore</th><th>"\
                          "<img src=/files/del-20.png></th></tr></td></tr>")
        for idx, ditta in enumerate(self.lista_ditte):
            html += B_TRTD+Markup(f"{(idx+1)}</td>")+ \
                                     ditta.renderme(number=idx, **kw)+Markup("</tr>")
        html += E_TRTD+Markup("</table><br>")
        html += Markup("<div align=right>")+self.T_more()+Markup("</div>")+E_TRTD
        html += B_TRTD+render_field(self.prezzo_gara)
        html += BRK+render_field(self.oneri_sic_gara)+E_TRTD
        html += B_TRTD+self.T_annulla()+NBSP+self.T_avanti()+E_TRTD
        return html

    def increment(self):
        "Incrementa numero di ditte"
        self.lista_ditte.append_entry()
        self.lista_ditte.append_entry()

    def validate(self, extra_validators=None):
        "Validazione"
        tt0 = ft.date_to_time(self.inizio_gara.data)
        if tt0 is None:
            self.errlist.append("Errore data inzio (usa formato: g/m/a)")
        tt1 = None
        if len(self.fine_gara.data.split()) == 2:
            tt1 = ft.date_to_time(self.fine_gara.data)
        if tt1 is None:
            self.errlist.append("Errore data/ora fine (usa formato: g/m/a o:m)")
        if tt0 and tt1:
            if tt1-tt0 < 86400:
                self.errlist.append("Date inizio e fine inconsistenti")
        if len(self.lista_ditte.data) < 1:
            self.errlist.append("Manca elenco ditte")
        n_vinc = 0      # Conta numero di vincitori
        for ditta in self.lista_ditte:
            if ditta.vincitore.data:
                n_vinc += 1
        if n_vinc > 1:
            self.errlist.append("E' ammesso un solo vincitore")
        return not self.errlist

class CodfForm(FormWErrors):
    "Modulo per modifica codici fondi"
    Codice = MyTextField('Codice', True)
    Titolo = MyTextField('Titolo', True)
    CUP = MyTextField('CUP', False)
    email_Responsabile = MySelectField('Responsabile', True)

    Commenti = MyTextAreaField('Commenti', False)
    avanti = wt.SubmitField('Avanti')
    annulla = wt.SubmitField('Annulla')
    cancella = wt.SubmitField('Cancella record')

    def validate(self, extra_validators=None):
        "Validazione"
        ret = True
        if not self.Codice.data:
            self.errlist.append("Il codice è obbligatorio")
            ret = False
        if not self.Titolo.data:
            self.errlist.append("Devi specificare un titolo")
            ret = False
        if not self.email_Responsabile.data:
            self.errlist.append("Devi specificare un responsabile")
            ret = False
        return ret

class UserForm(FormWErrors):
    "Form per modifica dati utente"
    userid = MyTextField('username',
                         [wt.validators.Optional()])
    name = MyTextField('Nome',
                       [wt.validators.Optional()])
    surname = MyTextField('Cognome',
                          [wt.validators.Optional()])

    email = MyTextField('e-mail', True, [wt.validators.Email()])
    amministratore = MyBooleanField('Funzioni di amministrazione', False)
    avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])
    cancella = wt.SubmitField('Cancella record', [wt.validators.Optional()])

    def validate(self, extra_validators=None):
        "Validazione"
        if not (self.userid.data and self.name.data \
                and self.surname.data and self.email.data):
            self.errlist.append("Devi specificare tutti i campi richesti")
            return False
        return True
