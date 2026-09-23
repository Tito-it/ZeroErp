# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La ricerca libera delle liste sul DB VERO: il BB
#        `add_ricerca_full_condition` legge il catalogo con
#        `ui.fn_lista_colonne_ricerca_full` e la condizione che costruisce
#        parte sulla vista della lista. Gemello di `test_ricerca_full_seed`,
#        che confronta gli elenchi senza database.
#
#        ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Tutto in transazione
#        annullata: lo spegnimento di una colonna del test 3 non resta.
# ------------------------------------------------------------
"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`):

1. test_la_condizione_parte_sulla_vista_di_ogni_lista
   Per ogni lista registrata, la condizione del BB applicata alla sua vista
   (`schema_dati.vista_sql` del catalogo) produce SQL valido. I mock del test
   gemello non eseguono la SQL: un `::text` mancante o un nome che la vista
   non ha sarebbe un 500 al primo operatore che cerca. Una lista senza vista
   deve nominare in `_ESERCITATE_DAL_REPOSITORY` il test che la cerca dal suo
   repository, sul DB vero: il nome si risolve, e un test rinominato o
   cancellato fa rosso qui.

2. test_il_catalogo_non_accende_colonne_sconosciute
   Le colonne che il catalogo accende per l'operatore sono tutte dichiarate
   dal repository: nessun `warning` «colonne accese non dichiarate».

3. test_spegnere_una_colonna_la_toglie_subito
   Il motivo della lettura a runtime: si spegne `ricercabile_full` su una
   colonna, e la stessa chiamata non la cerca piu' — senza toccare il codice.

4. test_la_ricerca_trova_ogni_colonna_accesa_dal_repository
   Per le liste che non hanno un mondo costruito nel loro dominio: una riga
   costruita, e per ogni colonna che il catalogo accende la ricerca dal
   repository la trova (`verifica_ricerca_colonna_per_colonna`). E' anche
   l'esercizio delle liste senza vista (registri, processi).

5. test_la_configurazione_dice_se_la_lista_cerca
   `ui_service.get_lista_config` porta `ricerca_full`: vero se il catalogo
   accende almeno una colonna per l'operatore, falso altrimenti — e falso
   subito se l'amministratore le spegne tutte. E' il dato con cui il frontend
   mostra la casella di ricerca (brief §7-bis).
"""

from __future__ import annotations

import importlib
import unittest

from django.db import connection, transaction

from apps.core.db._helpers import add_ricerca_full_condition
from apps.core.tests.db_e2e import (
    apri_contesto_operatore,
    richiedi_db_provvisto,
    verifica_ricerca_colonna_per_colonna,
)
from apps.core.tests.test_liste_configurabili_seed import _seed
from apps.core.tests.test_ricerca_full_seed import _RICERCHE


# Liste registrate SENZA `vista_sql`: la loro query e' quella del repository,
# e la si esercita dal repository sul mondo costruito — per ogni colonna accesa
# si cerca il valore di una riga e la riga deve uscire (brief §5.4 p.3).
# `codice lista` -> `modulo.Classe.metodo` del test che lo fa.
_QUI = "apps.core.tests.db.test_ricerca_full_db.RicercaFullDbTests."
_DOC = "apps.magazzino.tests.db.test_documento_interno_db.DocumentoInternoDbTests."
_PAG = "apps.pagamenti.tests.db.test_rate_lista_db.RicercaListeDbTests."
_MAG = "apps.magazzino.tests.db.test_anagrafiche_magazzino_db.AnagraficheMagazzinoDbTests."
_ESERCITATE_DAL_REPOSITORY: dict[str, str] = {
    "magazzino.magazzini": _MAG + "test_la_ricerca_trova_ogni_colonna_accesa",
    "magazzino.ubicazioni": _MAG + "test_la_ricerca_trova_ogni_colonna_accesa",
    "magazzino.lotti": _MAG + "test_la_ricerca_trova_ogni_colonna_accesa",
    "vendite.registri_numerazione": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "amm.processi": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "catalogo.unita_misura": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "catalogo.conversioni_uom": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "config.tipi_ruolo_tipi_indirizzo": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "config.utilities_tipi_ruolo": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "pratiche.pratiche": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "anagrafiche.emittenti_fiscali": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "anagrafiche.emittente_billing_account": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "magazzino.inventari": _DOC + "test_la_ricerca_trova_ogni_colonna_accesa",
    "magazzino.rettifiche": _DOC + "test_la_ricerca_trova_ogni_colonna_accesa",
    "magazzino.disponibilita": _DOC + "test_la_ricerca_trova_ogni_colonna_accesa",
    "magazzino.disponibilita_articoli": _DOC + "test_la_ricerca_trova_ogni_colonna_accesa",
    "magazzino.inventario_righe": _DOC + "test_la_ricerca_trova_ogni_colonna_accesa",
    "magazzino.rettifica_righe": _DOC + "test_la_ricerca_trova_ogni_colonna_accesa",
    "magazzino.inventario_piano": _DOC + "test_la_ricerca_trova_ogni_colonna_accesa",
    "magazzino.movimenti": _DOC + "test_la_ricerca_trova_ogni_colonna_accesa",
    "pagamenti.distinte": _PAG + "test_la_ricerca_trova_ogni_colonna_accesa",
    "pagamenti.righe": _PAG + "test_la_ricerca_trova_ogni_colonna_accesa",
    "pagamenti.distinta_righe": _PAG + "test_la_ricerca_trova_ogni_colonna_accesa",
    "pagamenti.rate_fuori_capienza": _PAG + "test_la_ricerca_trova_ogni_colonna_accesa",
    "pagamenti.eccedenze": _PAG + "test_la_ricerca_trova_ogni_colonna_accesa",
}


# Scopo: il test nominato esiste (modulo, classe e metodo si risolvono).
def _risolvi_test(percorso: str) -> None:
    modulo, classe, metodo = percorso.rsplit(".", 2)
    getattr(getattr(importlib.import_module(modulo), classe), metodo)


class _Annulla(Exception):
    """Esce dal blocco atomico annullandolo."""


# Scopo: la vista qualificata di una lista, dal seed del catalogo.
def _vista(codice: str) -> str | None:
    for riga in _seed("lista_definizione.csv"):
        if riga["codice"] == codice:
            vista = riga["vista_sql"]
            if not vista or vista == "NULL":
                return None
            return f"{riga['schema_dati']}.{vista}"
    raise AssertionError(f"lista '{codice}' assente da lista_definizione.csv")


class RicercaFullDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("ui.fn_lista_colonne_ricerca_full(character varying)")

    def test_la_condizione_parte_sulla_vista_di_ogni_lista(self):
        for codice, risolvi in _RICERCHE:
            with self.subTest(lista=codice):
                vista = _vista(codice)
                # ⚠️ Le liste senza vista si esercitano dal repository. Chi ne
                #    registra una senza deve nominare qui il test che lo fa —
                #    fallisce, non salta.
                if vista is None:
                    self.assertIn(
                        codice, _ESERCITATE_DAL_REPOSITORY,
                        f"{codice}: nessuna vista_sql, serve un esercizio dal repository",
                    )
                    _risolvi_test(_ESERCITATE_DAL_REPOSITORY[codice])
                    continue
                with transaction.atomic(), connection.cursor() as cur:
                    apri_contesto_operatore(cur)
                    conditions: list[str] = []
                    params: list = []
                    add_ricerca_full_condition(conditions, params, "abc", risolvi())
                    self.assertTrue(conditions, codice)
                    cur.execute(
                        f"EXPLAIN SELECT 1 FROM {vista} v WHERE {' AND '.join(conditions)}",  # noqa: S608
                        params,
                    )

    def test_il_catalogo_non_accende_colonne_sconosciute(self):
        for codice, risolvi in _RICERCHE:
            with self.subTest(lista=codice):
                with transaction.atomic(), connection.cursor() as cur:
                    apri_contesto_operatore(cur)
                    with self.assertNoLogs("apps.core.db._helpers", level="WARNING"):
                        add_ricerca_full_condition([], [], "abc", risolvi())

    def test_spegnere_una_colonna_la_toglie_subito(self):
        # La dichiarazione che il repository passa davvero, non una sua copia.
        ricerca = dict(_RICERCHE)["vendite.preventivi"]()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                prima: list[str] = []
                add_ricerca_full_condition(prima, [], "abc", ricerca)
                self.assertIn("(v.ba_codice)::text", prima[0])

                cur.execute(
                    "UPDATE ui.lista_colonna lc SET ricercabile_full = false "
                    "  FROM ui.lista_definizione ld "
                    " WHERE ld.id = lc.lista_id AND ld.codice = %s "
                    "   AND lc.campo_sorgente = 'ba_codice'",
                    ["vendite.preventivi"],
                )
                self.assertEqual(cur.rowcount, 1)
                dopo: list[str] = []
                add_ricerca_full_condition(dopo, [], "abc", ricerca)
                self.assertNotIn("ba_codice", dopo[0])
                self.assertIn("(v.numero)::text", dopo[0])
                raise _Annulla
        except _Annulla:
            pass

    def test_la_ricerca_trova_ogni_colonna_accesa_dal_repository(self):
        from apps.anagrafiche.db.categorie_clienti_repository import CategorieClientiRepository
        from apps.anagrafiche.db.emittenti_fiscali_repository import (
            EmittentiFiscaliBillingAccountRepository,
            EmittentiFiscaliRepository,
        )
        from apps.anagrafiche.db.fornitori_repository import FornitoriRepository
        from apps.config.db.tipi_ruolo_tipi_indirizzo_repository import TipiRuoloTipiIndirizzoRepository
        from apps.config.db.utilities_tipi_ruolo_repository import UtilitiesTipiRuoloRepository
        from apps.pratiche.db.pratiche_repository import PraticheRepository
        from apps.anagrafiche.db.indirizzi_repository import IndirizziRepository
        from apps.catalogo.db.catalogo_repository import CatalogoRepository
        from apps.core.db.processi_repository import ProcessiRepository
        from apps.vendite.db.registri_repository import RegistriRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                # Il mondo del cliente PRIMA del contesto: il builder vuole
                # scegliersi l'azienda, e col contesto aperto userebbe quella di
                # chi agisce (che qui non ne ha una).
                cur.execute("SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('ricerca full BE', 'RFC')")
                colonne = [c.name for c in cur.description]
                mondo = dict(zip(colonne, cur.fetchone()))
                apri_contesto_operatore(cur)
                # Il mondo si COSTRUISCE: una riga per lista, con un valore per
                # colonna che sta solo li'.
                cur.execute(
                    "INSERT INTO anagrafiche.categorie_clienti (codice, descrizione, codice_interno) "
                    "VALUES ('RICCODCAT', 'Categoria ricdesccat', 'RICCODCAT') RETURNING id"
                )
                categoria = cur.fetchone()[0]
                cur.execute("SELECT dbops.fn_pgtap_crea_indirizzo_dettaglio('ricerca full BE')")
                indirizzo = cur.fetchone()[0]
                cur.execute(
                    "SELECT indirizzo_normalizzato, descrizione_comune "
                    "  FROM anagrafiche.vw_indirizzi_dettaglio WHERE indirizzo_dettaglio_id = %s",
                    [indirizzo],
                )
                ind_normalizzato, ind_comune = cur.fetchone()
                cur.execute("SELECT soggetto_ruolo_id FROM dbops.fn_pgtap_crea_emittente_operatore('RFB')")
                cur.execute("SELECT script.fn_pgtap_registro_fattura(%s)", [cur.fetchone()[0]])
                registro = cur.fetchone()[0]
                cur.execute(
                    "UPDATE vendite.registri_fatturazione "
                    "   SET descrizione = 'Registro ricdescreg', prefisso = 'RPX/' "
                    " WHERE id = %s RETURNING codice",
                    [registro],
                )
                registro_codice = cur.fetchone()[0]
                # I processi sono SEED (contratto, non fotografia): si legge il suo.
                cur.execute("SELECT id, descrizione FROM dbops.processi WHERE codice = 'digest_presidi'")
                processo, processo_descrizione = cur.fetchone()
                cur.execute(
                    "INSERT INTO catalogo.uom_tipi (codice, codice_interno, descrizione) "
                    "VALUES ('RICCODUT', 'RICINTUT', 'Tipo ricdescut') RETURNING id"
                )
                uom_tipo = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO catalogo.unita_misura (codice, descrizione, tipo_uom_id) "
                    "VALUES ('RICCODUM', 'Unita ricdescum', %s) RETURNING id",
                    [uom_tipo],
                )
                unita = cur.fetchone()[0]
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Fornitore ricragfor')")
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_ruolo(%s, 'FO', 1)", [cur.fetchone()[0]])
                cur.execute(
                    "INSERT INTO anagrafiche.fornitori (soggetto_ruolo_id, stato_fornitore_id) "
                    "SELECT %s, id FROM config.stati_fornitore WHERE codice_interno = 'VE' RETURNING id",
                    [cur.fetchone()[0]],
                )
                fornitore = cur.fetchone()[0]
                cur.execute(
                    "SELECT codice, id_fiscale_univoco_cf_piva FROM anagrafiche.vw_fornitori_dettaglio WHERE id = %s",
                    [fornitore],
                )
                fornitore_codice, fornitore_id_fiscale = cur.fetchone()
                cur.execute(
                    "INSERT INTO catalogo.unita_misura (codice, descrizione, tipo_uom_id) "
                    "VALUES ('RICCODU2', 'Unita ricdescu2', %s) RETURNING id",
                    [uom_tipo],
                )
                unita_2 = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO catalogo.unita_misura_conversioni (uom_from_id, uom_to_id, fattore, valido_dal) "
                    "VALUES (%s, %s, 10, current_date) RETURNING id",
                    [unita, unita_2],
                )
                conversione = cur.fetchone()[0]
                # Le matrici di configurazione sono SEED (contratto): se ne legge una riga.
                cur.execute(
                    "SELECT x.id, tr.codice, tr.descrizione, ti.codice, ti.descrizione "
                    "  FROM config.tipi_ruolo_tipi_indirizzo x "
                    "  JOIN config.tipi_ruoli tr ON tr.id = x.tipo_ruolo_id "
                    "  JOIN config.tipi_indirizzi ti ON ti.id = x.tipo_indirizzo_id "
                    " ORDER BY x.id LIMIT 1"
                )
                trti = cur.fetchone()
                cur.execute(
                    "SELECT x.id, u.codice, u.descrizione, tr.codice, tr.descrizione "
                    "  FROM config.utilities_tipi_ruolo x "
                    "  JOIN config.utilities u ON u.id = x.utility_id "
                    "  JOIN config.tipi_ruoli tr ON tr.id = x.tipo_ruolo_id "
                    " ORDER BY x.id LIMIT 1"
                )
                utr = cur.fetchone()
                cur.execute(
                    "SELECT ef.codice, s.ragione_sociale_completa, s.partita_iva "
                    "  FROM anagrafiche.emittenti_fiscali ef "
                    "  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id "
                    "  JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id WHERE ef.id = %s",
                    [mondo["emittente_fiscale_id"]],
                )
                ef_codice, ef_ragione, ef_piva = cur.fetchone()
                cur.execute(
                    "SELECT ba.codice, s.ragione_sociale_completa, s.id_fiscale_univoco_cf_piva "
                    "  FROM anagrafiche.billing_account ba "
                    "  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id "
                    "  JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id WHERE ba.id = %s",
                    [mondo["billing_account_id"]],
                )
                ba_codice, ba_ragione, ba_id_fiscale = cur.fetchone()
                cur.execute(
                    "SELECT pratiche.fn_crea_pratica(%s, (SELECT id FROM pratiche.tipi_prestazione WHERE attivo ORDER BY id LIMIT 1), "
                    "       %s, NULL, NULL, NULL, 'Pratica ricdescpra', '{}'::jsonb)",
                    [mondo["emittente_fiscale_id"], mondo["cliente_soggetto_id"]],
                )
                pratica = cur.fetchone()[0]
                cur.execute("SELECT codice FROM pratiche.pratiche WHERE id = %s", [pratica])
                pratica_codice = cur.fetchone()[0]

                verifica_ricerca_colonna_per_colonna(
                    self, cur, "anagrafiche.categorie_clienti", categoria,
                    {"codice": "riccodcat", "descrizione": "ricdesccat"},
                    lambda t: CategorieClientiRepository().list_categorie(search=t, limit=200)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "anagrafiche.indirizzi", indirizzo,
                    {"indirizzo_normalizzato": ind_normalizzato, "descrizione_comune": ind_comune},
                    # Il comune e' di molti indirizzi: la pagina deve contenerli tutti.
                    lambda t: IndirizziRepository().list_indirizzi_dettaglio(search=t, limit=100_000)[0],
                    chiave="indirizzo_dettaglio_id",
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "vendite.registri_numerazione", registro,
                    {"codice": registro_codice, "descrizione": "ricdescreg", "prefisso": "RPX/"},
                    # `None` = nessun filtro di perimetro: qui si prova la ricerca, non lo scope.
                    lambda t: RegistriRepository().list_registri(None, search=t, limit=500)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "amm.processi", processo,
                    {"codice": "digest_presidi", "descrizione": processo_descrizione},
                    lambda t: ProcessiRepository().list_processi(search=t, limit=500)[0],
                )
                _uom = {"attivo": None, "order_by": "codice", "order_dir": "asc", "limit": 200, "offset": 0}
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "catalogo.uom_tipi", uom_tipo,
                    {"codice": "riccodut", "codice_interno": "ricintut", "descrizione": "ricdescut"},
                    lambda t: CatalogoRepository().list_uom_tipi(search=t, **_uom)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "catalogo.unita_misura", unita,
                    {"codice": "riccodum", "descrizione": "ricdescum"},
                    lambda t: CatalogoRepository().list_unita_misura(search=t, **_uom)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "anagrafiche.fornitori", fornitore,
                    {"codice": fornitore_codice, "ragione_sociale_completa": "ricragfor",
                     "id_fiscale_univoco_cf_piva": fornitore_id_fiscale},
                    lambda t: FornitoriRepository().list_fornitori(search=t, limit=500)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "catalogo.conversioni_uom", conversione,
                    {"uom_from_codice": "riccodum", "uom_from_descrizione": "ricdescum",
                     "uom_to_codice": "riccodu2", "uom_to_descrizione": "ricdescu2"},
                    lambda t: CatalogoRepository().list_conversioni(search=t, attivo=None, limit=200)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "config.tipi_ruolo_tipi_indirizzo", trti[0],
                    {"tipo_ruolo_codice": trti[1], "tipo_ruolo_descrizione": trti[2],
                     "tipo_indirizzo_codice": trti[3], "tipo_indirizzo_descrizione": trti[4]},
                    lambda t: TipiRuoloTipiIndirizzoRepository().list_matrice(search=t, limit=200)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "config.utilities_tipi_ruolo", utr[0],
                    {"utility_codice": utr[1], "utility_descrizione": utr[2],
                     "tipo_ruolo_codice": utr[3], "tipo_ruolo_descrizione": utr[4]},
                    lambda t: UtilitiesTipiRuoloRepository().list_matrice(search=t, limit=200)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "pratiche.pratiche", pratica,
                    {"codice": pratica_codice, "descrizione": "ricdescpra",
                     "soggetto_display": ba_ragione},
                    lambda t: PraticheRepository().list_pratiche(
                        emittente_fiscale_id=mondo["emittente_fiscale_id"], search=t, limit=200, offset=0)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "anagrafiche.emittenti_fiscali", mondo["emittente_fiscale_id"],
                    {"codice": ef_codice, "ragione_sociale_completa": ef_ragione, "partita_iva": ef_piva},
                    lambda t: EmittentiFiscaliRepository().list_emittenti_fiscali(search=t, limit=500)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "anagrafiche.emittente_billing_account", mondo["billing_account_id"],
                    {"billing_account_codice": ba_codice, "billing_account_ragione_sociale": ba_ragione,
                     "id_fiscale_univoco": ba_id_fiscale},
                    lambda t: EmittentiFiscaliBillingAccountRepository().list_by_emittente(
                        mondo["emittente_soggetto_ruolo_id"], search=t, limit=200)[0],
                    chiave="billing_account_id",
                )
                raise _Annulla
        except _Annulla:
            pass

    def test_la_configurazione_dice_se_la_lista_cerca(self):
        from django.contrib.auth import get_user_model

        from apps.ui.services.ui_service import UiService

        try:
            with transaction.atomic(), connection.cursor() as cur:
                uid = apri_contesto_operatore(cur)
                utente = get_user_model().objects.get(pk=uid)
                svc = UiService()
                self.assertTrue(svc.get_lista_config_per_video(utente, "vendite.preventivi")["ricerca_full"])
                # Una lista del seed che non accende colonne (contratto: non cerca).
                self.assertFalse(svc.get_lista_config_per_video(utente, "vendite.lotti")["ricerca_full"])
                cur.execute(
                    "UPDATE ui.lista_colonna lc SET ricercabile_full = false "
                    "  FROM ui.lista_definizione ld "
                    " WHERE ld.id = lc.lista_id AND ld.codice = 'vendite.preventivi'"
                )
                self.assertFalse(svc.get_lista_config_per_video(utente, "vendite.preventivi")["ricerca_full"])
                raise _Annulla
        except _Annulla:
            pass
