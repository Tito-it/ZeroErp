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

5. test_ogni_lista_del_seed_ha_un_preset_default
   Senza preset `is_default` la lista non ha una configurazione di partenza.

6. test_registro_copre_tutte_le_liste_montate_dal_frontend
   Chiude il buco del registro: una lista convertita ma non aggiunta a `_LISTE`
   sfuggirebbe a TUTTI i test sopra, in silenzio. La fonte di verita' e' il
   frontend — chi monta `<ListaConfigurabile codice="X">` dichiara di aver
   convertito X.

7. test_il_debito_non_cresce
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
    ("pratiche.pratiche", _da_costante("apps.pratiche.db.pratiche_repository", "_PRATICHE_ORDER_COLS")),
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
    # Sesto lotto, 2026-08-01. `storico.audit_log` NON e' qui: il seed non ha
    # la colonna calcolata *Dettaglio*, che la pagina mostra — conversione
    # sospesa in attesa della riga di seed (vedi brief).
    ("config.email_account", _da_costante("apps.core.db.email_repository", "EMAIL_ACCOUNT_ORDER_COLUMNS")),
    ("config.email_template", _da_costante("apps.core.db.email_repository", "EMAIL_TEMPLATE_ORDER_COLUMNS")),
    ("config.email_log", _da_costante("apps.core.db.email_repository", "EMAIL_LOG_ORDER_COLUMNS")),
    ("anagrafiche.categorie_clienti_listini", _da_costante("apps.anagrafiche.db.categorie_clienti_listini_repository", "_ORDER_COLS")),
    ("anagrafiche.operatori", _da_costante("apps.amm_software.db.amm_software_repository", "ALLOWED_ORDER_COLUMNS")),
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
            for m in re.finditer(
                r"<ListaConfigurabile\b[^>]*?(?<![:@\w-])codice=\"([^\"]+)\"",
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
