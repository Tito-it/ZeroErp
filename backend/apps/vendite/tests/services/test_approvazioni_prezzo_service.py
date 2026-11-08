# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test ApprovazioniPrezzoService (workflow L3 sviluppo-listini-v5 §14.6).
# ------------------------------------------------------------

"""
Indice test:
1) crea_richiesta_approvazione: pratica creata + stato APERTA + email best-effort
2) crea_richiesta_approvazione: contesto pratica mancante -> E_APPROVAZIONE_PREZZO_NON_AMMESSA
3) approva: riga PENDING + permesso ok -> APPROVED + pratica CHIUSA + nota INTERNA
4) approva: riga non PENDING -> E_APPROVAZIONE_PREZZO_NON_AMMESSA
5) approva: senza permesso -> E_PRICING_OVERRIDE_NON_AUTORIZZATO
6) approva: superuser bypass permesso
7) rifiuta: riga PENDING -> REJECTED + nota motivazione
8) rifiuta: senza motivazione -> nota generica
9) lista_coda: ok con scope emittente
10) lista_coda: senza emittente assegnato -> E_APPROVAZIONE_PREZZO_NON_AMMESSA
11) lookup cache modulo-level: tipo_prestazione_id riusato cross-call
12) invalidate_lookup_cache forza re-query
"""

from decimal import Decimal
from unittest import TestCase
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services import approvazioni_prezzo_service as svc
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova


class CreaRichiestaApprovazioneTests(TestCase):

    def setUp(self):
        svc.invalidate_lookup_cache()
        self.addCleanup(svc.invalidate_lookup_cache)

    def _setup_lookups(self, mock_cursor):
        # tipo_prestazione_id (5) + priorita default id (2)
        mock_cursor.fetchone.side_effect = [(5,), (2,)]

    @patch("apps.vendite.services.approvazioni_prezzo_service._invia_email_richiesta_approvazione")
    @patch("apps.vendite.services.approvazioni_prezzo_service.cambia_stato_pratica")
    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_pratica")
    @patch("apps.vendite.services.approvazioni_prezzo_service.PreventiviRepository", autospec=True)
    @patch("apps.core.db._helpers.connection")
    def test_crea_richiesta_pratica_aperta_con_email_bestffort(
        self, mock_conn, mock_repo_cls, mock_crea_pratica, mock_cambia_stato, mock_email
    ):
        mock_cursor = MagicMock()
        self._setup_lookups(mock_cursor)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        repo = MagicMock()
        repo.get_preventivo.return_value = {
            # La forma VERA di `get_preventivo` (`PreventivoDetailRow`): `numero`.
            "id": 1, "uid": "X-001", "numero": "P-001",
            "istanza_utility_id": 99,
        }
        repo.resolve_contesto_pratica.return_value = {
            "emittente_fiscale_id": 11,
            "soggetto_id": "soggetto-uuid",
            "soggetto_ruolo_id": 22,
            "billing_account_id": 33,
        }
        mock_repo_cls.return_value = repo
        mock_crea_pratica.return_value = 12345

        pratica_id = svc.crea_richiesta_approvazione(
            preventivo_id=1,
            articolo_id="art-uuid-1",
            prezzo_resolver=Decimal("50.00"),
            prezzo_manuale=Decimal("40.00"),
            violazione={
                "tipo_violazione": "SCONTO",
                "variazione_abs_pct": "20.00",
                "limite_pct": "15",
                "kind_label": "Sconto",
            },
            auth_user_id=42,
        )

        self.assertEqual(pratica_id, 12345)
        mock_crea_pratica.assert_called_once()
        crea_kwargs = mock_crea_pratica.call_args.kwargs
        self.assertEqual(crea_kwargs["emittente_fiscale_id"], 11)
        self.assertEqual(crea_kwargs["tipo_prestazione_id"], 5)
        self.assertEqual(crea_kwargs["priorita_id"], 2)
        self.assertEqual(crea_kwargs["soggetto_id"], "soggetto-uuid")
        self.assertEqual(crea_kwargs["istanza_utility_id"], 99)
        # Il cliente a grana fine della pratica e' il BA del documento (D-9).
        self.assertEqual(crea_kwargs["billing_account_id"], 33)
        # La pratica si descrive col NUMERO del preventivo, non con l'id.
        self.assertIn("preventivo P-001", crea_kwargs["descrizione"])
        # La pratica nasce gia' APERTA da crea_pratica: nessun transito esplicito.
        mock_cambia_stato.assert_not_called()
        # Email best-effort invocata (non solleva nemmeno se fallisce).
        mock_email.assert_called_once()

    @patch("apps.vendite.services.approvazioni_prezzo_service.PreventiviRepository", autospec=True)
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_crea_richiesta_contesto_mancante_solleva(
        self, mock_conn, mock_repo_cls
    ):
        repo = MagicMock()
        repo.get_preventivo.return_value = {"id": 1, "uid": "X-001"}
        repo.resolve_contesto_pratica.return_value = None
        mock_repo_cls.return_value = repo

        with self.assertRaises(ServiceError) as ctx:
            svc.crea_richiesta_approvazione(
                preventivo_id=1,
                articolo_id="art-uuid",
                prezzo_resolver=None,
                prezzo_manuale=Decimal("100"),
                violazione={"tipo_violazione": "SCONTO"},
                auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_APPROVAZIONE_PREZZO_NON_AMMESSA")


class ApprovaRifiutaTests(TestCase):

    def setUp(self):
        svc.invalidate_lookup_cache()
        self.addCleanup(svc.invalidate_lookup_cache)

    def _mock_cursor_riga_pending(self, mock_conn, riga_id=50, pratica_id=12345,
                                   stato="PENDING", meta=None):
        # Refactor 2026-05-19 sorgente-agnostico: la query include ora la
        # colonna `meta` (serve a `rifiuta` che proietta motivazione nel meta
        # riga) e il nome FK e' aliasato `AS documento_id`. Il test mock
        # riflette la nuova firma.
        mock_cursor = MagicMock()
        # Colonne come quelle di psycopg (`.name`): le legge `row_to_dict`/`rows_to_list`.
        mock_cursor.description = [
            SimpleNamespace(name=c) for c in (
                "id",
                "documento_id",
                "stato_approvazione_prezzo",
                "pratica_approvazione_prezzo_id",
                "meta",
            )
        ]
        mock_cursor.fetchone.return_value = (
            riga_id, 1, stato, pratica_id, meta or {},
        )
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        return mock_cursor

    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_nota_pratica")
    @patch("apps.vendite.services.approvazioni_prezzo_service.cambia_stato_pratica")
    @patch("apps.vendite.services.approvazioni_prezzo_service.PreventiviRepository", autospec=True)
    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_approva_riga_pending_chiude_pratica_e_aggiorna_riga(
        self, mock_conn, mock_get_user, mock_perm, mock_repo_cls,
        mock_cambia, mock_nota,
    ):
        self._mock_cursor_riga_pending(mock_conn)
        mock_user = operatore_di_prova()
        mock_get_user.return_value = mock_user
        mock_perm.check_azione.return_value = True
        repo = MagicMock(); mock_repo_cls.return_value = repo

        result = svc.approva(riga_id=50, auth_user_id=42, nota="Cliente strategico.")

        self.assertEqual(result["stato"], "APPROVED")
        self.assertEqual(result["pratica_id"], 12345)
        repo.update_riga.assert_called_once_with(50, stato_approvazione_prezzo="APPROVED")
        mock_cambia.assert_called_once_with(12345, "CHIUSA")
        mock_nota.assert_called_once()
        # nota tipo INTERNA + contenuto include la nota libera.
        nota_args = mock_nota.call_args[0]
        self.assertEqual(nota_args[1], "INTERNA")
        self.assertIn("Cliente strategico", nota_args[2])

    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_approva_riga_non_pending_solleva(
        self, mock_conn, mock_get_user, mock_perm
    ):
        # Permesso check passa per primo (defense-in-depth post-review F1):
        # serve mock utente + check_azione=True per arrivare al lookup riga.
        mock_user = operatore_di_prova()
        mock_get_user.return_value = mock_user
        mock_perm.check_azione.return_value = True
        self._mock_cursor_riga_pending(mock_conn, stato="APPROVED")

        with self.assertRaises(ServiceError) as ctx:
            svc.approva(riga_id=50, auth_user_id=42)
        self.assertEqual(ctx.exception.code, "E_APPROVAZIONE_PREZZO_NON_AMMESSA")

    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_approva_senza_permesso_solleva(
        self, mock_conn, mock_get_user, mock_perm
    ):
        self._mock_cursor_riga_pending(mock_conn)
        mock_user = operatore_di_prova()
        mock_get_user.return_value = mock_user
        mock_perm.check_azione.return_value = False  # nessun permesso

        with self.assertRaises(ServiceError) as ctx:
            svc.approva(riga_id=50, auth_user_id=42)
        self.assertEqual(ctx.exception.code, "E_PRICING_OVERRIDE_NON_AUTORIZZATO")

    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_nota_pratica")
    @patch("apps.vendite.services.approvazioni_prezzo_service.cambia_stato_pratica")
    @patch("apps.vendite.services.approvazioni_prezzo_service.PreventiviRepository", autospec=True)
    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_approva_superuser_bypassa_permesso(
        self, mock_conn, mock_get_user, mock_perm, mock_repo_cls,
        mock_cambia, mock_nota,
    ):
        self._mock_cursor_riga_pending(mock_conn)
        mock_user = MagicMock(); mock_user.is_superuser = True
        mock_get_user.return_value = mock_user
        mock_repo_cls.return_value = MagicMock()

        svc.approva(riga_id=50, auth_user_id=99)

        mock_perm.check_azione.assert_not_called()  # bypass

    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_nota_pratica")
    @patch("apps.vendite.services.approvazioni_prezzo_service.cambia_stato_pratica")
    @patch("apps.vendite.services.approvazioni_prezzo_service.PreventiviRepository", autospec=True)
    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_rifiuta_riga_pending_con_motivazione(
        self, mock_conn, mock_get_user, mock_perm, mock_repo_cls,
        mock_cambia, mock_nota,
    ):
        self._mock_cursor_riga_pending(mock_conn)
        mock_user = operatore_di_prova()
        mock_get_user.return_value = mock_user
        mock_perm.check_azione.return_value = True
        repo = MagicMock(); mock_repo_cls.return_value = repo

        result = svc.rifiuta(
            riga_id=50, auth_user_id=42, motivazione="Sconto eccessivo per categoria."
        )

        self.assertEqual(result["stato"], "REJECTED")
        # Check chiamata update_riga: stato + meta denormalizzato motivazione.
        # Verifichiamo solo la presenza della motivazione e degli ancoraggi
        # del meta (timestamp e user_id sono dinamici).
        self.assertEqual(repo.update_riga.call_count, 1)
        kwargs = repo.update_riga.call_args.kwargs
        self.assertEqual(kwargs["stato_approvazione_prezzo"], "REJECTED")
        self.assertIn("approvazione_rifiuto", kwargs["meta"])
        rif = kwargs["meta"]["approvazione_rifiuto"]
        self.assertEqual(rif["motivazione"], "Sconto eccessivo per categoria.")
        self.assertEqual(rif["approver_user_id"], 42)
        self.assertEqual(rif["pratica_id"], 12345)
        self.assertIn("rifiutato_il", rif)
        mock_cambia.assert_called_once_with(12345, "CHIUSA")
        nota_args = mock_nota.call_args[0]
        self.assertIn("Sconto eccessivo", nota_args[2])

    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_nota_pratica")
    @patch("apps.vendite.services.approvazioni_prezzo_service.cambia_stato_pratica")
    @patch("apps.vendite.services.approvazioni_prezzo_service.PreventiviRepository", autospec=True)
    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_rifiuta_senza_motivazione_nota_generica(
        self, mock_conn, mock_get_user, mock_perm, mock_repo_cls,
        mock_cambia, mock_nota,
    ):
        self._mock_cursor_riga_pending(mock_conn)
        mock_user = operatore_di_prova()
        mock_get_user.return_value = mock_user
        mock_perm.check_azione.return_value = True
        mock_repo_cls.return_value = MagicMock()

        svc.rifiuta(riga_id=50, auth_user_id=42)

        nota_args = mock_nota.call_args[0]
        self.assertEqual(nota_args[2], "Rifiutato override prezzo.")

    # =========================================================================
    # Dispatch sorgente=contratto (refactor 2026-05-19 BE porting gate riga
    # contratti). Verifica che approva/rifiuta su sorgente='contratto'
    # usino ContrattiRepository invece di PreventiviRepository.
    # =========================================================================

    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_nota_pratica")
    @patch("apps.vendite.services.approvazioni_prezzo_service.cambia_stato_pratica")
    @patch(
        "apps.vendite.db.contratti_repository.ContrattiRepository", autospec=True)
    @patch("apps.vendite.services.approvazioni_prezzo_service.PreventiviRepository", autospec=True)
    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_approva_riga_contratto_dispatch_contratti_repo(
        self, mock_conn, mock_get_user, mock_perm,
        mock_prev_repo_cls, mock_contr_repo_cls,
        mock_cambia, mock_nota,
    ):
        # Scopo: sorgente='contratto' deve passare per ContrattiRepository,
        # non PreventiviRepository. Verifica anche che la query _get_riga_pending
        # legga da `vendite.contratti_righe` (via mock cursor inspect).
        self._mock_cursor_riga_pending(mock_conn)
        mock_user = operatore_di_prova()
        mock_get_user.return_value = mock_user
        mock_perm.check_azione.return_value = True
        contr_repo = MagicMock(); mock_contr_repo_cls.return_value = contr_repo

        result = svc.approva(
            riga_id=50, auth_user_id=42, sorgente="contratto",
        )

        self.assertEqual(result["stato"], "APPROVED")
        # ContrattiRepository.update_riga chiamato con (riga_id, dict).
        contr_repo.update_riga.assert_called_once_with(
            50, {"stato_approvazione_prezzo": "APPROVED"},
        )
        # PreventiviRepository.update_riga NON chiamato.
        mock_prev_repo_cls.return_value.update_riga.assert_not_called()
        # Query SQL: il primo arg execute include `vendite.contratti_righe`.
        execute_call = mock_conn.cursor.return_value.__enter__.return_value.execute
        sql_text = execute_call.call_args.args[0]
        self.assertIn("vendite.contratti_righe", sql_text)
        self.assertIn("contratto_id", sql_text)

    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_nota_pratica")
    @patch("apps.vendite.services.approvazioni_prezzo_service.cambia_stato_pratica")
    @patch(
        "apps.vendite.db.contratti_repository.ContrattiRepository", autospec=True)
    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_rifiuta_riga_contratto_dispatch_meta_motivazione(
        self, mock_conn, mock_get_user, mock_perm,
        mock_contr_repo_cls, mock_cambia, mock_nota,
    ):
        # Scopo: rifiuta contratto popola meta motivazione su contratti_righe.
        self._mock_cursor_riga_pending(mock_conn, meta={})
        mock_user = operatore_di_prova()
        mock_get_user.return_value = mock_user
        mock_perm.check_azione.return_value = True
        contr_repo = MagicMock(); mock_contr_repo_cls.return_value = contr_repo

        svc.rifiuta(
            riga_id=50, auth_user_id=42,
            motivazione="Sconto fuori policy",
            sorgente="contratto",
        )

        # ContrattiRepository.update_riga chiamato con dict positional.
        args = contr_repo.update_riga.call_args.args
        self.assertEqual(args[0], 50)
        self.assertEqual(args[1]["stato_approvazione_prezzo"], "REJECTED")
        rif = args[1]["meta"]["approvazione_rifiuto"]
        self.assertEqual(rif["motivazione"], "Sconto fuori policy")
        self.assertEqual(rif["approver_user_id"], 42)


class ListaCodaTests(TestCase):

    def setUp(self):
        svc.invalidate_lookup_cache()
        self.addCleanup(svc.invalidate_lookup_cache)

    @patch("apps.vendite.services.approvazioni_prezzo_service.cerca_pratiche")
    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.core.db._helpers.connection")
    def test_lista_coda_filtra_aperte_per_emittente(
        self, mock_conn, mock_get_user, mock_perm, mock_cerca
    ):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (5,)  # tipo_prestazione_id
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_user = MagicMock(is_superuser=False)
        mock_get_user.return_value = mock_user
        mock_perm.get_emittente_for_user.return_value = 11
        mock_perm.check_azione.return_value = True  # utente puo' approvare
        mock_cerca.return_value = (
            [{"id": 100, "descrizione": "Test", "meta": {"riga_preventivo_id": 7}}],
            1,
        )

        result = svc.lista_coda(auth_user_id=42, limit=20, offset=0)

        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["results"]), 1)
        cerca_kwargs = mock_cerca.call_args.kwargs
        self.assertEqual(cerca_kwargs["emittente_fiscale_id"], 11)
        self.assertEqual(cerca_kwargs["tipo_prestazione_id"], 5)
        self.assertEqual(cerca_kwargs["stato_codice_interno"], "APERTA")
        # Fase 5.B1: capability arricchite per item.
        item = result["results"][0]
        self.assertTrue(item["can_approve"])
        self.assertTrue(item["can_reject"])
        self.assertIsNone(item["action_reason"])

    @patch("apps.vendite.services.approvazioni_prezzo_service.cerca_pratiche")
    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_lista_coda_capability_permesso_mancante(
        self, mock_conn, mock_get_user, mock_perm, mock_cerca
    ):
        # Fase 5.B1: utente senza azione approva_prezzo_override -> tutte le
        # righe della coda hanno can_*=False con reason='PERMESSO_MANCANTE'.
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (5,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_user.return_value = MagicMock(is_superuser=False)
        mock_perm.get_emittente_for_user.return_value = 11
        mock_perm.check_azione.return_value = False  # niente permesso
        mock_cerca.return_value = (
            [{"id": 100, "meta": {"riga_preventivo_id": 7}}], 1,
        )

        result = svc.lista_coda(auth_user_id=42)
        item = result["results"][0]
        self.assertFalse(item["can_approve"])
        self.assertFalse(item["can_reject"])
        self.assertEqual(item["action_reason"], "PERMESSO_MANCANTE")

    @patch("apps.vendite.services.approvazioni_prezzo_service.cerca_pratiche")
    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_lista_coda_capability_riga_non_linkata(
        self, mock_conn, mock_get_user, mock_perm, mock_cerca
    ):
        # Fase 5.B1: pratica senza meta.riga_preventivo_id (legacy / crash) ->
        # FE non puo' chiamare approva/rifiuta perche' manca l'id riga.
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (5,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_user.return_value = MagicMock(is_superuser=False)
        mock_perm.get_emittente_for_user.return_value = 11
        mock_perm.check_azione.return_value = True
        mock_cerca.return_value = (
            [{"id": 100, "meta": {}}],  # no riga_preventivo_id
            1,
        )

        result = svc.lista_coda(auth_user_id=42)
        item = result["results"][0]
        self.assertFalse(item["can_approve"])
        self.assertFalse(item["can_reject"])
        self.assertEqual(item["action_reason"], "RIGA_NON_LINKATA")

    @patch("apps.vendite.services.approvazioni_prezzo_service.cerca_pratiche")
    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_lista_coda_capability_meta_none(
        self, mock_conn, mock_get_user, mock_perm, mock_cerca
    ):
        # Edge case O2: pratica con meta=None (creata fuori dal flow standard
        # o con UPDATE manuale). _capabilities_per_pratica non deve crashare,
        # e deve riportare RIGA_NON_LINKATA (no riga linkata).
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (5,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_user.return_value = MagicMock(is_superuser=False)
        mock_perm.get_emittente_for_user.return_value = 11
        mock_perm.check_azione.return_value = True
        mock_cerca.return_value = (
            [{"id": 100, "meta": None}],  # meta None esplicito
            1,
        )

        result = svc.lista_coda(auth_user_id=42)
        item = result["results"][0]
        self.assertFalse(item["can_approve"])
        self.assertEqual(item["action_reason"], "RIGA_NON_LINKATA")

    @patch("apps.vendite.services.approvazioni_prezzo_service.cerca_pratiche")
    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_lista_coda_capability_riga_id_zero(
        self, mock_conn, mock_get_user, mock_perm, mock_cerca
    ):
        # Edge case B3: riga_preventivo_id = 0 (id invalido in PG ma teorico).
        # Il check `is not None` lo accetta come "linkato"; il falsy `or` di
        # prima cadeva nel fallback legacy. Documentiamo il comportamento.
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (5,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_user.return_value = MagicMock(is_superuser=False)
        mock_perm.get_emittente_for_user.return_value = 11
        mock_perm.check_azione.return_value = True
        mock_cerca.return_value = (
            [{"id": 100, "meta": {"riga_preventivo_id": 0}}],
            1,
        )

        result = svc.lista_coda(auth_user_id=42)
        item = result["results"][0]
        # 0 e' un id valido per il check (is not None); FE/BE downstream
        # rifiuteranno se la riga 0 non esiste — corretto separation of concerns.
        self.assertTrue(item["can_approve"])
        self.assertIsNone(item["action_reason"])

    @patch("apps.vendite.services.approvazioni_prezzo_service.cerca_pratiche")
    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    @patch("apps.vendite.services.approvazioni_prezzo_service.connection")
    def test_lista_coda_capability_superuser_bypass(
        self, mock_conn, mock_get_user, mock_perm, mock_cerca
    ):
        # Fase 5.B1: superuser bypassa il check azione ma non quello
        # linkability (sempre necessario riga_preventivo_id).
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (5,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_user.return_value = MagicMock(is_superuser=True)
        mock_perm.get_emittente_for_user.return_value = 11
        # check_azione NON viene chiamato per superuser (vedi
        # _user_can_approve_or_reject); non assegniamo return_value.
        mock_cerca.return_value = (
            [{"id": 100, "meta": {"riga_preventivo_id": 7}}], 1,
        )

        result = svc.lista_coda(auth_user_id=42)
        item = result["results"][0]
        self.assertTrue(item["can_approve"])
        self.assertTrue(item["can_reject"])

    @patch("apps.vendite.services.approvazioni_prezzo_service.PermissionResolver")
    @patch("apps.vendite.services.approvazioni_prezzo_service._get_user")
    def test_lista_coda_senza_emittente_solleva(self, mock_get_user, mock_perm):
        mock_get_user.return_value = MagicMock()
        mock_perm.get_emittente_for_user.return_value = None  # admin globale o non assegnato

        with self.assertRaises(ServiceError) as ctx:
            svc.lista_coda(auth_user_id=42)
        self.assertEqual(ctx.exception.code, "E_APPROVAZIONE_PREZZO_NON_AMMESSA")


class LookupCacheTests(TestCase):

    def setUp(self):
        svc.invalidate_lookup_cache()
        self.addCleanup(svc.invalidate_lookup_cache)

    @patch("apps.core.db._helpers.connection")
    def test_tipo_prestazione_lookup_riusa_cache(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (5,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # 3 chiamate -> 1 sola query DB.
        svc._get_tipo_prestazione_id()
        svc._get_tipo_prestazione_id()
        svc._get_tipo_prestazione_id()
        self.assertEqual(mock_cursor.execute.call_count, 1)

    @patch("apps.core.db._helpers.connection")
    def test_invalidate_cache_forza_re_query(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (5,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        svc._get_tipo_prestazione_id()
        svc.invalidate_lookup_cache()
        svc._get_tipo_prestazione_id()
        self.assertEqual(mock_cursor.execute.call_count, 2)
