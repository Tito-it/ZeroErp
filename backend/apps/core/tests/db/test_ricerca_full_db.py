# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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

6. test_la_configurazione_rifiuta_un_contesto_di_un_altro_utente
   La guardia di contesto (brief §12) sul DB vero: la GUC `app.current_user_id`
   di un altro utente, o vuota, e' `E_UI_CHIAMATA_NON_VALIDA` — la
   configurazione e la ricerca risponderebbero per due persone diverse.

7. test_la_soglia_e_della_lista_e_la_leggono_i_due_lettori
   La soglia della ricerca (`ui.lista_definizione.ricerca_min_caratteri`,
   brief-db-be-fe-ricerca-soglia-per-lista §5): la STESSA lista, messa a 1 e
   poi a 3 nel test (caso costruito, non il seed), filtra con un carattere solo
   nel primo caso — e la configurazione della schermata porta ogni volta lo
   stesso numero che il BB ha usato. Lista inesistente: `E_UI_LISTA_NON_TROVATA`.

8. test_il_resolver_soggetti_usa_la_soglia_della_lista
   Il `SoggettoResolver` cerca con la lista `anagrafiche.soggetti`: la sua
   configurazione (`min_search_length`) e' la soglia a catalogo di quella lista
   (brief §6 b). Caso costruito: la lista messa a 5 nel test, la configurazione
   del resolver risponde 5. Con una soglia sua, piu' bassa, il resolver
   proporrebbe soggetti non filtrati. Sul DB vero la configurazione del resolver
   non era mai passata: il filtro per nature castava a `bigint[]` un codice.
   Lo stesso ruolo senza matrice: `nature_ammesse` e' il dominio dell'enum
   `config.natura_soggetto_enum`, non un elenco scritto nel codice.

9. test_ricerca_soggetti_cerca_dove_il_catalogo_dice
   La ricerca universale (lista 113) sulla funzione: i campi arrivano dal BB
   (`p_campi_ricerca`, D-4 del 2026-10-31). Un soggetto costruito si trova da
   ogni colonna accesa; si spegne il CF a catalogo e il CF non lo trova piu',
   la ragione sociale si'; spente tutte, nessuna riga. ⭐ E' il caso che
   distingue: prima la funzione cercava sempre sui tre campi, e l'interruttore
   del catalogo non contava.
"""

from __future__ import annotations

import importlib
import unittest

from django.db import connection, transaction

from apps.core.db._helpers import add_ricerca_full_condition, soglia_ricerca
from apps.core.tests.db_e2e import (
    Annulla,
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
# Un utente che non esiste: la lista dei parametri esce intera anche senza i
# suoi override (i livelli restano vuoti), ed e' cio' che serve per cercare.
_ID_FINTO_UTENTE = 999_999_999
_DOC = "apps.magazzino.tests.db.test_documento_interno_db.DocumentoInternoDbTests."
_PAG = "apps.pagamenti.tests.db.test_rate_lista_db.RicercaListeDbTests."
_MAG = "apps.magazzino.tests.db.test_anagrafiche_magazzino_db.AnagraficheMagazzinoDbTests."
_TPL = "apps.documenti.tests.db.test_ricerca_liste_db.RicercaListeDocumentiDbTests."
_EML = "apps.core.tests.db.test_ricerca_email_db.RicercaEmailDbTests."
_ANA = "apps.anagrafiche.tests.db.test_ricerca_liste_db.RicercaListeAnagraficheDbTests."
_VEN = "apps.vendite.tests.db.test_ricerca_liste_db.RicercaListeVenditeDbTests."
_ESERCITATE_DAL_REPOSITORY: dict[str, str] = {
    "magazzino.magazzini": _MAG + "test_la_ricerca_trova_ogni_colonna_accesa",
    "magazzino.ubicazioni": _MAG + "test_la_ricerca_trova_ogni_colonna_accesa",
    "magazzino.lotti": _MAG + "test_la_ricerca_trova_ogni_colonna_accesa",
    "vendite.registri_numerazione": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "amm.processi": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "amm.reparti": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "core.sessioni_attive": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "pratiche.flussi": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "config.utilities_tipi_ruolo_usage": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "catalogo.unita_misura": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "catalogo.conversioni_uom": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "config.tipi_ruolo_tipi_indirizzo": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "config.utilities_tipi_ruolo": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "pratiche.pratiche": _QUI + "test_la_ricerca_trova_ogni_colonna_accesa_dal_repository",
    "pratiche.definizioni_workflow": _QUI + "test_definizioni_workflow_trova_ogni_colonna_accesa",
    "config.parametri_impostazioni": _QUI + "test_impostazioni_trova_ogni_colonna_accesa",
    "anagrafiche.ricerca_soggetti": _QUI + "test_ricerca_soggetti_cerca_dove_il_catalogo_dice",
    "vendite.note": _QUI + "test_note_trovano_ogni_colonna_accesa",
    "catalogo.note": _QUI + "test_note_trovano_ogni_colonna_accesa",
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
    "pagamenti.rate": _PAG + "test_la_ricerca_trova_ogni_colonna_accesa",
    "documenti.template_documenti": _TPL + "test_la_ricerca_trova_ogni_colonna_accesa",
    "documenti.template_asset": _TPL + "test_la_ricerca_trova_ogni_colonna_accesa",
    "documenti.template_versioni": _TPL + "test_versioni_e_documenti_sorgente_trovano_ogni_colonna_accesa",
    "documenti.documenti_sorgente": _TPL + "test_versioni_e_documenti_sorgente_trovano_ogni_colonna_accesa",
    "config.email_account": _EML + "test_la_ricerca_trova_ogni_colonna_accesa",
    "config.email_template": _EML + "test_la_ricerca_trova_ogni_colonna_accesa",
    "config.email_log": _EML + "test_la_ricerca_trova_ogni_colonna_accesa",
    "anagrafiche.soggetti": _ANA + "test_soggetti_trova_ogni_colonna_accesa",
    "anagrafiche.categorie_clienti_listini": _ANA + "test_categorie_clienti_listini_trova_ogni_colonna_accesa",
    "anagrafiche.operatori": _ANA + "test_operatori_trova_ogni_colonna_accesa",
    "vendite.listini": _VEN + "test_la_ricerca_trova_ogni_colonna_accesa",
    "vendite.listini_righe": _VEN + "test_la_ricerca_trova_ogni_colonna_accesa",
    "vendite.listini_versioni": _VEN + "test_la_ricerca_trova_ogni_colonna_accesa",
    "vendite.promo_articoli": _VEN + "test_la_ricerca_trova_ogni_colonna_accesa",
    "vendite.dash_competenza_gruppi": _VEN + "test_la_ricerca_trova_ogni_colonna_accesa",
    "vendite.contratto_righe": _VEN + "test_la_ricerca_trova_ogni_colonna_accesa",
    "vendite.offerta_righe": _VEN + "test_la_ricerca_trova_ogni_colonna_accesa",
}


# Scopo: il test nominato esiste (modulo, classe e metodo si risolvono).
def _risolvi_test(percorso: str) -> None:
    modulo, classe, metodo = percorso.rsplit(".", 2)
    getattr(getattr(importlib.import_module(modulo), classe), metodo)


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
                        f"EXPLAIN SELECT 1 FROM {vista} v WHERE {' AND '.join(conditions)}",
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
                raise Annulla
        except Annulla:
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
        from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
        from apps.core.db.session_audit_repository import SessionAuditRepository
        from apps.vendite.db.registri_repository import RegistriRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                # Il mondo del cliente PRIMA del contesto: il builder vuole
                # scegliersi l'azienda, e col contesto aperto userebbe quella di
                # chi agisce (che qui non ne ha una).
                cur.execute("SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('ricerca full BE', 'RFC')")
                colonne = [c.name for c in cur.description]
                mondo = dict(zip(colonne, cur.fetchone(), strict=True))
                operatore = apri_contesto_operatore(cur)
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
                    "VALUES (%s, %s, 10, script.fn_data_operativa()) RETURNING id",
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
                    "SELECT ef.codice, s.ragione_sociale_completa, s.id_fiscale_univoco_cf_piva "
                    "  FROM anagrafiche.emittenti_fiscali ef "
                    "  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id "
                    "  JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id WHERE ef.id = %s",
                    [mondo["emittente_fiscale_id"]],
                )
                ef_codice, ef_ragione, ef_id_fiscale = cur.fetchone()
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
                # I reparti (2026-09-27): un'unita' organizzativa costruita,
                # ATTIVA — la lista mostra solo quelle.
                cur.execute(
                    "INSERT INTO config.unita_organizzative (codice, codice_interno, descrizione) "
                    "VALUES ('RICCODREP', 'RICCODREP', 'Reparto ricdescrep') RETURNING id"
                )
                reparto = cur.fetchone()[0]
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "amm.reparti", reparto,
                    {"codice": "riccodrep", "descrizione": "ricdescrep"},
                    lambda t: AmmSoftwareRepository().list_reparti(search=t, limit=200)[0],
                )
                # Le sessioni attive (2026-09-27): un LOGIN di adesso per un
                # utente che ne ha altri; la chiave della riga e' il sid.
                # ⭐ L'IP si cerca come si mostra (`host()`, senza «/32»).
                # L'utente del contesto gia' aperto sopra (`apri_contesto_operatore`).
                utente = operatore
                cur.execute(
                    "INSERT INTO dbops.sessioni_utente (auth_user_id, evento, jti, ip_address, user_agent) "
                    "VALUES (%s, 'LOGIN', 'ric-sid-sessione', '10.99.88.77', 'RicUA/1.0 ricuaagent')",
                    [utente],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "core.sessioni_attive", "ric-sid-sessione",
                    {"user_agent": "ricuaagent", "ip_address": "10.99.88.77"},
                    lambda t: SessionAuditRepository().list_sessioni_attive_paginata(
                        utente, escludi_jti=None, search=t, limit=200)[0],
                    chiave="jti",
                )
                # I flussi di una pratica (2026-09-27, lista 85): un template
                # costruito sul tipo della pratica del mondo e un flusso DA
                # ESEGUIRE che lo istanzia. Si cerca per descrizione del
                # template (l'unica colonna accesa).
                cur.execute(
                    "INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, attivo, ripetibilita) "
                    "SELECT tipo_prestazione_id, 'TF_RICFLU', 'Template ricdescflu', true, 'SEMPRE' "
                    "  FROM pratiche.pratiche WHERE id = %s RETURNING id",
                    [pratica],
                )
                template_flusso = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id) "
                    "SELECT %s, %s, id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE' "
                    "RETURNING id",
                    [pratica, template_flusso],
                )
                flusso = cur.fetchone()[0]
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "pratiche.flussi", flusso,
                    {"template_flusso_descrizione": "ricdescflu"},
                    lambda t: PraticheRepository().list_flussi_pagina(pratica, search=t, limit=200)[0],
                )
                # L'utilizzo di una riga di matrice (2026-09-27, lista 86): una
                # riga SEED del ruolo EF (contratto) e un override dell'emittente
                # del mondo sulla sua utility. La riga della lista E'
                # l'emittente: chiave `emittente_id`.
                cur.execute(
                    "SELECT x.id, x.utility_id FROM config.utilities_tipi_ruolo x "
                    "  JOIN config.tipi_ruoli tr ON tr.id = x.tipo_ruolo_id "
                    " WHERE tr.codice_interno = 'EF' AND x.attivo "
                    " ORDER BY x.id LIMIT 1"
                )
                riga_ef = cur.fetchone()
                self.assertIsNotNone(riga_ef, "seed `config.utilities_tipi_ruolo` del ruolo EF assente")
                utr_ef, utr_ef_utility = riga_ef
                cur.execute(
                    "INSERT INTO anagrafiche.emittenti_fiscali_utilities "
                    "       (emittente_soggetto_ruolo_id, utility_id, arrotondamento_importi_dec, "
                    "        metodo_arrotondamento_importi) "
                    "VALUES (%s, %s, 2, 'HALF_UP') "
                    "ON CONFLICT (emittente_soggetto_ruolo_id, utility_id) DO NOTHING",
                    [mondo["emittente_soggetto_ruolo_id"], utr_ef_utility],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "config.utilities_tipi_ruolo_usage", mondo["emittente_fiscale_id"],
                    {"emittente_codice": ef_codice, "emittente_descrizione": ef_ragione},
                    lambda t: UtilitiesTipiRuoloRepository().list_emittenti_usage(
                        utr_ef, search=t, limit=200)[0],
                    chiave="emittente_id",
                )
                _uom = {"attivo": None, "order_by": "codice", "order_dir": "asc", "limit": 200, "offset": 0}
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "catalogo.uom_tipi", uom_tipo,
                    {"codice": "riccodut", "descrizione": "ricdescut"},
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
                    {"codice": ef_codice, "ragione_sociale_completa": ef_ragione,
                     "id_fiscale_univoco_cf_piva": ef_id_fiscale},
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
                raise Annulla
        except Annulla:
            pass

    # Scopo: la lista delle edizioni di workflow (2026-10-31) trova un'edizione
    #        da ogni colonna accesa. Si legge un'edizione che c'e' (i preset di
    #        sistema esistono per costruzione): costruirne una vorrebbe le fn
    #        del ciclo di vita, e la ricerca non ha bisogno di una riga nuova.
    def test_definizioni_workflow_trova_ogni_colonna_accesa(self):
        from apps.pratiche.db.definizioni_repository import DefinizioniRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute(
                    "SELECT wd.id, tp.descrizione, wd.descrizione"
                    "  FROM pratiche.workflow_definizioni wd"
                    "  JOIN pratiche.tipi_prestazione tp ON tp.id = wd.tipo_prestazione_id"
                    " ORDER BY wd.id LIMIT 1"
                )
                riga = cur.fetchone()
                self.assertIsNotNone(riga, "nessuna edizione di workflow su questo DB")
                definizione_id, tipo, descrizione = riga
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "pratiche.definizioni_workflow", definizione_id,
                    {"tipo_prestazione_descrizione": tipo, "descrizione": descrizione},
                    lambda t: DefinizioniRepository().list_definizioni(search=t, limit=200, offset=0)[0],
                )
                raise Annulla
        except Annulla:
            pass

    # Scopo: la lista delle impostazioni (2026-10-31) trova un parametro da ogni
    #        colonna accesa. Si legge un parametro che c'e' (il seed ne ha
    #        decine): la funzione restituisce l'intero catalogo per chiunque.
    def test_impostazioni_trova_ogni_colonna_accesa(self):
        from apps.core.db.parameter_repository import ParameterRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute(
                    "SELECT code, description FROM config.parameters"
                    " WHERE description IS NOT NULL ORDER BY id LIMIT 1"
                )
                code, description = cur.fetchone()
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "config.parametri_impostazioni", code,
                    {"code": code, "description": description},
                    lambda t: ParameterRepository().list_for_user(
                        _ID_FINTO_UTENTE, None, None, None, search=t, limit=200, offset=0,
                    )[0],
                    chiave="code",
                )
                raise Annulla
        except Annulla:
            pass

    # Scopo: la ricerca universale cerca dove il catalogo dice (test 9). Il
    #        soggetto e' un RE: nessuna entita' d'esistenza, si vede se esiste
    #        (come nel pgTAP `script/test-search-universale-campi-ricerca-v1`).
    #        ⚠️ Si chiede se QUEL soggetto-ruolo c'e', non quante righe tornano.
    def test_ricerca_soggetti_cerca_dove_il_catalogo_dice(self):
        from apps.core.db.search_repository import SearchRepository

        lista = "anagrafiche.ricerca_soggetti"
        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute(
                    "SELECT dbops.fn_pgtap_crea_soggetto_ruolo("
                    "  dbops.fn_pgtap_crea_soggetto_pg('ZQRICUNIV ricerca universale BE'),"
                    "  'RE'::character varying)"
                )
                sr_id = cur.fetchone()[0]
                cur.execute(
                    "SELECT s.codice, s.ragione_sociale_completa, s.id_fiscale_univoco_cf_piva,"
                    "       sr.tipo_ruolo_id"
                    "  FROM anagrafiche.soggetti_ruoli sr"
                    "  JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id"
                    " WHERE sr.id = %s",
                    [sr_id],
                )
                codice, ragione_sociale, cf, tipo_ruolo_id = cur.fetchone()

                def cerca(termine):
                    return SearchRepository().search_soggetti(
                        search_term=termine, tipo_ruolo_id=tipo_ruolo_id, limit=200,
                    )[0]

                def trova(termine) -> bool:
                    return sr_id in {r["soggetto_ruolo_id"] for r in cerca(termine)}

                verifica_ricerca_colonna_per_colonna(
                    self, cur, lista, sr_id,
                    {"soggetto_codice": codice, "ragione_sociale_completa": ragione_sociale,
                     "id_fiscale_univoco": cf},
                    cerca, chiave="soggetto_ruolo_id",
                )

                def spegni(*campi: str) -> None:
                    cur.execute(
                        "UPDATE ui.lista_colonna lc SET ricercabile_full = false"
                        "  FROM ui.lista_definizione ld"
                        " WHERE ld.id = lc.lista_id AND ld.codice = %s"
                        "   AND lc.campo_sorgente = ANY(%s)",
                        [lista, list(campi)],
                    )
                    self.assertEqual(cur.rowcount, len(campi))

                spegni("id_fiscale_univoco")
                self.assertFalse(trova(cf), "CF spento a catalogo: la funzione lo cerca ancora")
                self.assertTrue(trova(ragione_sociale))

                spegni("soggetto_codice", "ragione_sociale_completa")
                self.assertFalse(trova(ragione_sociale), "nessuna colonna accesa: deve non trovare niente")
                raise Annulla
        except Annulla:
            pass

    # Scopo: le due liste di note (2026-10-31, D-2), gemelle: una nota di un
    #        preventivo, una di un articolo e una di un componente, col testo
    #        che sta solo li', si trovano dalla loro lista con la ricerca del BB
    #        comune (`pagina_note`). ⭐ Il componente e' la SECONDA query di
    #        `catalogo.note` (l'altra partizione): la ricerca e' la stessa, la
    #        tabella no, e va eseguita anche lei. Dal 2026-11-11 le note di
    #        catalogo passano dal BB `PartitionedNoteRepository`, come vendita.
    def test_note_trovano_ogni_colonna_accesa(self):
        from apps.catalogo.db.note_repositories import (
            NOTE_REPO_ARTICOLO,
            NOTE_REPO_ARTICOLO_COMPONENTE,
        )
        from apps.vendite.db.note_repositories import NOTE_REPO_PREVENTIVO

        try:
            with transaction.atomic(), connection.cursor() as cur:
                cur.execute("SELECT preventivo_id FROM dbops.fn_pgtap_crea_preventivo('ricerca note')")
                preventivo_id = cur.fetchone()[0]
                apri_contesto_operatore(cur)
                cur.execute("SELECT dbops.fn_pgtap_crea_articolo('RICNOTEART')")
                articolo_id = cur.fetchone()[0]
                cur.execute("SELECT id FROM config.note_stili WHERE attivo ORDER BY id LIMIT 1")
                stile = cur.fetchone()[0]
                nota = {"anchor_tipo": "DOCUMENTO", "posizione": "HEADER", "id_stile": stile}
                nota_ven = NOTE_REPO_PREVENTIVO.create(preventivo_id, {**nota, "testo": "Nota ricnotaven"})
                nota_cat = NOTE_REPO_ARTICOLO.create(articolo_id, {**nota, "testo": "Nota ricnotacat"})
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "vendite.note", nota_ven, {"testo": "ricnotaven"},
                    lambda t: NOTE_REPO_PREVENTIVO.list(preventivo_id, search=t, limit=200)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "catalogo.note", nota_cat, {"testo": "ricnotacat"},
                    lambda t: NOTE_REPO_ARTICOLO.list(articolo_id, search=t, limit=200)[0],
                )
                # Il componente: un kit costruito, con l'articolo sopra dentro.
                cur.execute(
                    "SELECT dbops.fn_pgtap_crea_articolo('RICNOTEKIT', false, p_is_composito => TRUE)"
                )
                kit_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)"
                    " VALUES (%s, %s, 1, '2020-01-01') RETURNING id",
                    [kit_id, articolo_id],
                )
                componente_id = cur.fetchone()[0]
                nota_comp = NOTE_REPO_ARTICOLO_COMPONENTE.create(
                    componente_id, {**nota, "testo": "Nota ricnotacomp"},
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "catalogo.note", nota_comp, {"testo": "ricnotacomp"},
                    lambda t: NOTE_REPO_ARTICOLO_COMPONENTE.list(componente_id, search=t, limit=200)[0],
                )
                raise Annulla
        except Annulla:
            pass

    # Scopo: la lista delle UoM di un articolo (`catalogo.articolo_uom`,
    #        2026-10-31) trova la UoM da ogni colonna accesa, dalla query del
    #        REPOSITORY (`list_uom_operative_pagina`). Il test 1 la prova sulla
    #        vista del catalogo; la pagina pero' proietta colonne sue
    #        (`UOM_OPERATIVA_DETAIL_COLUMNS`), e va eseguita. L'articolo e'
    #        costruito: la sua UoM base la semina il trigger della nascita.
    def test_uom_operative_trovano_ogni_colonna_accesa(self):
        from apps.catalogo.db.catalogo_uom_repository import CatalogoUomRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT dbops.fn_pgtap_crea_articolo('RICUOMART')")
                articolo_id = cur.fetchone()[0]
                cur.execute(
                    "SELECT id, uom_codice, uom_descrizione"
                    "  FROM catalogo.vw_articoli_uom_operativa_dettaglio"
                    " WHERE articolo_id = %s AND is_base",
                    [articolo_id],
                )
                uom_id, codice, descrizione = cur.fetchone()
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "catalogo.articolo_uom", uom_id,
                    {"uom_codice": codice, "uom_descrizione": descrizione},
                    lambda t: CatalogoUomRepository().list_uom_operative_pagina(
                        articolo_id, search=t, limit=200, offset=0,
                    )[0],
                )
                raise Annulla
        except Annulla:
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
                raise Annulla
        except Annulla:
            pass

    def test_la_configurazione_rifiuta_un_contesto_di_un_altro_utente(self):
        from django.contrib.auth import get_user_model

        from apps.core.services.service_errors import ServiceError
        from apps.ui.services.ui_service import E_UI_CHIAMATA_NON_VALIDA, UiService

        try:
            with transaction.atomic(), connection.cursor() as cur:
                uid = apri_contesto_operatore(cur)
                utente = get_user_model().objects.get(pk=uid)
                # Il contesto di sessione nomina un ALTRO utente: l'id non deve
                # esistere, basta che sia diverso (la guardia confronta, non cerca).
                cur.execute("SET LOCAL app.current_user_id = %s", [str(uid + 1_000_000)])
                with self.assertRaises(ServiceError) as ctx:
                    UiService().get_lista_config_per_video(utente, "vendite.preventivi")
                self.assertEqual(ctx.exception.code, E_UI_CHIAMATA_NON_VALIDA)
                # E vuoto, come fuori da una richiesta.
                cur.execute("SET LOCAL app.current_user_id = ''")
                with self.assertRaises(ServiceError) as ctx:
                    UiService().get_lista_config_per_video(utente, "vendite.preventivi")
                self.assertEqual(ctx.exception.code, E_UI_CHIAMATA_NON_VALIDA)
                raise Annulla
        except Annulla:
            pass

    def test_la_soglia_e_della_lista_e_la_leggono_i_due_lettori(self):
        from django.contrib.auth import get_user_model
        from django.db import DatabaseError

        from apps.ui.services.ui_service import UiService

        ricerca = dict(_RICERCHE)["vendite.preventivi"]()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                uid = apri_contesto_operatore(cur)
                utente = get_user_model().objects.get(pk=uid)
                for soglia, filtra in ((1, True), (3, False)):
                    with self.subTest(soglia=soglia):
                        cur.execute(
                            "UPDATE ui.lista_definizione SET ricerca_min_caratteri = %s "
                            " WHERE codice = 'vendite.preventivi'",
                            [soglia],
                        )
                        self.assertEqual(cur.rowcount, 1)
                        self.assertEqual(soglia_ricerca("vendite.preventivi"), soglia)
                        conditions: list[str] = []
                        add_ricerca_full_condition(conditions, [], "K", ricerca)
                        self.assertEqual(bool(conditions), filtra, conditions)
                        # Il secondo lettore: la schermata riceve lo stesso numero,
                        # come intero (il frontend lo confronta con una lunghezza).
                        config = UiService().get_lista_config_per_video(utente, "vendite.preventivi")
                        self.assertEqual(config["ricerca_min_caratteri"], soglia)
                        self.assertIsInstance(config["ricerca_min_caratteri"], int)
                # Lista inesistente: lo stesso errore delle altre letture del catalogo.
                with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                    soglia_ricerca("x.lista_che_non_esiste")
                self.assertIn("E_UI_LISTA_NON_TROVATA", str(ctx.exception))
                raise Annulla
        except Annulla:
            pass

    def test_il_resolver_soggetti_usa_la_soglia_della_lista(self):
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute(
                    "UPDATE ui.lista_definizione SET ricerca_min_caratteri = 5 "
                    " WHERE codice = 'anagrafiche.soggetti'"
                )
                self.assertEqual(cur.rowcount, 1)
                # `CL` e' un tipo ruolo del seed (contratto, non fotografia).
                config = SoggettiRepository().get_config_resolver("CL")
                self.assertEqual(config["min_search_length"], 5)
                # ⚠️ Presidio del cast (`varchar[]`): la matrice delle nature del
                #    ruolo filtra i tipi di dettaglio, e col vecchio `bigint[]`
                #    questa chiamata falliva prima di arrivare qui.
                self.assertTrue(config["tipi_soggetto_dettaglio"])
                # Lo stesso ruolo SENZA matrice (spenta nel test, caso
                # costruito): «tutte le nature» e' il dominio dell'enum, letto
                # come app — non un elenco nel codice che invecchia.
                cur.execute(
                    "UPDATE config.tipi_ruoli_nature_ammesse trna SET attivo = false "
                    "  FROM config.tipi_ruoli tr "
                    " WHERE tr.id = trna.tipo_ruolo_id "
                    "   AND tr.codice_interno = 'CL'"
                )
                self.assertGreater(cur.rowcount, 0)
                cur.execute("SELECT enum_range(NULL::config.natura_soggetto_enum)::text[]")
                dominio = list(cur.fetchone()[0])
                config = SoggettiRepository().get_config_resolver("CL")
                self.assertEqual(config["nature_ammesse"], dominio)
                raise Annulla
        except Annulla:
            pass
