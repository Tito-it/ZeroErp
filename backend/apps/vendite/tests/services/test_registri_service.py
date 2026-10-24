# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidi del CRUD dei registri di numerazione — §10.4 del brief
#        brief-be-fe-crud-registri-di-numerazione.
# ------------------------------------------------------------

"""
Indice test eseguiti:

1)  RegistriVincoliTests.test_terna_occupata_dice_che_puo_essere_spento
1b) RegistriVincoliTests.test_terna_non_dichiara_un_campo
2)  RegistriVincoliTests.test_create_su_terna_libera_passa            (gemello positivo)
3)  RegistriVincoliTests.test_coppia_prefisso_suffisso_dice_che_puo_essere_spento
3b) RegistriVincoliTests.test_coppia_dichiara_il_campo_prefisso
3c) RegistriVincoliTests.test_coppia_si_prende_anche_in_MODIFICA
4)  RegistriVincoliTests.test_update_senza_conflitto_passa            (gemello positivo)
5)  RegistriVincoliTests.test_check_famiglia_tradotto
5b) RegistriVincoliTests.test_codice_duplicato_dichiara_il_campo
6)  RegistriScopeTests.test_scope_vuoto_non_vede_niente
6b) RegistriScopeTests.test_scope_none_non_filtra
6c) RegistriScopeTests.test_scope_lista_filtra_su_soggetto_ruolo
6d) RegistriScopeTests.test_get_fuori_scope_e_404
7)  RegistriFormaTests.test_update_forma_su_registro_che_ha_numerato_propaga_il_codice
8)  RegistriFormaTests.test_i_tre_campi_di_forma_sono_in_update      (gemello positivo)
8b) RegistriFormaTests.test_serie_default_non_e_scrivibile
8b-bis) RegistriFormaTests.test_serie_default_in_modifica_e_400
8b-ter) RegistriFormaTests.test_chiave_estranea_in_creazione_e_400
9)  RegistriPayloadTests.test_limiti_azzerati_su_famiglia_non_fattura
9b) RegistriPayloadTests.test_limiti_non_toccati_quando_la_famiglia_non_e_nel_payload
9c) RegistriPayloadTests.test_stringa_vuota_diventa_none
10) RegistriProgressiviTests.test_progressivi_letti_solo_dopo_lo_scope
10b) RegistriProgressiviTests.test_nessun_metodo_di_scrittura_sui_progressivi

--- Aggiunti dalla revisione critica del 2026-09-01 ---
11)  RegistriRevisioneTests.test_create_accetta_id_numerico_dal_corpo_json   (era un 500)
11b) RegistriRevisioneTests.test_attivo_mancante_non_diventa_accendi
12)  RegistriRevisioneTests.test_politica_data_neutralizzata_fuori_fattura
12b) RegistriRevisioneTests.test_politica_data_intatta_su_fattura
13)  RegistriRevisioneTests.test_set_attivo_legge_una_volta_sola
13b) RegistriRevisioneTests.test_set_attivo_fuori_scope_e_404

⚠️ Cosa questi test NON provano, ed e' voluto (§10.4): che i sei guard di
disattivazione e il guard sulla forma siano MONTATI. Quelli sono trigger, e si
presidiano in pgTAP — `test-registro-forma-numero-immutabile-v1.sql` (8/8) e il
test 6 di quello della disattivabile, che e' proprio cio' che ha trovato lo
scarto da tre figlie a sei. Ricontarli qui significherebbe metterli in un posto
dove nessuno li guarda.

⭐ I NOMI DEI VINCOLI sono stati verificati sul database vivo il 2026-09-01
(`pg_constraint` + `pg_indexes` su `vendite.registri_fatturazione`): tutti e
dodici quelli mappati esistono. E' la verifica che un mock non puo' fare —
`vincolo_violato` cerca il nome nel testo dell'eccezione, quindi un nome
sbagliato non solleverebbe nulla: cadrebbe nel fallback generico, che e' un
messaggio plausibile su un difetto invisibile (`feedback_rinomina_db_binding_mockato`).
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import IntegrityError

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.famiglie_repository import FamiglieDocumentoRepository
from apps.vendite.db.registri_repository import (
    _CAMPI_CREATE,
    _CAMPI_UPDATE,
    RegistriRepository,
)
from apps.vendite.services.registri_service import RegistriService
from apps.vendite.tests._helpers.mock_cursor import mock_cursor as _mock_cursor


# Scopo: un IntegrityError che *nomina* un vincolo, come lo consegna psycopg.
# ⚠️ `vincolo_violato` legge il TESTO dell'eccezione: il messaggio deve
#    contenere il nome, o nessuna voce della mappa fa match.
def _integrity(nome_vincolo: str) -> IntegrityError:
    return IntegrityError(
        f'duplicate key value violates unique constraint "{nome_vincolo}"\n'
        f'DETAIL:  Key (...)=(...) already exists.',
    )


# Scopo: un registro finto come lo restituisce il repository, per le riletture.
def _registro(**over):
    base = {
        "id": 7, "codice": "DDT-01", "descrizione": "DDT",
        "famiglia_documento": "DDT_VENDITA", "emittente_soggetto_ruolo_id": 99,
        "prefisso": "DDT", "suffisso": None, "lunghezza_numero": 7,
        "serie_default": None, "attivo": True,
        "rimozione_blocco_reason": None, "forma_blocco_reason": None,
    }
    base.update(over)
    return base


class RegistriVincoliTests(TestCase):
    """§10.4 presidi 1-5: i due `23505` parlanti, coi loro gemelli positivi."""

    def setUp(self):
        self.svc = RegistriService()

    # Scopo: (1) la terna occupata NON dice «esiste gia'» e basta — dice che la
    #        riga che blocca puo' essere SPENTA, cioe' invisibile nella lista.
    #        E' il difetto del §0: senza quella frase l'operatore cerca una riga
    #        che non vede.
    @patch.object(RegistriRepository, "create_registro")
    def test_terna_occupata_dice_che_puo_essere_spento(self, mock_create):
        mock_create.side_effect = _integrity(
            "uq_registri_fatturazione_famiglia_emittente_utility")
        with self.assertRaises(ServiceError) as ctx:
            self.svc.create_registro(99, {"codice": "X", "descrizione": "Y"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_DUPLICATO")
        self.assertIn("disattivato", ctx.exception.message)
        self.assertIn("riattiva", ctx.exception.message)

    # Scopo: (1b) la terna NON dichiara un campo. E' composta su tre colonne che
    #        l'operatore sceglie tutte: accenderne una manderebbe a correggere
    #        un campo che non e' piu' sbagliato degli altri due.
    @patch.object(RegistriRepository, "create_registro")
    def test_terna_non_dichiara_un_campo(self, mock_create):
        mock_create.side_effect = _integrity(
            "uq_registri_fatturazione_famiglia_emittente_utility")
        with self.assertRaises(ServiceError) as ctx:
            self.svc.create_registro(99, {"codice": "X", "descrizione": "Y"})
        self.assertIsNone((ctx.exception.context or {}).get("field"))

    # Scopo: (2) IL GEMELLO POSITIVO. Senza, il test non distingue «respinge il
    #        caso giusto» da «respinge tutto».
    @patch.object(RegistriRepository, "list_progressivi", return_value=[])
    @patch.object(RegistriRepository, "get_registro", return_value=_registro())
    @patch.object(RegistriRepository, "create_registro", return_value=7)
    def test_create_su_terna_libera_passa(self, mock_create, _get, _prog):
        out = self.svc.create_registro(99, {"codice": "DDT-01", "descrizione": "DDT"})
        self.assertEqual(out["id"], 7)
        mock_create.assert_called_once()

    # Scopo: (3) il SECONDO unique parziale, sull'altro asse — e anche lui non
    #        filtra su `attivo`.
    @patch.object(RegistriRepository, "create_registro")
    def test_coppia_prefisso_suffisso_dice_che_puo_essere_spento(self, mock_create):
        mock_create.side_effect = _integrity(
            "uq_registri_fatturazione_prefisso_suffisso")
        with self.assertRaises(ServiceError) as ctx:
            self.svc.create_registro(99, {"codice": "X", "descrizione": "Y",
                                          "prefisso": "DDT"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_DUPLICATO")
        self.assertIn("disattivato", ctx.exception.message)
        self.assertIn("forma", ctx.exception.message)

    # Scopo: (3b) QUI il campo si dichiara, e la differenza con la terna e'
    #        reale: le colonne in gioco sono due, l'emittente non e' un campo
    #        del form (lo da' il tab), e la coppia e' cio' che l'operatore ha
    #        appena scritto.
    @patch.object(RegistriRepository, "create_registro")
    def test_coppia_dichiara_il_campo_prefisso(self, mock_create):
        mock_create.side_effect = _integrity(
            "uq_registri_fatturazione_prefisso_suffisso")
        with self.assertRaises(ServiceError) as ctx:
            self.svc.create_registro(99, {"codice": "X", "descrizione": "Y"})
        self.assertEqual((ctx.exception.context or {}).get("field"), "prefisso")

    # Scopo: (3c) ⛔ SI PRENDE ANCHE IN MODIFICA, non solo in creazione — ed e'
    #        il punto che un test scritto sulla sola create mancherebbe. E' la
    #        ragione per cui la lista deve mostrare anche gli spenti su TUTTA
    #        la maschera, non solo nel form di inserimento (§2-bis).
    @patch.object(RegistriRepository, "update_registro")
    def test_coppia_si_prende_anche_in_MODIFICA(self, mock_update):
        mock_update.side_effect = _integrity(
            "uq_registri_fatturazione_prefisso_suffisso")
        with self.assertRaises(ServiceError) as ctx:
            self.svc.update_registro(7, [99], {"prefisso": "DDT"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_DUPLICATO")
        self.assertIn("disattivato", ctx.exception.message)

    # Scopo: (4) gemello positivo della modifica.
    @patch.object(RegistriRepository, "list_progressivi", return_value=[])
    @patch.object(RegistriRepository, "get_registro", return_value=_registro())
    @patch.object(RegistriRepository, "update_registro", return_value=1)
    def test_update_senza_conflitto_passa(self, mock_update, _get, _prog):
        out = self.svc.update_registro(7, [99], {"descrizione": "Nuova"})
        self.assertEqual(out["id"], 7)
        mock_update.assert_called_once()

    # Scopo: (5) il CHECK della famiglia diventa una frase che nomina la regola,
    #        non il fallback generico.
    @patch.object(RegistriRepository, "create_registro")
    def test_check_famiglia_tradotto(self, mock_create):
        mock_create.side_effect = _integrity(
            "chk_registri_fatturazione_famiglia_regole_fattura")
        with self.assertRaises(ServiceError) as ctx:
            self.svc.create_registro(99, {"codice": "X", "descrizione": "Y"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertIn("FATTURA", ctx.exception.message)

    # Scopo: (5b) il codice duplicato SI', un campo ce l'ha — ed e' il caso in
    #        cui accenderlo aiuta davvero.
    @patch.object(RegistriRepository, "create_registro")
    def test_codice_duplicato_dichiara_il_campo(self, mock_create):
        mock_create.side_effect = _integrity("uq_registri_fatturazione_codice")
        with self.assertRaises(ServiceError) as ctx:
            self.svc.create_registro(99, {"codice": "X", "descrizione": "Y"})
        self.assertEqual((ctx.exception.context or {}).get("field"), "codice")


class RegistriScopeTests(TestCase):
    """§10.4 presidio 6: senza RLS, questo e' l'UNICO presidio di perimetro."""

    # Scopo: (6) `[]` = nessun accesso -> zero righe, e NON «tutte».
    # ⛔ E' il verso che, sbagliato, apre l'intera tabella a chi non ha accesso
    #    a niente — senza che niente fallisca.
    @patch("apps.vendite.db.registri_repository.connection.cursor")
    def test_scope_vuoto_non_vede_niente(self, mock_factory):
        righe, tot = RegistriRepository().list_registri([])
        self.assertEqual((righe, tot), ([], 0))
        mock_factory.assert_not_called()

    # Scopo: (6b) `None` = nessuna restrizione -> la query gira, col predicato
    #        di scope neutralizzato. L'altro verso dello stesso errore: trattare
    #        `None` come vuoto spegnerebbe la pagina a chi puo' vedere tutto.
    @patch("apps.vendite.db.registri_repository.connection.cursor")
    def test_scope_none_non_filtra(self, mock_factory):
        mock_factory.return_value = _mock_cursor(fetchall=[], description=[])
        RegistriRepository().list_registri(None)
        sql, params = mock_factory.return_value.execute.call_args[0]
        self.assertIn("bigint[] IS NULL OR r.emittente_soggetto_ruolo_id = ANY", sql)
        self.assertIsNone(params[0])

    # Scopo: (6c) il filtro va sulla colonna SOGGETTO-RUOLO, non sulla PK
    #        dell'emittente fiscale (`feedback_emittente_pk_vs_soggetto_ruolo`).
    @patch("apps.vendite.db.registri_repository.connection.cursor")
    def test_scope_lista_filtra_su_soggetto_ruolo(self, mock_factory):
        mock_factory.return_value = _mock_cursor(fetchall=[], description=[])
        RegistriRepository().list_registri([11, 22])
        sql, params = mock_factory.return_value.execute.call_args[0]
        self.assertIn("r.emittente_soggetto_ruolo_id = ANY", sql)
        self.assertEqual(params[0], [11, 22])

    # Scopo: (6d) un id fuori perimetro e' un 404, non una riga altrui.
    @patch.object(RegistriRepository, "get_registro", return_value=None)
    def test_get_fuori_scope_e_404(self, _get):
        with self.assertRaises(ServiceError) as ctx:
            RegistriService().get_registro(7, [11])
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")


class RegistriFormaTests(TestCase):
    """§10.4 presidi 7-8: la forma del numero sotto un contatore vivo."""

    # Scopo: (7) il rifiuto del guard DB arriva al client come il SUO codice,
    #        non come un 500. ⛔ Il divieto non si ricalcola in Python: il
    #        criterio vive dove sta il rifiuto, e qui si traduce e basta.
    @patch.object(RegistriRepository, "update_registro")
    def test_update_forma_su_registro_che_ha_numerato_propaga_il_codice(self, mock_upd):
        mock_upd.side_effect = IntegrityError(
            "Registro ZZ: la forma del numero non si puo' piu' cambiare "
            "E_REGISTRO_FORMA_NUMERO_IMMUTABILE",
        )
        with self.assertRaises(ServiceError):
            RegistriService().update_registro(7, [99], {"prefisso": "NUOVO"})

    # Scopo: (8) IL GEMELLO POSITIVO DELLA DECISIONE DEL 2026-09-01 — i tre
    #        campi di forma SONO scrivibili. Il brief li teneva fuori come
    #        ripiego «finche' il guard non esiste»; il guard esiste, e tenerli
    #        fuori adesso sarebbe un divieto applicativo accanto a uno di
    #        database, cioe' il secondo elenco parallelo.
    def test_i_tre_campi_di_forma_sono_in_update(self):
        for campo in ("prefisso", "suffisso", "lunghezza_numero"):
            self.assertIn(campo, _CAMPI_UPDATE)

    # Scopo: (8b) `serie_default` si CREA ma non si MODIFICA: il guard non la
    #        copre (entra nella chiave del contatore, e il mirror CSV la
    #        riscrive a ogni migrate), quindi sarebbe l'unico campo editabile
    #        senza presidio.
    def test_serie_default_non_e_scrivibile(self):
        self.assertIn("serie_default", _CAMPI_CREATE)
        self.assertNotIn("serie_default", _CAMPI_UPDATE)
        # E le colonne che NESSUNO dei due verbi tocca.
        for campo in ("uid", "id", "emittente_soggetto_ruolo_id"):
            self.assertNotIn(campo, _CAMPI_CREATE)
            self.assertNotIn(campo, _CAMPI_UPDATE)

    # Scopo: (8b-bis) ⛔ ...e spedita in MODIFICA e' un 400, prima del
    #        database (2026-09-26). Fino a quel giorno il repository la
    #        scartava in silenzio: la PATCH rispondeva 200 senza aver scritto
    #        il campo.
    @patch.object(RegistriRepository, "update_registro")
    def test_serie_default_in_modifica_e_400(self, mock_update):
        with self.assertRaises(ServiceError) as ctx:
            RegistriService().update_registro(7, [99], {"serie_default": "B"})
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(ctx.exception.context.get("unknown_keys"), ["serie_default"])
        mock_update.assert_not_called()

    # Scopo: (8b-ter) stessa regola in creazione, su una chiave che nessun
    #        verbo scrive.
    @patch.object(RegistriRepository, "create_registro")
    def test_chiave_estranea_in_creazione_e_400(self, mock_create):
        with self.assertRaises(ServiceError) as ctx:
            RegistriService().create_registro(
                99, {"codice": "X", "descrizione": "Y", "attivo": False},
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(ctx.exception.context.get("unknown_keys"), ["attivo"])
        mock_create.assert_not_called()

    # Scopo: (8c) `reset_policy` si SCEGLIE alla nascita e non si cambia piu'.
    # ⭐ Il verso positivo conta quanto il negativo, ed e' nuovo dal 2026-09-08:
    #    prima la politica era fuori da entrambi i verbi, quindi accesa nel
    #    database (il CHECK ammette ANNUALE e NESSUNA dal 20260901-06, e
    #    `fn_get_next_progressivo` ramifica) e irraggiungibile dall'applicazione.
    # ⛔ E il verso negativo NON e' prudenza: la politica e' un asse della chiave
    #    del contatore. Cambiarla su un registro che ha gia' consegnato numeri
    #    sposta il secchio, il progressivo riparte da 1 e sbatte contro i numeri
    #    gia' scritti. ⚠️ Nessun trigger lo rifiuta: `_CAMPI_UPDATE` e' l'unico
    #    presidio, ed e' la ragione per cui questa riga esiste.
    def test_reset_policy_si_crea_ma_non_si_modifica(self):
        self.assertIn("reset_policy", _CAMPI_CREATE)
        self.assertNotIn("reset_policy", _CAMPI_UPDATE)

    # Scopo: (8d) «vuoto» su `reset_policy` vale «non l'ho scelto», e decide il
    #        default della colonna.
    # ⛔ Senza, `empty_to_none` manderebbe all'INSERT un NULL esplicito su una
    #    colonna NOT NULL: l'operatore leggerebbe «campo obbligatorio» per una
    #    scelta che il modello NON gli chiede di fare.
    # ⚠️ Si asserisce che la chiave SIA STATA TOLTA, non che valga 'ANNUALE':
    #    il default vive nella colonna, e ripeterlo qui creerebbe la terza sede
    #    che questo test esiste per non avere.
    def test_reset_policy_vuota_non_arriva_come_null(self):
        for vuoto in ("", None):
            with self.subTest(vuoto=vuoto):
                dati = RegistriService()._normalizza({
                    "codice": "X", "reset_policy": vuoto,
                })
                self.assertNotIn("reset_policy", dati)

    # Scopo: il verso positivo — una politica scelta passa intatta.
    def test_reset_policy_scelta_passa_intatta(self):
        dati = RegistriService()._normalizza({"reset_policy": "NESSUNA"})
        self.assertEqual(dati["reset_policy"], "NESSUNA")


class RegistriPayloadTests(TestCase):
    """La normalizzazione del payload — §FE-4 vista dal backend."""

    # Scopo: (9) i campi del limite si azzerano su una famiglia non fiscale.
    # ⛔ Nasconderli nel form non basta: un `defaultForm()` li porta comunque, e
    #    sulla famiglia sbagliata il CHECK li rifiuta con un messaggio che parla
    #    di un campo che l'operatore non ha nemmeno visto.
    def test_limiti_azzerati_su_famiglia_non_fattura(self):
        dati = RegistriService()._normalizza({
            "famiglia_documento": "DDT_VENDITA",
            "limite_emissione_giorni": 15,
            "limite_emissione_giorno_mese": 20,
        })
        self.assertIsNone(dati["limite_emissione_giorni"])
        self.assertIsNone(dati["limite_emissione_giorno_mese"])

    # Scopo: (9b) e NON si azzerano quando la famiglia non e' nel payload — che
    #        e' il caso di ogni update, dove la famiglia non e' modificabile.
    #        Dedurre «non e' FATTURA» dalla sua assenza cancellerebbe i limiti
    #        di un registro fiscale a ogni salvataggio.
    def test_limiti_non_toccati_quando_la_famiglia_non_e_nel_payload(self):
        dati = RegistriService()._normalizza({"limite_emissione_giorni": 15})
        self.assertEqual(dati["limite_emissione_giorni"], 15)

    # Scopo: (9c) stringa vuota -> NULL. Su prefisso/suffisso non e' cosmetica:
    #        e' il predicato dell'UNIQUE parziale.
    def test_stringa_vuota_diventa_none(self):
        dati = RegistriService()._normalizza({"prefisso": "", "suffisso": "  "})
        self.assertIsNone(dati["prefisso"])
        self.assertIsNone(dati["suffisso"])


class RegistriProgressiviTests(TestCase):
    """§BE-4: i contatori si leggono, non si scrivono."""

    # Scopo: (10) i progressivi si leggono DOPO che lo scope ha risolto il
    #        registro. Leggerli per id prima del controllo risponderebbe coi
    #        contatori di un sezionale altrui dentro un 404.
    @patch.object(RegistriRepository, "list_progressivi")
    @patch.object(RegistriRepository, "get_registro", return_value=None)
    def test_progressivi_letti_solo_dopo_lo_scope(self, _get, mock_prog):
        with self.assertRaises(ServiceError):
            RegistriService().get_registro(7, [11])
        mock_prog.assert_not_called()

    # Scopo: (10b) ⛔ non esiste NESSUN metodo di scrittura sui progressivi, e
    #        non deve nascerne uno «per l'amministratore»: cambiare
    #        `last_numero` a mano significa riassegnare un numero gia' uscito.
    #        Il presidio e' sulla SUPERFICIE del repository, non su una chiamata.
    def test_nessun_metodo_di_scrittura_sui_progressivi(self):
        metodi = [m for m in dir(RegistriRepository) if "progressiv" in m]
        self.assertEqual(metodi, ["list_progressivi"])


class RegistriRepositoryQueryTests(TestCase):
    """La query di lista porta i DUE verbi, con due nomi diversi."""

    # Scopo: le due LATERAL ci sono entrambe, e le colonne non si confondono.
    # ⛔ Riusare `rimozione_blocco_*` per la domanda sulla forma mostrerebbe la
    #    frase sbagliata senza che niente fallisca: su un registro che ha
    #    numerato sono spenti entrambi, ma per motivi diversi.
    @patch("apps.vendite.db.registri_repository.connection.cursor")
    def test_la_lista_legge_le_due_check(self, mock_factory):
        mock_factory.return_value = _mock_cursor(fetchall=[], description=[])
        RegistriRepository().list_registri(None)
        sql = mock_factory.return_value.execute.call_args[0][0]
        self.assertIn("script.fn_check_registro_disattivabile", sql)
        self.assertIn("script.fn_check_registro_forma_modificabile", sql)
        for col in ("rimozione_blocco_reason_key", "forma_blocco_reason_key",
                    "rimozione_blocco_dettaglio", "forma_blocco_dettaglio"):
            self.assertIn(col, sql)
        # ⚠️ LEFT JOIN LATERAL e non CROSS JOIN: la check risponde `[]` quando
        #    l'azione e' ammessa, e un CROSS JOIN farebbe sparire dalla lista
        #    proprio i registri senza problemi.
        self.assertNotIn("CROSS JOIN LATERAL", sql)
        self.assertEqual(sql.count("LEFT JOIN LATERAL"), 2)

    # Scopo: `order_by` fuori whitelist e' un 400 (`order_by_invalid`) e non
    #        arriva all'SQL: la colonna viene dal client e un ORDER BY non e'
    #        parametrizzabile. Dal 2026-10-20 non ripiega piu' sul default.
    @patch("apps.vendite.db.registri_repository.connection.cursor")
    def test_order_by_fuori_whitelist_e_rifiutato(self, mock_factory):
        mock_factory.return_value = _mock_cursor(fetchall=[], description=[])
        with self.assertRaisesRegex(ValueError, "order_by_invalid"):
            RegistriRepository().list_registri(None, order_by="; DROP TABLE x")
        mock_factory.return_value.execute.assert_not_called()


# Scopo: un `MagicMock` non deve passare per una lista di id — se un domani
#        `get_emittenti_sr_ids` cambiasse forma, il ramo `[] -> vuoto` va
#        comunque distinto da `None -> tutto`.
class RegistriScopeSemanticaTests(TestCase):

    def test_le_tre_forme_dello_scope_sono_distinte(self):
        repo = RegistriRepository()
        self.assertEqual(repo.list_registri([]), ([], 0))
        self.assertIsNone(repo.get_registro(1, []))
        self.assertEqual(repo.update_registro(1, [], {"codice": "X"}), 0)
        self.assertEqual(repo.set_attivo(1, [], attivo=False), 0)
        # ⚠️ Nessuna di queste ha toccato il database: e' il punto.
        self.assertIsInstance(repo, RegistriRepository)
        self.assertNotIsInstance([], MagicMock)


class RegistriRevisioneTests(TestCase):
    """I difetti trovati dalla revisione critica del 2026-09-01, e i loro presidi.

    ⭐ Ognuno di questi test esiste perche' il difetto **non falliva a vista**:
    tre su quattro producevano una risposta plausibile.
    """

    # Scopo: (11) ⛔ IL 500 SU OGNI CREAZIONE. La vista normalizzava l'id
    #        dell'emittente con `qp_int_optional`, che e' l'helper della QUERY
    #        STRING e fa `raw.strip()`: un id che arriva come NUMERO dal corpo
    #        JSON — cioe' sempre, dal frontend — gli faceva sollevare
    #        `AttributeError`. ⚠️ Un test scritto con la stringa "99" sarebbe
    #        passato: e' il motivo per cui qui il valore e' un `int`.
    def test_create_accetta_id_numerico_dal_corpo_json(self):
        from apps.core.api.payload_validators import optional_int
        self.assertEqual(optional_int({"x": 99}, "x"), 99)
        self.assertEqual(optional_int({"x": "99"}, "x"), 99)
        self.assertIsNone(optional_int({}, "x"))

    # Scopo: (11b) il verbo `attivo` non ha un default silenzioso. Un corpo
    #        vuoto e' una richiesta incompleta, non «accendilo»: il verbo ha due
    #        direzioni e una delle due e' distruttiva.
    @patch("apps.vendite.api.views_registri.PermissionResolver.get_emittenti_sr_ids",
           return_value=None)
    def test_attivo_mancante_non_diventa_accendi(self, _scope):
        from apps.vendite.api.views_registri import ApiRegistroAttivo
        richiesta = MagicMock()
        richiesta.data = {}
        with self.assertRaises(ServiceError) as ctx:
            ApiRegistroAttivo().post(richiesta, 7)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual((ctx.exception.context or {}).get("field"), "attivo")

    # Scopo: (12) `politica_data_documento` e' il TERZO campo condizionato alla
    #        famiglia, non due. Il `CHECK` verificato sul vivo dice
    #        «famiglia = FATTURA OR (limiti NULL AND politica = OGGI)».
    # ⛔ E il suo neutro e' il VALORE 'OGGI', non NULL: la colonna e' NOT NULL, e
    #    azzerarla come gli altri due la farebbe respingere da un vincolo
    #    diverso, con un messaggio che parla di un campo obbligatorio invece
    #    che della famiglia.
    # ⚠️ Il flag si MOCKA, e non e' pigrizia: dal 2026-09-02 lo legge il catalogo
    #    (`famiglie_documento.ammette_regole_fiscali`, §11.10 BE-F2 · §12.2). Lasciarlo
    #    andare al database trasformerebbe due test di contratto — che questo
    #    file dichiara di fare coi mock — in due test che senza database
    #    falliscono, e il difetto si vedrebbe in CI e non qui.
    @patch.object(FamiglieDocumentoRepository, "ammette_regole_fiscali", return_value=False)
    def test_politica_data_neutralizzata_fuori_fattura(self, _ammette):
        dati = RegistriService()._normalizza({
            "famiglia_documento": "DDT_VENDITA",
            "politica_data_documento": "FINE_MESE_COMPETENZA",
            "limite_emissione_giorni": 15,
        })
        self.assertEqual(dati["politica_data_documento"], "OGGI")
        self.assertIsNone(dati["limite_emissione_giorni"])

    # Scopo: (12b) il gemello positivo — su FATTURA la politica passa intatta.
    #        Senza, il test non distingue «normalizza il caso giusto» da
    #        «schiaccia tutto su OGGI».
    @patch.object(FamiglieDocumentoRepository, "ammette_regole_fiscali", return_value=True)
    def test_politica_data_intatta_su_fattura(self, _ammette):
        dati = RegistriService()._normalizza({
            "famiglia_documento": "FATTURA",
            "politica_data_documento": "FINE_MESE_COMPETENZA",
            "limite_emissione_giorni": 15,
        })
        self.assertEqual(dati["politica_data_documento"], "FINE_MESE_COMPETENZA")
        self.assertEqual(dati["limite_emissione_giorni"], 15)

    # Scopo: (12c) ⭐ LA PROVA CHE IL CRITERIO NON E' PIU' IL NOME. Una famiglia
    #        che non si chiama FATTURA ma che a catalogo presidia la data tiene
    #        i suoi tre campi. Col letterale `_FAMIGLIA_FISCALE = "FATTURA"`
    #        — tolto il 2026-09-02, §11.10 BE-F2 — questo test sarebbe rosso, e
    #        i campi di quella famiglia sarebbero spariti dalla maschera senza
    #        che niente fallisse.
    @patch.object(FamiglieDocumentoRepository, "ammette_regole_fiscali", return_value=True)
    def test_i_campi_fiscali_seguono_il_catalogo_non_il_nome(self, _ammette):
        dati = RegistriService()._normalizza({
            "famiglia_documento": "PARCELLA",
            "politica_data_documento": "FINE_MESE_COMPETENZA",
            "limite_emissione_giorni": 15,
        })
        self.assertEqual(dati["politica_data_documento"], "FINE_MESE_COMPETENZA")
        self.assertEqual(dati["limite_emissione_giorni"], 15)

    # Scopo: (12d) e il verso opposto — famiglia SCONOSCIUTA al catalogo: i tre
    #        campi si azzerano. ⛔ Non e' «si presume non fiscale per prudenza»:
    #        e' che a rifiutare una famiglia inesistente deve essere la FK, col
    #        suo messaggio, un attimo dopo. Ripiegare su «presidia» manderebbe
    #        al database valori che il CHECK respinge, con un errore che parla
    #        di un campo invece che della famiglia.
    @patch.object(FamiglieDocumentoRepository, "ammette_regole_fiscali", return_value=None)
    def test_famiglia_sconosciuta_azzera_i_campi_fiscali(self, _ammette):
        dati = RegistriService()._normalizza({
            "famiglia_documento": "NON_ESISTE",
            "politica_data_documento": "FINE_MESE_COMPETENZA",
            "limite_emissione_giorni": 15,
        })
        self.assertEqual(dati["politica_data_documento"], "OGGI")
        self.assertIsNone(dati["limite_emissione_giorni"])

    # Scopo: (13) `set_attivo` legge UNA volta sola. La prima stesura leggeva
    #        anche prima della scrittura per distinguere il 404, e ogni lettura
    #        fa girare le DUE check in LATERAL piu' la query dei contatori: due
    #        letture per un'informazione che la rilettura da' comunque.
    @patch.object(RegistriRepository, "list_progressivi", return_value=[])
    @patch.object(RegistriRepository, "set_attivo", return_value=1)
    @patch.object(RegistriRepository, "get_registro", return_value=_registro())
    def test_set_attivo_legge_una_volta_sola(self, mock_get, mock_set, _prog):
        RegistriService().set_attivo(7, [99], attivo=False)
        self.assertEqual(mock_get.call_count, 1)
        # ⚠️ E la scrittura viene PRIMA: la rilettura deve vedere lo stato nuovo.
        self.assertEqual(mock_set.call_count, 1)

    # Scopo: (13b) e togliendo la pre-lettura il 404 deve reggere lo stesso —
    #        e' la rilettura a produrlo. Senza questo test la semplificazione
    #        avrebbe trasformato un id fuori perimetro in un 200 silenzioso.
    @patch.object(RegistriRepository, "set_attivo", return_value=0)
    @patch.object(RegistriRepository, "get_registro", return_value=None)
    def test_set_attivo_fuori_scope_e_404(self, _get, _set):
        with self.assertRaises(ServiceError) as ctx:
            RegistriService().set_attivo(7, [11], attivo=False)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")
