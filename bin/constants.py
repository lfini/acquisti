"""
Definizione delle costanti per procedura acquisti
"""

import os.path
from enum import IntEnum

__version__ = "2.3"
__date__ = "5/5/2024"
__author__ = "Luca Fini"

CONFIG_NAME = 'config.json'      # nome file di configurazione
CONFIG_SAVE = 'config.save'      # nome file di configurazione backup
CONFIG_VERSION = 'config_version'
CONFIG_REQUIRED = 6              # versione file configurazione richiesta

DECIS_FILE = 'decisioni.lst'           # nome file per lista decisioni
DECIS_FMT = '{ndecis} {date} {nprat}'  # formato linee lista decisioni

UPLOAD_TYPES = ('.pdf', '.rtf', '.p7m')
PDF_TYPES = ('.pdf',)

EDIT_SYMB = '<font color=red><b>&ofcir;</b></font>'

FILE_VERSION = 3    # Versione file pratica.json

# Stringhe di uso frequente

ATTESA_APPROVAZIONE = 'In attesa di approvazione'
CHIUSA = "Chiusa"
NUOVA_PRATICA = 'Nuova pratica'
BASEDIR = 'basedir'

#  Campi temporanei (da non registrare in dati pratica)
AVANTI = "T_avanti"
ANNULLA = "T_annulla"
MORE = "T_more"

TEMPORARY_KEY_PREFIX = "T_"

# Costanti per menu modalità acquisto
ACC_QUADRO = "acc.quadro"
CONSIP = "consip"
INFER_5000 = "infer.5000"
CAT_MEPA = 'cat.mepa'
TRATT_MEPA_143 = 'tratt.mepa143'
TRATT_MEPA_40 = 'tratt.mepa40'
TRATT_UBUY_143 = 'tratt.ubuy143'
TRATT_UBUY_40 = 'tratt.ubuy40'
GENERIC = 'prat.generic'

TAB_TEMPLATE = {          # suffissi per i template delle varie modalità di acquisto
        ACC_QUADRO: 'aquad',
        CONSIP: 'cnsip',
        INFER_5000: 'inf5k',
        CAT_MEPA: 'cmepa',
        TRATT_MEPA_143: 'tm143k',
        TRATT_MEPA_40: 'tm40k',
        TRATT_UBUY_143: 'ub143k',
        TRATT_UBUY_40: 'ub40k',
        GENERIC: 'generic',
        }


MOD_TUTTE = 'mod.tutte'   # Valido per tutte le modalità di acquisto

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
CITTA = "citta"
COD_FISC = "cod_fisc"
CUU = 'cuu'
EMAIL_DIRETTORE = 'email_direttore'
EMAIL_DIREZIONE = 'email_direzione'
EMAIL_PROCEDURA = 'email_procedura'
EMAIL_SERVIZIO = 'email_servizio'
EMAIL_UFFICIO = 'email_ufficio'
EMAIL_WEBMASTER = 'email_webmaster'
EMAIL_VICARIO = 'email_vicario'
FLASK_KEY = 'flask_key'
GENDER_DIRETTORE = 'gender_direttore'
INDIRIZZO = "indirizzo"
LATEX_PATH = "latex_path"
LDAP_HOST = "ldap_host"
LDAP_PORT = "ldap_port"
NOME_WEBMASTER = 'nome_webmaster'
NOME_DIRETTORE = 'nome_direttore'
NOME_VICARIO = 'nome_vicario'
PART_IVA = "part_iva"
PEC_OSS = "pec_oss"
SEDE = 'sede'
SEDE_IT = 'sede_it'
SEDE_UK = 'sede_uk'
SMTP_HOST = 'smtp_host'
TEL_OSS = 'tel_oss'
TEST_MODE = 'test_mode'
WEBSITE = 'website'

# opzioni per generazione documenti
PROVVISORIO = 'provvisorio'
RESPONSABILE = 'responsabile'
DIRETTORE = 'direttore'
VICARIO = 'vicario'
RICH_IS_RESP = 'rich_resp'

# nomi file generati
DOC_DECISIONE = "decisione.pdf"
DOC_NOMINARUP = "nominarup.pdf"
DOC_PROGETTO = "progetto.pdf"
DOC_PROPOSTA = "proposta.pdf"
DOC_ORDINE = "ordine.pdf"
DOC_RDO = "rdo.pdf"

# nomi azioni
INVIA_PROGETTO = 'invia_progetto'
RESP_APPROVA = 'resp_approva'
INDICA_RUP = 'indica_rup'
INVIA_DOC_RUP = 'invia_doc_rup'
DIR_AUTORIZZA = 'dir_autorizza'
VIC_AUTORIZZA = 'vic_autorizza'
INVIA_DECISIONE = 'invia_decisione'
CHIUDI_PRATICA = 'chiudi_pratica'

# Costanti per dict dati_pratica
CAPITOLO = 'capitolo'                           # dati_pratica
CIG_MASTER = 'cig_master'                       # dati_pratica
CONVENZIONE = 'convenzione'                     # dati pratica
COSTO_PROGETTO = 'costo_progetto'               # dati_pratica
COSTO_RDO = 'costo_rdo'                         # dati_pratica
COSTO_DETTAGLIO = 'costo_dettaglio'             # dati pratica
COSTO_BASE = 'costo_base'                       # dati pratica
COSTO_IVA = 'costo_iva'                         # dati pratica
COSTO_NETTO = 'costo_netto'                     # dati pratica
COSTO_ORDINE = 'costo_ordine'                   # dati_pratica
COSTO_TOTALE = 'costo_totale'                   # dati_pratica
CRIT_ASS = 'criterio_assegnazione'              # dati_pratica
DATA_DECISIONE = 'data_decisione'               # dati_pratica
DATA_NEGOZIAZIONE = 'data_negoziazione'         # dati_pratica
DATA_OFFERTA = 'data_offerta'                   # dati_pratica
DATA_PRATICA = 'data_pratica'                   # dati_pratica
DATA_PROPOSTA = 'data_proposta'                 # dati_pratica
DATA_SCADENZA = 'data_scadenza'                 # dati_pratica
DATA_RESP_APPROVA = 'data_resp_approva'         # dati_pratica
DATA_DIR_AUTORIZZA = 'data_dir_autorizza'       # dati_pratica
DATA_RUP_APPROV_DIR = 'data_rup_approv_dir'     # dati_pratica
DEC_FIRMA_VICARIO = 'dec_firma_vicario'         # dati pratica
DECIS_DA_FIRMARE = 'decis_da_firmare'           # dati_pratica
DESCRIZIONE_ACQUISTO = 'descrizione_acquisto'   # dati_pratica
DESCRIZIONE_ORDINE = 'descrizione_ordine'       # dati_pratica
DETTAGLIO_ORDINE = 'dettaglio_ordine'           # dati_pratica
DIFFORMITA = 'difformita'                       # dati_pratica
EMAIL_RESPONSABILE = 'email_responsabile'       # dati_pratica
EMAIL_RICHIEDENTE = 'email_richiedente'         # dati_pratica
EMAIL_RUP = 'email_rup'                         # dati_pratica
FINE_GARA = "fine_gara"                         # dati pratica
FINE_GARA_GIORNO = "fine_gara_giorno"           # dati pratica
FINE_GARA_ORE = "fine_gara_ore"                 # dati pratica
FIRMA_APPROV_RESP = 'firma_approvazione'        # dati_pratica
FIRMA_AUTORIZZ_DIR = 'firma_autorizzazione'     # dati_pratica
FORNITORE_NOME = 'fornitore_nome'               # dati_pratica
FORNITORE_SEDE = 'fornitore_sede'               # dati_pratica
FORNITORE_CODFISC = 'fornitore_codfisc'         # dati_pratica
FORNITORE_PARTIVA = 'fornitore_pativa'          # dati_pratica
GIUSTIFICAZIONE = 'giustificazione'             # dati_pratica
GUF_EU_NUM = 'guf_eu_num'                       # dati_pratica
GUF_EU_DATA = 'guf_eu_data'                     # dati_pratica
GUF_IT_NUM = 'guf_it_num'                       # dati_pratica
GUF_IT_DATA = 'guf_it_data'                     # dati_pratica
IMPORTO = 'importo'
INIZIO_GARA = "inizio_gara"                     # dati pratica
INTERNO_RUP = 'interno_rup'                     # dati pratica
IVA = "iva"
IVAFREE = "iva_free"                            # dati_pratica[costo]
LINGUA_ORDINE = 'lingua_ordine'                 # dati_pratica
LISTA_CODF = 'lista_codf'                       # dati_pratica
LISTA_DITTE = 'lista_ditte'                     # dati_pratica
LOTTO = 'lotto'                                 # dati_pratica
MOD_ACQUISTO = 'modalita_acquisto'              # dati_pratica
MODO_TRASP = 'modo_trasp'
MOTIVAZIONE_ACQUISTO = 'motivazione_acquisto'   # dati_pratica
MOTIVAZIONE_ANNULLAMENTO = 'motivazione_annullamento'   # dati_pratica
NOME_RESPONSABILE = 'nome_responsabile'         # dati_pratica
NOME_RICHIEDENTE = 'nome_richiedente'           # dati_pratica
NOME_RUP = 'nome_rup'                           # dati_pratica
NUMERO_CIG = "numero_cig"                       # dati_pratica
NUMERO_CUP = "numero_cup"                       # dati_pratica
NUMERO_DECISIONE = 'numero_decisione'           # dati_pratica
NUMERO_NEGOZIAZIONE = 'numero_negoziazione'     # dati praticayy
NUMERO_OFFERTA = 'numero_offerta'               # dati_pratica
NUMERO_PRATICA = 'numero_pratica'               # dati_pratica
ONERI_SICUREZZA = 'oneri_sicurezza'             # dati_pratica
ONERI_SIC_GARA = 'oneri_sic_gara'               # dati_pratica
ORD_FIRMA_VICARIO = 'ord_firma_vicario'         # dati pratica
PDF_NOMINARUP = 'pdf_nominarup'                 # dati_pratica
PDF_DECISIONE = 'pdf_decisione'                 # dati_pratica
PDF_PROPOSTA = 'pdf_proposta'                   # dati_pratica
PDF_ORDINE = 'pdf_ordine'                       # dati_pratica
PDF_RDO = 'pdf_rdo'                             # dati_pratica
PDF_PROGETTO = 'pdf_progetto'                   # dati_pratica
PRAT_JFILE = 'pratica.json'
PRATICA_ANNULLATA = 'pratica_annullata'         # dati_pratica
PRATICA_APERTA = 'pratica_aperta'               # dati_pratica
PREZZO_GARA = 'prezzo_gara'                     # dati_pratica
PROGETTO_INVIATO = 'progetto_inviato'           # dati_pratica
RDO_FIRMA_VICARIO = 'rdo_firma_vicario'         # dati pratica
RUP = 'rup'                                     # dati_pratica
RUP_FIRMA_VICARIO = 'rup_firma_vicario'         # dati pratica
SAVED = '_saved'                                # dati_pratica
SIGLA_DITTA = 'sigla_ditta'                     # form MyUpload1
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
TAB_PASSI = 'tab_passi'                         # dati pratica
VALUTA = "valuta"
VEDI_STORIA = '_vedi_storia'                    # dati_pratica
VERSIONE = 'versione'                           # dati_pratica
VINCITORE = 'ditta_vincitrice'                  # dati_pratica


################################## Stringhe derivate

# Definizione menu
MENU_CRIT_ASS = ((PREZ_PIU_BASSO, "Prezzo pi&ugrave; basso"),
                 (OFF_PIU_VANT, "Offerta pi&ugrave; vantaggiosa"))

MENU_VALUTA = ((EURO, "EUR"),
               (POUND, "GBP"),
               (DOLLAR, "USD"),
               (SFR, "SFR"))

MENU_MOD_ACQ = ((TRATT_MEPA_40, "Trattativa diretta MePA sotto 40k€"),
                (TRATT_MEPA_143, "Trattativa diretta MePA da 40k€ e sotto 140k€"),
                (CONSIP, "Adesione a convenzione Consip"),
                (ACC_QUADRO, "Adesione ad accordo quadro"),
#               (CAT_MEPA, "Acquisto a catalogo MePA"),
                (TRATT_UBUY_40, "Trattativa diretta UBUY sotto 40k€"),
                (TRATT_UBUY_143, "Trattativa diretta UBUY da 40k€ e sotto 140k€"),
                (INFER_5000, "Trattativa diretta sotto 5k€ con PCP"),
                (GENERIC, "Pratica generica (da utilizzare solo su " \
                          "richiesta dell'Amministrazione)"),
               )

# Tipi allegato
ALL_CIG = "CIG"
ALL_CV_RUP = 'CV RUP'
ALL_DECIS_FIRM = 'Decis. Firmata'
ALL_DICH_RUP = 'Dich. RUP'
ALL_GENERICO = "All. Generico"
ALL_LISTA_DETT = "Lista dett."
ALL_OBBLIG = "Obblig. Perf."
ALL_STIPULA = "Doc. Stipula"
ALL_PREV = "preventivo"
ALL_RDO = "RdO Firmata"

ALL_OFF_DITTA = 'off_ditta'
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

# indicatori per extra_validators

CIG = 'cig'

# Specifica allegati
ALL_SING = 0    # Allegato singolo
ALL_SPEC = 1    # Allegato multiplo con specifica
ALL_NAME = 2    # Allegato multiplo con nome file
ALL_PRAT = 3    # Allegato singolo con numero pratica

# Tabella allegati  key   pref.nome file     descrizione  singolo/multiplo
TAB_ALLEGATI = {ALL_GENERICO: ("A99_", "Documento generico", ALL_NAME),
                ALL_CV_RUP: ('A04_CV_RUP', "Curric. Vitae del RUP", ALL_SING),
                ALL_DICH_RUP: ('A05_Dich_RUP', "Dichiaraz. ass. conflitto int. del RUP", ALL_SING),
                ALL_PREV: ('A02_Preventivo', "Preventivo", ALL_SING),
                ALL_CIG: ("A12_CIG", "CIG", ALL_SING),
                ALL_RDO: ("A16_RdO_Firmata", "RdO con firma digitale RUP", ALL_SING),
                ALL_DECIS_FIRM: ("A24_Decisione_Firmata",
                                  "Decisione di contrarre con firma digitale", ALL_SING),
                ALL_LISTA_DETT: ("A30_Lista_Dettagliata",
                                 "Lista dettagliata da allegare all'ordine", ALL_SING),
                ALL_STIPULA: ("A28_Documento_Stipula",
                                  "Documento di stipula", ALL_SING),
                ALL_OBBLIG: ("A30_Obbligaz_Giurid_Perfezionata",
                                  "Obbligazione giuridicamente perfezionata", ALL_SING),
               }

class CdP(IntEnum):
    'Codici passi operativi'
    NUL = -1
    INI = 0
    GEN = 5
    PIR = 10
    PAR = 20
    RUI = 30
    IRD = 40
    AUD = 50
    PRO = 55
    ROG = 60
    DEC = 70
    DCI = 80
    ORD = 85
    ALS = 87
    OGP = 90
    END = 100
    FIN = 101
    ANN = 500

############### Tabella generale passi operativi   ############################
TABELLA_PASSI = {
    CdP.NUL: ("Inizio",
              [],
              [],
              [],
              {TRATT_MEPA_40: CdP.INI,   # prossimo passo dipende da
               TRATT_UBUY_40: CdP.INI,   # modalità acquisto
               TRATT_MEPA_143: CdP.INI,
               TRATT_UBUY_143: CdP.INI,
               CONSIP: CdP.INI,
               ACC_QUADRO: CdP.INI,
               INFER_5000: CdP.INI,
               GENERIC: CdP.GEN}),
    CdP.INI: ("Genera progetto",                     # Descrizione stato
              [DOC_PROGETTO, [PROVVISORIO]],         # File da generare per procedere (con opzioni)
              ['modificaprogetto', 'inviaprogetto'], # Comandi abilitati
              [ALL_PREV],                            # Allegati necessari per procedere
              CdP.PIR),                              # passo successivo
    CdP.GEN: ("Archiviazione documenti",             # Descrizione stato
              [],                                    # File da generare per procedere (con opzioni)
              ['chiudipratica'],                     # Comandi abilitati
              [],                                    # Allegati necessari per procedere
              CdP.FIN),                              # passo successivo
    CdP.PIR: ("Progetto inviato al resp. dei fondi",
              [],
              ['approvaprogetto'],
              [],
              CdP.PAR),
    CdP.PAR: ("Progetto approvato dal resp. dei fondi",
              [DOC_NOMINARUP, [PROVVISORIO]],
              ['indicarup'],
              [],
              CdP.RUI),
    CdP.RUI: ("RUP indicato",
              [],
              ['rich_autorizzazione'],
              [ALL_CV_RUP, ALL_DICH_RUP],
              CdP.IRD),
    CdP.IRD: ("Inviata richiesta di autorizzazione e nomina RUP al Direttore",
              [],
              ['autorizza'],
              [],
              {TRATT_MEPA_40: CdP.AUD,   # prossimo passo dipende da
               TRATT_UBUY_40: CdP.AUD,   # modalità acquisto
               TRATT_MEPA_143: CdP.AUD,
               TRATT_UBUY_143: CdP.AUD,
               CONSIP: CdP.PRO,
               ACC_QUADRO: CdP.PRO,
               INFER_5000: CdP.PRO}),
    CdP.AUD: ("Genera RdO, allega RdO firmata",
              [DOC_RDO, []],
              ['modificardo', 'procedi_rdo'],
              [ALL_RDO],
              CdP.PRO),
    CdP.PRO: ("Genera proposta di aggiudicazione",
              [DOC_PROPOSTA, []],
              ['genera_proposta', 'procedi_pro'],
              [],
              CdP.DEC),
    CdP.ROG: ("Passo non più definito",
              [],
              ['procedi'],
              [],
              CdP.DEC),
    CdP.DEC: ("Genera decisione",
              [DOC_DECISIONE, [PROVVISORIO]],
              ['modificadecisione', 'inviadecisione'],
              [ALL_CIG],
              CdP.DCI),
    CdP.DCI: ("Decisione di contrarre inviata al Direttore per firma",
              [],
              ['procedi_dci'],
              [ALL_DECIS_FIRM],
              {TRATT_MEPA_40: CdP.OGP,   # prossimo passo dipende da
               TRATT_UBUY_40: CdP.ORD,   # modalità acquisto
               TRATT_MEPA_143: CdP.OGP,
               TRATT_UBUY_143: CdP.ORD,
               CONSIP: CdP.ALS,
               ACC_QUADRO: CdP.ALS,
               INFER_5000: CdP.ORD}),
    CdP.ORD: ("Genera ordine",
              [DOC_ORDINE, []],
              ['modificaordine', 'procedi'],
              [],
              CdP.OGP),
    CdP.ALS: ("Allega documento di stipula",
              [],
              ['procedi'],
              [ALL_STIPULA],
              CdP.OGP),
    CdP.OGP: ("Allega Obbligazione giuridicamente perfezionata",
              [],
              ['procedi'],
              [ALL_OBBLIG],
              CdP.END),
    CdP.END: ("Pratica conclusa. Attesa chiusura",
              [],
              ['chiudipratica'],
              [],
              CdP.FIN),
    CdP.FIN: ("Pratica chiusa",
              [],
              ['apripratica'],
              [],
              CdP.END),
    CdP.ANN: ("Pratica annullata",
              [],
              [],
              [],
              CdP.ANN),
    }

################################################### Varie stringhe
ACCESSO_NON_PREVISTO = "Sequenza di accesso non prevista. URL: "

DETTAGLIO_PRATICA = """

-----------------------------------------
Dettaglio pratica:

Richiedente: {nome_richiedente}
Respons. dei fondi: {nome_responsabile}

Acquisto/fornitura: {descrizione_acquisto}

Motivazione:

{motivazione_acquisto}

Importo netto: {costo_netto} 

I.V.A.: {costo_iva}

Totale: {costo_totale}
"""

MESSAGGIO_DI_PROVA = '''
Invio messaggio di prova per verifica funzionamento del server.

Messaggio inviato all'indirizzo corrispondente al Webmaster
tramite {}
'''

OBBLIGATORIO = """<font color=red><b>N.B.:</b> Tutti i campi sottolineati
sono obbligatori e devono essere specificati</font>"""

TABLE_HEADER = """<!DOCTYPE html>
<html>
<head>
<title>gestione tabelle</title>
</head>
<body>
"""

TESTO_APPROVAZIONE = """
Ti è stato inviato il progetto di acquisto N. {} (vedi dettagli sotto).

Per approvare progetto e fondi, puoi accedere alla procedura Acquisti:

     {}

e selezionare: Elenco pratiche da approvare (come resp. fondi)
"""

TESTO_NOTIFICA_APPROVAZIONE = """
Il progetto di acquisto N. {numero_pratica}:

   {descrizione_acquisto}

è stato approvato dal responsabile dei fondi.
"""

TESTO_INDICA_RUP = '''
Sei stato indicato come RUP per la pratica N. {}

Sei pregato di accedere alla procedura Acquisti

      {}

per allegare alla pratica CV e dichiarazione di assenza conflitto d'interesse
e poi richiedere l'autorizzazione al direttore.
'''


TESTO_NOMINA_RUP = '''
Il direttore ha firmato la nomina a RUP per la pratica N. {}.
'''

TESTO_RICHIESTA_AUTORIZZAZIONE = '''
{nome_rup} chiede al direttore la nomina a RUP del progetto di acquisto
N. {numero_pratica} e l'autorizzazione a procedere.

Per autorizzarlo puoi accedere alla procedura Acquisti:

     {url}

e selezionare: Elenco pratiche da approvare (come Direttore)
'''

TESTO_INVIA_DECISIONE = '''
Ti è stata inviata la decisione di contrarre relativa al progetto di acquisto
N. {numero_pratica} sotto dettagliato.

Il documento: {decis_da_firmare} deve essere inviato al direttore per la firma digitale.

'''

BINDIR = os.path.dirname(os.path.abspath(__file__))  # Path della directory eseguibili
PKG_ROOT = os.path.abspath(os.path.join(BINDIR, ".."))  # Path della root del package

AUXFILEDIR = "files"          # nome directory per file ausiliari

DATADIR = os.path.join(PKG_ROOT, "data")     # path della directory per i dati"
FILEDIR = os.path.join(PKG_ROOT, AUXFILEDIR)  # path della directory dei files ausiliari"
WORKDIR = os.path.join(PKG_ROOT, "work")      # path della directory di lavoro"

CONFIG_FILE = os.path.join(DATADIR, CONFIG_NAME)

# VARIABILI MANTENUTE PER COMPATIBILITA' DURANTE MODIFICHE

RDO_MEPA = 'rdo_mepa'          # modalità acquisto
