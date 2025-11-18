"""
Definizione forms per procedura acquisti
"""

# pylint: disable=C0302

import wtforms as wt
import flask as fk
from markupsafe import Markup

import ftools as ft
import constants as cs

__version__ = "2.11"
__date__ = "18/6/2025"
__author__ = "Luca Fini"


class DEBUG:  # pylint: disable=R0903
    "debug flag"
    enable = False


def debug_enable(enable=True):
    "abilita/disabilita printout di debug"
    DEBUG.enable = enable


def _debug(*f):
    print("DBG FORMS>", *f)


def radio_widget(field, **kwargs):
    "La mia versione del RadioWidget"
    kwargs.setdefault("type", "radio")
    field_id = kwargs.pop("id", field.id)
    html = []
    for item in field.iter_choices():
        value, label, checked = item[:3]
        choice_id = f"{field_id}-{value}"
        options = dict(kwargs, name=field.name, value=value, id=choice_id)
        if checked:
            options["checked"] = "checked"
        html.append(f"<input {ft.html_params(options)} />")
        html.append(f'<label for="{field_id}">{label}</label><br>')
    return "".join(html)


def _has(hspec):
    if hspec in ft.GlobLists.HELPLIST:
        return "help_" + hspec + ".html"
    return ""


def popup(url, text, size=(700, 500)):
    "Genera codice HTML per popup"
    return (
        f"<a href=\"{url}\"  onclick=\"window.open('{url}', 'newwindow', 'width={size[0]}, "
        f"height={size[1]}, scrollbars=yes'); return false;\">{text}</a>"
    )


def render_field(field, sameline=False, **kw):
    "Rendering di un campo"
    if field.help_spec:
        help_url = Markup(f"/files/{field.help_spec}")
        hlink = popup(
            help_url, "<sup><img src=/files/qm-12.png></sup>", size=(640, 480)
        )
    else:
        hlink = ""
    if sameline:
        sep = "&nbsp;&nbsp;&nbsp;"
    else:
        sep = "<br />"
    if field.is_required:
        lab = Markup(f"<u>{field.a_label:s}</u>{hlink}{sep}")
    else:
        lab = Markup(f"{field.a_label}{hlink}{sep}")
    if isinstance(field, MyFormField):
        return lab + Markup(field.form.renderme(**kw))
    return lab + Markup(field(**kw))


B_TRTD = Markup("<tr><td>")
E_TRTD = Markup("</td></tr>\n")
BRK = Markup("<br />\n")
PAR = Markup("<p>\n")
NBSP = Markup(" &nbsp; ")
NBSP4 = Markup("&nbsp;&nbsp;&nbsp;&nbsp;")


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


class MyRadioFieldOneLine(MyRadioField):
    "Rendering su una sola linea"

    def __call__(self, **kwargs):
        "Rendering del field"
        field_id = kwargs.pop("id", self.id)
        html = []
        for num, item in enumerate(self.iter_choices()):
            value, label, checked = item[:3]
            choice_id = f"{field_id}-{num}"
            options = {
                "name": self.name,
                "value": value,
                "id": choice_id,
                "type": "radio",
            }
            if checked:
                options["checked"] = "checked"
            html.append(f"<input {ft.html_params(options)} /> {label}&nbsp;&nbsp;")
        return " ".join(html)


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


ATTACH_BUTTON = (
    '<td><input type="image" name="%s" src="/files/attach.png" border="0" '
    'alt="Allega" style="width: 20px;" /></td><td> %s %s</td></tr>\n'
)


class MyAttachField(wt.Field):
    "Field per attachments"

    def set(self, choices):
        "Imposta scelte del menù"
        self.choices = choices  # pylint: disable=W0201

    def __call__(self, **_unused):
        "rendering del form"
        ret = "<table><tr>"
        for atch in self.choices:
            if atch[2] == cs.ALL_SPEC:
                spec = (
                    atch[0],
                    atch[1],
                    "&nbsp;(<input type=text name=sigla_ditta size=5>)",
                )
            else:
                spec = (atch[0], atch[1], "&nbsp;")
            ret += ATTACH_BUTTON % spec
        return Markup(ret + "</table>")


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
        _debug("MyFormField.validate")
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
    upload_file = wt.FileField("Aggiungi allegato", [wt.validators.Optional()])
    tipo_allegato = MyAttachField()
    sigla_ditta = wt.StringField("")

    def __init__(self, choices, *p, **kw):
        super().__init__(*p, **kw)
        self.tipo_allegato.set(choices)


class ImportoPiuIva(wt.Form):
    "Form per importo più I.V.A."
    inbase = wt.BooleanField(default=True, render_kw={"checked": ""})
    importo = wt.StringField(render_kw={"size": 8})
    iva = wt.StringField(render_kw={"size": 2})
    nota_iva = wt.StringField(render_kw={"size": 15})
    descrizione = wt.StringField("", render_kw={"size": 30})

    def __call__(self, show_ck=True, **_unused):
        "Rendering del form"
        #       _debug(f'Rendering di ImportoPiuIva(show_ck:{show_ck})')
        ckstr = self.inbase() if show_ck else ""
        ret = (
            Markup("<td>")
            + ckstr
            + self.descrizione()
            + Markup("</td><td align=right>")
            + self.importo()
            + Markup("&nbsp;</td><td align=right>")
            + self.iva()
            + Markup("</td><td align=right>")
            + self.nota_iva()
            + Markup("&nbsp;</td>")
        )
        return ret

    def validate(self, *_unused1, **_unused2):
        "Validazione dati"
        if self.importo.data:  # campo importo specificato
            try:
                self.importo.data = f"{float(self.importo.data):.2f}"
            except ValueError:
                return False
        else:  # Campo importo bianco
            if self.iva.data:
                return False
            return True
        if self.iva.data:  # campo IVA specificato
            try:
                self.iva.data = f"{int(self.iva.data)}"
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
        ret = (
            Markup("&nbsp;&nbsp; Valuta: ")
            + self.valuta()
            + Markup("\n<table>")
            + Markup("<r><td> &nbsp; </td><td align=center>Descrizione</td>")
            + Markup("<td align=center> Importo </td><td align=center> I.V.A. % </td>")
            + Markup("<td align=center> Nota</tr>\n")
            + Markup("<tr><td>voce&nbsp;1:</td>")
            + self.voce_1.form(show_ck)
            + Markup("</tr>\n")
            + Markup("<tr><td>voce&nbsp;2:</td>")
            + self.voce_2.form(show_ck)
            + Markup("</tr>\n")
            + Markup("<tr><td>voce&nbsp;3:</td>")
            + self.voce_3.form(show_ck)
            + Markup("</tr>\n")
            + Markup("<tr><td>voce&nbsp;4:</td>")
            + self.voce_4.form(show_ck)
            + Markup("</tr>\n")
            + Markup("<tr><td>voce&nbsp;5:</td>")
            + self.voce_5.form(show_ck)
            + Markup("</tr>\n")
            + Markup("</table>\n")
        )
        if show_ck:
            ret += Markup(
                "Togliere la spunta alle voci che non contribuiscono "
                "al prezzo base di asta\n"
            )
        return ret

    def renderme(self, **_unused):
        "Deve essere definita nel discendente"
        raise RuntimeError("Metodo non definito")

    def validate(self, *_unused1, **_unused2):
        "Validazione del form"
        self.errlist = []
        if not self.voce_1.validate(self):
            self.errlist.append("Errore alla voce 1")
        if not self.voce_2.validate(self):
            self.errlist.append("Errore alla voce 2")
        if not self.voce_3.validate(self):
            self.errlist.append("Errore alla voce 3")
        if not self.voce_4.validate(self):
            self.errlist.append("Errore alla voce 4")
        if not self.voce_5.validate(self):
            self.errlist.append("Errore alla voce 5")
        return not self.errlist


class Costo1(_Costo):
    "Versione di costo senza checkbox"

    def renderme(self, **_unused):
        "render senza checbnox"
        return super()._renderme(False)


class Costo2(_Costo):
    "Versione di costo con checkbox"

    def renderme(self, **_unused):
        "render con checknox"
        return super()._renderme(True)


class MyLoginForm(FormWErrors):
    "Form per login"
    userid = wt.StringField("Username")
    password = wt.PasswordField("Password")

    def __init__(  # pylint: disable=R0917
        self, thedir, us, pw, ldap_host, ldap_port, **kwargs
    ):  # pylint: disable=R0913
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
    "Form per nomina RUP"
    annulla = wt.SubmitField("Annulla", [])
    conferma = wt.SubmitField("Conferma", [])


class IndicaRUP(FormWErrors):
    "Form per nomina RUP"
    email_rup = MySelectField("", True, [])
    interno_rup = MyTextField("Tel. Interno", True, [])
    rup_firma_vicario = MyBooleanField("Firma il Direttore Vicario", False)
    T_avanti = wt.SubmitField("Avanti", [wt.validators.Optional()])
    T_annulla = wt.SubmitField("Annulla", [wt.validators.Optional()])

    def __call__(self):
        "rendering del form"
        html = (
            B_TRTD
            + render_field(self.email_rup, size=20)
            + BRK
            + BRK
            + render_field(self.interno_rup, sameline=True, size=3)
            + E_TRTD
            + B_TRTD
            + render_field(self.rup_firma_vicario, sameline=True)
            + E_TRTD
            + B_TRTD
            + self.T_annulla()
            + NBSP
            + self.T_avanti()
            + E_TRTD
        )
        return html

    def validate(self, *_unused):
        "validazione campi"
        if not self.email_rup.data:
            self.errlist.append("selezionare l'indirizzo e-mail del RUP")
        if not self.interno_rup.data:
            self.errlist.append("specificare il num.telefonico interno del RUP")
        return not self.errlist


class ProgettoAcquisto(FormWErrors):
    "Form per progetto di acquisto"
    cig_master = MyTextField("CIG Master", True)
    data_pratica = MyTextField("Data pratica (g/m/aaaa)", True)
    descrizione_acquisto = MyTextField("Descrizione", True)
    descrizione_ordine = MyTextAreaField(
        "Descrizione per ordine  (Solo se diversa dalla precedente)", False
    )
    motivazione_acquisto = MyTextAreaField("Motivazione acquisto", True)
    lista_codf = MySelectMultipleField(
        "Codice Fondo", True, [wt.validators.InputRequired("Manca codice Fu.Ob.")]
    )
    email_responsabile = MySelectField(
        "Responsabile",
        True,
        [wt.validators.InputRequired("Manca responsabile acquisto")],
    )
    modalita_acquisto = MyRadioField(
        "Modalit&agrave; di acquisto",
        True,
        choices=cs.MENU_MOD_ACQ,
        widget=radio_widget,
    )
    criterio_assegnazione = MyRadioField(
        "Criterio di assegnazione", True, choices=cs.MENU_CRIT_ASS, widget=radio_widget
    )
    guf_eu_num = MyTextField("Numero", True)
    guf_eu_data = MyTextField("Data pubblicazione su G.Uff EU", True)
    guf_it_num = MyTextField("Numero", True)
    guf_it_data = MyTextField("Data pubblicazione su G.Uff Ita.", True)
    convenzione = MyTextField("Convenzione", True)
    lotto = MyTextField("Lotto", True)
    tot_lotti = MyTextField("Numero Lotti", True)
    giustificazione = MyTextAreaField("Giustificazione procedura", True)
    fornitore_nome = MyTextField("Denominazione fornitore", True)
    fornitore_sede = MyTextField("Indirizzo fornitore", True)
    fornitore_codfisc = MyTextField("Codice Fiscale", True)
    fornitore_partiva = MyTextField("Partita Iva", True)
    costo_progetto = MyFormField(Costo1, "Quadro economico", True)
    note_progetto = MyTextAreaField("Note", False, [wt.validators.Optional()])
    T_avanti = wt.SubmitField("Avanti", [wt.validators.Optional()])
    T_annulla = wt.SubmitField("Annulla", [wt.validators.Optional()])

    def __call__(self):
        "rendering del form"
        html = (
            B_TRTD
            + render_field(self.data_pratica, sameline=True, size=15)
            + E_TRTD
            + B_TRTD
            + render_field(self.modalita_acquisto)
            + E_TRTD
        )
        if self.modalita_acquisto.data is not None:
            if self.modalita_acquisto.data in (cs.CONSIP, cs.ACC_QUADRO):
                html += (
                    B_TRTD
                    + render_field(self.cig_master, size=10, sameline=True)
                    + E_TRTD
                )
            html += B_TRTD + render_field(self.descrizione_acquisto, size=80) + E_TRTD
            if self.modalita_acquisto.data == cs.INFER_5000:
                html += (
                    B_TRTD
                    + render_field(self.descrizione_ordine, rows=5, cols=80)
                    + E_TRTD
                )
            html += (
                B_TRTD
                + render_field(self.motivazione_acquisto, rows=10, cols=80)
                + E_TRTD
            )
            pop = popup(
                fk.url_for("vedicodf"),
                "Vedi lista Codici fondi e responsabili",
                size=(1100, 900),
            )
            html += (
                B_TRTD
                + Markup(f"<div align=right> &rightarrow; {pop}</div>")
                + render_field(self.email_responsabile, sameline=True)
                + BRK
                + render_field(self.lista_codf)
                + E_TRTD
            )
            if self.modalita_acquisto.data != cs.GENERIC:
                if self.modalita_acquisto.data == cs.CONSIP:
                    html += (
                        B_TRTD
                        + Markup("<h4>Dati relativi alla convenzione Consip</h4>\n")
                        + render_field(self.convenzione, size=20, sameline=True)
                        + NBSP
                        + render_field(self.tot_lotti, size=10, sameline=True)
                        + NBSP
                        + render_field(self.lotto, size=10, sameline=True)
                        + PAR
                        + render_field(self.guf_it_data, size=10, sameline=True)
                        + NBSP
                        + render_field(self.guf_it_num, size=10, sameline=True)
                        + BRK
                        + render_field(self.guf_eu_data, size=10, sameline=True)
                        + NBSP
                        + render_field(self.guf_eu_num, size=10, sameline=True)
                        + E_TRTD
                    )
                html += (
                    B_TRTD
                    + render_field(self.fornitore_nome, size=80)
                    + PAR
                    + render_field(self.fornitore_sede, sep="", size=80)
                    + PAR
                    + render_field(self.fornitore_codfisc, sameline=True)
                    + BRK
                    + render_field(self.fornitore_partiva, sameline=True)
                    + E_TRTD
                    + B_TRTD
                    + render_field(self.costo_progetto, sameline=True)
                    + E_TRTD
                )
            html += B_TRTD + render_field(self.note_progetto, rows=10, cols=80) + E_TRTD
        html += B_TRTD + self.T_annulla() + NBSP + self.T_avanti() + E_TRTD
        return html

    def validate(self, extra_validators=None):  # pylint: disable=R0912
        if not self.modalita_acquisto.data:
            self.errlist.append("Specificare modalità di acquisto")
            return not self.errlist
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
        if self.modalita_acquisto.data == cs.GENERIC:
            return not self.errlist
        if not (
            self.fornitore_nome.data
            and self.fornitore_sede.data
            and self.fornitore_codfisc.data
            and self.fornitore_partiva.data
        ):
            self.errlist.append("dati fornitore incompleti")
        if not self.costo_progetto.validate():
            self.errlist.append("Costo: " + ", ".join(self.costo_progetto.errlist))
        return not self.errlist


class Proposta(FormWErrors):
    "form per definizione proposta di aggiudicazione"
    costo_rdo = MyFormField(Costo2, "Quadro economico", True)
    conferma_migliora = MyRadioFieldOneLine(
        "", False, choices=(("migliora", "migliora"), ("conferma", "conferma"))
    )
    T_avanti = wt.SubmitField("Avanti", [wt.validators.Optional()])
    T_annulla = wt.SubmitField("Annulla", [wt.validators.Optional()])

    def __call__(self, d_prat):
        "rendering del form"
        html = (
            B_TRTD
            + Markup(
                f"Pratica del {d_prat[cs.DATA_PRATICA]}. "
                f"Resp.Fondi: {d_prat[cs.NOME_RESPONSABILE]}. "
                f"Richiedente: {d_prat[cs.NOME_RICHIEDENTE]}"
            )
            + Markup(f"<p><b>{d_prat[cs.DESCRIZIONE_ACQUISTO]}")
            + E_TRTD
            + B_TRTD
            + render_field(self.costo_rdo, sameline=True)
            + E_TRTD
            + B_TRTD
            + Markup("L'offerta proposta ")
            + render_field(self.conferma_migliora, sameline=True)
            + Markup(" il quadro economico")
            + E_TRTD
            + B_TRTD
            + self.T_annulla()
            + NBSP
            + self.T_avanti()
            + E_TRTD
        )
        return html

    def validate(self, _):  # pylint: disable=W0222
        "Validazione specifica per il form"
        self.errlist = []
        if self.conferma_migliora.data not in ("migliora", "conferma"):
            self.errlist.append("Manca indicazione miglioramento/conferma")
        return not self.errlist


# Tabella informazioni variabili in funzione della modalità di acquisto
#
#                         PCP Mepa<40 mepa<143 ubuy<40 ubuy<143 acc.quad consip
# numero_decisione      -  X    X        X       X       X         X       X
# data_decisione        -  X    X        X       X       X         X       X
# data_negoziazione     -       X        X       X       X
# numero_negoziazione   -       X        X       X       X
# data_offerta          -       X        X       X       X
# numero_offerta        -       X        X       X       X
# data_scadenza         -       X        X       X       X
# data_protocollo_doc   -  X                                       X
# numero_protocollo_doc -  X                                       X


class Decisione(FormWErrors):
    "form per definizione decisione di contrarre"
    numero_decisione = MyTextField("Numero decisione", True)
    data_decisione = MyTextField("Data (g/m/aaaa)", True)
    ccnl = MyTextField("CCNL", False)
    data_negoziazione = MyTextField("Data di pubblicazione (g/m/aaaa)", True)
    numero_negoziazione = MyTextField("ID negoziazione", True)
    data_scadenza = MyTextField(
        "Data scadenza per presentazione offerta (g/m/aaaa)", True
    )
    data_offerta = MyTextField("Data offerta (g/m/aaaa)", True)
    numero_offerta = MyTextField("ID offerta", True)
    data_protocollo_doc = MyTextField("Data protocollo documentazione (g/m/aaaa)", True)
    numero_protocollo_doc = MyTextField("Numero protocollo documentazione", True)
    numero_cup = MyTextField("CUP", True, [wt.validators.Optional()])
#   numero_cig = MyTextField("CIG", True, [wt.validators.Optional()])
    capitolo = MyTextField(
        "Capitolo", True, [wt.validators.InputRequired("Manca indicazione capitolo")]
    )
    dec_firma_vicario = MyBooleanField("Firma il Direttore Vicario", False)
    T_avanti = wt.SubmitField("Avanti", [wt.validators.Optional()])
    T_annulla = wt.SubmitField("Annulla", [wt.validators.Optional()])

    def __call__(self, d_prat):
        "rendering del form"
        html = (
            B_TRTD
            + Markup(
                f"Pratica del {d_prat[cs.DATA_PRATICA]}. "
                f"Resp.Fondi: {d_prat[cs.NOME_RESPONSABILE]}. "
                f"Richiedente: {d_prat[cs.NOME_RICHIEDENTE]}"
            )
            + Markup(f"<p><b>{d_prat[cs.DESCRIZIONE_ACQUISTO]}")
            + E_TRTD
            + B_TRTD
        )
        if self.numero_decisione.data:
            html += render_field(self.numero_decisione, sameline=True) + NBSP4
            html += render_field(self.data_decisione, sameline=True) + BRK
        html += (
#           render_field(self.numero_cig, sameline=True) + BRK +
            render_field(self.numero_cup, sameline=True)
            + BRK
            + E_TRTD
        )
        if d_prat[cs.MOD_ACQUISTO] in (
            cs.TRATT_MEPA_40,
            cs.TRATT_MEPA_143,
            cs.TRATT_UBUY_40,
            cs.TRATT_UBUY_143,
        ):
            html += (
                B_TRTD
                + render_field(self.data_negoziazione, sameline=True)
                + NBSP4
                + render_field(self.numero_negoziazione, sameline=True)
                + PAR
                + render_field(self.data_scadenza, sameline=True)
                + PAR
                + render_field(self.data_offerta, sameline=True)
                + NBSP4
                + render_field(self.numero_offerta, sameline=True)
                + E_TRTD
            )
        if d_prat[cs.MOD_ACQUISTO] in (cs.INFER_5000, cs.ACC_QUADRO):
            html += (
                B_TRTD
                + render_field(self.data_protocollo_doc, sameline=True)
                + NBSP4
                + render_field(self.numero_protocollo_doc, sameline=True)
                + E_TRTD
            )
        html += (
            B_TRTD
            + Markup(f"Fu. Ob.: {d_prat[cs.STR_CODF]}<p>")
            + render_field(self.ccnl, sameline=True)
            + BRK
            + render_field(self.capitolo, sameline=True)
            + Markup("&nbsp;&nbsp;&nbsp;&nbsp;")
            + render_field(self.dec_firma_vicario, sameline=True)
            + E_TRTD
            + B_TRTD
            + self.T_annulla()
            + NBSP
            + self.T_avanti()
            + E_TRTD
        )
        return html

    def validate(self, d_prat):  # pylint: disable=W0237
        "Validazione specifica per il form"
        self.errlist = []
        #       if not self.numero_decisione.data:
        #           self.errlist.append("Manca numero decisione")
        #       if not self.data_decisione.data:
        #           self.errlist.append("Manca data decisione")
        if not self.capitolo.data:
            self.errlist.append("Manca indicazione capitolo")
        has_negoz = d_prat.get(cs.MOD_ACQUISTO) in (
            cs.TRATT_MEPA_40,
            cs.TRATT_MEPA_143,
            cs.TRATT_UBUY_40,
            cs.TRATT_UBUY_143,
        )
        if has_negoz and not self.data_negoziazione.data:
            self.errlist.append("Manca data negoziazione")
        if has_negoz and not self.numero_negoziazione.data:
            self.errlist.append("Manca numero ID negoziazione")
        if has_negoz and not self.data_scadenza.data:
            self.errlist.append("Manca data scadenza per presentazione offerta")
        if has_negoz and not self.data_offerta.data:
            self.errlist.append("Manca data offerta")
        if has_negoz and not self.numero_offerta.data:
            self.errlist.append("Manca numero ID offerta")
        has_protdoc = d_prat[cs.MOD_ACQUISTO] in (cs.INFER_5000, cs.ACC_QUADRO)
        if has_protdoc and not self.data_protocollo_doc:
            self.errlist.append("Manca data protocollo documentazione")
        if has_protdoc and not self.numero_protocollo_doc:
            self.errlist.append("Manca numero protocollo documentazione")
#       if not self.numero_cig.data:
#           self.errlist.append("Manca indicazione CIG")
        return not self.errlist


class Ordine(FormWErrors):
    "form per definizione ordine"
    numero_ordine = MyTextField("Numero ordine", True, [])
    numero_cig = MyTextField('CIG', True, [wt.validators.InputRequired()])
    termine_giorni = MyTextField(
        "Termine di esecuzione della prestazione (giorni)", True, []
    )
    descrizione_ordine = MyTextAreaField("Descrizione", True, [])
    ord_firma_vicario = MyBooleanField("Firma il Direttore Vicario", False)
    note_ordine = MyTextAreaField("Note", False, [])

    T_avanti = wt.SubmitField("Avanti", [wt.validators.Optional()])
    T_annulla = wt.SubmitField("Annulla", [wt.validators.Optional()])

    def validate(self, extra_validators=None):
        "Validazione specifica per il form"
        self.errlist = []
        if not self.numero_ordine.data:
            self.errlist.append("Manca numero ordine")
        if not self.numero_cig.data:
            self.errlist.append("Manca numero CIG")
        if not self.termine_giorni.data:
            self.errlist.append("Manca indicazione termine di esecuzione")
        return not self.errlist

    def __call__(self, d_prat):
        "rendering del form"
        html = (
            B_TRTD
            + Markup(
                f"Pratica del {d_prat[cs.DATA_PRATICA]}. "
                f"Resp.Fondi: {d_prat[cs.NOME_RESPONSABILE]}. "
                f"Richiedente: {d_prat[cs.NOME_RICHIEDENTE]}"
            )
            + Markup(
                f"""<p><b>Descrizione acquisto:</b>
        <blockquote>{d_prat[cs.DESCRIZIONE_ACQUISTO]}</blockquote>
        """
            )
            + Markup(
                f"""<p><b>Numero CIG:</b> {d_prat[cs.NUMERO_CIG]}<br>
        <b>Numero CUP:</b> {d_prat[cs.NUMERO_CUP]}
        """
            )
            + Markup(
                f"<p><b>Fornitore:</b><blockquote>{d_prat[cs.FORNITORE_NOME]}<br>"
                f"{d_prat[cs.FORNITORE_SEDE]}</blockquote>"
            )
            + E_TRTD
            + B_TRTD
            + render_field(self.numero_ordine)
            + E_TRTD
            + B_TRTD
            + render_field(self.termine_giorni)
            + E_TRTD
            + B_TRTD
            + render_field(self.descrizione_ordine, rows=3, cols=80)
            + E_TRTD
            + B_TRTD
            + render_field(self.ord_firma_vicario, sameline=True)
            + E_TRTD
            + B_TRTD
            + render_field(self.note_ordine, rows=10, cols=80)
            + E_TRTD
            + B_TRTD
            + self.T_annulla()
            + NBSP
            + self.T_avanti()
            + E_TRTD
        )
        return html


class AnnullaPratica(FormWErrors):
    "Form per conferma annullamento pratica"
    motivazione_annullamento = MyTextField(
        "Motivazione annullamento",
        True,
        [wt.validators.InputRequired("Devi specificare la motivazione")],
    )
    T_conferma = wt.SubmitField("Conferma", [wt.validators.Optional()])
    T_annulla = wt.SubmitField("Annulla", [wt.validators.Optional()])

    def __call__(self):
        "rendering del form"
        html = (
            B_TRTD
            + render_field(self.motivazione_annullamento, size=30, sameline=True)
            + BRK
            + BRK
            + B_TRTD
            + self.T_annulla()
            + NBSP
            + self.T_conferma()
            + E_TRTD
        )
        return html


class TrovaPratica(FormWErrors):
    "form per ricerca pratiche"
    trova_prat_aperta = MySelectField(
        "Stato pratica: ",
        False,
        choices=((-1, "Tutte"), (0, "Aperta"), (1, "Chiusa"), (2, "Annullata")),
    )
    trova_richiedente = MyTextField("Richiedente: ", False)
    trova_responsabile = MyTextField("Responsabile: ", False)
    trova_rup = MyTextField("RUP: ", False)
    trova_anno = MySelectField("Anno: ", False)
    trova_parola = MyTextField("Parola nella descrizione: ", False)
    elenco_ascendente = MyBooleanField("Ordine ascendente", False)
    T_avanti = wt.SubmitField("Trova", [wt.validators.Optional()])
    T_annulla = wt.SubmitField("Annulla", [wt.validators.Optional()])

    def __call__(self):
        "Rendering del form"
        html = (
            B_TRTD
            + render_field(self.trova_prat_aperta, sameline=True)
            + BRK
            + BRK
            + render_field(self.trova_richiedente, sameline=True)
            + BRK
            + BRK
            + render_field(self.trova_responsabile, sameline=True)
            + BRK
            + BRK
            + render_field(self.trova_rup, sameline=True)
            + BRK
            + BRK
            + render_field(self.trova_anno, sameline=True)
            + BRK
            + BRK
            + render_field(self.trova_parola, sameline=True)
            + BRK
            + BRK
            + render_field(self.elenco_ascendente, sameline=True)
            + E_TRTD
            + B_TRTD
            + self.T_annulla()
            + NBSP
            + self.T_avanti()
            + E_TRTD
        )
        return html


B_TD = Markup("<td>")
E_TD = Markup("</td>")


class RdO(FormWErrors):
    "form per specifiche per la generazione di RdO"
    numero_cup = MyTextField("CUP", True, [wt.validators.Optional()])
    costo_rdo = MyFormField(Costo2, "Quadro economico", True)
    fine_gara = MyTextField("Data scadenza presentazione offerta (g/m/aaaa)", True)
    T_avanti = wt.SubmitField("Avanti", [wt.validators.Optional()])
    T_annulla = wt.SubmitField("Annulla", [wt.validators.Optional()])

    def __call__(self, **kw):
        "Rendering del form"
        html = (
            B_TRTD
            + render_field(self.numero_cup)
            + BRK
            + B_TRTD
            + render_field(self.fine_gara)
            + E_TRTD
            + B_TRTD
            + render_field(self.costo_rdo, sameline=True)
            + E_TRTD
            + B_TRTD
            + self.T_annulla()
            + NBSP
            + self.T_avanti()
            + E_TRTD
        )
        return html

    def validate(self, extra_validators=None):
        "Validazione"
        tt0 = ft.date_to_time(self.fine_gara.data)
        #       if not self.numero_cig.data:
        #           self.errlist.append("Manca indicazione numero CIG")
        if tt0 is None:
            self.errlist.append("Errore data fine_gara (usa formato: g/m/a)")
        return not self.errlist


class CodfForm(FormWErrors):
    "Modulo per modifica codici fondi"
    Codice = MyTextField("Codice", True)
    Titolo = MyTextField("Titolo", True)
    CUP = MyTextField("CUP", False)
    email_Responsabile = MySelectField("Responsabile", True)

    Commenti = MyTextAreaField("Commenti", False)
    avanti = wt.SubmitField("Avanti")
    annulla = wt.SubmitField("Annulla")
    cancella = wt.SubmitField("Cancella record")

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
    userid = MyTextField("username", [wt.validators.Optional()])
    name = MyTextField("Nome", [wt.validators.Optional()])
    surname = MyTextField("Cognome", [wt.validators.Optional()])

    email = MyTextField("e-mail", True, [wt.validators.Email()])
    amministratore = MyBooleanField("Funzioni di amministrazione", False)
    avanti = wt.SubmitField("Avanti", [wt.validators.Optional()])
    annulla = wt.SubmitField("Annulla", [wt.validators.Optional()])
    cancella = wt.SubmitField("Cancella record", [wt.validators.Optional()])

    def validate(self, extra_validators=None):
        "Validazione"
        if not (
            self.userid.data
            and self.name.data
            and self.surname.data
            and self.email.data
        ):
            self.errlist.append("Devi specificare tutti i campi richesti")
            return False
        return True
