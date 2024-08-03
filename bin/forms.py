"""
Definizione forms per procedura acquisti
"""

import wtforms as wt
import flask as fk
from markupsafe import Markup

import ftools as ft
import constants as cs

__version__ = "2.4"
__date__ = "22/05/2024"
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
    for item in field.iter_choices():
        value, label, checked = item[:3]
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
        return not self.errlist

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
    inbase = wt.BooleanField(default=True, render_kw={'checked': ''})
    importo = wt.StringField(render_kw={'size': 8})
    iva = wt.StringField(render_kw={'size': 2})
    descrizione = wt.StringField("", render_kw={'size': 30})

    def __call__(self, show_ck=True, **_unused):
        "Rendering del form"
#       _debug(f'Rendering di ImportoPiuIva(show_ck:{show_ck})')
        ckstr = self.inbase() if show_ck else ''
        ret = Markup('<td>')+ckstr+self.descrizione()+Markup('</td><td align=right>')+ \
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

class _Costo(FormWErrors):
    "Form per costo del bene"
    valuta = wt.SelectField("Valuta", choices=cs.MENU_VALUTA)
    voce_1 = wt.FormField(ImportoPiuIva)
    voce_2 = wt.FormField(ImportoPiuIva)
    voce_3 = wt.FormField(ImportoPiuIva)
    voce_4 = wt.FormField(ImportoPiuIva)
    voce_5 = wt.FormField(ImportoPiuIva)

    def _renderme(self, show_ck):
        "Rendering del form"
        ret = Markup('&nbsp;&nbsp; Valuta: ')+self.valuta()+Markup('\n<table>')
        ret += Markup('<r><td> &nbsp; </td><td align=center>Descrizione</td>')
        ret += Markup('<td align=center> Importo </td><td align=center> I.V.A. % </td></tr>\n')
        ret += Markup('<tr><td>voce&nbsp;1:</td>')+self.voce_1.form(show_ck)+Markup('</tr>\n')
        ret += Markup('<tr><td>voce&nbsp;2:</td>')+self.voce_2.form(show_ck)+Markup('</tr>\n')
        ret += Markup('<tr><td>voce&nbsp;3:</td>')+self.voce_3.form(show_ck)+Markup('</tr>\n')
        ret += Markup('<tr><td>voce&nbsp;4:</td>')+self.voce_4.form(show_ck)+Markup('</tr>\n')
        ret += Markup('<tr><td>voce&nbsp;5:</td>')+self.voce_5.form(show_ck)+Markup('</tr>\n')
        ret += Markup('</table>\n')
        if show_ck:
            ret += Markup('Togliere la spunta alle voci che non contribuiscono ' \
                          'al prezzo base di asta\n')
        return ret

    def renderme(self, **_unused):
        'Deve essere definita nel discendente'
        raise RuntimeError('Metodo non definito')

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
        return not self.errlist

class Costo1(_Costo):
    'Versione di costo senza checkbox'

    def renderme(self, **_unused):
        'render senza checknox'
        return super()._renderme(False)

class Costo2(_Costo):
    'Versione di costo con checkbox'

    def renderme(self, **_unused):
        'render con checknox'
        return super()._renderme(True)

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
        return not self.errlist

    def password_ok(self):
        "Verifica password"
        return ft.authenticate(self._us, self._pw, self._ldap_host, self._ldap_port)

class Rollback(FormWErrors):
    'Form per nomina RUP'
    annulla = wt.SubmitField('Annulla', [])
    conferma = wt.SubmitField('Conferma', [])

class IndicaRUP(FormWErrors):
    'Form per nomina RUP'
    email_rup = MySelectField('', True, [])
    interno_rup = MyTextField('Tel. Interno', True, [])
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __call__(self):
        "rendering del form"
        html = B_TRTD+render_field(self.email_rup, size=20)+BRK+BRK
        html += render_field(self.interno_rup, sameline=True, size=3)+E_TRTD
        html += B_TRTD+self.T_annulla()+NBSP+self.T_avanti()+E_TRTD
        return html

    def validate(self, *_unused):
        'validazione campi'
        if not self.email_rup.data:
            self.errlist.append("selezionare l'indirizzo e-mail del RUP")
        if not self.interno_rup.data:
            self.errlist.append("specificare il num.telefonico interno del RUP")
        return not self.errlist

class ProgettoAcquisto(FormWErrors):
    "Form per progetto di acquisto"
    data_pratica = MyTextField('Data pratica (g/m/aaaa)', True)
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
    costo_progetto = MyFormField(Costo1, 'Quadro economico', True)
    note_progetto = MyTextAreaField('Note', False, [wt.validators.Optional()])
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __call__(self):
        "rendering del form"
        html = B_TRTD+render_field(self.data_pratica, sameline=True, size=15)+E_TRTD
        html += B_TRTD+render_field(self.modalita_acquisto)+E_TRTD
        if self.modalita_acquisto.data is not None and self.modalita_acquisto.data != 'None':
            html += B_TRTD+render_field(self.descrizione_acquisto, size=50)+E_TRTD
            if self.modalita_acquisto.data == cs.INFER_5000:
                html += B_TRTD+render_field(self.descrizione_ordine, rows=5, cols=80)+E_TRTD
            html += B_TRTD+render_field(self.motivazione_acquisto, rows=10, cols=80)+E_TRTD
            pop =popup(fk.url_for('vedicodf'),
                       'Vedi lista Codici fondi e responsabili', size=(1100, 900))
            html += B_TRTD+Markup(f'<div align=right> &rightarrow; {pop}</div>')
            html += render_field(self.email_responsabile, sameline=True)
            html += BRK+render_field(self.lista_codf)+E_TRTD
            html += B_TRTD+render_field(self.fornitore_nome, size=50)+BRK
            html += render_field(self.fornitore_sede, sep='', size=50)+BRK
            html += render_field(self.fornitore_codfisc)+BRK
            html += render_field(self.fornitore_partiva)+E_TRTD
            html += B_TRTD+render_field(self.costo_progetto, sameline=True)+E_TRTD
            html += B_TRTD+render_field(self.note_progetto, rows=10, cols=80)+E_TRTD
        html += B_TRTD+self.T_annulla()+NBSP+self.T_avanti()+E_TRTD
        return html

    def validate(self, extra_validators=None):                                   #pylint: disable=R0912
        if not ft.date_to_time(self.data_pratica.data):
            self.errlist.append("Errore specifica data")
        if not self.descrizione_acquisto.data:
            self.errlist.append("Manca descrizione acquisto")
        if not self.motivazione_acquisto.data:
            self.errlist.append("Manca motivazione acquisto")
        if not self.lista_codf.data:
            self.errlist.append("Manca codice Fu.Ob.")
        if not self.email_responsabile.data:
            self.errlist.append("Manca responsabile acquisto")
        if not self.modalita_acquisto.data:
            self.errlist.append("Specificare modalità di acquisto")
        if not self.costo_progetto.validate():
            self.errlist.append("Costo: "+", ".join(self.costo_progetto.errlist))
        return not self.errlist

class Decisione(FormWErrors):
    "form per definizione decisione di contrarre"
    numero_decisione = MyTextField('Numero decisione', True,
                                   [wt.validators.InputRequired("Manca numero decisione")])
    data_decisione = MyTextField('Data (g/m/aaaa)', True,
                                 [wt.validators.Optional("Manca data decisione")])
    numero_cup = MyTextField('CUP', True, [wt.validators.Optional()])
    numero_cig = MyTextField('CIG', True, [wt.validators.Optional()])
    costo_rdo = MyFormField(Costo1, 'Quadro economico', True)
    capitolo = MyTextField('Capitolo', True,
                           [wt.validators.InputRequired("Manca indicazione capitolo")])
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __call__(self, d_prat):
        "rendering del form"
        html = B_TRTD+Markup(f'Pratica del {d_prat[cs.DATA_PRATICA]}. '\
                                f'Resp.Fondi: {d_prat[cs.NOME_RESPONSABILE]}. '\
                                f'Richiedente: {d_prat[cs.NOME_RICHIEDENTE]}')
        html += Markup(f'<p><b>{d_prat[cs.DESCRIZIONE_ACQUISTO]}')+E_TRTD
        html += B_TRTD+render_field(self.numero_decisione)+BRK
        if d_prat[cs.MOD_ACQUISTO] == cs.INFER_5000:
            html += render_field(self.numero_cig)+BRK
            html += render_field(self.numero_cup)+BRK
        html += render_field(self.data_decisione)+BRK
        html += B_TRTD+render_field(self.costo_rdo, sameline=True)+E_TRTD
        html += B_TRTD+Markup(f"Fu. Ob.: {d_prat[cs.STR_CODF]}<p>")
        html += render_field(self.capitolo)+BRK
        html += B_TRTD+self.T_annulla()+NBSP+self.T_avanti()+E_TRTD
        return html

    def validate(self, extra_validators=None):
        "Validazione specifica per il form"
        self.errlist = []
        if not self.numero_decisione.data:
            self.errlist.append("Manca numero decisione")
        if not self.data_decisione.data:
            self.errlist.append("Manca data decisione")
        if not self.capitolo.data:
            self.errlist.append("Manca indicazione capitolo")
        if extra_validators:
            if not self.numero_cig.data:
                self.errlist.append("Manca indicazione CIG")
            if not self.numero_cup.data:
                self.errlist.append("Manca indicazione CUP")
        return not self.errlist

class Ordine(FormWErrors):
    "form per definizione ordine"
    numero_ordine = MyTextField('Numero ordine', True, [])
    termine_giorni = MyTextField('Termine di esecuzione della prestazione (giorni)', True, [])
    descrizione_ordine = MyTextAreaField('Descrizione', True, [])
    note_ordine = MyTextAreaField('Note', False, [])

    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def validate(self, extra_validators=None):
        "Validazione specifica per il form"
        self.errlist = []
        if not self.numero_ordine.data:
            self.errlist.append("Manca numero ordine")
        if not self.termine_giorni.data:
            self.errlist.append("Manca indicazione termine di esecuzione")
        return not self.errlist

    def __call__(self, d_prat):
        "rendering del form"
        html = B_TRTD+Markup(f'Pratica del {d_prat[cs.DATA_PRATICA]}. '\
                             f'Resp.Fondi: {d_prat[cs.NOME_RESPONSABILE]}. '\
                             f'Richiedente: {d_prat[cs.NOME_RICHIEDENTE]}')
        html += Markup(f'''<p><b>Descrizione acquisto:</b>
        <blockquote>{d_prat[cs.DESCRIZIONE_ACQUISTO]}</blockquote>
        ''')
        html += Markup(f'''<p><b>Numero CIG:</b> {d_prat[cs.NUMERO_CIG]}<br>
        <b>Numero CUP:</b> {d_prat[cs.NUMERO_CUP]}
        ''')
        html += Markup(f'<p><b>Fornitore:</b><blockquote>{d_prat[cs.FORNITORE_NOME]}<br>'\
                          f'{d_prat[cs.FORNITORE_SEDE]}</blockquote>')+E_TRTD
        html += B_TRTD+ render_field(self.numero_ordine)+E_TRTD
        html += B_TRTD+ render_field(self.termine_giorni)+E_TRTD
        html += B_TRTD+render_field(self.descrizione_ordine, rows=3, cols=80)+E_TRTD
        html += B_TRTD+render_field(self.note_ordine, rows=10, cols=80)+E_TRTD
        html += B_TRTD+self.T_annulla()+NBSP+self.T_avanti()+E_TRTD
        return html

class AnnullaPratica(FormWErrors):
    'Form per conferma annullamento pratica'
    motivazione_annullamento = MyTextField('Motivazione annullamento', True,
                              [wt.validators.InputRequired("Devi specificare la motivazione")])
    T_conferma = wt.SubmitField('Conferma', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __call__(self):
        "rendering del form"
        html = B_TRTD+render_field(self.motivazione_annullamento, size=30, sameline=True)+BRK+BRK
        html += B_TRTD+self.T_annulla()+NBSP+self.T_conferma()+E_TRTD
        return html

class TrovaPratica(FormWErrors):
    "form per ricerca pratiche"
    trova_prat_aperta = MySelectField('Stato pratica: ', False,
                                      choices=((-1, 'Tutte'), (0, 'Aperta'),
                                               (1, 'Chiusa'), (2, 'Annullata')))
    trova_richiedente = MyTextField('Richiedente: ', False)
    trova_responsabile = MyTextField('Responsabile: ', False)
    trova_rup = MyTextField('RUP: ', False)
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
        html += render_field(self.trova_rup, sameline=True)+BRK+BRK
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

class RdO(FormWErrors):
    "form per specifiche per la generazione di RdO"
    numero_cup = MyTextField('CUP', True, [wt.validators.InputRequired()])
    numero_cig = MyTextField('CIG', True, [wt.validators.InputRequired()])
    costo_rdo = MyFormField(Costo2, 'Quadro economico', True)
    fine_gara = MyTextField('Data scadenza presentazione offerta (g/m/aaaa)', True)
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __call__(self, **kw):
        "Rendering del form"
        html = B_TRTD+render_field(self.numero_cup)+BRK
        html += render_field(self.numero_cig)+BRK
        html += B_TRTD+render_field(self.fine_gara)+E_TRTD
        html += B_TRTD+render_field(self.costo_rdo, sameline=True)+E_TRTD
        html += B_TRTD+self.T_annulla()+NBSP+self.T_avanti()+E_TRTD
        return html

    def validate(self, extra_validators=None):
        "Validazione"
        tt0 = ft.date_to_time(self.fine_gara.data)
        if not self.numero_cup.data:
            self.errlist.append("Manca indicazione numero CUP")
        if not self.numero_cig.data:
            self.errlist.append("Manca indicazione numero CIG")
        if tt0 is None:
            self.errlist.append("Errore data fine_gara (usa formato: g/m/a)")
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
        if not self.Codice.data:
            self.errlist.append("Il codice è obbligatorio")
        if not self.Titolo.data:
            self.errlist.append("Devi specificare un titolo")
        if not self.email_Responsabile.data:
            self.errlist.append("Devi specificare un responsabile")
        return not self.errlist

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
