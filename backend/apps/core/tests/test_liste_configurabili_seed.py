# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio TRASVERSALE del contratto fra il seed delle liste
#        configurabili (`ui.lista_colonna`) e le whitelist di ordinamento dei
#        repository. Test senza DB (unittest.TestCase): leggono i CSV di seed e
#        le costanti del codice, quindi girano anche in CI.
#
#        Vive in `apps/core` e non in un dominio perche' il contratto e' del
#        building block `<ListaConfigurabile>`, non di vendite o anagrafiche:
#        ogni lista che si converte si aggiunge a `_LISTE`, e il presidio la
#        copre senza scrivere un test nuovo.
# ------------------------------------------------------------
"""Indice test (parametrici su ogni lista registrata in `_LISTE`):

1. test_whitelist_copre_le_colonne_ordinabili
   Ogni colonna ATTIVA e `ordinabile = t` nel seed sta nella whitelist del suo
   repository: altrimenti l'intestazione mostra una freccia che, al click,
   risponde 400.

2. test_seed_offre_tutto_cio_che_il_backend_sa_ordinare
   Il verso opposto: nessuna capacita' di ordinamento resta irraggiungibile
   dall'operatore.

3. test_whitelist_chiavata_sul_campo_sorgente
   `<ListaConfigurabile>` monta le Column con `:field="col.campo_sorgente"`,
   quindi `event.sortField` porta il nome FISICO. Chiavare la whitelist sui
   `codice` logici romperebbe proprio le colonne dove i due divergono — e' il
   difetto trovato su `vendite.lotti` il 2026-07-31.

4. test_colonna_azione_mai_ordinabile
   `tipo_colonna='azione'` non ha campo sorgente: ordinarla non significa nulla.

4-bis. test_lo_slot_delle_azioni_si_chiama_actions
   ⛔ Chi monta `<ListaConfigurabile>` deve fornire lo slot `#actions`, non
   `#cell-azioni`. Il BB rende la colonna delle azioni solo se la config la
   dichiara **e** il caller passa quello slot: col nome sbagliato la colonna
   non viene resa affatto — nessun kebab e NESSUN errore. Difetto reale su
   `LottoDrawer.vue`, visto solo in app il 2026-08-24.

4-ter. test_chi_fornisce_lo_slot_actions_ha_la_colonna_a_catalogo
   Il VERSO OPPOSTO del 4-bis (BE-3): chi fornisce lo slot pretende che la
   lista abbia una colonna `azione` a catalogo. Senza, il BB non rende la
   colonna e le azioni di riga spariscono senza che niente fallisca — e' il
   difetto DB-1, trovato convertendo e non da un test.

5. test_ogni_lista_del_seed_ha_un_preset_default
   Senza preset `is_default` la lista non ha una configurazione di partenza.

6. test_registro_copre_tutte_le_liste_montate_dal_frontend
   Chiude il buco del registro: una lista convertita ma non aggiunta a `_LISTE`
   sfuggirebbe a TUTTI i test sopra, in silenzio. La fonte di verita' e' il
   frontend — chi monta `<ListaConfigurabile codice="X">` dichiara di aver
   convertito X.

7. test_colonna_sensibile_ha_sempre_un_grant
   `sensibile = t` senza riga in `ui.lista_colonna_permesso` non protegge: la
   colonna viene RIMOSSA per tutti, e il badge «colonne nuove» continua a
   contarla. Cancello su un difetto DB noto e non ancora corretto.

8-bis. test_le_liste_locali_sono_montate_non_paginate
   Chiude il cerchio della sentinella `ORDINAMENTO_LOCALE`: una lista dichiarata
   «ordina nel browser» DEVE essere montata con `:paginata="false"`. Se qualcuno
   togliesse la prop, la lista tornerebbe a ordinare lato server — dove non ha
   nessuna whitelist — e la freccia risponderebbe 400 al primo click, mentre
   questo registro continuerebbe a dire che va tutto bene.

8. test_il_debito_non_cresce
   `_DEBITO_WHITELIST_LOGICA` e' un registro di debito, non una lista di
   eccezioni: una lista rientrata va tolta, o il debito residuo risulta piu'
   grande del vero e l'eccezione diventa permanente.

9. test_ogni_formato_del_seed_e_reso_dal_frontend
   Ogni `formato` scritto nel seed e' uno che `CellaConfigurabile.formatValue`
   conosce. Un formato sconosciuto NON da' errore: cade su `String(value)` e la
   colonna esce come testo grezzo — su `natura_doc` la descrizione senza Tag, su
   un `yesno` scritto male «true»/«false». Il vocabolario si LEGGE dal `.vue`,
   non si ricopia qui.

9-bis. test_la_gemella_di_un_formato_si_legge_dal_frontend
   Il verso che arma `campi_gemelli_per_formato` (letto da
   `test_lista_proiezione_campo_sorgente`): il nome della colonna gemella che
   `natura_doc` pretende nella riga arriva dal sorgente FE, e se il FE lo
   rinomina senza che questa lettura lo trovi il test fa rosso — non verde a
   vuoto.

10. test_le_colonne_data_dichiarate_sono_quelle_del_seed
   `sql_order_clause(colonne_desc=…)` e' il ripiego DESC delle colonne DATA
   quando il client manda `order_by` senza `order_dir` (regola di Tid del
   2026-09-02). Quell'insieme e' scritto A MANO in ogni repository che lo
   dichiara, e fino al 18/09 nessuno lo confrontava col `tipo_dato` del seed:
   una data ordinabile che manca dall'insieme ripiega ASC — nessun errore, la
   lista si apre dal 2019 — e un nome che nel seed non e' piu' una data resta
   nell'insieme a raccontare una colonna che non c'e'. L'insieme si LEGGE dal
   sito di chiamata (`colonne=` accanto a `colonne_desc=`), non da un secondo
   registro di nomi.

10-bis. test_il_debito_del_ripiego_asc_non_cresce
   Le liste con date ordinabili il cui `sql_order_clause` NON dichiara
   `colonne_desc` sono un REGISTRO DI DEBITO (`_DEBITO_RIPIEGO_DATA_ASC`):
   li' il ramo senza `order_dir` ripiega ASC su una data. Oggi e' dormiente —
   `useSearchTable.onSort` manda sempre i due campi — ma il contratto e'
   dichiarato ammesso e va provato per intero. Il registro puo' solo calare:
   una lista che dichiara il ripiego va tolta, una nuova senza ripiego fa rosso.

⚠️ I test 1-3 girano su `_liste_allineate()`, cioe' tutte tranne il debito noto.
I test 4-6 girano su TUTTE: valgono a prescindere dalla chiave della whitelist.
"""

import csv
import re
import unittest
from functools import lru_cache
from apps.core.tests._repo import repo_root


_SEED_DIR = repo_root() / "db/changelog/migrations_v2/80_data/sql/ui"


# Scopo: sorgente `.vue` senza commenti. Serve a distinguere chi USA uno slot da
#        chi lo NOMINA — un presidio che cerca una PAROLA si accende sui
#        messaggi, ed e' successo il 2026-08-26: un commento che citava
#        `#cell-azioni` per spiegare il difetto ha fatto diventare rosso il
#        test che quel difetto presidia.
# ⭐ Non e' una toppa: il guard gemello `frontend/scripts/check-liste-configurabili.mjs`
#    ha `senzaCommenti()` dal primo giorno, con la stessa motivazione scritta
#    accanto. Qui mancava, ed era l'unica differenza fra i due.
def _senza_commenti(testo: str) -> str:
    senza_html = re.sub(r"<!--.*?-->", "", testo, flags=re.S)
    senza_blocco = re.sub(r"/\*.*?\*/", "", senza_html, flags=re.S)
    return re.sub(r"^\s*//.*$", "", senza_blocco, flags=re.M)


# Scopo: TUTTI i montaggi di lista del frontend, letti UNA volta sola.
#        Per ogni `<ListaConfigurabile codice="X">` / `<DrawerTabLista codice="X">`
#        ritorna il codice, il TAG DI APERTURA (gli attributi) e il CORPO (gli
#        slot), che sono le tre cose su cui i test di questo modulo interrogano
#        il frontend.
#
# ⭐ Estratto il 2026-09-02 alla TERZA copia (regola del 2). Le tre erano nello
#    stesso file e divergevano gia': due cercavano il tag con `_tag_apertura`,
#    la terza con una finestra a caratteri — cioe' la versione che il 02-09
#    stesso era stata corretta perche' sbagliava in direzione «verde».
# ⚠️ E percorrevano `frontend/src` **tre volte**: `lru_cache` perche' un
#    presidio lento e' un presidio che prima o poi qualcuno toglie dalla corsa
#    veloce (stessa ragione scritta in `test_perimetro_emittente_copertura`).
@lru_cache(maxsize=1)
def _montaggi_lista() -> tuple[tuple[str, str, str, str], ...]:
    src = repo_root() / "frontend/src"
    trovati: list[tuple[str, str, str, str]] = []
    for percorso in src.rglob("*.vue"):
        senza_commenti = _senza_commenti(percorso.read_text(encoding="utf-8"))
        # ⛔ Non un componente solo. Una lista si monta con
        #    `<ListaConfigurabile>`, con `<DrawerTabLista>` o con
        #    `<ListaPaginaSemplice>`: cercare
        #    solo il primo rende il censimento cieco sulle liste nate per ultime
        #    (successo con `vendite.registri_numerazione`, 2026-09-01).
        # ⭐ E dal 2026-09-27 `<ListaPaginaSemplice>`, la pagina-lista chiusa
        #    (le sei geografiche): stesso `codice="X"`, stessi slot di cella.
        for tag in ("ListaConfigurabile", "DrawerTabLista", "ListaPaginaSemplice"):
            for m in re.finditer(rf"<{tag}\b", senza_commenti):
                apertura = _tag_apertura(senza_commenti, m.start())
                # `(?<![:@\w-])codice=` esclude i binding DINAMICI
                # (`:codice="var"`): il loro valore non e' risolvibile
                # staticamente. Sono coperti lo stesso — `ResiCodaTable` sceglie
                # fra due costanti, entrambe in `_LISTE`.
                mc = re.search(r'(?<![:@\w-])codice="([^"]+)"', apertura)
                if not mc:
                    continue
                inizio = m.start() + len(apertura)
                fine = senza_commenti.find(f"</{tag}>", inizio)
                corpo = senza_commenti[inizio:fine if fine != -1 else len(senza_commenti)]
                trovati.append((mc.group(1), apertura, corpo, percorso.name))
    return tuple(trovati)


# Scopo: il TAG DI APERTURA che comincia a `inizio`, fino al `>` che lo chiude.
#
# ⛔ Non si puo' usare una regex `[^>]*`: un `>` vive dentro gli attributi
#    (`v-if="documentiCount > 0"`) e la classe negata si fermerebbe li' — e' il
#    difetto gia' corretto nel test 6 il 2026-08-03.
# ⛔ E non si puo' usare una FINESTRA a caratteri, che e' la scorciatoia in cui
#    ero cascato: se l'attributo cercato cade appena oltre la finestra il test
#    non lo trova e passa. Un guard che sbaglia in direzione «verde» e' peggio
#    di uno assente, perche' qualcuno ci conta.
# ⇒ Si scandisce carattere per carattere tenendo conto delle virgolette: il `>`
#   dentro un valore quotato non chiude niente. In un template Vue i valori
#   degli attributi sono sempre quotati, quindi la scansione e' esatta.
def _tag_apertura(testo: str, inizio: int) -> str:
    virgoletta: str | None = None
    for i in range(inizio, len(testo)):
        c = testo[i]
        if virgoletta is not None:
            if c == virgoletta:
                virgoletta = None
        elif c in "\"'":
            virgoletta = c
        elif c == ">":
            return testo[inizio:i + 1]
    return testo[inizio:]


# Scopo: whitelist di ordinamento di una lista il cui ORDINE vive nella funzione
#        DB, non in Python — letta dalla doc auto-gen della funzione.
#
# ⭐ RIUSA il lettore di `scripts/gen_seed_lista.py` invece di ricopiarne la
#    regex: le due letture devono dare lo stesso insieme, e due regex gemelle
#    sono il modo classico per farle divergere quando una delle due funzioni
#    cambia forma. Il generatore e' gia' la sede di quel parsing.
# ⚠️ Import per percorso e non `from scripts...`: `scripts/` non e' un package
#    e non sta sul path del runner Django.
def _whitelist_da_funzione_db(percorso_doc: str):
    def risolvi() -> set[str]:
        import importlib.util

        sorgente = repo_root() / "scripts" / "gen_seed_lista.py"
        spec = importlib.util.spec_from_file_location("_gen_seed_lista", sorgente)
        assert spec and spec.loader
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return modulo.whitelist_funzione_db(percorso_doc)

    return risolvi


# Scopo: whitelist di ordinamento di ogni lista convertita, risolta pigramente
#        (import dentro la lambda) per non legare l'import di questo modulo a
#        tutti i repository coinvolti.
def _whitelist_lotti() -> set[str]:
    from apps.vendite.db.vendite_repository import VenditeRepository

    return set(VenditeRepository.LOTTI_SORT_COLUMNS)


def _whitelist_categorie_clienti() -> set[str]:
    from apps.anagrafiche.db import categorie_clienti_repository as m

    return set(m._ORDER_COLS)


def _whitelist_utilities_tipi_ruolo() -> set[str]:
    from apps.config.db import utilities_tipi_ruolo_repository as m

    return set(m._ORDER_COLS)


def _whitelist_indirizzi() -> set[str]:
    from apps.anagrafiche.db import indirizzi_repository as m

    return set(m._ORDER_COLS)


def _whitelist_tipi_ruolo_tipi_indirizzo() -> set[str]:
    from apps.config.db import tipi_ruolo_tipi_indirizzo_repository as m

    return set(m._ORDER_COLS)


# Scopo: whitelist del tab BA dell'emittente. Vive come attributo di CLASSE
#        (come `LOTTI_SORT_COLUMNS`), non come costante di modulo.
def _whitelist_emittente_billing_account() -> set[str]:
    from apps.anagrafiche.db.emittenti_fiscali_repository import (
        EmittentiFiscaliBillingAccountRepository,
    )

    return set(EmittentiFiscaliBillingAccountRepository._ORDER_COLS)


# Scopo: whitelist delle due CODE resi. ⚠️ Non sono `_ORDER_COLS_RESI`: le code
#        leggono viste dedicate e hanno mappe proprie in `_CODA_META`, indicizzate
#        per nome vista. Il registro le ha attribuite alla costante sbagliata fino
#        al 2026-07-31 — stesso inganno del difetto che questo modulo presidia:
#        una whitelist va letta dal simbolo che il repository USA, non da quello
#        che sembra suo per nome.
def _whitelist_coda_resi(vista: str):
    def risolvi() -> set[str]:
        from apps.vendite.db import resi_repository as m

        return set(m._CODA_META[vista]["order_cols"])

    return risolvi


# Scopo: risolutore per le 5 whitelist delle dashboard vendite, che vivono
#        come ClassVar di `VenditeRepository` (cinque nello stesso modulo:
#        una costante di modulo per ognuna sarebbe stata piu' rumore che
#        informazione). L'ancora e' la classe, non il modulo.
def _whitelist_di_classe(attributo: str):
    def risolvi() -> set[str]:
        from apps.vendite.db.vendite_repository import VenditeRepository

        return set(getattr(VenditeRepository, attributo))

    return risolvi


# Scopo: fabbrica di risolutori per le whitelist che vivono in una costante di
#        modulo con nome proprio (la maggioranza). Evita nove funzioni identiche
#        a meno del nome — le uniche scritte a mano sopra sono quelle con una
#        forma diversa (attributo di classe, `_ORDER_COLS` senza suffisso).
def _da_costante(modulo: str, costante: str):
    def risolvi() -> set[str]:
        import importlib

        return set(getattr(importlib.import_module(modulo), costante))

    # ⭐ Il test 10 deve TROVARE il sito di chiamata di `sql_order_clause` che
    #    usa questa whitelist, per leggere il `colonne_desc` accanto: il nome
    #    della costante e il modulo restano attaccati al risolutore, invece di
    #    vivere in un secondo elenco che invecchia per conto suo.
    risolvi.modulo = modulo
    risolvi.costante = costante
    return risolvi


# Scopo: risolutore per le RIGHE di un documento di vendita, che ordinano
#        tramite il BB `RigheDocumentoRepositoryMixin` (brief-db-liste-righe-
#        documento, lotto A, 2026-09-28): whitelist e colonne DESC sono
#        attributi della CLASSE del repository, e la chiamata a
#        `sql_order_clause` sta nel mixin, non nel modulo.
# ⛔ Per questo porta con se' `colonne_desc`: senza, il test 10 cercherebbe
#    il sito di chiamata nel modulo del repository, non lo troverebbe, e
#    salterebbe la lista — verde per sottrazione su quattro liste con date.
def _da_righe_documento(modulo: str, classe: str):
    def _classe():
        import importlib

        return getattr(importlib.import_module(modulo), classe)

    def risolvi() -> set[str]:
        return set(_classe().righe_colonne_ordinabili())

    risolvi.colonne_desc = lambda: {
        f"{classe}._righe_colonne_desc": set(_classe()._righe_colonne_desc),
    }
    return risolvi


# Sentinella per le liste montate con `:paginata="false"` (2026-09-02).
# ⭐ Non hanno una whitelist di ordinamento lato backend perche' NON ordinano
#    lato backend: l'ordine lo calcola PrimeVue nel browser, sulle righe gia'
#    consegnate. Chiedere loro una whitelist significherebbe pretendere un
#    contratto con un interlocutore che non esiste.
# ⛔ NON e' `_DEBITO_WHITELIST_LOGICA`, ed e' una distinzione che va tenuta:
#    quello e' un REGISTRO DI DEBITO e deve calare, questa e' una PROPRIETA'
#    della lista e resta. Confonderli farebbe sembrare debito una scelta, e
#    sparire dal debito una cosa che debito non e'.
ORDINAMENTO_LOCALE = "ordinamento-locale"


# Registro delle liste convertite: `codice` -> risolutore della whitelist di
# ordinamento del suo repository.
#
# ⚠️ **Aggiungere una riga a ogni conversione.** Non e' un promemoria: se manca,
# `test_registro_copre_tutte_le_liste_montate_dal_frontend` diventa rosso —
# perche' una lista assente da qui sfuggirebbe in silenzio a tutti gli altri
# test di questo modulo.
_LISTE: tuple[tuple[str, object], ...] = (
    # Convertite 2026-07-30/31.
    ("vendite.lotti", _whitelist_lotti),
    ("anagrafiche.categorie_clienti", _whitelist_categorie_clienti),
    ("config.utilities_tipi_ruolo", _whitelist_utilities_tipi_ruolo),
    ("anagrafiche.indirizzi", _whitelist_indirizzi),
    ("config.tipi_ruolo_tipi_indirizzo", _whitelist_tipi_ruolo_tipi_indirizzo),
    # Secondo lotto, 2026-07-31 (seed nato gia' in regola: `pratiche` e il tab
    # BA non hanno chiesto nulla al backend, emittenti solo `partita_iva`).
    ("pratiche.pratiche", _da_costante("apps.pratiche.db.pratiche_repository", "PRATICHE_ORDER_COLS")),
    ("anagrafiche.emittenti_fiscali", _da_costante("apps.anagrafiche.db.emittenti_fiscali_repository", "_EMITTENTI_ORDER_COLS")),
    ("anagrafiche.emittente_billing_account", _whitelist_emittente_billing_account),
    # Terzo lotto, 2026-08-01: le tre liste UoM di catalogo. L'ordinamento
    # server-side non esisteva quando erano state scartate; ora c'e', e le
    # mappe vivono come costanti di modulo del repository.
    ("catalogo.uom_tipi", _da_costante("apps.catalogo.db.catalogo_repository", "UOM_TIPI_ORDER_COLUMNS")),
    ("catalogo.unita_misura", _da_costante("apps.catalogo.db.catalogo_repository", "UOM_ORDER_COLUMNS")),
    ("catalogo.conversioni_uom", _da_costante("apps.catalogo.db.catalogo_repository", "UOM_CONVERSIONI_ORDER_COLUMNS")),
    # Quarto lotto, 2026-08-01.
    ("vendite.promo_articoli", _da_costante("apps.vendite.db.promo_articoli_repository", "_ORDER_COLS")),
    ("documenti.template_documenti", _da_costante("apps.documenti.db.documenti_repository", "TEMPLATES_ORDER_COLUMNS")),
    ("documenti.template_asset", _da_costante("apps.documenti.db.documenti_repository", "ASSET_ORDER_COLUMNS")),
    # I documenti generati di una sorgente e le versioni di un template
    # (2026-09-27, brief-db-liste-datatable-grezze righe 2 e 6): fino a quel
    # giorno `DataTable` grezze — i documenti troncati a 50 senza dirlo, le
    # versioni senza pagine.
    ("documenti.documenti_sorgente",
     _da_costante("apps.documenti.db.documenti_repository", "DOCUMENTI_SORGENTE_ORDER_COLUMNS")),
    ("documenti.template_versioni",
     _da_costante("apps.documenti.db.documenti_repository", "TEMPLATE_VERSIONI_ORDER_COLUMNS")),
    # Quinto lotto, 2026-08-01.
    ("catalogo.articoli", _da_costante("apps.catalogo.db.catalogo_repository", "ARTICOLI_ORDER_COLUMNS")),
    ("vendite.listini", _da_costante("apps.vendite.db.listini_repository", "LISTINI_ORDER_COLUMNS")),
    # Le versioni di un listino (2026-10-31, brief-db-liste-datatable-grezze-
    # secondo-giro riga 5): fino a quel giorno la riga espansa della lista.
    # Note e UoM (2026-10-31, secondo giro righe 3 e 4): le due liste di note
    # sono gemelle, sulla stessa whitelist.
    ("vendite.note", _da_costante("apps.core.db.partitioned_note_repository", "NOTE_ORDER_COLUMNS")),
    ("catalogo.note", _da_costante("apps.core.db.partitioned_note_repository", "NOTE_ORDER_COLUMNS")),
    ("catalogo.articolo_uom", _da_costante("apps.catalogo.db.catalogo_uom_repository", "ARTICOLO_UOM_ORDER_COLUMNS")),
    # La ricerca universale (2026-10-31, secondo giro riga 6).
    ("anagrafiche.ricerca_soggetti", _da_costante("apps.core.api.search_validators", "ALLOWED_ORDER_COLUMNS")),
    # Le impostazioni (2026-10-31, secondo giro riga 2).
    ("config.parametri_impostazioni", _da_costante("apps.core.db.parameter_repository", "IMPOSTAZIONI_ORDER_COLUMNS")),
    # Le edizioni di workflow (2026-10-31, secondo giro riga 1).
    ("pratiche.definizioni_workflow", _da_costante("apps.pratiche.db.definizioni_repository", "DEFINIZIONI_ORDER_COLUMNS")),
    ("vendite.listini_versioni", _da_costante("apps.vendite.db.listini_repository", "VERSIONI_ORDER_COLUMNS")),
    # Sesto lotto, 2026-08-01/02.
    ("config.email_account", _da_costante("apps.core.db.email_repository", "EMAIL_ACCOUNT_ORDER_COLUMNS")),
    ("config.email_template", _da_costante("apps.core.db.email_repository", "EMAIL_TEMPLATE_ORDER_COLUMNS")),
    ("config.email_log", _da_costante("apps.core.db.email_repository", "EMAIL_LOG_ORDER_COLUMNS")),
    ("anagrafiche.categorie_clienti_listini", _da_costante("apps.anagrafiche.db.categorie_clienti_listini_repository", "_ORDER_COLS")),
    ("anagrafiche.operatori", _da_costante("apps.amm_software.db.amm_software_repository", "ALLOWED_ORDER_COLUMNS")),
    # L'area «Accessi» (2026-10-02, brief-db-be-fe-area-accessi R-BE-d).
    ("anagrafiche.accessi_altri", _da_costante("apps.amm_software.db.accessi_repository", "ACCESSI_ALTRI_ORDER_COLUMNS")),
    ("anagrafiche.accessi_sistema", _da_costante("apps.amm_software.db.accessi_repository", "ACCESSI_SISTEMA_ORDER_COLUMNS")),
    # `storico.audit_log` era sospesa: il seed aveva 4 colonne e la pagina ne
    # mostra 5 (mancava la calcolata *Dettaglio*). Riga 378 aggiunta dal team DB
    # il 2026-08-02, conversione completata. E' l'unica lista polimorfa
    # (`storico.{code}` scelto a runtime da `script.vw_audit_sources`).
    ("storico.audit_log", _da_costante("apps.amm_software.db.amm_software_repository", "AUDIT_ORDER_COLUMNS")),
    # Settimo lotto, 2026-08-03: le due code Strumenti + la coda approvazioni
    # prezzo (che attraversa `cerca_pratiche`, stessa whitelist della lista
    # pratiche) + le righe versione listino (endpoint UNION standalone+compositi,
    # decisione Tid 2026-08-02). Le whitelist delle code sono i dizionari
    # nome->SQL dei rispettivi repository: `set(dict)` = le chiavi.
    # ⭐ La SETTIMA lista del ciclo attivo, 2026-08-24: fino ad allora la fattura
    # era l'unico documento senza la sua, e si raggiungeva solo passando da un
    # lotto o da un collegamento.
    ("vendite.fatture", _da_costante("apps.vendite.db.fatture_repository", "_ORDER_COLS_FATTURE")),
    ("dbops.coda_lavori", _da_costante("apps.core.services.coda_lavori.repository", "ELENCA_SORT_SQL")),
    ("vendite.fatture_stampa_coda", _da_costante("apps.vendite.db.pipeline_repository", "CODA_STAMPA_SORT_SQL")),
    ("vendite.approvazioni_prezzo", _da_costante("apps.pratiche.db.pratiche_repository", "PRATICHE_ORDER_COLS")),
    ("vendite.listini_righe", _da_costante("apps.vendite.db.listini_repository", "RIGHE_ORDER_COLUMNS")),
    # Ottavo lotto, 2026-08-03: il drawer commessa + le 5 liste delle 3
    # dashboard vendite. Chiude il Gruppo A.
    #
    # ⚠️ `commesse_attivita` e' la PRIMA lista la cui whitelist NON vive in
    # Python: ordine e paginazione stanno dentro `fn_list_commessa_attivita`
    # (ordinare a valle ordinerebbe la pagina gia' estratta), e il BE ne tiene
    # solo lo specchio per validare prima del round-trip. E' quello specchio
    # che il presidio confronta col seed: se i due divergessero, il BE
    # rifiuterebbe una colonna che la funzione accetta (o viceversa).
    ("vendite.commesse_attivita", _da_costante("apps.vendite.db.commesse_repository", "ATTIVITA_SORT_COLUMNS")),
    # ══════════════════════════════════════════════════════════════════
    # Le tre liste del drawer lotto di fatturazione (L3 del team DB,
    # seed 2026-08-22). Registrate PRIMA della conversione dei `.vue`
    # (FE-2): il registro copre gia' i test 1-6, che leggono il seed e
    # non il frontend — e una lista che nasce senza presidio viene
    # dichiarata a posto senza essere stata guardata.
    # ══════════════════════════════════════════════════════════════════
    ("vendite.lotto_fatture",
     _da_costante("apps.vendite.db.vendite_repository", "LOTTO_FATTURE_SORT_COLUMNS")),
    # ⭐ Le due sotto NON hanno una whitelist Python, e non e' una dimenticanza:
    # ordine e paginazione stanno nella stessa funzione DB (ordinare a valle
    # ordinerebbe la pagina gia' estratta), e tenerne uno specchio nel backend
    # sarebbe una seconda verita' da riallineare a mano a ogni colonna nuova.
    # Si legge quindi dalla doc auto-gen della funzione — la stessa sorgente che
    # usa `gen_seed_lista.py`.
    ("vendite.lotto_task_runs",
     _whitelist_da_funzione_db("docs/it/dbzero/vendite/funzioni/fn_list_lotto_task_runs.md")),
    ("vendite.lotto_segnalazioni",
     _whitelist_da_funzione_db("docs/it/dbzero/vendite/funzioni/fn_list_lotto_segnalazioni.md")),
    # ⭐ La QUARTA scheda del drawer lotto (2026-09-06,
    # brief-db-esito-gruppo-lotto): i DOCUMENTI presi in carico, con l'esito di
    # ciascuno. Registrata nello STESSO passo in cui nasce il seed — una lista
    # che nasce senza presidio viene dichiarata a posto senza essere stata
    # guardata, ed e' la lezione dei residui di competenza.
    ("vendite.lotto_gruppi",
     _da_costante("apps.vendite.db.vendite_repository", "LOTTO_GRUPPI_SORT_COLUMNS")),
    # Montata il 2026-08-22 (Vendite -> Tool fatturazione, primo tab). Era
    # seedata dal 15-08 e SENZA consumatore frontend: il registro contava 46
    # liste montate contro 47 codici a catalogo, e la differenza era questa.
    ("vendite.fondi_fattura_da_decidere",
     _whitelist_di_classe("FONDI_DA_DECIDERE_SORT_COLUMNS")),
    ("vendite.dash_aperto_documenti", _whitelist_di_classe("DASH_APERTO_SORT_COLUMNS")),
    ("vendite.dash_backlog_documenti", _whitelist_di_classe("DASH_BACKLOG_SORT_COLUMNS")),
    ("vendite.dash_competenza_errori", _whitelist_di_classe("DASH_COMPETENZA_ERRORI_SORT_COLUMNS")),
    ("vendite.dash_competenza_gruppi", _whitelist_di_classe("DASH_COMPETENZA_GRUPPI_SORT_COLUMNS")),
    ("vendite.dash_competenza_commesse", _whitelist_di_classe("DASH_COMPETENZA_COMMESSE_SORT_COLUMNS")),
    # Lista dei RESIDUI (2026-08-27): l'elenco su cui agisce «Riporta da
    # emettere». ⭐ Registrata nello STESSO passo in cui il frontend la monta,
    # ed e' il presidio ad averlo imposto: montandola senza registrarla
    # `test_registro_copre_tutte_le_liste_montate_dal_frontend` e' andato
    # rosso da solo, che e' esattamente il suo mestiere.
    ("vendite.dash_competenza_residui", _whitelist_di_classe("DASH_COMPETENZA_RESIDUI_SORT_COLUMNS")),
    # Preesistenti: erano fuori da qualunque presidio prima del 2026-07-31.
    ("anagrafiche.clienti", _da_costante("apps.anagrafiche.db.clienti_repository", "_CLIENTI_ORDER_COLS")),
    ("anagrafiche.fornitori", _da_costante("apps.anagrafiche.db.fornitori_repository", "_FORNITORI_ORDER_COLS")),
    ("anagrafiche.soggetti", _da_costante("apps.anagrafiche.db.soggetti_repository", "_SOGGETTI_ORDER_COLS")),
    ("vendite.contratti", _da_costante("apps.vendite.db.contratti_repository", "_ORDER_COLS_CONTRATTI")),
    ("vendite.ddt", _da_costante("apps.vendite.db.ddt_repository", "_ORDER_COLS_DDT")),
    ("vendite.offerte", _da_costante("apps.vendite.db.offerte_repository", "_ORDER_COLS_OFFERTE")),
    ("vendite.ordini", _da_costante("apps.vendite.db.ordini_repository", "_ORDER_COLS_ORDINI")),
    ("vendite.preventivi", _da_costante("apps.vendite.db.preventivi_repository", "_ORDER_COLS_PREVENTIVI")),
    # I due tab «Revisioni» (2026-09-27, brief-db-liste-datatable-grezze §4
    # righe 7 e 8): colonne GEMELLE, whitelist SEPARATE da quelle delle liste
    # principali (che `rev`/`revisione_numero` non li ordinano, §7.3).
    # ⚠️ Montate da `RevisioniTab` con `:codice` dinamico: il test 6 non le
    #    vede nel frontend, e' questa riga a registrarle.
    ("vendite.preventivo_revisioni",
     _da_costante("apps.vendite.db.preventivi_repository", "PREVENTIVO_REVISIONI_ORDER_COLUMNS")),
    ("vendite.offerta_revisioni",
     _da_costante("apps.vendite.db.offerte_repository", "OFFERTA_REVISIONI_ORDER_COLUMNS")),
    ("vendite.resi", _da_costante("apps.vendite.db.resi_repository", "_ORDER_COLS_RESI")),
    ("vendite.resi_da_accreditare", _whitelist_coda_resi("vendite.vw_resi_da_accreditare")),
    ("vendite.resi_da_riconsegnare", _whitelist_coda_resi("vendite.vw_resi_da_riconsegnare")),
    # ══════════════════════════════════════════════════════════════════
    # Le quattro liste del cantiere INCASSI (seed lotto 9 del team DB,
    # 2026-08-27; montate dal frontend il 2026-08-28).
    #
    # 🔴 E QUI IL PRESIDIO HA TROVATO UN DIFETTO VERO, non solo una riga
    # mancante. Le quattro whitelist erano chiavate sul `codice` LOGICO
    # del seed — perche' cosi' diceva il brief con cui il team DB le ha
    # generate, e cosi' era stato verificato: `codice` contro chiave, in
    # entrambi i versi, tutto combaciante. Ma il confronto era fra le
    # cose sbagliate: `<ListaConfigurabile>` monta `:field="campo_sorgente"`,
    # quindi al click PrimeVue manda il nome FISICO. Le SETTE colonne in
    # cui i due nomi divergono — `stato`, `centro`, `distinta`, `fattura`
    # (×2), `cliente` — avrebbero risposto **400** su un gesto normale.
    # ⭐ Non l'ha trovato una rilettura: l'ha trovato questo test, andando
    # rosso da solo appena le liste sono state montate.
    # ══════════════════════════════════════════════════════════════════
    ("pagamenti.distinte",
     _da_costante("apps.pagamenti.db.pagamenti_repository", "DISTINTE_SORT_COLUMNS")),
    ("pagamenti.righe",
     _da_costante("apps.pagamenti.db.pagamenti_repository", "RIGHE_SORT_COLUMNS")),
    # Le righe di UNA distinta (lista 69, 2026-09-18): dal drawer, con la
    # paginazione e l'export che la DataTable grezza non aveva.
    ("pagamenti.distinta_righe",
     _da_costante("apps.pagamenti.db.pagamenti_repository", "DISTINTA_RIGHE_SORT_COLUMNS")),
    # Magazzino, Lotto 2 (2026-09-18, piano-be-fe-magazzino-lotto-2-motore §4.3):
    # le otto liste del motore, seedate PRIMA del frontend. ⭐ Inventari e
    # rettifiche condividono la proiezione (una famiglia, Q-1) e quindi la
    # whitelist; le righe NO — la chiave della quantita' e' fisica e diversa
    # (`qta_contata` / `qta_delta`), e una whitelist unica dichiarerebbe su
    # ogni famiglia una colonna che la sua SELECT non ha (un 500 «ammesso»).
    ("magazzino.inventari",
     _da_costante("apps.magazzino.db.magazzino_repository", "DOCUMENTI_SORT_COLUMNS")),
    ("magazzino.rettifiche",
     _da_costante("apps.magazzino.db.magazzino_repository", "DOCUMENTI_SORT_COLUMNS")),
    # Righe dei documenti di vendita (2026-09-28, brief-db-liste-righe-documento
    # lotto A): whitelist sulla classe del repository, via il mixin.
    ("vendite.preventivo_righe",
     _da_righe_documento("apps.vendite.db.preventivi_repository", "PreventiviRepository")),
    ("vendite.ordine_righe",
     _da_righe_documento("apps.vendite.db.ordini_repository", "OrdiniRepository")),
    ("vendite.ddt_righe",
     _da_righe_documento("apps.vendite.db.ddt_repository", "DdtRepository")),
    ("vendite.reso_righe",
     _da_righe_documento("apps.vendite.db.resi_repository", "ResiRepository")),
    # La distinta base (2026-09-28, lotto C): lista 101 sulla vista della BoM.
    ("catalogo.articolo_componenti",
     _da_costante("apps.catalogo.db.catalogo_bom_repository", "COMPONENTI_SORT_COLUMNS")),
    # Le righe di una fattura (2026-09-28, lotto C): lista 102.
    ("vendite.fattura_righe",
     _da_costante("apps.vendite.db.fatture_repository", "_ORDER_COLS_RIGHE_FATTURA")),
    # Le righe di un contratto (2026-09-30, lotto D): lista 103.
    ("vendite.contratto_righe",
     _da_costante("apps.vendite.db.contratti_repository", "_ORDER_COLS_RIGHE_CONTRATTO")),
    # Le righe di un'offerta (2026-10-05): lista 106, gemella della 103.
    ("vendite.offerta_righe",
     _da_costante("apps.vendite.db.offerte_repository", "_ORDER_COLS_RIGHE_OFFERTA")),
    ("magazzino.inventario_righe",
     _da_costante("apps.magazzino.db.magazzino_repository", "INVENTARIO_RIGHE_SORT_COLUMNS")),
    ("magazzino.rettifica_righe",
     _da_costante("apps.magazzino.db.magazzino_repository", "RETTIFICA_RIGHE_SORT_COLUMNS")),
    ("magazzino.inventario_piano",
     _da_costante("apps.magazzino.db.magazzino_repository", "PIANO_SORT_COLUMNS")),
    ("magazzino.disponibilita",
     _da_costante("apps.magazzino.db.magazzino_repository", "DISPONIBILITA_SORT_COLUMNS")),
    ("magazzino.disponibilita_articoli",
     _da_costante("apps.magazzino.db.magazzino_repository", "DISPONIBILITA_ARTICOLI_SORT_COLUMNS")),
    ("magazzino.movimenti",
     _da_costante("apps.magazzino.db.magazzino_repository", "MOVIMENTI_SORT_COLUMNS")),
    # Le tre anagrafiche di magazzino (2026-09-21, piano-be-fe-magazzino-
    # anagrafiche-fuori-dal-pannello-config §4-6): fuori dal pannello config,
    # con endpoint e liste proprie.
    ("magazzino.magazzini",
     _da_costante("apps.magazzino.db.anagrafiche_magazzino_repository", "MAGAZZINI_SORT_COLUMNS")),
    ("magazzino.ubicazioni",
     _da_costante("apps.magazzino.db.anagrafiche_magazzino_repository", "UBICAZIONI_SORT_COLUMNS")),
    ("magazzino.lotti",
     _da_costante("apps.magazzino.db.anagrafiche_magazzino_repository", "LOTTI_SORT_COLUMNS")),
    ("pagamenti.rate_fuori_capienza",
     _da_costante("apps.pagamenti.db.pagamenti_repository", "RATE_FUORI_CAPIENZA_SORT_COLUMNS")),
    ("pagamenti.rate",
     _da_costante("apps.pagamenti.db.pagamenti_repository", "RATE_SORT_COLUMNS")),
    ("pagamenti.eccedenze",
     _da_costante("apps.pagamenti.db.pagamenti_repository", "ECCEDENZE_SORT_COLUMNS")),
    # Registri di numerazione (2026-09-01), primo tab dell'emittente fiscale.
    # ⭐ E' entrata qui insieme all'allargamento del censimento a
    # `<DrawerTabLista>`: montata solo con quel componente, era invisibile al
    # test 6 e quindi fuori da tutti i presidi di questo modulo.
    ("vendite.registri_numerazione",
     _da_costante("apps.vendite.db.registri_repository", "_ORDER_COLS")),
    # Famiglie di documento (2026-09-02): il CRUD della REGOLA che il registro
    # applica. ⭐ E' la prima lista del gruppo con `vista_sql` VALORIZZATA — il
    # trigger DB le valida i `campo_sorgente` contro la vista — ma la whitelist
    # di ORDINAMENTO resta materia di questo presidio: la vista non sa niente
    # di cosa il repository accetta in `ORDER BY`.
    ("vendite.famiglie_documento",
     _da_costante("apps.vendite.db.famiglie_repository", "_ORDER_COLS")),
    # Le 4 liste della pagina tecnica `ui` (2026-09-02) — primo lotto montato
    # con `:paginata="false"`. ⭐ Nessuna whitelist di ordinamento: non ordinano
    # lato backend, quindi non c'e' un contratto seed<->repository da esigere.
    # Restano coperte da TUTTI gli altri test di questo modulo (azione mai
    # ordinabile, slot `actions`, preset di default, `sensibile` col grant,
    # censimento dal frontend) piu' il test 9, che pretende che il frontend le
    # monti davvero come non paginate.
    ("ui.lista_definizione", ORDINAMENTO_LOCALE),
    ("ui.lista_colonna", ORDINAMENTO_LOCALE),
    ("ui.lista_preset", ORDINAMENTO_LOCALE),
    ("ui.lista_colonna_permesso", ORDINAMENTO_LOCALE),
    # Lotto 2 (2026-09-02): gli atti di sistemazione di una fattura, montati
    # nel drawer dell'eccedenza.
    # ⭐ PAGINATA dal 2026-09-02 (decisione di Tid), dopo esserlo stata per
    #    mezza giornata no. La ragione per cui era «ordinamento locale» —
    #    «gli atti di una fattura sono pochi per modello» — e' una previsione
    #    sui DATI, e le previsioni sui dati non decidono la forma di una lista:
    #    il drawer restava senza pagine, senza «Personalizza colonne» e senza
    #    export, cioe' fuori dallo standard delle altre quaranta, e nessuno
    #    poteva accorgersene perche' non falliva niente.
    # ⇒ Da qui la whitelist di BE-1 non e' piu' «pronta per domani»: e' la
    #   whitelist che l'intestazione cliccata usa oggi, ed e' esigibile dai
    #   test 1-3 come per ogni altra lista. Il ponte del lotto 2 e' sparito
    #   insieme all'ultima riga che conteneva.
    ("pagamenti.sistemazioni_fattura",
     _da_costante("apps.pagamenti.db.pagamenti_repository", "SISTEMAZIONI_SORT_COLUMNS")),
    # Le altre tre del lotto 2. ⭐ Entrano nel registro col SEED e non con la
    # conversione: `test_lista_proiezione_campo_sorgente` pretende che ogni
    # lista senza vista abbia qui la sua whitelist, perche' altrimenti «i loro
    # ordinamenti non li prova nessuno» — ed e' vero anche prima che una view
    # le monti.
    ("pagamenti.canali_incasso",
     _da_costante("apps.pagamenti.db.pagamenti_repository", "ENTI_INCASSO_SORT_COLUMNS")),
    ("anagrafiche.titoli_iva_sfondati",
     _da_costante("apps.anagrafiche.db.titoli_iva_repository", "_ORDER_COLS_SFONDATI")),
    # ⭐ PAGINATA dal 2026-09-02 (rilievo di Tid: il drawer era fuori standard —
    #    niente pagine, niente scelta colonne, niente export). Da quel giorno
    #    ordina lato SERVER, quindi rientra nei test 1-3 con la sua whitelist e
    #    la riga corrispondente esce dal ponte del lotto 2.
    ("anagrafiche.soggetto_titoli_iva",
     _da_costante("apps.anagrafiche.db.titoli_iva_repository",
                  "_ORDER_COLS_TITOLI_SOGGETTO")),
    # Lotto 3 (2026-09-02): le due liste dentro `TitoloIvaDrawer`, seedate prima
    # della conversione del drawer (Gruppo B).
    # ⭐ Il registro le prende col SEED, come il lotto 2: e' `_LISTE` a dover
    #    coprire il frontend, non a fotografarlo.
    ("anagrafiche.titolo_iva_movimenti",
     _da_costante("apps.anagrafiche.db.titoli_iva_repository",
                  "_ORDER_COLS_MOVIMENTI")),
    # ⭐ Gli AMBITI non ordinano lato server, e non e' un debito: a catalogo
    #    NESSUNA loro colonna e' `ordinabile = t` (il seed lo dichiara), quindi
    #    non c'e' nessun contratto da esigere. `livello` sta a `f` per disegno —
    #    l'ordine di un ambito e' la sua gerarchia, non una preferenza — e
    #    `oggetto` e' composta dal frontend, senza una colonna SQL dietro.
    ("anagrafiche.titolo_iva_ambiti", ORDINAMENTO_LOCALE),
    # Processi automatici (2026-09-05, cantiere «nessun processo senza
    # operatore»). ⚠️ La lista non nasce da una vista: la compone
    # `ProcessiRepository.list_processi` con le sue colonne derivate, e la
    # whitelist di ordinamento e' la costante di modulo del repository.
    ("amm.processi", _da_costante("apps.core.db.processi_repository", "_ORDER_COLS_PROCESSI")),
    # La consultazione di `dbops.error_log` (pezzo E dell'osservabilita',
    # 2026-09-19): il diario degli errori tecnici col catalogo dei messaggi per
    # JOIN. Le frasi (`messaggio`, `causa`, `soluzione`) sono `ordinabile = f`
    # a catalogo e fuori whitelist, di proposito.
    ("dbops.error_log", _da_costante("apps.core.db.dbops_repository", "ERROR_LOG_SORT_COLUMNS")),
    # Il giornale trasversale degli eventi (pezzo G, 2026-09-19): terzo lettore
    # di `script.vw_giornale_entita`, stesse due colonne ordinabili della
    # Storia di un'entita' (`gravita` = il rango, `quando`). ⚠️ Non passa da
    # `sql_order_clause`: l'ordine per gravita' porta il tempo DESC dentro di
    # se' (`_giornale_order_clause`), che e' uno dei dodici casi dichiarati fuori
    # dal BB — il test 10 non lo vede, e non finge.
    ("vendite.giornale", _da_costante("apps.vendite.db.vendite_repository", "GIORNALE_SORT_COLUMNS")),
    # Flussi di una pratica e utilizzo di una riga della matrice utility/ruoli
    # (2026-09-27, brief-db-liste-datatable-grezze righe 3 e 4): fino a quel
    # giorno `DataTable` grezze nei due drawer — i flussi senza pagine, l'uso
    # troncato a 100 righe.
    ("pratiche.flussi", _da_costante("apps.pratiche.db.pratiche_repository", "FLUSSI_ORDER_COLS")),
    ("config.utilities_tipi_ruolo_usage",
     _da_costante("apps.config.db.utilities_tipi_ruolo_repository", "USAGE_ORDER_COLS")),
    # Sessioni attive e reparti (2026-09-27, brief-db-liste-datatable-grezze
    # righe 1 e 5): fino a quel giorno `DataTable` grezze, senza pagine.
    ("core.sessioni_attive",
     _da_costante("apps.core.db.session_audit_repository", "SESSIONI_ATTIVE_ORDER_COLUMNS")),
    ("amm.reparti",
     _da_costante("apps.amm_software.db.amm_software_repository", "REPARTI_ORDER_COLUMNS")),
    # Le sei liste geografiche (2026-09-27, brief-db-liste-datatable-grezze
    # riga 9): fino a quel giorno `GeoSearchTable` con le colonne scritte nel
    # `.vue`. Whitelist `colonne_identita` del repository (il nome E' la colonna
    # della tabella o della vista `config.vw_*_lista`).
    ("config.stati", _da_costante("apps.anagrafiche.db.geo_repository", "_STATI_ORDER_COLS")),
    ("config.regioni", _da_costante("apps.anagrafiche.db.geo_repository", "_REGIONI_ORDER_COLS")),
    ("config.province", _da_costante("apps.anagrafiche.db.geo_repository", "_PROVINCE_ORDER_COLS")),
    ("config.comuni", _da_costante("apps.anagrafiche.db.geo_repository", "_COMUNI_ORDER_COLS")),
    ("config.codici_postali", _da_costante("apps.anagrafiche.db.geo_repository", "_CODICI_POSTALI_ORDER_COLS")),
    ("config.toponomastica", _da_costante("apps.anagrafiche.db.geo_repository", "_TOPONOMASTICA_ORDER_COLS")),
)


# ⚠️ REGISTRO DI DEBITO, non lista di eccezioni.
#
# Liste convertite PRIMA che questo presidio esistesse, in cui la whitelist di
# ordinamento del repository e' chiavata sui `codice` LOGICI del catalogo invece
# che sui `campo_sorgente` fisici. Conseguenza reale: le colonne dove i due nomi
# divergono sembrano ordinabili, ma `order_by` non entra nella whitelist e il
# repository **ripiega in silenzio** sull'ordinamento di default — nessun errore,
# nessun rosso, solo una freccia che non fa quello che promette.
#
# Rilevate il 2026-07-31 estendendo il registro a tutto il codice: 25 casi su 11
# liste. **CHIUSO in giornata**, in due mosse: il team DB ha allineato il seed
# (30 colonne fuori dal nucleo portate a `ordinabile=f`, colonna Emittente e
# Id. Fiscale rinominate col nome fedele al campo che leggono), il BE ha
# ri-chiavato le whitelist dei 9 repository sui `campo_sorgente`.
#
# **L'insieme e' VUOTO e deve restare vuoto**: da qui in avanti ogni lista e'
# esaminata dai test stretti 1-3. Ri-aggiungere un codice qui non e' una
# soluzione, e' spegnere il presidio proprio dove serve.
_DEBITO_WHITELIST_LOGICA: frozenset[str] = frozenset()


# ⛔ REGISTRO DI DEBITO — le liste con colonne DATA ordinabili il cui
# `sql_order_clause` NON dichiara `colonne_desc` (2026-09-18, rilettura critica
# di D19). Li' il ramo «`order_by` senza `order_dir`» ripiega ASC su una data,
# contro la regola di Tid del 02/09 («gli ordinamenti per data hanno sempre
# default DESC»). Il ramo oggi e' DORMIENTE — `useSearchTable.onSort` manda
# sempre i due campi — ed e' proprio il caso in cui un contratto dichiarato va
# provato per intero: nessuno lo attraversa, quindi nessuno se ne accorge.
#
# Il rimedio per una lista e' una riga nel repository: `colonne_desc=<insieme>`
# accanto a `colonne=`, con l'insieme che il test 10 confronta col seed. Una
# lista sanata va TOLTA da qui (il test 10-bis lo pretende); una lista nuova
# senza ripiego fa rosso e non entra per inerzia.
#
# ⚠️ Fuori perimetro, e dichiarato: le liste che non passano da
#    `sql_order_clause` con una costante di modulo (forma vecchia dell'ORDER BY,
#    whitelist di classe, funzione DB) — il presidio non le vede, e non finge.
_DEBITO_RIPIEGO_DATA_ASC: frozenset[str] = frozenset({
    "amm.processi",
    "anagrafiche.categorie_clienti_listini",
    "anagrafiche.clienti",
    "anagrafiche.emittenti_fiscali",
    "anagrafiche.fornitori",
    "pagamenti.distinte",
    "pagamenti.rate_fuori_capienza",
    "pagamenti.righe",
    "vendite.approvazioni_prezzo",
    "vendite.contratti",
    "vendite.ddt",
    "vendite.famiglie_documento",
    "vendite.fatture",
    "vendite.ordini",
    "vendite.preventivi",
    "pratiche.pratiche",
    "vendite.promo_articoli",
    "vendite.registri_numerazione",
    "vendite.resi",
})

_TIPI_DATA: frozenset[str] = frozenset({"date", "datetime"})


# Scopo: il testo di ogni chiamata `sql_order_clause(...)` in un sorgente, a
#        parentesi bilanciate (le chiamate sono su piu' righe).
def _chiamate_sql_order_clause(sorgente: str) -> list[str]:
    chiamate = []
    for m in re.finditer(r"sql_order_clause\(", sorgente):
        i, profondita = m.end(), 1
        while profondita and i < len(sorgente):
            profondita += {"(": 1, ")": -1}.get(sorgente[i], 0)
            i += 1
        chiamate.append(sorgente[m.end():i - 1])
    return chiamate


# Scopo: per una lista risolta da `_da_costante`, i `colonne_desc` dichiarati
#        nei siti di chiamata che usano la sua whitelist — `None` se la lista
#        non passa da `sql_order_clause` con quella costante (fuori perimetro),
#        insieme vuoto se ci passa e non dichiara nessun ripiego (debito).
#        Ritorna `{nome_costante: insieme}`, gia' risolto dal modulo.
def _colonne_desc_dichiarate(whitelist_fn) -> dict[str, set[str]] | None:
    import importlib
    from pathlib import Path

    # Il risolutore che le colonne DESC le dichiara da se' (righe di documento).
    diretto = getattr(whitelist_fn, "colonne_desc", None)
    if diretto is not None:
        return diretto()
    modulo = getattr(whitelist_fn, "modulo", None)
    costante = getattr(whitelist_fn, "costante", None)
    if not modulo or not costante:
        return None
    mod = importlib.import_module(modulo)
    sorgente = _senza_commenti(Path(mod.__file__).read_text(encoding="utf-8"))
    siti = [
        c for c in _chiamate_sql_order_clause(sorgente)
        if re.search(rf"colonne\s*=\s*{re.escape(costante)}\b", c)
    ]
    if not siti:
        return None
    dichiarate: dict[str, set[str]] = {}
    for sito in siti:
        m = re.search(r"colonne_desc\s*=\s*(\w+)", sito)
        if m:
            dichiarate[m.group(1)] = set(getattr(mod, m.group(1)))
    return dichiarate


# Scopo: le colonne DATA ordinabili di una lista, per `campo_sorgente` — cio'
#        che il ripiego DESC deve coprire.
def _colonne_data_ordinabili(codice: str) -> set[str]:
    return {
        r["campo_sorgente"] for r in _colonne_attive(codice)
        if r["ordinabile"] == "t" and r["tipo_dato"] in _TIPI_DATA
    }


# Scopo: liste su cui il contratto seed<->whitelist e' esigibile: tutte tranne
#        il debito noto e quelle che ordinano nel browser.
def _liste_allineate() -> tuple[tuple[str, object], ...]:
    return tuple(
        (c, w) for c, w in _LISTE
        if c not in _DEBITO_WHITELIST_LOGICA and w is not ORDINAMENTO_LOCALE
    )


# Scopo: i codici delle liste dichiarate a ordinamento locale.
def _liste_locali() -> tuple[str, ...]:
    return tuple(c for c, w in _LISTE if w is ORDINAMENTO_LOCALE)


# Scopo: righe di un CSV di seed della cartella ui.
def _seed(nome: str) -> list[dict[str, str]]:
    with (_SEED_DIR / nome).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# Scopo: id della lista dal suo codice (il seed puo' rinumerare: il test segue).
def _lista_id(codice: str) -> str:
    for riga in _seed("lista_definizione.csv"):
        if riga["codice"] == codice:
            return riga["id"]
    raise AssertionError(f"lista '{codice}' assente da lista_definizione.csv")


# Scopo: colonne ATTIVE del catalogo di una lista. Le disattivate non arrivano a
#        video (`fn_resolve_lista_config` le esclude), quindi i loro flag non
#        dicono nulla sul contratto lista<->backend.
def _colonne_attive(codice: str) -> list[dict[str, str]]:
    lista_id = _lista_id(codice)
    return [
        r for r in _seed("lista_colonna.csv")
        if r["lista_id"] == lista_id and r["attivo"] == "t"
    ]


# Scopo: colonne per cui ESISTE un grant esplicito in `ui.lista_colonna_permesso`.
#        Il seed di quella tabella oggi NON esiste nella cartella `ui`: la
#        funzione ritorna un insieme vuoto e il cancello sotto blocca qualunque
#        colonna sensibile. Il giorno in cui il seed arrivera', il test si stringe
#        da se' sulla singola colonna, senza modifiche.
def _colonne_con_grant() -> set[str]:
    percorso = _SEED_DIR / "lista_colonna_permesso.csv"
    if not percorso.exists():
        return set()
    with percorso.open(newline="", encoding="utf-8") as fh:
        return {r["colonna_id"] for r in csv.DictReader(fh)}


_CELLA_VUE = repo_root() / "frontend/src/core/components/CellaConfigurabile.vue"


# Scopo: i `formato` che il frontend sa RENDERE, letti dal sorgente di
#        `CellaConfigurabile` (i `case '...'` dello switch e i confronti
#        `formato === '...'`), non ricopiati qui: due elenchi dello stesso
#        vocabolario ne hanno sempre uno stantio.
# ⛔ Se la lettura non trova nulla SOLLEVA: un insieme vuoto renderebbe verde
#    per sottrazione il test che lo consuma.
@lru_cache(maxsize=1)
def _formati_resi_dal_frontend() -> frozenset[str]:
    sorgente = _senza_commenti(_CELLA_VUE.read_text(encoding="utf-8"))
    trovati = set(re.findall(r"case '([a-z0-9_]+)':", sorgente))
    trovati |= set(re.findall(r"formato === '([a-z0-9_]+)'", sorgente))
    if not trovati:
        raise AssertionError(
            f"nessun formato letto da {_CELLA_VUE.name}: la lettura e' rotta, "
            "non il catalogo"
        )
    return frozenset(trovati)


# Scopo: per ogni `formato` che pretende una SECONDA colonna nella riga oltre
#        al `campo_sorgente`, il nome di quella gemella — letto dal sorgente FE
#        (`CAMPO_GEMELLO_NATURA_DOC` in `CellaConfigurabile`), che e' l'unica
#        sede in cui il nome decide qualcosa.
# ⭐ Oggi il solo `natura_doc`: il Tag della natura vuole il `codice_interno`
#    accanto alla descrizione. Un formato nuovo con una gemella si aggiunge qui
#    E nel `.vue`, e il 9-bis pretende che le due letture si trovino.
# ⛔ Non e' un dizionario scritto a mano con il nome dentro: se il FE rinomina la
#    costante e questa lettura non la trova piu', la funzione SOLLEVA — un
#    presidio che perde la sua fonte deve dirlo, non tornare vuoto.
@lru_cache(maxsize=1)
def _gemelle_per_formato() -> dict[str, tuple[str, ...]]:
    sorgente = _senza_commenti(_CELLA_VUE.read_text(encoding="utf-8"))
    m = re.search(r"const CAMPO_GEMELLO_NATURA_DOC = '([a-z0-9_]+)'", sorgente)
    if m is None:
        raise AssertionError(
            f"`CAMPO_GEMELLO_NATURA_DOC` non trovato in {_CELLA_VUE.name}: il "
            "presidio sulla gemella di `natura_doc` ha perso la sua fonte"
        )
    return {"natura_doc": (m.group(1),)}


# Il nome pubblico che `test_lista_proiezione_campo_sorgente` importa.
def campi_gemelli_per_formato() -> dict[str, tuple[str, ...]]:
    return _gemelle_per_formato()


class ListeConfigurabiliSeedTests(unittest.TestCase):
    """Il contratto seed <-> whitelist, che nessun altro test copre.

    E' il tipo di disallineamento che non produce un errore in fase di build: si
    manifesta come una colonna che a video sembra ordinabile e in risposta da'
    400, oppure come una capacita' del backend che l'operatore non puo'
    raggiungere. Entrambi si scoprono solo cliccando.
    """

    def test_whitelist_copre_le_colonne_ordinabili(self) -> None:
        for codice, whitelist_fn in _liste_allineate():
            with self.subTest(lista=codice):
                ordinabili = {
                    r["campo_sorgente"] for r in _colonne_attive(codice)
                    if r["ordinabile"] == "t"
                }
                mancanti = sorted(ordinabili - whitelist_fn())
                self.assertEqual(
                    mancanti, [],
                    "colonne ordinabili nel seed ma assenti dalla whitelist del "
                    "repository: la freccia a video risponderebbe 400.",
                )

    def test_seed_offre_tutto_cio_che_il_backend_sa_ordinare(self) -> None:
        for codice, whitelist_fn in _liste_allineate():
            with self.subTest(lista=codice):
                colonne = _colonne_attive(codice)
                ordinabili = {
                    r["campo_sorgente"] for r in colonne if r["ordinabile"] == "t"
                }
                # Solo le colonne che il catalogo espone: una whitelist puo'
                # legittimamente conoscere campi che la lista non mostra.
                in_catalogo = {r["campo_sorgente"] for r in colonne}
                inutilizzate = sorted((whitelist_fn() & in_catalogo) - ordinabili)
                self.assertEqual(
                    inutilizzate, [],
                    "colonne presenti nel catalogo e ordinabili lato backend, ma "
                    "marcate ordinabile=f: capacita' irraggiungibile. Se e' "
                    "voluto, va motivato nel seed.",
                )

    def test_whitelist_chiavata_sul_campo_sorgente(self) -> None:
        divergenti_totali = 0
        for codice, whitelist_fn in _liste_allineate():
            with self.subTest(lista=codice):
                whitelist = whitelist_fn()
                for riga in _colonne_attive(codice):
                    sorgente = riga["campo_sorgente"]
                    if not sorgente or sorgente == riga["codice"]:
                        continue
                    divergenti_totali += 1
                    if riga["ordinabile"] != "t":
                        continue
                    self.assertIn(
                        sorgente, whitelist,
                        f"[{codice}] la whitelist deve usare il campo fisico "
                        f"'{sorgente}', non il codice '{riga['codice']}'.",
                    )
                    self.assertNotIn(
                        riga["codice"], whitelist,
                        f"[{codice}] '{riga['codice']}' e' il codice logico: il "
                        "frontend non lo invia mai come sortField.",
                    )
        # Se nessuna lista avesse piu' i due nomi divergenti, il test passerebbe
        # per caso senza discriminare le due convenzioni.
        self.assertGreater(
            divergenti_totali, 0,
            "nessuna colonna con codice != campo_sorgente in tutto il registro: "
            "il test non discrimina piu' le due convenzioni, va rivisto.",
        )

    def test_colonna_azione_mai_ordinabile(self) -> None:
        for codice, _ in _LISTE:
            with self.subTest(lista=codice):
                for riga in _colonne_attive(codice):
                    if riga["tipo_colonna"] == "azione":
                        self.assertEqual(
                            riga["ordinabile"], "f",
                            "una colonna azione non ha campo sorgente: "
                            "ordinarla non significa nulla.",
                        )

    # Scopo: ⛔ LO SLOT DELLE AZIONI SI CHIAMA `actions`.
    #
    #        `<ListaConfigurabile>` rende la colonna delle azioni solo quando
    #        `haAzioni` e' vero, e quella condizione ha DUE termini: la config
    #        dichiara una colonna `tipo_colonna='azione'` **e** il caller
    #        fornisce lo slot `#actions`. La colonna azioni NON passa dalla
    #        catena `#cell-<campo>`, che serve alle colonne dati.
    #
    # 🔴 Col nome sbagliato non succede niente di visibile: nessun errore,
    #    nessun warning, solo una colonna che non c'e'. Su `LottoDrawer.vue` il
    #    seed dichiarava la colonna, i permessi erano a posto e la preferenza
    #    utente non la nascondeva — tutto corretto tranne il nome dello slot, e
    #    il kebab delle fatture non e' mai comparso. Trovato in app da Tid il
    #    2026-08-24, su 19 consumatori era l'unico sbagliato.
    #
    # ⚠️ Il presidio guarda i `.vue`, non il seed: e' un difetto di CHIAMATA,
    #    e nel database non se ne vede traccia.
    # ⚠️ E guarda il sorgente SENZA COMMENTI (`_senza_commenti`): chi NOMINA lo
    #    slot sbagliato per spiegarlo non lo sta usando. Senza, il presidio si
    #    accende sulla propria documentazione — successo il 2026-08-26.
    def test_lo_slot_delle_azioni_si_chiama_actions(self) -> None:
        src = repo_root() / "frontend/src"
        colpevoli: list[str] = []
        for percorso in sorted(src.rglob("*.vue")):
            testo = _senza_commenti(percorso.read_text(encoding="utf-8"))
            if "<ListaConfigurabile" not in testo:
                continue
            if "#cell-azioni" in testo:
                colpevoli.append(str(percorso.relative_to(src)))
        self.assertEqual(
            colpevoli, [],
            "slot `#cell-azioni` su un montaggio di <ListaConfigurabile>: il BB "
            "si aspetta `#actions`, e col nome sbagliato la colonna delle "
            f"azioni non viene resa (nessun kebab, nessun errore): {colpevoli}",
        )

    # 4-ter. IL VERSO MANCANTE del 4-bis (richiesta BE-3 del team DB,
    #        2026-09-02). Quello controlla «la config dichiara l'azione ⇒ il
    #        caller deve fornire lo slot col nome giusto». Questo controlla
    #        l'opposto: **il caller fornisce `#actions` ⇒ la lista deve avere
    #        una colonna `azione` a catalogo**.
    #
    # 🔴 E' il difetto DB-1, trovato convertendo e non da un test: la lista
    #    `anagrafiche.soggetto_titoli_iva` non aveva la colonna a catalogo
    #    mentre il suo drawer ha un pulsante ELIMINA per riga. Il BB rende la
    #    colonna delle azioni solo se la config la dichiara: senza la riga, il
    #    cestino sparisce e **non fallisce niente** — nessun errore, nessun
    #    rosso, solo un'azione che non c'e' piu'.
    # ⚠️ Il generatore del seed non poteva vederla: riconosce la colonna azioni
    #    dall'header `common.col_azioni`, e li' la `<Column v-if="!isReadonly">`
    #    non aveva header. Il presidio va quindi sul FRONTEND, che e' l'unico
    #    posto dove quell'intenzione e' scritta.
    def test_chi_fornisce_lo_slot_actions_ha_la_colonna_a_catalogo(self) -> None:
        # ⭐ Il registro di debito che stava qui e' VUOTO dal 2026-09-02 ed e'
        #    stato tolto, non azzerato: un registro vuoto che resta e' un posto
        #    dove la prossima eccezione si infila senza discussione.
        #    Conteneva `vendite.registri_numerazione` (lista 54) — SECONDO caso
        #    della specie di DB-1, trovato da questo test alla PRIMA corsa: il
        #    tab forniva `#actions` con un `RowActionsMenu`, il catalogo non
        #    aveva la colonna, e quel kebab non si e' mai reso senza che
        #    fallisse niente. Chiuso dalla riga 702 a catalogo (DB-2).
        con_slot = {
            codice: dove
            for codice, _apertura, corpo, dove in _montaggi_lista()
            if re.search(r"#actions|v-slot:actions", corpo)
        }
        self.assertTrue(
            con_slot,
            "nessuno slot `#actions` trovato: il rilevamento e' rotto, non e' "
            "che nessuna lista abbia azioni di riga.",
        )
        senza_colonna = sorted(
            f"{codice} ({dove})"
            for codice, dove in con_slot.items()
            if not any(
                r["tipo_colonna"] == "azione" for r in _colonne_attive(codice)
            )
        )
        self.assertEqual(
            senza_colonna, [],
            "il frontend fornisce lo slot `#actions` ma il catalogo non ha una "
            "colonna `tipo_colonna = 'azione'`: il building block NON rende la "
            "colonna e non fallisce niente — le azioni di riga spariscono in "
            "silenzio. Serve la riga a catalogo (richiesta al team DB).",
        )

    def test_registro_copre_tutte_le_liste_montate_dal_frontend(self) -> None:
        # La fonte di verita' su "quali liste sono convertite" e' il frontend:
        # chi monta `<ListaConfigurabile codice="X">` ha convertito X. Senza
        # questo controllo, dimenticare una riga in `_LISTE` non produce un
        # rosso — produce un presidio che non presidia, che e' peggio di non
        # averlo.
        montate = {codice for codice, _a, _c, _d in _montaggi_lista()}
        self.assertTrue(
            montate,
            "nessun <ListaConfigurabile codice=\"...\"> trovato nel frontend: "
            "il rilevamento e' rotto, non e' che non ci siano liste.",
        )
        scoperte = sorted(montate - {codice for codice, _ in _LISTE})
        self.assertEqual(
            scoperte, [],
            "liste montate dal frontend ma assenti dal registro `_LISTE`: "
            "non sono coperte da nessun test di questo modulo. Aggiungere una "
            "riga a `_LISTE` con la whitelist del rispettivo repository.",
        )

    # 8. `sensibile = t` senza grant = colonna MORTA per tutti, e badge bugiardo.
    #    Non e' una regola di stile: e' il cancello che tiene innocuo un difetto
    #    noto e volutamente NON corretto lato DB.
    #
    #    `ui.fn_resolve_lista_config` §5 calcola
    #       COALESCE(permesso, CASE WHEN lc.sensibile THEN 'BLOCCATO' ELSE 'TUTTO' END)
    #    e subito dopo RIMUOVE le colonne 'BLOCCATO'. Quindi una colonna
    #    `sensibile = t` senza una riga in `ui.lista_colonna_permesso` non e'
    #    "nascosta a chi non ha il permesso": e' invisibile a CHIUNQUE, per
    #    sempre. Ed e' peggio, perche' `colonne_nuove` viene contato PRIMA di
    #    quel filtro e non viene decrementato: il pannello annuncia una colonna
    #    nuova che la funzione stessa ha appena tolto, e l'operatore non ha modo
    #    di distinguere fra «cerco male», «e' rotto» e «esiste ma non mi spetta».
    #
    #    Successo reale (2026-08-17): la colonna «Id fiscale» della lista gruppi
    #    fatturabili, seminata `sensibile = t` credendo che il flag fosse
    #    un'etichetta. Il tag esiste davvero in `ListaColonneModal.vue` — ma e'
    #    cio' che resta DOPO il cancello, non il cancello.
    #
    #    ⚠️ Il giorno in cui una colonna andra' protetta davvero, la strada e'
    #    completa: `sensibile = t` PIU' i grant. Questo test lo pretende, ed e'
    #    anche il momento in cui va corretto il contatore lato DB — vedi §4-ter
    #    di `brief-db-dash-competenza-gruppi-cliente-e-ricerca.md`.
    def test_colonna_sensibile_ha_sempre_un_grant(self) -> None:
        con_grant = _colonne_con_grant()
        for codice, _ in _LISTE:
            with self.subTest(lista=codice):
                orfane = [
                    r["codice"] for r in _colonne_attive(codice)
                    if r["sensibile"] == "t" and r["id"] not in con_grant
                ]
                self.assertEqual(
                    orfane, [],
                    f"lista '{codice}': colonne con sensibile=t e nessun grant in "
                    f"ui.lista_colonna_permesso -> {orfane}. Non sono protette: "
                    "sono RIMOSSE per tutti da fn_resolve_lista_config, e il "
                    "contatore colonne_nuove continua ad annunciarle. O si "
                    "seminano i grant, o la colonna va a sensibile=f.",
                )

    def test_il_debito_non_cresce(self) -> None:
        # Il registro di debito deve CALARE. Questo test lo verifica dal verso
        # che conta: una lista elencata come "in debito" ma che in realta' e'
        # gia' allineata va TOLTA dall'insieme — altrimenti il debito sembra
        # piu' grande di quello che e', e un'eccezione dimenticata diventa
        # permanente. Il verso opposto (aggiungerne di nuove) e' gia' impedito:
        # una lista nuova non nell'insieme viene esaminata dai test stretti.
        rientrate = []
        for codice, whitelist_fn in _LISTE:
            if codice not in _DEBITO_WHITELIST_LOGICA:
                continue
            whitelist = whitelist_fn()
            divergenti = [
                r for r in _colonne_attive(codice)
                if r["campo_sorgente"]
                and r["codice"] != r["campo_sorgente"]
                and r["ordinabile"] == "t"
            ]
            # "Rientrata" = ogni colonna divergente e ordinabile ha ormai il
            # campo FISICO in whitelist.
            if divergenti and all(r["campo_sorgente"] in whitelist for r in divergenti):
                rientrate.append(codice)

        self.assertEqual(
            sorted(rientrate), [],
            "liste ormai allineate ma ancora elencate in `_DEBITO_WHITELIST_LOGICA`: "
            "toglierle dall'insieme, cosi' il registro dice la verita' sul debito "
            "residuo e le protegge dalle regressioni.",
        )

    # 8-bis. La sentinella del registro deve corrispondere a come il frontend
    #        MONTA la lista. Il registro dice «questa non ordina lato server»;
    #        se il `.vue` non dice `:paginata="false"`, il registro sta mentendo
    #        e nessun altro test se ne accorge — le liste locali sono proprio
    #        quelle escluse dai test 1-3.
    #
    # ⚠️ Il difetto che previene e' una RIMOZIONE, non un'aggiunta: togliere la
    #    prop e' un'operazione che sembra innocua (e la pagina continua a
    #    funzionare, perche' i dati arrivano tutti lo stesso), ma riaccende
    #    l'ordinamento server-side su una lista senza whitelist. Il primo click
    #    su un'intestazione risponde 400.
    def test_le_liste_locali_sono_montate_non_paginate(self) -> None:
        locali = _liste_locali()
        self.assertTrue(
            locali,
            "nessuna lista a ordinamento locale nel registro: se e' voluto, "
            "togliere questo test insieme alla sentinella.",
        )
        # codice lista -> TAG DI APERTURA del montaggio. ⚠️ Serve il tag
        # INTERO: `:paginata` vive fra gli attributi, dopo `codice`.
        montaggi = {c: apertura for c, apertura, _corpo, _dove in _montaggi_lista()}
        for codice in locali:
            with self.subTest(lista=codice):
                montaggio = montaggi.get(codice)
                # ⚠️ TERZO STATO, che la prima stesura di questo guard non
                #    prevedeva (corretto il 2026-09-02): una lista puo' essere
                #    **seedata e registrata ma non ancora convertita**. Succede
                #    perche' `test_lista_proiezione_campo_sorgente` pretende la
                #    riga in `_LISTE` gia' col SEED — «altrimenti i loro
                #    ordinamenti non li prova nessuno» — mentre la view arriva
                #    dopo. Non e' un difetto: e' l'ordine in cui si lavora.
                # ⛔ Qui si esce, NON si fallisce: questo test dice «se la monti,
                #    montala non paginata», non «devi averla montata».
                if montaggio is None:
                    continue
                self.assertRegex(
                    montaggio,
                    r':paginata="false"',
                    f"`{codice}` e' dichiarata a ordinamento locale nel registro "
                    "ma il frontend la monta SENZA `:paginata=\"false\"`. Cosi' "
                    "ordina lato server, dove non ha nessuna whitelist: la "
                    "freccia risponde 400 al primo click. O si rimette la prop, "
                    "o la lista esce dalla sentinella e prende una whitelist.",
                )

    def test_ogni_lista_del_seed_ha_un_preset_default(self) -> None:
        preset = _seed("lista_preset.csv")
        for codice, _ in _LISTE:
            with self.subTest(lista=codice):
                lista_id = _lista_id(codice)
                default = [
                    p for p in preset
                    if p["lista_id"] == lista_id and p["is_default"] == "t"
                ]
                self.assertEqual(
                    len(default), 1,
                    "serve esattamente un preset is_default: zero lascia la "
                    "lista senza configurazione di partenza, due la rendono "
                    "non deterministica.",
                )

    # 9. Un `formato` che il frontend non conosce non fa errore: la colonna esce
    #    come testo grezzo. Il precedente e' `yesno` (frontend-standards §Si'/No):
    #    tre liste si erano riscritte il Tag in uno slot, una sopra una colonna
    #    che il formato ce l'aveva gia' — e con `natura_doc` (2026-09-18) la
    #    strada «una riga di CSV, non uno slot» vale per una seconda resa.
    def test_ogni_formato_del_seed_e_reso_dal_frontend(self) -> None:
        conosciuti = _formati_resi_dal_frontend()
        self.assertIn("yesno", conosciuti)
        self.assertIn("natura_doc", conosciuti)
        sconosciuti = sorted({
            (r["formato"], r["id"], r["codice"])
            for r in _seed("lista_colonna.csv")
            if r["attivo"] == "t" and (r["formato"] or "").strip()
            and r["formato"].strip() not in conosciuti
        })
        self.assertEqual(
            sconosciuti, [],
            "formato a catalogo che `CellaConfigurabile` non rende: a video "
            "uscirebbe `String(value)`, senza nessun errore",
        )

    # 9-bis. La gemella si legge dal FE: se la lettura si rompe, il presidio
    #        della proiezione (test DB) smetterebbe di chiedere la colonna e
    #        sarebbe verde a vuoto — qui lo si dice PRIMA, senza database.
    def test_la_gemella_di_un_formato_si_legge_dal_frontend(self) -> None:
        gemelle = campi_gemelli_per_formato()
        self.assertEqual(set(gemelle), {"natura_doc"})
        self.assertEqual(gemelle["natura_doc"], ("natura_doc_codice_interno",))
        # E ogni formato con una gemella e' anche un formato reso: le due
        # letture guardano lo stesso file e devono trovarsi.
        for formato in gemelle:
            self.assertIn(formato, _formati_resi_dal_frontend())


    # 10. L'insieme delle colonne DATA col ripiego DESC si confronta col seed,
    #     non si legge da un secondo elenco: il sito di chiamata dice quale
    #     costante e' (`colonne_desc=`), il seed dice quali colonne SONO date
    #     (`tipo_dato`) e ordinabili. Uguaglianza nei due versi: una data
    #     ordinabile fuori dall'insieme ripiega ASC (la lista si apre dal piu'
    #     vecchio, senza errore); un nome nell'insieme che il seed non ha piu'
    #     come data ordinabile e' una colonna raccontata e non mostrata.
    def test_le_colonne_data_dichiarate_sono_quelle_del_seed(self) -> None:
        esaminate = 0
        for codice, whitelist_fn in _liste_allineate():
            dichiarate = _colonne_desc_dichiarate(whitelist_fn)
            if not dichiarate:
                continue
            attese = _colonne_data_ordinabili(codice)
            for costante, insieme in dichiarate.items():
                with self.subTest(lista=codice, costante=costante):
                    esaminate += 1
                    self.assertEqual(
                        sorted(insieme), sorted(attese),
                        f"lista '{codice}': `{costante}` non coincide con le "
                        "colonne DATA ordinabili del seed (tipo_dato date/datetime, "
                        "ordinabile=t). Mancanti ripiegano ASC senza errore; in "
                        "piu' raccontano una colonna che il catalogo non ha.",
                    )
        # Il presidio deve avere materia: a zero insiemi esaminati sarebbe
        # verde per sottrazione (oggi ne dichiara quattro).
        self.assertGreaterEqual(esaminate, 4)

    # 10-bis. Il registro del ripiego ASC puo' solo calare, e nei due versi: una
    #         lista che ha guadagnato `colonne_desc` va tolta (o il debito sembra
    #         piu' grande del vero), una lista nuova con date ordinabili e senza
    #         ripiego non entra per inerzia. Chi non passa da `sql_order_clause`
    #         con una costante di modulo resta fuori, ed e' dichiarato.
    def test_il_debito_del_ripiego_asc_non_cresce(self) -> None:
        senza_ripiego = set()
        for codice, whitelist_fn in _liste_allineate():
            dichiarate = _colonne_desc_dichiarate(whitelist_fn)
            if dichiarate is None or dichiarate:
                continue
            if _colonne_data_ordinabili(codice):
                senza_ripiego.add(codice)
        self.assertEqual(
            sorted(senza_ripiego - _DEBITO_RIPIEGO_DATA_ASC), [],
            "liste con date ordinabili e senza `colonne_desc` NON registrate: "
            "o si dichiara il ripiego DESC nel repository, o la lista entra in "
            "`_DEBITO_RIPIEGO_DATA_ASC` con una decisione, non per inerzia.",
        )
        self.assertEqual(
            sorted(_DEBITO_RIPIEGO_DATA_ASC - senza_ripiego), [],
            "liste elencate in `_DEBITO_RIPIEGO_DATA_ASC` che hanno ormai il "
            "ripiego (o non hanno piu' date ordinabili): toglierle, cosi' il "
            "registro dice la verita' sul debito residuo.",
        )
