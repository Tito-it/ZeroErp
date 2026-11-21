# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: BE11 di brief-db-revisione-dbops (blocco 7-bis-c, 2026-11-08) sul
#        DATABASE PROVVISTO: `ui` e' nell'ambito delle automazioni.
#        - L'audit (`user_insert`, `data_update`, `user_update`) lo scrive il
#          trigger generico dal JWT (`app.jwt_user`): il repository admin non
#          lo nomina piu', e i suoi INSERT/UPDATE devono legare lo stesso.
#        - La data del CONTENUTO di un preset e' `contenuto_aggiornato_il`,
#          per chiave dal giro 1b di brief-db-revisione-ui (`{chiave: data}`):
#          si sposta solo la chiave il cui contenuto cambia, non a ogni
#          UPDATE, e la scrive solo il DB (`E_UI_PRESET_CONTENUTO_DERIVATO`
#          a chi la scrive). Lo snapshot della preferenza la copia, e lo
#          scrive il DB (giro 1a); «Ignora» e' riscrivere `preset_base_id`.
#        - Spegnere una lista con colonne attive e' un 409 del guard ATTIVO,
#          non un fallback di validazione del service.
# Note: ⭐ La giuntura, non la regola: la regola la provano i pgTAP di `ui`
#       (`ui/test-ui-nell-ambito-v1`). Qui si prova che il BE parla al DB col
#       nome nuovo e senza l'audit a mano — un mock non lo vede (la rinomina
#       dello snapshot ha rotto il salvataggio delle preferenze con la suite
#       unitaria verde). I soggetti si COSTRUISCONO nel test (lista, colonna,
#       preset, utente): niente dipende dai seed. Tutto in transazione
#       ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) AuditUiDalTriggerDbTests.test_insert_e_update_admin_audit_dal_trigger
2) AuditUiDalTriggerDbTests.test_contenuto_fermo_se_cambia_solo_la_descrizione
3) AuditUiDalTriggerDbTests.test_contenuto_si_sposta_se_cambia_il_contenuto
4) AuditUiDalTriggerDbTests.test_snapshot_e_preferenza_sulla_data_del_contenuto
5) AuditUiDalTriggerDbTests.test_ignora_riallinea_lo_snapshot
6) AuditUiDalTriggerDbTests.test_ignora_riallinea_lo_snapshot_della_dashboard
7) AuditUiDalTriggerDbTests.test_data_del_contenuto_scritta_dall_app_rifiutata
8) AuditUiDalTriggerDbTests.test_upsert_permesso_audit_dal_trigger
9) AuditUiDalTriggerDbTests.test_spegnere_lista_con_colonne_attive_409
"""
from __future__ import annotations

import unittest
from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import jsonb_out
from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.ui.db.dashboard_repository import DashboardRepository
from apps.ui.db.ui_admin_repository import UiAdminRepository
from apps.ui.db.ui_repository import UiRepository
from apps.ui.services._preferenza import preset_base_id_di_oggi
from apps.ui.services.lista_definizione_admin_service import ListaDefinizioneAdminService

_ATTORE = "test_be11_audit_ui"
# ⛔ Gli UPDATE girano con un ALTRO utente. Il trigger scrive `data_update` e
#    `user_update` anche sull'INSERT, e dentro la transazione `now()` e' fermo:
#    con lo stesso attore la prova dell'UPDATE sarebbe verde a vuoto (la
#    passerebbe anche un UPDATE mai eseguito). Il secondo attore e' l'unico
#    segno che distingue chi ha scritto.
_ATTORE_UPDATE = "test_be11_audit_ui_upd"


class AuditUiDalTriggerDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # La sonda sulla colonna del blocco 7-bis-c: un DB indietro fallirebbe
        # sull'attesa invece che sul prerequisito.
        richiedi_db_provvisto("ui.trgfn_preferenza_preset_base_snapshot()")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.repo = UiAdminRepository()
        self._come(_ATTORE)
        self.lista_id = self.repo.create_definizione({
            "codice": "ui.test_be11_audit",
            "descrizione": "BE11 audit dal trigger",
            "schema_dati": "ui",
            "vista_sql": None,
            "attivo": True,
        })
        self.colonna_id = self.repo.create_colonna({
            "lista_id": self.lista_id,
            "codice": "be11_info",
            "etichetta": "Info",
            "tipo_colonna": "informazione",
            "tipo_dato": "string",
            "ordine_default": 1,
            # Spenta di proposito: la accende il test che la compone nel preset.
            "attivo": False,
        })
        self.preset_id = self.repo.create_preset({
            "lista_id": self.lista_id,
            "codice": "be11_sistema",
            "descrizione": "Preset di sistema BE11",
            "ambito": "sistema",
            # La bozza nasce spenta (Q26): il test la vuole accesa.
            "attivo": True,
        })

    def _riga(self, tabella: str, riga_id: int, colonne: str) -> tuple[Any, ...]:
        with connection.cursor() as cur:
            cur.execute(
                # tabella e colonne sono costanti del test, mai input esterno
                f"SELECT {colonne} FROM {tabella} WHERE id = %s",
                [riga_id],
            )
            riga = cur.fetchone()
        assert riga is not None, f"{tabella} id={riga_id} non trovato"
        return tuple(riga)

    # La data del contenuto per chiave, come istanti: la mappa e' un jsonb di
    # stringhe, e due stringhe non si confrontano come due date.
    def _contenuto(self) -> dict[str, Any]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT c.key, c.value::timestamptz "
                "  FROM ui.lista_preset lp, "
                "       jsonb_each_text(lp.contenuto_aggiornato_il) c "
                " WHERE lp.id = %s",
                [self.preset_id],
            )
            return dict(cur.fetchall())

    # La mappa intera come la legge il BE (`jsonb_out`): e' la forma che
    # `get_preferenza` restituisce per lo snapshot.
    def _contenuto_jsonb(self) -> tuple[Any]:
        (grezzo,) = self._riga("ui.lista_preset", self.preset_id, "contenuto_aggiornato_il")
        return (jsonb_out(grezzo),)

    def _adesso(self) -> Any:
        with connection.cursor() as cur:
            cur.execute("SELECT now()")
            return cur.fetchone()[0]

    def _come(self, attore: str) -> None:
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.jwt_user', %s, true)", [attore])

    def test_insert_e_update_admin_audit_dal_trigger(self) -> None:
        for tabella, riga_id in (
            ("ui.lista_definizione", self.lista_id),
            ("ui.lista_colonna", self.colonna_id),
            ("ui.lista_preset", self.preset_id),
        ):
            with self.subTest(tabella=tabella):
                self.assertEqual(self._riga(tabella, riga_id, "user_insert"), (_ATTORE,))
        self._come(_ATTORE_UPDATE)
        self.assertTrue(self.repo.update_definizione(self.lista_id, {"note": "be11"}))
        self.assertTrue(self.repo.update_colonna(self.colonna_id, {"etichetta": "Az."}))
        self.assertTrue(self.repo.update_preset(self.preset_id, {"descrizione": "Altra"}))
        adesso = self._adesso()
        for tabella, riga_id in (
            ("ui.lista_definizione", self.lista_id),
            ("ui.lista_colonna", self.colonna_id),
            ("ui.lista_preset", self.preset_id),
        ):
            with self.subTest(tabella=tabella):
                self.assertEqual(
                    self._riga(tabella, riga_id, "user_insert, user_update, data_update"),
                    (_ATTORE, _ATTORE_UPDATE, adesso),
                )

    # ⭐ Il cuore di N1: `descrizione` non e' contenuto, quindi l'UPDATE muove
    #    l'audit ma non la data che il badge «preset aggiornato» confronta.
    #    L'ora e' `clock_timestamp()`: una riscrittura dentro la stessa
    #    transazione darebbe un istante nuovo, e il test la vedrebbe.
    def test_contenuto_fermo_se_cambia_solo_la_descrizione(self) -> None:
        prima = self._contenuto()
        self.assertIn("pagina_dimensione", prima)
        self.assertTrue(self.repo.update_preset(self.preset_id, {"descrizione": "Altra"}))
        self.assertTrue(self.repo.update_preset(self.preset_id, {"attivo": True}))
        self.assertEqual(self._contenuto(), prima)

    # Si sposta la sola chiave cambiata. ⭐ Dal giro 2 di brief-db-revisione-ui
    # (Q38/Q39 §6) le chiavi di una lista sono `colonne` e `pagina_dimensione`:
    # `ordinamento_default` resta del preset ma non e' una chiave del banner,
    # quindi cambiarlo non sposta niente (era la chiave che questo test muoveva).
    def test_contenuto_si_sposta_se_cambia_il_contenuto(self) -> None:
        prima = self._contenuto()
        self.assertTrue(self.repo.update_preset(
            self.preset_id, {"ordinamento_default": [{"col": "be11_info", "dir": "desc"}]},
        ))
        self.assertEqual(self._contenuto(), prima)

        self.assertTrue(self.repo.update_preset(self.preset_id, {"pagina_dimensione": 100}))
        dopo = self._contenuto()
        self.assertGreater(dopo["pagina_dimensione"], prima["pagina_dimensione"])
        for chiave in set(prima) - {"pagina_dimensione"}:
            with self.subTest(chiave=chiave):
                self.assertEqual(dopo[chiave], prima[chiave])

    # BE5 + BE6 di brief-db-revisione-ui (giro 1a): la base viene dalla
    # risoluzione (`preset_base`, ramo «sistema»), e lo snapshot lo scrive il
    # trigger `ui.trgfn_preferenza_preset_base_snapshot` sulla data del
    # CONTENUTO. L'upsert del BE nomina solo `preset_base_id`: un mock non vede
    # che e' quella colonna, nel SET, a far scattare il trigger.
    def test_snapshot_e_preferenza_sulla_data_del_contenuto(self) -> None:
        auth_user_id = self._utente_con_base()
        (contenuto,) = self._contenuto_jsonb()
        # Un UPDATE che non tocca il contenuto non sposta la data.
        self.assertTrue(self.repo.update_preset(self.preset_id, {"descrizione": "Altra"}))

        repo = UiRepository()
        risoluzione = repo.resolve_lista_config(
            lista_codice="ui.test_be11_audit",
            auth_user_id=auth_user_id,
            emittente_fiscale_id=None,
        )
        self.assertEqual(preset_base_id_di_oggi(risoluzione), self.preset_id)

        repo.upsert_preferenza(
            auth_user_id=auth_user_id,
            lista_id=self.lista_id,
            configurazione={"pagina_dimensione": 50},
            preset_base_id=self.preset_id,
        )
        preferenza = repo.get_preferenza(auth_user_id, self.lista_id)
        assert preferenza is not None
        self.assertEqual(preferenza["preset_base_id"], self.preset_id)
        self.assertEqual(preferenza["preset_base_contenuto_aggiornato_il"], contenuto)

        # Il contenuto cambia: il secondo salvataggio riallinea lo snapshot
        # anche con la stessa base (ramo ON CONFLICT DO UPDATE).
        self.assertTrue(self.repo.update_preset(self.preset_id, {"pagina_dimensione": 100}))
        (contenuto_nuovo,) = self._contenuto_jsonb()
        self.assertNotEqual(contenuto_nuovo, contenuto)
        repo.upsert_preferenza(
            auth_user_id=auth_user_id,
            lista_id=self.lista_id,
            configurazione={"pagina_dimensione": 50},
            preset_base_id=self.preset_id,
        )
        preferenza = repo.get_preferenza(auth_user_id, self.lista_id)
        assert preferenza is not None
        self.assertEqual(preferenza["preset_base_contenuto_aggiornato_il"], contenuto_nuovo)

    # BE7 (parte 1b) di brief-db-revisione-ui: «Ignora» riscrive
    # `preset_base_id` col valore che ha gia', e il trigger riallinea lo
    # snapshot. Prima del giro 1b scriveva `preset_aggiornato_ignored_at`,
    # colonna che non c'e' piu': il mock del service non lo vedeva.
    def test_ignora_riallinea_lo_snapshot(self) -> None:
        auth_user_id = self._utente_con_base()
        repo = UiRepository()
        repo.upsert_preferenza(
            auth_user_id=auth_user_id,
            lista_id=self.lista_id,
            configurazione={"pagina_dimensione": 50},
            preset_base_id=self.preset_id,
        )
        # L'amministratore cambia la chiave che la preferenza ha scelto.
        self.assertTrue(self.repo.update_preset(self.preset_id, {"pagina_dimensione": 10}))

        def _banner() -> tuple[Any, Any]:
            risoluzione = repo.resolve_lista_config(
                lista_codice="ui.test_be11_audit",
                auth_user_id=auth_user_id,
                emittente_fiscale_id=None,
            )
            return risoluzione["preset_aggiornato"], risoluzione["preset_aggiornato_chiavi"]

        self.assertEqual(_banner(), (True, ["pagina_dimensione"]))
        self.assertTrue(repo.riallinea_snapshot_base(auth_user_id, self.lista_id))
        self.assertEqual(_banner(), (False, []))
        preferenza = repo.get_preferenza(auth_user_id, self.lista_id)
        assert preferenza is not None
        self.assertEqual(preferenza["preset_base_id"], self.preset_id)
        self.assertEqual(preferenza["preset_base_contenuto_aggiornato_il"], self._contenuto_jsonb()[0])
        # Senza preferenza non c'e' riga da riallineare: il service da' 404.
        self.assertFalse(repo.riallinea_snapshot_base(auth_user_id + 1, self.lista_id))

    # Il gemello della dashboard: un UPDATE suo, su un'altra tabella e con un
    # altro montaggio del trigger, e i mock del service non lo vedono (prima
    # del giro 1b era un 500 anche qui). La dashboard si fabbrica: quella di
    # seed porterebbe la prova sui dati di oggi.
    def test_ignora_riallinea_lo_snapshot_della_dashboard(self) -> None:
        auth_user_id = self._utente_con_base()
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO ui.dashboard_definizione (codice, descrizione) "
                "VALUES ('test_be11_audit', 'Dashboard del test') RETURNING id",
            )
            dashboard_id = int(cur.fetchone()[0])
            cur.execute(
                "INSERT INTO ui.widget (codice, etichetta) "
                "VALUES ('test_be11_audit', 'Card del test') RETURNING id",
            )
            widget_id = int(cur.fetchone()[0])
            cur.execute(
                "INSERT INTO ui.dashboard_widget (dashboard_id, widget_id, ordine_default) "
                "VALUES (%s, %s, 1)",
                [dashboard_id, widget_id],
            )
            cur.execute(
                "INSERT INTO ui.dashboard_preset (dashboard_id, codice, descrizione, ambito) "
                "VALUES (%s, 'be11_sistema', 'Preset di sistema', 'sistema') RETURNING id",
                [dashboard_id],
            )
            preset_id = int(cur.fetchone()[0])
            # Un preset vale come base solo con contenuto (U3): un widget del pool.
            cur.execute(
                "INSERT INTO ui.dashboard_preset_widget (preset_id, widget_id, ordine) "
                "VALUES (%s, %s, 1)",
                [preset_id, widget_id],
            )
        repo = DashboardRepository()

        def _banner() -> tuple[Any, Any]:
            risoluzione = repo.resolve_dashboard_config(
                dashboard_codice="test_be11_audit",
                auth_user_id=auth_user_id,
                emittente_fiscale_id=None,
            )
            return risoluzione["preset_aggiornato"], risoluzione["preset_aggiornato_chiavi"]

        def _contenuto() -> Any:
            (grezzo,) = self._riga("ui.dashboard_preset", preset_id, "contenuto_aggiornato_il")
            return jsonb_out(grezzo)

        repo.upsert_preferenza(
            auth_user_id=auth_user_id,
            dashboard_id=dashboard_id,
            configurazione={"dimensione_max": 4},
            preset_base_id=preset_id,
        )
        # L'amministratore cambia la chiave che la preferenza ha scelto.
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE ui.dashboard_preset SET dimensione_max = 6 WHERE id = %s",
                [preset_id],
            )
        self.assertEqual(_banner(), (True, ["dimensione_max"]))
        self.assertTrue(repo.riallinea_snapshot_base(auth_user_id, dashboard_id))
        self.assertEqual(_banner(), (False, []))
        preferenza = repo.get_preferenza(auth_user_id, dashboard_id)
        assert preferenza is not None
        self.assertEqual(preferenza["preset_base_id"], preset_id)
        self.assertEqual(preferenza["preset_base_contenuto_aggiornato_il"], _contenuto())
        self.assertFalse(repo.riallinea_snapshot_base(auth_user_id + 1, dashboard_id))

    # BE25 di brief-db-revisione-ui: la data del contenuto la scrive solo il
    # DB. Chi la scrive (un chiamante rimasto alla forma di prima) riceve il
    # codice nuovo, con la sua policy: un TECNICO, non un 500 anonimo.
    def test_data_del_contenuto_scritta_dall_app_rifiutata(self) -> None:
        with self.assertRaises(Exception) as ctx, transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE ui.lista_preset SET contenuto_aggiornato_il = '{}'::jsonb "
                    "WHERE id = %s",
                    [self.preset_id],
                )
        api_error = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(api_error.code, "E_UI_PRESET_CONTENUTO_DERIVATO")
        self.assertEqual(ErrorTranslator.get_http_status(api_error), 500)

    # Un utente e una lista col preset di sistema come base: un preset vale
    # come base solo con contenuto (U3), cioe' una colonna ACCESA nella
    # composizione (la colonna del setUp nasce spenta).
    def _utente_con_base(self) -> int:
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO auth_user (password, is_superuser, username, first_name, "
                "last_name, email, is_staff, is_active, date_joined) "
                "VALUES ('!', false, %s, '', '', '', false, true, now()) RETURNING id",
                [_ATTORE],
            )
            auth_user_id = int(cur.fetchone()[0])
        self.assertTrue(self.repo.update_colonna(self.colonna_id, {"attivo": True}))
        self.repo.replace_preset_colonne(
            self.preset_id, [{"colonna_id": self.colonna_id, "ordine": 1}],
        )
        return auth_user_id

    def test_upsert_permesso_audit_dal_trigger(self) -> None:
        # Il profilo si FABBRICA: «il primo che c'e'» dipendeva dai seed e,
        # su un DB senza profili, saltava il test in silenzio.
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO config.profili_accesso (tipo, codice, descrizione) "
                "VALUES ('AD_HOC', 'TEST_BE11_AUDIT', 'Profilo del test BE11') "
                "RETURNING id",
            )
            profilo_id = int(cur.fetchone()[0])
        permesso_id = self.repo.upsert_permesso(
            colonna_id=self.colonna_id,
            profilo_accesso_id=profilo_id,
            livello_accesso="LETTURA",
        )
        self.assertEqual(
            self._riga("ui.lista_colonna_permesso", permesso_id, "user_insert"),
            (_ATTORE,),
        )
        # Il ramo DO UPDATE: stessa coppia, l'audit lo scrive il trigger.
        self._come(_ATTORE_UPDATE)
        self.assertEqual(
            self.repo.upsert_permesso(
                colonna_id=self.colonna_id,
                profilo_accesso_id=profilo_id,
                livello_accesso="BLOCCATO",
            ),
            permesso_id,
        )
        self.assertEqual(
            self._riga(
                "ui.lista_colonna_permesso", permesso_id,
                "user_insert, user_update, livello_accesso::text",
            ),
            (_ATTORE, _ATTORE_UPDATE, "BLOCCATO"),
        )

    # (d) di BE11: il BLOCK del guard ATTIVO arriva all'operatore come 409
    #     col suo codice, non come il fallback di validazione del service.
    def test_spegnere_lista_con_colonne_attive_409(self) -> None:
        with connection.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")
        with self.assertRaises(Exception) as ctx, transaction.atomic():
            ListaDefinizioneAdminService().update_definizione(
                self.lista_id, {"attivo": False},
            )
        api_error = ErrorTranslator.to_api_error(ctx.exception)
        self.assertEqual(api_error.code, "E_ATTIVO_BLOCK_CHILDREN_ACTIVE")
        self.assertEqual(ErrorTranslator.get_http_status(api_error), 409)
