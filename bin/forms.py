"""
Definizione forms per procedura acquisti
"""

import wtforms as wt
import flask as fk

import ftools as ft
from constants import *

__version__ = "1.4"
__date__ = "20/10/2019"
__author__ = "Luca Fini"

def radio_widget(field, **kwargs):
    "La mia versione del RadioWidget"
    kwargs.setdefault('type', 'radio')
    field_id = kwargs.pop('id', field.id)
    html = []
    for value, label, checked in field.iter_choices():
        choice_id = '%s-%s'%(field_id, value)
        options = dict(kwargs, name=field.name, value=value, id=choice_id)
        if checked:
            options['checked'] = 'checked'
        html.append('<input %s />'%ft.html_params(options))
        html.append('<label for="%s">%s</label><br>'%(field_id, label))
    return ''.join(html)

def _has(hspec):
    if hspec in ft.HELPLIST:
        return 'help_'+hspec+'.html'
    return ''

def popup(url, text, args=None, size=(700, 500)):
    "Genera codice HTML per popup"
    full_url = url.copy()
    if args:
        aux = []
        for item in args.items():
            aux.append("%s=%s"%tuple(item))
        full_url += "?"+"&".join(args)
    return '<a href="%s"  onclick="window.open(\'%s\', \'newwindow\', \'width=%d, height=%d, '\
           'scrollbars=yes\'); return false;">%s</a>'%(full_url, full_url, size[0], size[1], text)

def render_field(field, **kw):
    "Rendering di un campo"
    if field.help_spec:
        help_url = '/files/%s'%field.help_spec
        hlink = popup(help_url, '<sup><img src=/files/qm-12.png></sup>', size=(640, 480))
    else:
        hlink = ''
    if field.is_required:
        lab = '<dt><u>%s</u>%s</dt>'%(str(field.a_label), hlink)
    else:
        lab = '<dt>%s%s</dt>'%(str(field.a_label), hlink)
    if isinstance(field, MyFormField):
        ret = field.form.renderme(**kw)
    else:
        ret = field(**kw)
    return lab+ret

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

class MyTextField(wt.TextField):
    "La mia versione del TextField"
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
        self.choices = choices

    def __call__(self, *_unused):
        ret = "<table><tr>"
        for atch in self.choices:
            if atch[2] == ALL_SPEC:
                spec = (atch[0], atch[1], "&nbsp;(<input type=text name=sigla_ditta size=5>)")
            else:
                spec = (atch[0], atch[1], "&nbsp;")
            ret += ATTACH_BUTTON % spec
        return ret+"</table>"

class MyFormField(wt.FormField):
    "La mia versione del FormField"
    def __init__(self, fclass, label, required, *f, **kw):
        super().__init__(fclass, *f, **kw)
        self.errlist = []
        self.help_spec = None
        self.is_required = required
        self.a_label = label

    def __call__(self, **kw):
        return render_field(self, **kw)

    def validate(self, *_unused):
        "Validazione modificata"
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

    def __call__(self, **kw):
        for item in self:
            return render_field(item, **kw)

class MyForm(wt.Form):
    "Ridefinizione form per supporto help"
    def _render_field(self, field, **kw):
        if field.help_spec:
            help_url = '/files/%s' % field.help_spec
            hlink = popup(help_url, '<sup><img src=/files/qm-12.png></sup>', size=(640, 480))
        else:
            hlink = ''
        ret = field(hlink, **kw)
        if not ret:
            if field.is_required:
                lab = '<dt><u>%s</u>%s</dt>' % (field.label, hlink)
            else:
                lab = '<dt>%s%s</dt>' % (field.label, hlink)
            ret = lab+'<dd> %s </dd>' % field(**kw)
        return ret

class ModifiedForm(wt.Form):
    "Form modificato per gestione errori"
    def __init__(self, *f, **w):
        super().__init__(*f, **w)
        self.errlist = []

    def get_errors(self):
        "Riporta elenco errori"
        return self.errlist

class MyUpload(ModifiedForm):
    "Form per upload di files"
    upload_file = wt.FileField('Aggiungi allegato', [wt.validators.Optional()])
    tipo_allegato = MyAttachField()
    sigla_ditta = wt.TextField('')

    def __init__(self, choices, *p, **kw):
        super().__init__(*p, **kw)
        self.tipo_allegato.set(choices)

class ImportoPiuIva(ModifiedForm):
    "Form per importo più I.V.A."
    importo = wt.TextField("Importo", [wt.validators.Optional()])
    valuta = wt.SelectField("Valuta", choices=MENU_VALUTA)
    iva = wt.SelectField("Iva", choices=MENU_IVA)
    iva_free = wt.TextField("", [wt.validators.Optional()])

    def validate(self, *_unused1, **_unused2):
        "Validazione dati"
        if not ft.is_number(self.importo.data):
            self.errlist.append("errore specifica importo")
#       if self.iva.data == IVA_NO:
#           if not self.iva_free.data:
#               self.errlist.append("errore specifica I.V.A.")
        return len(self.errlist) == 0

    def renderme(self, **_unused):
        "Rendering del form"
        return self.importo(size=8)+self.valuta()+self.iva()+self.iva_free()

class CostoPiuTrasporto(ModifiedForm):
    "Form per costo+trasporto"
    costo = wt.FormField(ImportoPiuIva)
    modo_trasp = wt.SelectField('', choices=MENU_TRASPORTO)
    costo_trasporto = wt.FormField(ImportoPiuIva)

    def validate(self, *_unused1, **_unused2):
        "Validazione del form"
        self.costo.form.validate()
        self.errlist.extend(self.costo.form.errlist)
        if self.modo_trasp.data == "spec" and not self.costo_trasporto.validate(self):
            self.errlist.append("errore spese di trasporto")
        return len(self.errlist) == 0

    def renderme(self, **_unused):
        "Rendering del form"
        ret = "&nbsp;&nbsp;&nbsp;Importo: "+self.costo.renderme()+"<br />\n"
        ret += "Trasporto: "+self.modo_trasp()+"<br />\n"
        ret += "&nbsp;&nbsp;&nbsp;&nbsp;"+self.costo_trasporto.renderme()
        return ret

class MyLoginForm(ModifiedForm):
    "Form per login"
    userid = wt.TextField('Username')
    password = wt.PasswordField('Password')

    def __init__(self, thedir, us, pw, ldap_host, ldap_port, **kwargs):
        "Costruttore"
        self._dd = thedir
        self._us = us
        self._pw = pw
        self._ldap_host = ldap_host
        self._ldap_port = ldap_port
        super().__init__(**kwargs)

    def validate(self):
        "Validazione specifica"
        if not self.userid.data:
            self.errlist.append("Devi specificare il nome utente")
        if not self.password.data:
            self.errlist.append("Devi specificare la password")
        return len(self.errlist) == 0

    def password_ok(self):
        "Verifica password"
        return ft.authenticate(self._us, self._pw, self._ldap_host, self._ldap_port)

class RichiestaAcquisto(ModifiedForm):
    "Form per richiesta acquisto"
    data_richiesta = MyTextField('Data richiesta (g/m/aaaa)', True)
    descrizione_acquisto = MyTextField('Descrizione', True)
    descrizione_ordine = MyTextAreaField('Descrizione per ordine '\
                                         '(Solo se diversa dalla precedente)', False)
    motivazione_acquisto = MyTextAreaField('Motivazione acquisto', True)
    lista_codf = MySelectMultipleField('Codice Fondo', True,
                                       [wt.validators.InputRequired("Manca codice fondo")])
    email_responsabile = MySelectField('Responsabile', True,
                                       [wt.validators.InputRequired("Manca responsabile acquisto")])
    modalita_acquisto = MyRadioField('Modalit&agrave; di acquisto', True,
                                     choices=MENU_MOD_ACQ,
                                     widget=radio_widget)
    criterio_assegnazione = MyRadioField("Criterio di assegnazione", True,
                                         choices=MENU_CRIT_ASS,
                                         widget=radio_widget)
    giustificazione = MyTextAreaField('Giustificazione procedura', True)
    nome_fornitore = MyTextField('Denominazione fornitore', True)
    ind_fornitore = MyTextField('Indirizzo fornitore', True)
    costo = MyFormField(CostoPiuTrasporto, "Costo presunto", True)
    oneri_sicurezza = MyFormField(ImportoPiuIva, "Oneri sicurezza", True)
    newform = wt.HiddenField()

    note_richiesta = MyTextAreaField('Note', False, [wt.validators.Optional()])
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def validate(self):
        if not ft.date_to_time(self.data_richiesta.data):
            self.errlist.append("Errore specifica data")
        if not self.descrizione_acquisto.data:
            self.errlist.append("Manca descrizione acquisto")
        if not self.motivazione_acquisto.data:
            self.errlist.append("Manca motivazione acquisto")
        if not self.lista_codf.data:
            self.errlist.append("Manca codice fondo")
        if not self.email_responsabile.data:
            self.errlist.append("Manca responsabile acquisto")
        if not self.modalita_acquisto.data:
            self.errlist.append("Specificare modalit&agrave; di acquisto")
        if not self.giustificazione.data and self.modalita_acquisto.data == SUPER_5000:
            self.errlist.append('Manca giustificazione per '\
                                'affidamento diretto ed importo sup. a 5000 €')
        if not self.giustificazione.data and self.modalita_acquisto.data == SUPER_1000:
            self.errlist.append('Manca giustificazione per '\
                                'affidamento diretto ed importo sup. a 1000 €')
        if self.modalita_acquisto.data not in (RDO_MEPA, PROC_NEG, MANIF_INT):
            if not (self.nome_fornitore.data and self.ind_fornitore.data):
                self.errlist.append("Dati fornitore incompleti")
        if not self.costo.validate():
            self.errlist.append("Costo: "+", ".join(self.costo.errlist))
        if self.modalita_acquisto.data == RDO_MEPA:
            print("DEBUG:", self.criterio_assegnazione.data)
            if self.criterio_assegnazione.data not in (PREZ_PIU_BASSO, OFF_PIU_VANT):
                self.errlist.append("Specificare criterio di assegnazione")
#           if not self.oneri_sicurezza.validate():
#               self.errlist.append("Oneri sicurezza: "+", ".join(self.oneri_sicurezza.errlist))
        return len(self.errlist) == 0

    def renderme(self):
        "rendering del form"
        html = ['<tr><td>'+(render_field(self.data_richiesta, size=15)+'</td></tr>')]
        html.append('<tr><td>'+render_field(self.modalita_acquisto))
        html.append('</td></tr>')

        if self.modalita_acquisto.data != 'None':
            html.append('<tr><td>'+render_field(self.descrizione_acquisto,
                                                size=50)+'</td></tr>')
            if self.modalita_acquisto.data in (INFER_5000, SUPER_5000,
                                               INFER_1000, SUPER_1000, PROC_NEG):
                html.append('<tr><td>'+render_field(self.descrizione_ordine,
                                                    rows=3, cols=80)+'</td></tr>')
            if self.modalita_acquisto.data in (SUPER_5000, SUPER_1000, PROC_NEG):
                html.append('<tr><td>'+render_field(self.giustificazione,
                                                    rows=3, cols=80)+'</td></tr>')
            html.append('<tr><td>'+render_field(self.motivazione_acquisto,
                                                rows=10, cols=80)+'</td></tr>')
            html.append('<tr><td>'+'<div align=right> &rightarrow; %s</div>'% \
                        popup(fk.url_for('vedicodf'),
                              'Vedi lista Codici fondi e responsabili', size=(1100, 900)))
            html.append(render_field(self.email_responsabile))
            html.append('<br>'+render_field(self.lista_codf)+'</td></tr>')

            if self.modalita_acquisto.data not in (RDO_MEPA, PROC_NEG, MANIF_INT):
                html.append('<tr><td>'+render_field(self.nome_fornitore, size=50)+'<br>')
                html.append(render_field(self.ind_fornitore, sep='', size=50)+'</td></tr>')
            html.append('<tr><td>'+render_field(self.costo))
            html.append('</td></tr>')

            if self.modalita_acquisto.data in (RDO_MEPA, PROC_NEG):
                html.append('<tr><td>'+render_field(self.criterio_assegnazione)+'</tr></td>')
                html.append('<tr><td>'+render_field(self.oneri_sicurezza))
                html.append('</td></tr>')
            html.append('<tr><td>'+render_field(self.note_richiesta, rows=10, cols=80)+'</td></tr>')
        html.append('<tr><td>' + self.T_annulla() + ' &nbsp; ' + self.T_avanti() +'</td></tr>')
        html.append(self.newform())
        return '\n'.join(html)

class DeterminaA(ModifiedForm):
    "form per definizione determina fase A"
    numero_determina = MyTextField('Numero determina', True,
                                   [wt.validators.InputRequired("Manca numero determina")])
    data_determina = MyTextField('Data (g/m/aaaa)', True,
                                 [wt.validators.Optional("Manca data determina")])
    nome_direttore = MyTextField('Direttore', True,
                                 [wt.validators.Optional("Manca nome direttore")])
    capitolo = MyTextField('Capitolo', True,
                           [wt.validators.InputRequired("Manca indicazione capitolo")])
    cup = MyTextField('CUP', False, [wt.validators.Optional()])
    email_rup = MySelectField('RUP', True,
                              [wt.validators.InputRequired("Manca indicazione RUP")])
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def validate(self):
        "Validazione specifica per il form"
        if not self.numero_determina.data:
            self.errlist.append("Manca numero determina")
        if not self.data_determina.data:
            self.errlist.append("Manca data determina")
        if not self.nome_direttore.data:
            self.errlist.append("Manca nome direttore")
        if not self.capitolo.data:
            self.errlist.append("Manca indicazione capitolo")
        if not self.email_rup.data:
            self.errlist.append("Manca indicazione RUP")
        return len(self.errlist) == 0

    def renderme(self, dati_pratica):
        "rendering del form"
        html = ['<tr><td>Richiesta del %(data_richiesta)s. Resp.Fondi:'\
                '%(nome_responsabile)s. Richiedente: %(nome_richiedente)s' % dati_pratica]
        html.append('<p><b>%(descrizione_acquisto)s</td></tr>' % dati_pratica)
        html.append('<tr><td>'+render_field(self.numero_determina)+'<br>')
        html.append(render_field(self.data_determina)+'<br>')
        html.append(render_field(self.nome_direttore)+'</td></tr><tr><td>')
        html.append("Codici Fondi: %s<p>" % dati_pratica[STR_CODF])
        html.append(render_field(self.capitolo)+'<br>')
        html.append(render_field(self.cup)+'<br>')
        html.append(render_field(self.email_rup)+'</td></tr><tr><td>')
        html.append('<tr><td>'+self.T_annulla()+' &nbsp; '+self.T_avanti() +'</td></tr>')
        return '\n'.join(html)

class DeterminaB(ModifiedForm):
    "form per definizione determina fase B"
    numero_determina_b = MyTextField('Numero determina', True,
                                     [wt.validators.InputRequired("Manca numero determina")])
    data_determina_b = MyTextField('Data (g/m/aaaa)', True,
                                   [wt.validators.Optional("Manca data determina")])
    nome_direttore_b = MyTextField('Direttore', True,
                                   [wt.validators.Optional("Manca nome direttore")])
#   modalita_acquisto_b = MyRadioField('Modalit&agrave; di acquisto', True,
#                                      choices=MENU_MOD_ACQ_B,
#                                      widget=radio_widget)
#   criterio_assegnazione = MyRadioField("Criterio di assegnazione", True,
#                                        choices=MENU_CRIT_ASS,
#                                        widget=radio_widget)
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def validate(self):
        "Validazione specifica per il form"
        if not self.numero_determina_b.data:
            self.errlist.append("Manca numero determina")
        if not self.data_determina_b.data:
            self.errlist.append("Manca data determina")
        if not self.nome_direttore_b.data:
            self.errlist.append("Manca nome direttore")
#       if not self.modalita_acquisto_b.data:
#           self.errlist.append("Devi specificare la modalità di acquisto")
#       if not self.criterio_assegnazione.data:
#           self.errlist.append("Devi specificare il criterio di assegnazione")
        return len(self.errlist) == 0

    def renderme(self, dati_pratica):
        "rendering del form"
        html = ['<tr><td>Richiesta del %(data_richiesta)s. Resp.Fondi: '\
                '%(nome_responsabile)s. Richiedente: %(nome_richiedente)s' % dati_pratica]
        html.append('<p><b>%(descrizione_acquisto)s</td></tr>' % dati_pratica)
        html.append('<tr><td>'+render_field(self.numero_determina_b)+'<br>')
        html.append(render_field(self.data_determina_b)+'<br>')
        html.append(render_field(self.nome_direttore_b)+'</td></tr><tr><td>')
        html.append("<b>Modalità acquisto:</b> %s<br>" % dati_pratica[STR_MOD_ACQ])
        html.append("<b>Criterio di assegnazione:</b> %s<br>" % dati_pratica[STR_CRIT_ASS])
        html.append("<b>Codici Fondi:</b> %s<br>" % dati_pratica[STR_CODF])
        html.append("<b>Capitolo:</b> %s<br>"%dati_pratica[CAPITOLO])
        cup = dati_pratica.get(CUP).strip()
        if cup:
            html.append("<b>CUP:</b> %s<br>"%cup)
        html.append("<b>RUP:</b> %s"%dati_pratica[RUP]+'</td></tr><tr><td>')
        html.append('<tr><td>'+self.T_annulla()+' &nbsp; '+self.T_avanti() +'</td></tr>')
        return '\n'.join(html)

class Ordine(ModifiedForm):
    "form per definizione ordine"
    lingua_ordine = MySelectField('', True, choices=(('IT', 'Italiano'), ('EN', 'Inglese')))
    numero_ordine = MyTextField('Numero ordine', True,
                                [wt.validators.InputRequired("Manca numero ordine")])
    data_ordine = MyTextField('Data (g/m/aaaa)', True,
                              [wt.validators.InputRequired("Manca data ordine")])
    descrizione_ordine = MyTextAreaField('Descrizione', True,
                                         [wt.validators.InputRequired("Manca descrizione ordine")])
    costo_ordine = MyFormField(CostoPiuTrasporto, "Costo per Ordine", True)
    cig = MyTextField('CIG', True, [wt.validators.InputRequired("Manca specifica CIG")])
    note_ordine = MyTextAreaField('Note', False, [wt.validators.Optional()])

    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def validate(self):
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

    def renderme(self, dati_pratica):
        "rendering del form"
        html = ['<tr><td>Richiesta del %(data_richiesta)s. Resp.Fondi: '\
                '%(nome_responsabile)s. Richiedente: %(nome_richiedente)s' % dati_pratica]
        html.append('<p><b>%(descrizione_acquisto)s</b></p>' % dati_pratica)
        html.append('<p>Presso la ditta:<blockquote>%(nome_fornitore)s<br>'\
                    '%(ind_fornitore)s</blockquote></td></tr>' % dati_pratica)
        html.append('<tr><td><table width=100%><tr><td align=left>'+ \
                    render_field(self.numero_ordine)+'</td>')
        html.append('<td align=right>'+render_field(self.lingua_ordine)+'</td></tr></table></br>')
        html.append(render_field(self.data_ordine)+'<br>')
        html.append(render_field(self.cig)+'</td></tr>')
        html.append('<tr><td>'+render_field(self.descrizione_ordine, rows=3, cols=80)+'</td></tr>')
        html.append('<tr><td>'+self.costo_ordine.renderme()+'</td></tr>')
        html.append('<tr><td>'+render_field(self.note_ordine, rows=10, cols=80)+'</td></tr>')
        html.append('<tr><td>'+self.T_annulla()+' &nbsp; '+self.T_avanti() + '</td></tr>')
        return '\n'.join(html)

class AggiornaFormato(ModifiedForm):
    "Classe per aggiornamento formato pratiche vers.0/1"
    nuovo_costo = MyFormField(CostoPiuTrasporto, "Costo", True)
    nuova_modalita_acquisto = MyRadioField('Modalit&agrave; di acquisto', True,
                                           choices=MENU_MOD_ACQ,
                                           widget=radio_widget)
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def renderme(self, dati_pratica):
        "rendering del form"
        html = ['<tr><td> Vedi richiesta originale: <a href=/vedifile/richiesta.pdf>'\
                'richiesta.pdf</a> </td></tr>']
        html.append('<tr><td> Costo: '+dati_pratica.get("costo", "")+'<br>'+ \
                    render_field(self.nuovo_costo)+'</td></tr>')
        html.append('<tr><td>'+render_field(self.nuova_modalita_acquisto) +'</tr></td>')
        html.append('<tr><td>'+self.T_annulla()+' &nbsp; '+self.T_avanti()+'</tr></td>')
        return '\n'.join(html)

class TrovaPratica(ModifiedForm):
    "form per ricerca pratiche"
    trova_prat_aperta = MySelectField('Stato pratica', False,
                                      choices=((-1, 'Tutte'), (1, 'Aperta'), (0, 'Chiusa')))
    trova_email_rich = MySelectField('Richiedente', False)
    trova_email_resp = MySelectField('Responsabile', False)
    trova_anno = MySelectField('Anno', False)
    trova_parola = MyTextField('Parola', False)
    elenco_ascendente = MyBooleanField('Ordine ascendente', False)
    T_avanti = wt.SubmitField('Trova', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def renderme(self):
        "Rendering del form"
        html = []
        html.append('<tr><td>'+render_field(self.trova_prat_aperta)+'<br>')
        html.append(render_field(self.trova_email_rich)+'<br>')
        html.append(render_field(self.trova_email_resp)+'<br>')
        html.append(render_field(self.trova_anno)+'<br>')
        html.append(render_field(self.trova_parola)+'<br>')
        html.append(render_field(self.elenco_ascendente)+'</td></tr>')
        html.append('<tr><td>' + self.T_annulla() + ' &nbsp; ' + self.T_avanti() +'</tr></td>')
        return '\n'.join(html)

class Ditta(ModifiedForm):
    "form per singola ditta"
    nome_ditta = MyTextField('', True)
    sede_ditta = MyTextField('', True)
    offerta = wt.BooleanField()
    vincitore = wt.BooleanField()

    def renderme(self, **kw):
        "Rendering del form"
        html = []
        html.append("<td>"+render_field(self.nome_ditta)+"</td>")
        html.append("<td>"+render_field(self.sede_ditta)+"</td>")
        html.append("<td>"+self.offerta()+"</td>")
        html.append("<td>"+self.vincitore()+"</td>")
        return "".join(html)

def newListaDitte(m_entries=5):
    return MyFieldList(wt.FormField(Ditta), "Elenco ditte", True, min_entries=m_entries)

class PraticaRDO(ModifiedForm):
    "form per specifiche della pratica RDO"
    inizio_gara = MyTextField('Data inizio (g/m/aaaa)', True)
    fine_gara = MyTextField('Data/ora fine (g/m/aaaa ora:min)', True)
    lista_ditte = newListaDitte()
    prezzo_gara = MyFormField(CostoPiuTrasporto, "Prezzo di gara", True)
    oneri_sic_gara = MyFormField(ImportoPiuIva, "Oneri sicurezza", True)
    T_more = wt.SubmitField("+Ditte")
    T_avanti = wt.SubmitField('Avanti', [wt.validators.Optional()])
    T_annulla = wt.SubmitField('Annulla', [wt.validators.Optional()])

    def __init__(self, *pw, **kw):
        ModifiedForm.__init__(self, *pw, **kw)
        self.min_entries = 2

    def increment(self):
        "Incrementa numero di ditte"
        self.lista_ditte.append_entry()
        self.lista_ditte.append_entry()

    def renderme(self, **kw):
        "Rendering del form"
        html = ["<tr><td>"]
        html.append(render_field(self.inizio_gara)+"<br>")
        html.append(render_field(self.fine_gara))
        html.append("</td></tr>")
        html.append("<tr><td><b>Elenco ditte</b><br>")
        html.append("<table border=1><tr><th>n.</th><th>Denominazione</th>"\
                    "<th>Indirizzo</th><th>Offerta</th><th>Vincitore</th></tr></td></tr>")
        for idx, ditta in enumerate(self.lista_ditte):
            html.append("<tr><td>%d</td>"%(idx+1)+ditta.renderme(**kw)+"</tr>")
        html.append("</td></tr></table><br>")
        html.append("<div align=right>"+self.T_more()+"</div></td></tr>")
        html.append('<tr><td>'+render_field(self.prezzo_gara))
        html.append('<br>'+render_field(self.oneri_sic_gara)+'</td></tr>')
        html.append('<tr><td>' + self.T_annulla() + ' &nbsp; ' + self.T_avanti() +'</tr></td>')
        return '\n'.join(html)

    def validate(self):
        "Validazione"
        tt0 = ft.date_to_time(self.inizio_gara.data)
        tt1 = ft.date_to_time(self.fine_gara.data)
        if tt0 is None:
            self.errlist.append("Errore data inzio (usa formato: g/m/a)")
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
