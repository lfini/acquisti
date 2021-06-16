"""
Definizione delle costanti per procedura acquisti
"""

import os.path

__version__ = "2.1"
__date__ = "16/6/2021"
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

NOME_DITTA = "nome_ditta"
SEDE_DITTA = "sede_ditta"

# Costanti di tipo stringa
APPROVAL_HOSTS = 'approval_hosts'               # config
CAPITOLO = 'capitolo'                           # dati_pratica
CITTA = "citta"                                 # config, sede
COD_FISC = "cod_fisc"                           # config, sede
#CODICE_APPROVAZIONE = 'codice_approvazione'     # dati_pratica
CONF_CHIUSURA = '_conf_chiusura'                # dati_pratica
CONSIP = "consip"                               # MENU_MOD_ACQ
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
DOLLAR = "dollar"                               # MENU_VALUTA
EMAIL_DIRETTORE = 'email_direttore'             # config
EMAIL_RESPONSABILE = 'email_responsabile'       # dati_pratica
EMAIL_RICHIEDENTE = 'email_richiedente'         # dati_pratica
EMAIL_RUP = 'email_rup'                         # dati_pratica
EMAIL_PROCEDURA = 'email_procedura'             # config
EMAIL_UFFICIO = 'email_ufficio'                 # config
EMAIL_WEBMASTER = 'email_webmaster'             # config
EURO = "euro"                                   # MENU_VALUTA
FINE_GARA = "fine_gara"                         # dati pratica
FINE_GARA_GIORNO = "fine_gara_giorno"           # dati pratica
FINE_GARA_ORE = "fine_gara_ore"                 # dati pratica
FIRMA_APPROVAZIONE = 'firma_approvazione'       # dati_pratica
FLASK_KEY = 'flask_key'                         # config
GIUSTIFICAZIONE = 'giustificazione'             # dati_pratica
IMPORTO = 'importo'
INDIRIZZO = "indirizzo"                         # config
IND_FORNITORE = 'ind_fornitore'                 # dati_pratica
INFER_1000 = "infer.1000"                       # Obsoleto. Mantenuto per compatibilità
INFER_5000 = "infer.5000"                       # MENU_MOD_ACQ
INIZIO_GARA = "inizio_gara"                     # dati pratica
IVA = "iva"
IVA_ = "iva_"                                   # MENU_IVA
IVA10 = "iva_10"                                # MENU_IVA
IVA22 = "iva_22"                                # MENU_IVA
IVA4 = "iva_4"                                  # MENU_IVA
IVAESENTE = "iva_esente"                        # MENU_IVA
IVAFREE = "iva_free"                            # dati_pratica[costo]
IVAINCL10 = "iva_incl10"                        # MENU_IVA
IVAINCL22 = "iva_incl22"                        # MENU_IVA
IVAINCL4 = "iva_incl4"                          # MENU_IVA
IVAINCL = "iva_incl"                            # MENU_IVA
IVA_NO = "iva_no"                               # MENU_IVA
LATEX_PATH = "latex_path"                       # config
LDAP_HOST = "ldap_host"                         # config
LDAP_PORT = "ldap_port"                         # config
LINGUA_ORDINE = 'lingua_ordine'                 # dati_pratica
LISTA_CODF = 'lista_codf'                       # dati_pratica
LISTA_DITTE = 'lista_ditte'                     # dati_pratica
LISTA_DITTE_INV = 'lista_ditte_inv'             # MENU allegati
MANIF_INT = "manif.interesse"                   # MENU_MOD_ACQ
MEPA = "mepa"                                   # MENU_MOD_ACQ
MOD_ACQUISTO = 'modalita_acquisto'              # dati_pratica
MOD_ACQUISTO_B = 'modalita_acquisto_b'          # dati_pratica
MODO_TRASP = 'modo_trasp'
MOTIVAZIONE_ACQUISTO = 'motivazione_acquisto'   # dati_pratica
TRATT_MEPA = 'tratt.mepa'                       # MENU_MOD_ACQ
NOME_DIRETTORE = 'nome_direttore'               # dati_pratica, config
NOME_DIRETTORE_B = 'nome_direttore_b'           # dati_pratica
NOME_FORNITORE = 'nome_fornitore'               # dati_pratica
NOME_RESPONSABILE = 'nome_responsabile'         # dati_pratica
NOME_RICHIEDENTE = 'nome_richiedente'           # dati_pratica
NOME_WEBMASTER = 'nome_webmaster'               # config
NON_APP = "non.app"                             # MENU_TRASPORTO
NOTE_RICHIESTA = 'note_richiesta'               # dati_pratica
NUMERO_DETERMINA_A = 'numero_determina'         # dati_pratica
NUMERO_DETERMINA_B = 'numero_determina_b'       # dati_pratica
NUMERO_ORDINE = 'numero_ordine'                 # dati_pratica
NUMERO_PRATICA = 'numero_pratica'               # dati_pratica
OFF_PIU_VANT = 'off.piu.vant'                   # MENU_CRIT_ASS
ONERI_SICUREZZA = 'oneri_sicurezza'             # dati_pratica
ORD_PDF_FILE = "ordine.pdf"
ORD_NAME_EN = 'ordine_inglese'
ORD_NAME_IT = 'ordine_italiano'
PART_IVA = "part_iva"                           # config, sede
PDF_DETERMINA_A = 'pdf_determina'               # dati_pratica
PDF_DETERMINA_B = 'pdf_determina_b'             # dati_pratica
PDF_ORDINE = 'pdf_ordine'                       # dati_pratica
PDF_RICHIESTA = 'pdf_richiesta'                 # dati_pratica
POUND = "pound"                                 # MENU_VALUTA
PRAT_JFILE = 'pratica.json'
PRATICA_ANNULLATA = 'pratica_annullata'         # dati_pratica
PRATICA_APERTA = 'pratica_aperta'               # dati_pratica
PREZ_PIU_BASSO = 'prezzo.piu.basso'             # MENU_CRIT_ASS
PREZZO_GARA = 'prezzo_gara'                     # dati_pratica
ONERI_SIC_GARA = 'oneri_sic_gara'               # dati_pratica
PROC_NEG = "proc.neg.acq"                       # MENU_MOD_ACQ, dati_pratica
RDO_MEPA = "rdo.mepa"                           # MENU_MOD_ACQ, dati_pratica
RIC_PDF_FILE = "richiesta.pdf"
RICHIESTA_INVIATA = 'richiesta_inviata'         # dati_pratica
RUP = 'rup'                                     # dati_pratica
SAVED = '_saved'                                # dati_pratica
SEDE = 'sede'                                   # config
SEDE_IT = 'sede_it'                             # config.sede
SEDE_UK = 'sede_uk'                             # config.sede
SFR = "sfr"                                     # MENU_VALUTA
SIGLA_DITTA = 'sigla_ditta'                     # form MyUpload1
SMTP_HOST = 'smtp_host'                         # config
SPECIFICARE = "spec"                            # MENU_TRASPORTO
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
SUPER_1000 = "super.1000"                       # Obsoleto. Mantenuto per compatibilità
SUPER_5000 = "super.5000"                       # MENU_MOD_ACQ
TITOLO_DIRETTORE = 'titolo_direttore'           # dati_pratica, config
TITOLO_DIRETTORE_UK = 'titolo_direttore_uk'     # dati_pratica, config
TRASP_INC = "t.inc"                             # MENU_TRASPORTO
VALUTA = "valuta"
VEDI_STORIA = '_vedi_storia'                    # dati_pratica
VERSIONE = 'versione'                           # dati_pratica
VINCITORE = 'ditta_vincitrice'                  # dati_pratica
WEB_HOST = 'web_host'                           # config
WEB_PORT = 'web_port'                           # config
WEBSITE = 'website'                             # config, sede

# Chiavi da rinominare in dati_pratica per versione 1 del file
#                  Vecchio  Nuovo
KEYS_TO_UPDATE = (("lista_cram", "lista_codf"),
                  ("stringa_cram", "stringa_codf"))

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

MENU_MOD_ACQ = ((MEPA, "Acquisto su MEPA"),
                (CONSIP, "Acquisto nella Vetrina delle convenzioni Consip"),
                (TRATT_MEPA, "Trattativa diretta su MEPA"),
                (RDO_MEPA, "Richiesta di Offerta (RdO) su MEPA"),
                (INFER_5000, "Affidamento diretto per importi inferiori a 5000 Euro"),
                (SUPER_5000, "Affidamento diretto per importi superiori o uguali a 5000 Euro"),
                (PROC_NEG, "Procedura di cottimo fiduciario"),
                (MANIF_INT, "Manifestazione di interesse"),
               )

MENU_MOD_ACQ_B = ((SUPER_5000, "Affidamento diretto per importi superiori o uguali a 5000 Euro"),
                  (PROC_NEG, "Procedura di cottimo fiduciario"),
                 )

# Tipi allegato
ALLEGATO_GENERICO_A = "allegato_gen_a"
ALLEGATO_GENERICO_B = "allegato_gen_b"
ALLEGATO_CIG = "all_cig"
CAPITOLATO_RDO = 'capit_rdo'
DICH_IMPOSTA_BOLLO = "dich_bollo"
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
                DICH_IMPOSTA_BOLLO: ('A12_Dichiarazione_Imposta_bollo',
                                     "Dichiarazione sostitutiva di assolvimento Imposta Bollo",
                                     ALL_SING),
                LETT_INVITO_A: ('A06_Lettera_Invito', "Lettera di invito", ALL_SPEC),
                LETT_INVITO_B: ('B06_Lettera_Invito', "Lettera di invito", ALL_SPEC),
                LETT_INVITO_MEPA: ('A06_Lettera_Invito_MEPA', "Lettera di invito MEPA", ALL_SING),
                LISTA_DETTAGLIATA_A: ('A40_Lista_dettagliata_per_ordine',
                                      "Lista dettagliata allegata all'ordine", ALL_SING),
                LISTA_DETTAGLIATA_B: ('B40_Lista_dettagliata_per_ordine',
                                      "Lista dettagliata allegata all'ordine", ALL_SING),
                LISTA_DITTE_INV: ('A08_Lista_ditte_invitate', "Lista ditte invitate", ALL_SING),
                DOCUM_STIPULA: ("A09_Documento_di_stipula",
                                "Documento di stipula su MEPA", ALL_SING),
                OFFERTA_DITTA_A: ('A10_Offerta_ditta', "Offerta di una ditta", ALL_SPEC),
                OFFERTA_DITTA_B: ('B10_Offerta_ditta', "Offerta di una ditta", ALL_SPEC),
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
L'approvazione della richiesta di acquisto N. {numero_pratica} è stata
registrata.
"""

HEADER_NOTIFICA_RESPONSABILE_EMAIL = """
L'approvazione della richiesta di acquisto N. {numero_pratica} è stata
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
Ti è stata inviata la richiesta di acquisto N. {numero_pratica} per approvazione.
(vedi dettagli sotto).

Per approvarla puoi accedere alla procedura per la gestione degli ordini:

     %s

e selezionare: Elenco richieste aperte"""

TESTO_NOTIFICA_APPROVAZIONE = """
La richiesta di acquisto N. {numero_pratica}:

   {descrizione_acquisto}

è stata approvata dal responsabile dei fondi.
"""

BINDIR = os.path.dirname(os.path.abspath(__file__))  # Path della directory eseguibili
PKG_ROOT = os.path.abspath(os.path.join(BINDIR, ".."))  # Path della root del package

DATADIR = os.path.join(PKG_ROOT, "data")   # path della directory per i dati"
FILEDIR = os.path.join(PKG_ROOT, "files")  # path della directory dei files ausiliari"
WORKDIR = os.path.join(PKG_ROOT, "work")   # path della directory di lavoro"
