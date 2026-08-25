# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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

8. test_il_debito_non_cresce
   `_DEBITO_WHITELIST_LOGICA` e' un registro di debito, non una lista di
   eccezioni: una lista rientrata va tolta, o il debito residuo risulta piu'
   grande del vero e l'eccezione diventa permanente.

⚠️ I test 1-3 girano su `_liste_allineate()`, cioe' tutte tranne il debito noto.
I test 4-6 girano su TUTTE: valgono a prescindere dalla chiave della whitelist.
"""

import csv
import re
import unittest
from pathlib import Path


# Scopo: root del repo cercata risalendo fino a `db/changelog`, invece di
#        contare i livelli a mano (`parents[N]` si rompe in silenzio se il file
#        di test viene spostato).
def _repo_root() -> Path:
    for cartella in Path(__file__).resolve().parents:
        if (cartella / "db" / "changelog").is_dir():
            return cartella
    raise AssertionError("root del repo non trovata (nessun db/changelog risalendo)")


_SEED_DIR = _repo_root() / "db/changelog/migrations_v2/80_data/sql/ui"


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

        sorgente = _repo_root() / "scripts" / "gen_seed_lista.py"
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

    return risolvi


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
    # Quinto lotto, 2026-08-01.
    ("catalogo.articoli", _da_costante("apps.catalogo.db.catalogo_repository", "ARTICOLI_ORDER_COLUMNS")),
    ("vendite.listini", _da_costante("apps.vendite.db.listini_repository", "LISTINI_ORDER_COLUMNS")),
    # Sesto lotto, 2026-08-01/02.
    ("config.email_account", _da_costante("apps.core.db.email_repository", "EMAIL_ACCOUNT_ORDER_COLUMNS")),
    ("config.email_template", _da_costante("apps.core.db.email_repository", "EMAIL_TEMPLATE_ORDER_COLUMNS")),
    ("config.email_log", _da_costante("apps.core.db.email_repository", "EMAIL_LOG_ORDER_COLUMNS")),
    ("anagrafiche.categorie_clienti_listini", _da_costante("apps.anagrafiche.db.categorie_clienti_listini_repository", "_ORDER_COLS")),
    ("anagrafiche.operatori", _da_costante("apps.amm_software.db.amm_software_repository", "ALLOWED_ORDER_COLUMNS")),
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
    # Preesistenti: erano fuori da qualunque presidio prima del 2026-07-31.
    ("anagrafiche.clienti", _da_costante("apps.anagrafiche.db.clienti_repository", "_CLIENTI_ORDER_COLS")),
    ("anagrafiche.fornitori", _da_costante("apps.anagrafiche.db.fornitori_repository", "_FORNITORI_ORDER_COLS")),
    ("anagrafiche.soggetti", _da_costante("apps.anagrafiche.db.soggetti_repository", "_SOGGETTI_ORDER_COLS")),
    ("vendite.contratti", _da_costante("apps.vendite.db.contratti_repository", "_ORDER_COLS_CONTRATTI")),
    ("vendite.ddt", _da_costante("apps.vendite.db.ddt_repository", "_ORDER_COLS_DDT")),
    ("vendite.offerte", _da_costante("apps.vendite.db.offerte_repository", "_ORDER_COLS_OFFERTE")),
    ("vendite.ordini", _da_costante("apps.vendite.db.ordini_repository", "_ORDER_COLS_ORDINI")),
    ("vendite.preventivi", _da_costante("apps.vendite.db.preventivi_repository", "_ORDER_COLS_PREVENTIVI")),
    ("vendite.resi", _da_costante("apps.vendite.db.resi_repository", "_ORDER_COLS_RESI")),
    ("vendite.resi_da_accreditare", _whitelist_coda_resi("vendite.vw_resi_da_accreditare")),
    ("vendite.resi_da_riconsegnare", _whitelist_coda_resi("vendite.vw_resi_da_riconsegnare")),
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


# Scopo: liste su cui il contratto seed<->whitelist e' esigibile, cioe' tutte
#        tranne il debito noto.
def _liste_allineate() -> tuple[tuple[str, object], ...]:
    return tuple((c, w) for c, w in _LISTE if c not in _DEBITO_WHITELIST_LOGICA)


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
        src = _repo_root() / "frontend/src"
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

    def test_registro_copre_tutte_le_liste_montate_dal_frontend(self) -> None:
        # La fonte di verita' su "quali liste sono convertite" e' il frontend:
        # chi monta `<ListaConfigurabile codice="X">` ha convertito X. Senza
        # questo controllo, dimenticare una riga in `_LISTE` non produce un
        # rosso — produce un presidio che non presidia, che e' peggio di non
        # averlo.
        src = _repo_root() / "frontend/src"
        montate: set[str] = set()
        for percorso in src.rglob("*.vue"):
            testo = percorso.read_text(encoding="utf-8")
            # Solo il montaggio reale: i commenti che NOMINANO il componente
            # (es. GeoSearchTable, che dichiara di non usarlo) sono esclusi.
            senza_commenti = re.sub(r"^\s*//.*$", "", testo, flags=re.M)
            # `(?<![:@\w-])codice=` esclude i binding DINAMICI (`:codice="var"`):
            # il loro valore non e' risolvibile staticamente, e catturare il nome
            # della variabile produrrebbe un falso "codice lista" inesistente.
            # Sono comunque coperti: `ResiCodaTable` sceglie fra due costanti,
            # entrambe presenti in `_LISTE`.
            #
            # ⚠️ **Niente `[^>]*` fra il tag e l'attributo** (difetto corretto il
            # 2026-08-03): un `>` puo' vivere DENTRO un attributo — e ci vive
            # davvero, in `v-if="documentiCount > 0 || documentiLoading"` sulle
            # dashboard. La classe negata si fermava li' e quattro liste su sei
            # risultavano NON MONTATE: il presidio taceva proprio sulle liste
            # appena convertite, che e' il caso per cui esiste. Ora si cerca
            # `codice="..."` entro una finestra di caratteri dal nome del tag,
            # senza pretendere di sapere dove finisce il tag stesso.
            for m in re.finditer(
                r"<ListaConfigurabile\b.{0,400}?(?<![:@\w-])codice=\"([^\"]+)\"",
                senza_commenti,
                re.S,
            ):
                montate.add(m.group(1))

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
