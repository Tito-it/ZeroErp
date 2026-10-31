# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio del contratto fra il catalogo liste (`ui.lista_colonna`,
#        flag `ricercabile_full`) e le dichiarazioni `RicercaFull` con cui i
#        repository dicono cosa SANNO cercare. Test senza DB: legge i CSV di
#        seed e le costanti del codice (la lettura del catalogo a runtime e'
#        mockata), quindi gira in CI. Il gemello sul DB vero e'
#        `apps/core/tests/db/test_ricerca_full_db`.
# ------------------------------------------------------------
"""Indice test:

1. test_la_dichiarazione_copre_il_seed
   Per ogni lista registrata in `_RICERCHE`, ogni colonna `ricercabile_full = t`
   attiva del seed e' una colonna che la dichiarazione sa cercare (⊇). Se ne
   manca una, il catalogo la accende e il BB la ignora: e' il difetto di
   Preventivi e Offerte del 2026-09-23 (codice BA e id fiscale), spostato di un
   posto. Una colonna IN PIU' nella dichiarazione non e' un errore: e' una
   capacita' che il catalogo puo' accendere.

2. test_la_dichiarazione_nomina_la_sua_lista
   La `RicercaFull` registrata per la lista X porta `lista_codice = X`. Un
   codice sbagliato leggerebbe a runtime le colonne di un'altra lista: la
   ricerca girerebbe, sulle colonne sbagliate, senza nessun errore.

3. test_ogni_lista_ricercabile_e_registrata_o_in_debito
   Ogni lista del seed con almeno una colonna `ricercabile_full = t` sta in
   `_RICERCHE` oppure nel registro di debito `_DEBITO_RICERCA_A_MANO`. Una lista
   nuova che non passa dal BB fa rosso qui, invece di nascere con la sua copia.

4. test_il_debito_non_cresce
   `_DEBITO_RICERCA_A_MANO` puo' solo calare: una lista convertita va tolta, e
   una voce che nomina una lista senza colonne ricercabili e' rimasta senza
   motivo.

5. test_bb_*
   Il comportamento del BB, con la lettura del catalogo mockata:
   intersezione (anche da sola, `colonne_ricerca_attive`), colonne accese ma non dichiarate (warning), nessuna colonna
   (`FALSE`), soglia DELLA LISTA (termine vuoto: niente letture; sotto soglia:
   si legge la soglia, non le colonne), escape, mappa, alias invalido (esplode
   anche a lista aperta senza ricerca).

6. test_dichiarazione_invalida_esplode_alla_costruzione
   Un nome sbagliato esce quando il modulo si importa, non al primo operatore
   che cerca. Compresa la stringa scambiata per tupla (`("numero")`).

7. test_dichiarazione_congelata_sulla_copia
   Validata alla costruzione, la dichiarazione non cambia dopo: ne' da chi
   modifica la mappa passata, ne' scrivendoci dentro.

8. test_nessuna_chiamata_dichiara_la_soglia
   La soglia e' un fatto della lista, e la dice il catalogo
   (`ricerca_min_caratteri`, brief-db-be-fe-ricerca-soglia-per-lista §5):
   nessuna chiamata al BB e nessuno schema OpenAPI la passano. Il controllo e'
   sul sorgente (AST) e non a runtime: una chiamata del repository con
   l'argomento vecchio sarebbe un `TypeError` solo al primo operatore che cerca.

9. test_i_test_fingono_il_catalogo_da_una_sede
   Il BB legge il catalogo in due punti (colonne e soglia): un test che ne
   sostituisce uno solo manda l'altro al database. I test li fingono insieme,
   con `catalogo_ricerca_finto` — nessun altro file scrive i due percorsi.
"""

import ast
import importlib
import inspect
import unittest
from pathlib import Path

from apps.core.api.openapi_params import param_ricerca_full
from apps.core.db._helpers import RicercaFull, add_ricerca_full_condition, colonne_ricerca_attive
from apps.core.tests.ricerca_catalogo_fakes import catalogo_ricerca_finto
from apps.core.tests.test_liste_configurabili_seed import (
    _colonne_attive,
    _seed,
)


# Scopo: la dichiarazione di una lista, letta dal simbolo che il repository
#        PASSA al BB (non da uno che gli somiglia per nome).
def _da_costante(modulo: str, costante: str):
    def risolvi() -> RicercaFull:
        return getattr(importlib.import_module(modulo), costante)

    return risolvi


# Scopo: una dichiarazione tenuta in una mappa del modulo (per famiglia).
def _da_voce(modulo: str, costante: str, chiave: str):
    def risolvi() -> RicercaFull:
        return getattr(importlib.import_module(modulo), costante)[chiave]

    return risolvi


# Scopo: le due code resi hanno la dichiarazione dentro `_CODA_META`, per vista.
def _da_coda_resi(vista: str):
    def risolvi() -> RicercaFull:
        from apps.vendite.db import resi_repository as m

        return m._CODA_META[vista]["ricerca"]

    return risolvi


_V = "apps.vendite.db."
_M = "apps.magazzino.db."
_P = "apps.pagamenti.db.pagamenti_repository"

# Registro delle liste la cui ricerca libera passa dal BB:
# `codice lista` -> risolutore della `RicercaFull` passata ad `add_ricerca_full_condition`.
# ⚠️ Chi converte una lista del debito la AGGIUNGE qui e la TOGLIE dal debito.
_RICERCHE: tuple[tuple[str, object], ...] = (
    ("vendite.preventivi", _da_costante(_V + "preventivi_repository", "_RICERCA_PREVENTIVI")),
    ("vendite.offerte", _da_costante(_V + "offerte_repository", "_RICERCA_OFFERTE")),
    ("vendite.ordini", _da_costante(_V + "ordini_repository", "_RICERCA_ORDINI")),
    ("vendite.ddt", _da_costante(_V + "ddt_repository", "_RICERCA_DDT")),
    ("vendite.fatture", _da_costante(_V + "fatture_repository", "_RICERCA_FATTURE")),
    ("vendite.contratti", _da_costante(_V + "contratti_repository", "_RICERCA_CONTRATTI")),
    ("vendite.resi", _da_costante(_V + "resi_repository", "_RICERCA_RESI")),
    ("vendite.resi_da_accreditare", _da_coda_resi("vendite.vw_resi_da_accreditare")),
    ("vendite.resi_da_riconsegnare", _da_coda_resi("vendite.vw_resi_da_riconsegnare")),
    ("vendite.famiglie_documento", _da_costante(_V + "famiglie_repository", "_RICERCA")),
    ("magazzino.magazzini", _da_costante(_M + "anagrafiche_magazzino_repository", "_RICERCA_MAGAZZINI")),
    ("magazzino.ubicazioni", _da_costante(_M + "anagrafiche_magazzino_repository", "_RICERCA_UBICAZIONI")),
    ("magazzino.lotti", _da_costante(_M + "anagrafiche_magazzino_repository", "_RICERCA_LOTTI")),
    ("anagrafiche.categorie_clienti", _da_costante("apps.anagrafiche.db.categorie_clienti_repository", "_RICERCA")),
    ("anagrafiche.indirizzi", _da_costante("apps.anagrafiche.db.indirizzi_repository", "_RICERCA")),
    ("vendite.registri_numerazione", _da_costante(_V + "registri_repository", "_RICERCA")),
    ("amm.processi", _da_costante("apps.core.db.processi_repository", "_RICERCA_PROCESSI")),
    ("catalogo.uom_tipi", _da_costante("apps.catalogo.db.catalogo_repository", "_RICERCA_UOM_TIPI")),
    ("catalogo.unita_misura", _da_costante("apps.catalogo.db.catalogo_repository", "_RICERCA_UNITA_MISURA")),
    ("anagrafiche.fornitori", _da_costante("apps.anagrafiche.db.fornitori_repository", "_RICERCA_FORNITORI")),
    ("magazzino.inventari", _da_voce(_M + "magazzino_repository", "_RICERCA_DOCUMENTI", "magazzino.inventari")),
    ("magazzino.rettifiche", _da_voce(_M + "magazzino_repository", "_RICERCA_DOCUMENTI", "magazzino.rettifiche")),
    ("magazzino.disponibilita", _da_costante(_M + "magazzino_repository", "_RICERCA_DISPONIBILITA")),
    ("magazzino.disponibilita_articoli", _da_costante(_M + "magazzino_repository", "_RICERCA_DISPONIBILITA_ARTICOLI")),
    ("magazzino.inventario_righe", _da_voce(_M + "magazzino_repository", "_RICERCA_RIGHE", "magazzino.inventario_righe")),
    ("magazzino.rettifica_righe", _da_voce(_M + "magazzino_repository", "_RICERCA_RIGHE", "magazzino.rettifica_righe")),
    ("magazzino.inventario_piano", _da_costante(_M + "magazzino_repository", "_RICERCA_PIANO")),
    ("magazzino.movimenti", _da_costante(_M + "magazzino_repository", "_RICERCA_MOVIMENTI")),
    ("pagamenti.distinte", _da_costante(_P, "_RICERCA_DISTINTE")),
    ("pagamenti.righe", _da_costante(_P, "_RICERCA_RIGHE_CODA")),
    ("pagamenti.distinta_righe", _da_costante(_P, "_RICERCA_RIGHE_DISTINTA")),
    ("pagamenti.rate_fuori_capienza", _da_costante(_P, "_RICERCA_RATE_FUORI_CAPIENZA")),
    ("pagamenti.eccedenze", _da_costante(_P, "_RICERCA_ECCEDENZE")),
    ("pagamenti.rate", _da_costante(_P, "_RICERCA_RATE")),
    ("catalogo.articoli", _da_costante("apps.catalogo.db.catalogo_repository", "_RICERCA_ARTICOLI")),
    ("documenti.template_documenti", _da_costante("apps.documenti.db.documenti_repository", "_RICERCA_TEMPLATE_DOCUMENTI")),
    ("documenti.template_asset", _da_costante("apps.documenti.db.documenti_repository", "_RICERCA_TEMPLATE_ASSET")),
    # Documenti di una sorgente e versioni di un template (2026-09-27,
    # brief-db-liste-datatable-grezze righe 2 e 6).
    ("documenti.documenti_sorgente", _da_costante("apps.documenti.db.documenti_repository", "_RICERCA_DOCUMENTI_SORGENTE")),
    ("documenti.template_versioni", _da_costante("apps.documenti.db.documenti_repository", "_RICERCA_TEMPLATE_VERSIONI")),
    ("config.email_account", _da_costante("apps.core.db.email_repository", "_RICERCA_EMAIL_ACCOUNT")),
    ("config.email_template", _da_costante("apps.core.db.email_repository", "_RICERCA_EMAIL_TEMPLATE")),
    ("config.email_log", _da_costante("apps.core.db.email_repository", "_RICERCA_EMAIL_LOG")),
    ("anagrafiche.clienti", _da_costante("apps.anagrafiche.db.clienti_repository", "_RICERCA_CLIENTI")),
    ("anagrafiche.soggetti", _da_costante("apps.anagrafiche.db.soggetti_repository", "_RICERCA_SOGGETTI")),
    ("anagrafiche.categorie_clienti_listini", _da_costante("apps.anagrafiche.db.categorie_clienti_listini_repository", "_RICERCA_MATRICE")),
    ("anagrafiche.operatori", _da_costante("apps.amm_software.db.amm_software_repository", "_RICERCA_OPERATORI")),
    ("anagrafiche.accessi_altri", _da_costante("apps.amm_software.db.accessi_repository", "_RICERCA_ACCESSI_ALTRI")),
    ("anagrafiche.accessi_sistema", _da_costante("apps.amm_software.db.accessi_repository", "_RICERCA_ACCESSI_SISTEMA")),
    ("vendite.listini", _da_costante(_V + "listini_repository", "_RICERCA_LISTINI")),
    ("vendite.listini_versioni", _da_costante(_V + "listini_repository", "_RICERCA_VERSIONI")),
    ("vendite.listini_righe", _da_costante(_V + "listini_repository", "_RICERCA_LISTINI_RIGHE")),
    ("vendite.promo_articoli", _da_costante(_V + "promo_articoli_repository", "_RICERCA_PROMO")),
    ("vendite.dash_competenza_gruppi", _da_costante(_V + "vendite_repository", "_RICERCA_DASH_COMPETENZA_GRUPPI")),
    ("catalogo.conversioni_uom", _da_costante("apps.catalogo.db.catalogo_repository", "_RICERCA_CONVERSIONI")),
    ("config.tipi_ruolo_tipi_indirizzo", _da_costante("apps.config.db.tipi_ruolo_tipi_indirizzo_repository", "_RICERCA")),
    ("config.utilities_tipi_ruolo", _da_costante("apps.config.db.utilities_tipi_ruolo_repository", "_RICERCA")),
    ("vendite.note", _da_costante("apps.core.db.partitioned_note_repository", "_RICERCA_NOTE_VENDITE")),
    ("catalogo.note", _da_costante("apps.core.db.partitioned_note_repository", "_RICERCA_NOTE_CATALOGO")),
    ("catalogo.articolo_uom", _da_costante("apps.catalogo.db.catalogo_uom_repository", "_RICERCA_ARTICOLO_UOM")),
    ("config.parametri_impostazioni", _da_costante("apps.core.db.parameter_repository", "_RICERCA_IMPOSTAZIONI")),
    ("pratiche.definizioni_workflow", _da_costante("apps.pratiche.db.definizioni_repository", "_RICERCA_DEFINIZIONI")),
    ("pratiche.pratiche", _da_costante("apps.pratiche.db.pratiche_repository", "_RICERCA_PRATICHE")),
    ("anagrafiche.emittenti_fiscali", _da_costante("apps.anagrafiche.db.emittenti_fiscali_repository", "_RICERCA_EMITTENTI")),
    ("anagrafiche.emittente_billing_account", _da_costante("apps.anagrafiche.db.emittenti_fiscali_repository", "_RICERCA_EMITTENTE_BA")),
    # Flussi di una pratica e utilizzo della matrice utility/ruoli (2026-09-27,
    # brief-db-liste-datatable-grezze righe 3 e 4).
    ("pratiche.flussi", _da_costante("apps.pratiche.db.pratiche_repository", "_RICERCA_FLUSSI")),
    ("config.utilities_tipi_ruolo_usage", _da_costante("apps.config.db.utilities_tipi_ruolo_repository", "_RICERCA_USAGE")),
    # Sessioni attive e reparti (2026-09-27, brief-db-liste-datatable-grezze righe 1 e 5).
    ("core.sessioni_attive", _da_costante("apps.core.db.session_audit_repository", "_RICERCA_SESSIONI_ATTIVE")),
    ("amm.reparti", _da_costante("apps.amm_software.db.amm_software_repository", "_RICERCA_REPARTI")),
    # Le sei geografiche (2026-09-27, brief-db-liste-datatable-grezze riga 9).
    ("config.stati", _da_costante("apps.anagrafiche.db.geo_repository", "_RICERCA_STATI")),
    ("config.regioni", _da_costante("apps.anagrafiche.db.geo_repository", "_RICERCA_REGIONI")),
    ("config.province", _da_costante("apps.anagrafiche.db.geo_repository", "_RICERCA_PROVINCE")),
    ("config.comuni", _da_costante("apps.anagrafiche.db.geo_repository", "_RICERCA_COMUNI")),
    ("config.codici_postali", _da_costante("apps.anagrafiche.db.geo_repository", "_RICERCA_CODICI_POSTALI")),
    ("config.toponomastica", _da_costante("apps.anagrafiche.db.geo_repository", "_RICERCA_TOPONOMASTICA")),
    # Righe dei documenti di vendita (2026-09-28, brief-db-liste-righe-documento
    # lotto A): la dichiarazione passata al BB dal mixin `RigheDocumentoRepositoryMixin`.
    ("vendite.preventivo_righe", _da_costante(_V + "preventivi_repository", "_RICERCA_RIGHE")),
    ("vendite.ordine_righe", _da_costante(_V + "ordini_repository", "_RICERCA_RIGHE")),
    ("vendite.ddt_righe", _da_costante(_V + "ddt_repository", "_RICERCA_RIGHE")),
    ("vendite.reso_righe", _da_costante(_V + "resi_repository", "_RICERCA_RIGHE")),
    # La distinta base (2026-09-28, lotto C): lista 101 dentro il drawer BoM.
    ("catalogo.articolo_componenti", _da_costante("apps.catalogo.db.catalogo_bom_repository", "_RICERCA_COMPONENTI")),
    # Le righe di una fattura (2026-09-28, lotto C): lista 102 sulla vista di lista.
    ("vendite.fattura_righe", _da_costante(_V + "fatture_repository", "_RICERCA_RIGHE_FATTURA")),
    # Le righe di un contratto (2026-09-30, lotto D): lista 103 sulla funzione.
    ("vendite.contratto_righe", _da_costante(_V + "contratti_repository", "_RICERCA_RIGHE_CONTRATTO")),
    # Le righe di un'offerta (2026-10-05, gemella della 103): lista 106 sulla funzione.
    ("vendite.offerta_righe", _da_costante(_V + "offerte_repository", "_RICERCA_RIGHE_OFFERTA")),
    # La ricerca universale (2026-10-31, D-4 di brief-db-liste-datatable-grezze-
    # secondo-giro): lista 113 sulla funzione, che riceve i campi dal BB.
    ("anagrafiche.ricerca_soggetti", _da_costante("apps.core.db.search_repository", "RICERCA_SOGGETTI")),
)

# Liste con colonne `ricercabile_full = t` la cui ricerca e' ancora scritta a
# mano (o assente) e non passa dal BB. Fotografia del 2026-09-23: PUO' SOLO
# CALARE (test 4). Il piano per svuotarlo:
# docs/it/dev/work-done/brief-be-ricerca-full-liste-residue.md
_DEBITO_RICERCA_A_MANO: frozenset[str] = frozenset()


# Scopo: i `campo_sorgente` ricercabili e attivi di una lista, dal seed.
def _ricercabili(codice: str) -> set[str]:
    return {
        r["campo_sorgente"] for r in _colonne_attive(codice)
        if r["ricercabile_full"] == "t" and r["campo_sorgente"]
    }


# Scopo: codici delle liste che hanno almeno una colonna ricercabile attiva.
def _liste_ricercabili() -> set[str]:
    return {
        d["codice"] for d in _seed("lista_definizione.csv") if _ricercabili(d["codice"])
    }


# Scopo: chiama il BB con le due letture del catalogo sostituite: le colonne
#        accese (`accese`) e la soglia della lista (`soglia`, di norma quella di
#        progetto). Torna anche i due mock, per chi guarda COSA si e' letto.
def _condizione(termine, ricerca, accese, *, soglia=3, **kwargs):
    conditions: list[str] = []
    params: list = []
    with catalogo_ricerca_finto(accese, soglia=soglia) as (lettura, lettura_soglia):
        add_ricerca_full_condition(conditions, params, termine, ricerca, **kwargs)
    return conditions, params, lettura, lettura_soglia


class RicercaFullSeedTests(unittest.TestCase):
    def test_la_dichiarazione_copre_il_seed(self):
        for codice, risolvi in _RICERCHE:
            with self.subTest(lista=codice):
                dichiarate = set(risolvi().colonne)
                mancanti = _ricercabili(codice) - dichiarate
                self.assertFalse(
                    mancanti,
                    f"{codice}: il catalogo accende {sorted(mancanti)} ma la "
                    f"dichiarazione `RicercaFull` non le sa cercare",
                )

    def test_la_dichiarazione_nomina_la_sua_lista(self):
        for codice, risolvi in _RICERCHE:
            with self.subTest(lista=codice):
                self.assertEqual(risolvi().lista_codice, codice)

    def test_ogni_lista_ricercabile_e_registrata_o_in_debito(self):
        registrate = {c for c, _ in _RICERCHE}
        scoperte = _liste_ricercabili() - registrate - _DEBITO_RICERCA_A_MANO
        self.assertFalse(
            scoperte,
            f"liste con colonne `ricercabile_full` senza BB e fuori dal debito: "
            f"{sorted(scoperte)} — dichiarare una `RicercaFull`, cercare con "
            f"`add_ricerca_full_condition` e registrarle in `_RICERCHE`",
        )

    def test_il_debito_non_cresce(self):
        registrate = {c for c, _ in _RICERCHE}
        self.assertFalse(
            registrate & _DEBITO_RICERCA_A_MANO,
            "lista registrata e ancora in debito: toglierla da `_DEBITO_RICERCA_A_MANO`",
        )
        stantie = _DEBITO_RICERCA_A_MANO - _liste_ricercabili()
        self.assertFalse(stantie, f"debito su liste senza colonne ricercabili: {sorted(stantie)}")

    # --- Il BB --------------------------------------------------------------

    def test_bb_cerca_sull_intersezione_nell_ordine_della_dichiarazione(self):
        ricerca = RicercaFull("x.lista", ("numero", "ba_codice", "descrizione"))
        conditions, params, lettura, lettura_soglia = _condizione(
            "  50%_x  ", ricerca, ["descrizione", "numero"],
        )
        lettura.assert_called_once_with("x.lista")
        lettura_soglia.assert_called_once_with("x.lista")
        self.assertEqual(
            conditions, ["((v.numero)::text ILIKE %s OR (v.descrizione)::text ILIKE %s)"],
        )
        self.assertEqual(params, ["%50\\%\\_x%", "%50\\%\\_x%"])

    def test_bb_mappa_usa_le_espressioni_dichiarate(self):
        ricerca = RicercaFull("x.lista", {"ba_codice": "ba.codice", "fase": "COALESCE(p.a, p.b)"})
        conditions, _, _, _ = _condizione("abc", ricerca, ["ba_codice", "fase"], alias="ignorato")
        self.assertEqual(
            conditions, ["((ba.codice)::text ILIKE %s OR (COALESCE(p.a, p.b))::text ILIKE %s)"],
        )

    def test_bb_colonna_accesa_non_dichiarata_ignorata_con_warning(self):
        ricerca = RicercaFull("x.lista", ("numero",))
        with self.assertLogs("apps.core.db._helpers", level="WARNING") as log:
            conditions, params, _, _ = _condizione("abc", ricerca, ["numero", "segreta"])
        self.assertEqual(conditions, ["((v.numero)::text ILIKE %s)"])
        self.assertEqual(len(params), 1)
        self.assertIn("segreta", log.output[0])

    # ⭐ La sola intersezione (estratta il 2026-10-31): la legge chi passa i
    #    NOMI a una funzione DB invece di un `ILIKE` (la ricerca universale).
    #    Stesso ordine, stesso warning, elenco vuoto senza colonne accese; su
    #    una mappa conta il nome, non l'espressione.
    def test_bb_colonne_attive_sono_l_intersezione(self):
        ricerca = RicercaFull("x.lista", ("numero", "ba_codice", "descrizione"))
        with catalogo_ricerca_finto(["descrizione", "numero"]) as (lettura, _):
            self.assertEqual(colonne_ricerca_attive(ricerca), ["numero", "descrizione"])
        lettura.assert_called_once_with("x.lista")
        with self.assertLogs("apps.core.db._helpers", level="WARNING") as log, \
                catalogo_ricerca_finto(["numero", "segreta"]):
            self.assertEqual(colonne_ricerca_attive(ricerca), ["numero"])
        self.assertIn("segreta", log.output[0])
        with catalogo_ricerca_finto([]):
            self.assertEqual(colonne_ricerca_attive(ricerca), [])
        mappa = RicercaFull("x.lista", {"ba_codice": "ba.codice"})
        with catalogo_ricerca_finto(["ba_codice"]):
            self.assertEqual(colonne_ricerca_attive(mappa), ["ba_codice"])

    def test_bb_nessuna_colonna_accesa_non_trova_niente(self):
        ricerca = RicercaFull("x.lista", ("numero",))
        conditions, params, _, _ = _condizione("abc", ricerca, [])
        self.assertEqual((conditions, params), (["FALSE"], []))

    def test_bb_termine_vuoto_non_legge_niente(self):
        ricerca = RicercaFull("x.lista", ("numero",))
        for termine in (None, "", "   "):
            with self.subTest(termine=termine):
                conditions, params, lettura, lettura_soglia = _condizione(termine, ricerca, ["numero"])
                self.assertEqual((conditions, params), ([], []))
                lettura.assert_not_called()
                lettura_soglia.assert_not_called()

    def test_bb_la_soglia_e_quella_della_lista(self):
        ricerca = RicercaFull("x.lista", ("numero",))
        # Sotto la soglia della lista: si legge la soglia, non le colonne.
        conditions, params, lettura, lettura_soglia = _condizione(" ab ", ricerca, ["numero"], soglia=3)
        self.assertEqual((conditions, params), ([], []))
        lettura_soglia.assert_called_once_with("x.lista")
        lettura.assert_not_called()
        # Lo stesso termine, su una lista che cerca da uno, filtra.
        for termine in ("F", "ab"):
            with self.subTest(termine=termine):
                conditions, _, _, _ = _condizione(termine, ricerca, ["numero"], alias="t", soglia=1)
                self.assertEqual(conditions, ["((t.numero)::text ILIKE %s)"])
        # Esattamente sulla soglia: filtra (la soglia e' «da», non «oltre»).
        conditions, _, _, _ = _condizione("abc", ricerca, ["numero"], soglia=3)
        self.assertEqual(conditions, ["((v.numero)::text ILIKE %s)"])

    def test_bb_alias_invalido_esplode_anche_senza_termine(self):
        ricerca = RicercaFull("x.lista", ("numero",))
        for termine in (None, "abc"):
            with self.subTest(termine=termine), self.assertRaises(RuntimeError):
                _condizione(termine, ricerca, ["numero"], alias="v; DROP")

    def test_dichiarazione_congelata_sulla_copia(self):
        mappa = {"ba_codice": "ba.codice"}
        ricerca = RicercaFull("x.lista", mappa)
        mappa["intrusa"] = "1; --"
        self.assertEqual(set(ricerca.colonne), {"ba_codice"})
        with self.assertRaises(TypeError):
            ricerca.colonne["altra"] = "x"  # type: ignore[index]

    def test_dichiarazione_invalida_esplode_alla_costruzione(self):
        for kwargs in (
            {"lista_codice": "x.lista", "colonne": ("v.numero",)},
            {"lista_codice": "x.lista", "colonne": ()},
            {"lista_codice": "", "colonne": ("numero",)},
            {"lista_codice": "x.lista", "colonne": {"numero": "  "}},
            {"lista_codice": "x.lista", "colonne": {"Numero": "v.numero"}},
            # `("numero")` senza virgola e' una stringa: sei colonne di una lettera.
            {"lista_codice": "x.lista", "colonne": "numero"},
        ):
            with self.subTest(**{k: repr(v) for k, v in kwargs.items()}):
                with self.assertRaises(RuntimeError):
                    RicercaFull(**kwargs)

    # --- La soglia non si dichiara nel codice --------------------------------

    def test_nessuna_chiamata_dichiara_la_soglia(self):
        for funzione in (add_ricerca_full_condition, param_ricerca_full):
            with self.subTest(firma=funzione.__name__):
                self.assertNotIn("min_caratteri", inspect.signature(funzione).parameters)
        apps = Path(__file__).resolve().parents[2]
        colpevoli: list[str] = []
        for sorgente in sorted(apps.rglob("*.py")):
            albero = ast.parse(sorgente.read_text(encoding="utf-8"), filename=str(sorgente))
            for nodo in ast.walk(albero):
                if not isinstance(nodo, ast.Call):
                    continue
                nome = getattr(nodo.func, "id", None) or getattr(nodo.func, "attr", None)
                if nome not in {"add_ricerca_full_condition", "param_ricerca_full"}:
                    continue
                if any(k.arg == "min_caratteri" for k in nodo.keywords):
                    colpevoli.append(f"{sorgente.relative_to(apps)}:{nodo.lineno}")
        self.assertFalse(
            colpevoli,
            f"chiamate che dichiarano la soglia: {colpevoli} — la soglia e' "
            f"`ricerca_min_caratteri` del catalogo della lista",
        )

    def test_i_test_fingono_il_catalogo_da_una_sede(self):
        apps = Path(__file__).resolve().parents[2]
        sede = Path(__file__).resolve().parent / "ricerca_catalogo_fakes.py"
        # Composti, non scritti: scritti per intero, questo file troverebbe se stesso.
        letture = tuple(f"_helpers.{nome}" for nome in ("colonne_ricerca_accese", "soglia_ricerca"))
        colpevoli = [
            str(sorgente.relative_to(apps))
            for sorgente in sorted(apps.rglob("tests/**/*.py"))
            if sorgente != sede
            and any(lettura in sorgente.read_text(encoding="utf-8") for lettura in letture)
        ]
        self.assertFalse(
            colpevoli,
            f"test che sostituiscono a mano le letture del catalogo: {colpevoli} — "
            f"si usa `catalogo_ricerca_finto` (apps/core/tests/ricerca_catalogo_fakes.py)",
        )
