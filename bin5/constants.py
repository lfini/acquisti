"""
Definizione delle costanti per procedura acquisti
"""

import os.path

__version__ = "2.2"
__date__ = "6/3/2024"
__author__ = "Luca Fini"

UPLOAD_TYPES = ('.pdf', '.rtf', '.p7m')
PDF_TYPES = ('.pdf',)

EDIT_SYMB = '<font color=red><b>&ofcir;</b></font>'

APPROVAL_EXPIRATION = 7*24*3600.     # Tempo espirazione per approvazione

# Stringhe di uso frequente

ATTESA_APPROVAZIONE = 'In attesa di approvazione'
CHIUSA = "Chiusa"
NUOVA_PRATICA = 'Nuova pratica'

#  Campi temporanei (da non registrare in dati pratica)
AVANTI = "T_avanti"
ANNULLA = "T_annulla"
MORE = "T_more"

TEMPORARY_KEY_PREFIX = "T_"

CONFIG_NAME = 'config.json'      # nome file di configurazione

NOME_DITTA = "nome_ditta"
SEDE_DITTA = "sede_ditta"

# Costanti per menu modalità acquisto
ACCORDO_QUADRO = "acc.quadro"
CONSIP = "consip"
INFER_5000 = "infer.5000"
MEPA = 'cat.mepa'
TRATT_MEPA_143 = 'tratt.mepa143'
TRATT_MEPA_40 = 'tratt.mepa40'
TRATT_UBUY_143 = 'tratt.ubuy143'
TRATT_UBUY_40 = 'tratt.ubuy40'

# Costanti per menu valuta
DOLLAR = "dollar"
EURO = "euro"
POUND = "pound"
SFR = "sfr"

# Costanti per menu trasporto
TRASP_INC = "t.inc"
NON_APP = "non.app"
SPECIFICARE = "spec"

# Costanti per menu iva
IVA_ = "iva_"
IVA10 = "iva_10"
IVA22 = "iva_22"
IVA4 = "iva_4"
IVAESENTE = "iva_esente"
IVAINCL10 = "iva_incl10"
IVAINCL22 = "iva_incl22"
IVAINCL4 = "iva_incl4"
IVAINCL = "iva_incl"
IVA_NO = "iva_no"

# Costanti per menu allegati
LISTA_DITTE_INV = 'lista_ditte_inv'

# Costanti per menu criteri din assegnazione
OFF_PIU_VANT = 'off.piu.vant'
PREZ_PIU_BASSO = 'prezzo.piu.basso'

# chiavi per dict configurazione
#APPROVAL_HOSTS = 'approval_hosts'
CITTA = "citta"
COD_FISC = "cod_fisc"
EMAIL_DIRETTORE = 'email_direttore'
EMAIL_PROCEDURA = 'email_procedura'
EMAIL_UFFICIO = 'email_ufficio'
EMAIL_WEBMASTER = 'email_webmaster'
FLASK_KEY = 'flask_key'
GENDER_DIRETTORE = 'gender_direttore'
INDIRIZZO = "indirizzo"
LATEX_PATH = "latex_path"
LDAP_HOST = "ldap_host"
LDAP_PORT = "ldap_port"
NOME_WEBMASTER = 'nome_webmaster'
PART_IVA = "part_iva"
SEDE = 'sede'
SEDE_IT = 'sede_it'
SEDE_UK = 'sede_uk'
SMTP_HOST = 'smtp_host'
WEBSITE = 'website'                             # config, sede

# Costanti per dict dati_pratica
CAPITOLO = 'capitolo'                           # dati_pratica
CONF_CHIUSURA = '_conf_chiusura'                # dati_pratica
COSTO = 'costo'                                 # dati_pratica
COSTO_ORDINE = 'costo_ordine'                   # dati_pratica
CRIT_ASS = 'criterio_assegnazione'              # dati_pratica
CUP = 'cup'                                     # dati_pratica
DATA_DETERMINA_A = 'data_determina'             # dati_pratica
DATA_DETERMINA_B = 'data_determina_b'           # dati_pratica
DATA_ORDINE = 'data_ordine'                     # dati_pratica
DATA_RICHIESTA = 'data_richiesta'               # dati_pratica
DESCRIZIONE_ACQUISTO = 'descrizione_acquisto'   # dati_pratica
DESCRIZIONE_ORDINE = 'descrizione_ordine'       # dati_pratica
DETA_PDF_FILE = "determina.pdf"
DETB_PDF_FILE = "determinaB.pdf"
DETTAGLIO_ORDINE = 'dettaglio_ordine'           # dati_pratica
DIFFORMITA = 'difformita'                       # dati_pratica
DIRETTORE_M = 'dir_is_m'                        # dati_pratica
EMAIL_RESPONSABILE = 'email_responsabile'       # dati_pratica
EMAIL_RICHIEDENTE = 'email_richiedente'         # dati_pratica
EMAIL_RUP = 'email_rup'                         # dati_pratica
FINE_GARA = "fine_gara"                         # dati pratica
FINE_GARA_GIORNO = "fine_gara_giorno"           # dati pratica
FINE_GARA_ORE = "fine_gara_ore"                 # dati pratica
FIRMA_APPROVAZIONE = 'firma_approvazione'       # dati_pratica
GIUSTIFICAZIONE = 'giustificazione'             # dati_pratica
IMPORTO = 'importo'
IND_FORNITORE = 'ind_fornitore'                 # dati_pratica
INIZIO_GARA = "inizio_gara"                     # dati pratica
IVA = "iva"
IVAFREE = "iva_free"                            # dati_pratica[costo]
LINGUA_ORDINE = 'lingua_ordine'                 # dati_pratica
LISTA_CODF = 'lista_codf'                       # dati_pratica
LISTA_DITTE = 'lista_ditte'                     # dati_pratica
MOD_ACQUISTO = 'modalita_acquisto'              # dati_pratica
MOD_ACQUISTO_B = 'modalita_acquisto_b'          # dati_pratica
MODO_TRASP = 'modo_trasp'
MOTIVAZIONE_ACQUISTO = 'motivazione_acquisto'   # dati_pratica
NOME_DIRETTORE = 'nome_direttore'               # dati_pratica, config
NOME_DIRETTORE_B = 'nome_direttore_b'           # dati_pratica
NOME_FORNITORE = 'nome_fornitore'               # dati_pratica
NOME_RESPONSABILE = 'nome_responsabile'         # dati_pratica
NOME_RICHIEDENTE = 'nome_richiedente'           # dati_pratica
NOME_RUP = 'nome_rup'                           # dati_pratica
NOTE_RICHIESTA = 'note_richiesta'               # dati_pratica
NUMERO_DETERMINA_A = 'numero_determina'         # dati_pratica
NUMERO_DETERMINA_B = 'numero_determina_b'       # dati_pratica
NUMERO_ORDINE = 'numero_ordine'                 # dati_pratica
NUMERO_PRATICA = 'numero_pratica'               # dati_pratica
ONERI_SICUREZZA = 'oneri_sicurezza'             # dati_pratica
ORD_PDF_FILE = "ordine.pdf"
ORD_NAME_EN = 'ordine_inglese'
ORD_NAME_IT = 'ordine_italiano'
PDF_DETERMINA_A = 'pdf_determina'               # dati_pratica
PDF_DETERMINA_B = 'pdf_determina_b'             # dati_pratica
PDF_ORDINE = 'pdf_ordine'                       # dati_pratica
PDF_PROGETTO = 'pdf_progetto'                   # dati_pratica
PRAT_JFILE = 'pratica.json'
PRATICA_ANNULLATA = 'pratica_annullata'         # dati_pratica
PRATICA_APERTA = 'pratica_aperta'               # dati_pratica
PREZZO_GARA = 'prezzo_gara'                     # dati_pratica
PROG_PDF_FILE = "progetto.pdf"
ONERI_SIC_GARA = 'oneri_sic_gara'               # dati_pratica
PROGETTO_INVIATO = 'progetto_inviato'         # dati_pratica
RUP = 'rup'                                     # dati_pratica
SAVED = '_saved'                                # dati_pratica
SIGLA_DITTA = 'sigla_ditta'                     # form MyUpload1
STATO_PRATICA = 'stato_pratica'                 # dati_pratica
STORIA_PRATICA = 'storia_pratica'               # dati_pratica
STR_COSTO_IT = 'str_costo_it'                   # dati_pratica
STR_CODF = 'stringa_codf'                       # dati_pratica
STR_COSTO_UK = 'str_costo_uk'                   # dati_pratica
STR_COSTO_ORD_IT = 'str_costo_ord_it'           # dati_pratica
STR_COSTO_ORD_UK = 'str_costo_ord_uk'           # dati_pratica
STR_CRIT_ASS = 'str_crit_ass'                   # dati_pratica
STR_MOD_ACQ = 'str_mod_acq'                     # dati_pratica
STR_ONERI_IT = 'str_oneri_it'                   # dati_pratica
STR_ONERI_UK = 'str_oneri_uk'                   # dati_pratica
STR_PREZZO_GARA = 'str_prezzo_gara'             # dati_pratica
TITOLO_DIRETTORE = 'titolo_direttore'           # dati_pratica, config
TITOLO_DIRETTORE_UK = 'titolo_direttore_uk'     # dati_pratica, config
VALUTA = "valuta"
VEDI_STORIA = '_vedi_storia'                    # dati_pratica
VERSIONE = 'versione'                           # dati_pratica
VINCITORE = 'ditta_vincitrice'                  # dati_pratica


################################## Stringhe derivate

# Definizione menu
MENU_CRIT_ASS = ((PREZ_PIU_BASSO, "Prezzo pi&ugrave; basso"),
                 (OFF_PIU_VANT, "Offerta pi&ugrave; vantaggiosa"))

MENU_IVA = ((IVA_NO, "-"),
            (IVA22, "+ I.V.A. 22%"),
            (IVA10, "+ I.V.A. 10%"),
            (IVA4, "+ I.V.A. 4%"),
            (IVA_, "+ I.V.A."),
            (IVAINCL22, "I.V.A. 22% inclusa"),
            (IVAINCL10, "I.V.A. 10% inclusa"),
            (IVAINCL4, "I.V.A. 4% inclusa"),
            (IVAINCL, "I.V.A. inclusa"),
            (IVAESENTE, "esente I.V.A."))

MENU_VALUTA = ((EURO, "Euro"),
               (POUND, "Pounds"),
               (DOLLAR, "Dollars"),
               (SFR, "Fr.Svizzeri"))

MENU_TRASPORTO = ((NON_APP, "Non applicabile"),
                  (TRASP_INC, "Incluso"),
                  (SPECIFICARE, "Specificare"))

MENU_MOD_ACQ = ((TRATT_MEPA_40, "Trattativa diretta MePA sotto 40k€"),
                (TRATT_MEPA_143, "Trattativa diretta MePA da 40k€i a 143k€"),
                (CONSIP, "Acquisto nella Vetrina delle convenzioni Consip"),
                (ACCORDO_QUADRO, "Adesione ad accordo quadro"),
                (MEPA, "Acquisto a catalogo MePA"),
                (TRATT_UBUY_40, "Trattativa diretta UBUY sotto 40 k€"),
                (TRATT_UBUY_143, "Trattativa diretta UBUY sotto 143 k€"),
                (INFER_5000, "Trattativa diretta sotto 5k€ con PCP"),
               )

# Tipi allegato
ALLEGATO_GENERICO_A = "allegato_gen_a"
ALLEGATO_GENERICO_B = "allegato_gen_b"
ALLEGATO_CIG = "all_cig"
CAPITOLATO_RDO = 'capit_rdo'
LETT_INVITO_A = 'lett_invito_a'
LETT_INVITO_B = 'lett_invito_b'
LETT_INVITO_MEPA = 'lett_invito_mepa'
LISTA_DETTAGLIATA_A = 'lista_dett_a'
LISTA_DETTAGLIATA_B = 'lista_dett_b'
DOCUM_STIPULA = 'doc_stipula'
OFFERTA_DITTA_A = "offerta_ditta_a"
OFFERTA_DITTA_B = "offerta_ditta_b"
OFFERTE_DITTE = "offerta_ditta"
ORDINE_DITTA = "ordine_ditta"
ORDINE_MEPA = "ordine_mepa"
PREV_TRATT_MEPA = "prev.tratt.mepa"
VERBALE_GARA = "verbale_gara"

# Specifica allegati
ALL_SING = 0    # Allegato singolo
ALL_SPEC = 1    # Allegato multiplo con specifica
ALL_NAME = 2    # Allegato multiplo con nome file
ALL_PRAT = 3    # Allegato singolo con numero pratica

# Tabella allegati  key   pref.nome file     descrizione  singolo/multiplo
TAB_ALLEGATI = {ALLEGATO_GENERICO_A: ("A99_", "Allegato generico", ALL_NAME),
                ALLEGATO_GENERICO_B: ("B99_", "Allegato generico", ALL_NAME),
                ALLEGATO_CIG: ("A88_CIG_Prat.", "CIG", ALL_PRAT),
                CAPITOLATO_RDO: ('A07_Capitolato_RDO', "Capitolato per RDO", ALL_SING),
                DOCUM_STIPULA: ("A09_Documento_di_stipula",
                                "Documento di stipula su MEPA", ALL_SING),
                LETT_INVITO_A: ('A06_Lettera_Invito', "Lettera di invito", ALL_SPEC),
                LETT_INVITO_B: ('B06_Lettera_Invito', "Lettera di invito", ALL_SPEC),
                LETT_INVITO_MEPA: ('A06_Lettera_Invito_MEPA', "Lettera di invito MEPA", ALL_SING),
                LISTA_DETTAGLIATA_A: ('A40_Lista_dettagliata_per_ordine',
                                      "Lista dettagliata allegata all'ordine", ALL_SING),
                LISTA_DETTAGLIATA_B: ('B40_Lista_dettagliata_per_ordine',
                                      "Lista dettagliata allegata all'ordine", ALL_SING),
                LISTA_DITTE_INV: ('A08_Lista_ditte_invitate', "Lista ditte invitate", ALL_SING),
                OFFERTA_DITTA_A: ('A10_Offerta_ditta', "Offerta di una ditta", ALL_SPEC),
                OFFERTA_DITTA_B: ('B10_Offerta_ditta', "Offerta di una ditta", ALL_SPEC),
                PREV_TRATT_MEPA: ('A01_Preventivo_trattativa_MePA',
                                  "Preventivo trattativa diretta MePA", ALL_SING),
                ORDINE_MEPA: ('A10_Bozza_Ordine_MEPA', "Bozza ordine MEPA", ALL_SING),
                VERBALE_GARA: ('B50_Verbale_Gara', "Verbale di gara", ALL_SING)}

################################################### Varie stringhe
ACCESSO_NON_PREVISTO = "Sequenza di accesso non prevista. URL: "

#APPROV_EMAIL_RESPINTA_OGGETTO = "Approvazione per e-mail respinta"

#APPROV_EMAIL_RESPINTA = """
#L'approvazione della richiesta di cui alla pratica numero %(numero_pratica)s
#
#   %(descrizione_acquisto)s
#
#è stata ricevuta per e-mail, ma è stata respinta perché la pratica
#nel frattempo è stata  modificata
#"""

DETTAGLIO_PRATICA = """

-----------------------------------------
Dettaglio pratica:

Richiedente: {nome_richiedente}
Respons. dei fondi: {nome_responsabile}

Acquisto/fornitura: {descrizione_acquisto}

Motivazione:

{motivazione_acquisto}

Importo: {str_costo_it}
"""

HEADER_NOTIFICA_RESPONSABILE_WEB = """
L'approvazione del progetto di acquisto N. {numero_pratica} è stata
registrata.
"""

HEADER_NOTIFICA_RESPONSABILE_EMAIL = """
L'approvazione del progetto di acquisto N. {numero_pratica} è stata
ricevuta per e-mail e registrata.
"""
OBBLIGATORIO = """<font color=red><b>N.B.:</b> Tutti i campi sottolineati
sono obbligatori e devono essere specificati</font>"""

OPER_SOLO_AMMINISTRAZIONE = "Operazione consentita solo all'Amministrazione"

TABLE_HEADER = """<!DOCTYPE html>
<html>
<head>
<title>gestione tabelle</title>
</head>
<body>
"""

TESTO_APPROVAZIONE = """
Ti è stata inviato il progetto di acquisto N. {numero_pratica} per approvazione.
(vedi dettagli sotto).

Per approvarla puoi accedere alla procedura per la gestione degli ordini:

     %s

e selezionare: Elenco pratiche aperte (come resp. fondi)
"""

TESTO_NOTIFICA_APPROVAZIONE = """
Il progetto di acquisto N. {numero_pratica}:

   {descrizione_acquisto}

è stato approvato dal responsabile dei fondi.
"""

BINDIR = os.path.dirname(os.path.abspath(__file__))  # Path della directory eseguibili
PKG_ROOT = os.path.abspath(os.path.join(BINDIR, ".."))  # Path della root del package

AUXFILEDIR = "files5"          # nome directory per file ausiliari

DATADIR = os.path.join(PKG_ROOT, "data_tmp")      # path della directory per i dati"
FILEDIR = os.path.join(PKG_ROOT, AUXFILEDIR)  # path della directory dei files ausiliari"
WORKDIR = os.path.join(PKG_ROOT, "work")      # path della directory di lavoro"
