# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: BE11 di brief-db-revisione-dbops (blocco 7-bis-c, 2026-11-08) sul
#        DATABASE PROVVISTO: `ui` e' nell'ambito delle automazioni.
#        - L'audit (`user_insert`, `data_update`, `user_update`) lo scrive il
#          trigger generico dal JWT (`app.jwt_user`): il repository admin non
#          lo nomina piu', e i suoi INSERT/UPDATE devono legare lo stesso.
#        - La data del CONTENUTO di un preset e' `contenuto_aggiornato_il`:
#          si sposta solo quando cambia il contenuto (il WHEN del trigger
#          `a20`), non a ogni UPDATE. Lo snapshot della preferenza la legge.
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
5) AuditUiDalTriggerDbTests.test_upsert_permesso_audit_dal_trigger
6) AuditUiDalTriggerDbTests.test_spegnere_lista_con_colonne_attive_409
"""
from __future__ import annotations

import unittest
from typing import Any

from django.db import connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.ui.db.ui_admin_repository import UiAdminRepository
from apps.ui.db.ui_repository import UiRepository, fetch_preset_base_snapshot
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
        richiedi_db_provvisto("ui.trgfn_preset_contenuto_aggiornato()")

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
        })
        self.preset_id = self.repo.create_preset({
            "lista_id": self.lista_id,
            "codice": "be11_sistema",
            "descrizione": "Preset di sistema BE11",
            "ambito": "sistema",
            "is_default": True,
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
    def test_contenuto_fermo_se_cambia_solo_la_descrizione(self) -> None:
        (prima,) = self._riga("ui.lista_preset", self.preset_id, "contenuto_aggiornato_il")
        with connection.cursor() as cur:
            # La riga nasce con `now()`: la si porta indietro per distinguere
            # «fermo» da «riscritto con lo stesso istante della transazione».
            cur.execute(
                "UPDATE ui.lista_preset SET contenuto_aggiornato_il = %s - interval '1 day' "
                "WHERE id = %s",
                [prima, self.preset_id],
            )
        (indietro,) = self._riga("ui.lista_preset", self.preset_id, "contenuto_aggiornato_il")
        self.assertTrue(self.repo.update_preset(self.preset_id, {"descrizione": "Altra"}))
        self.assertTrue(self.repo.update_preset(self.preset_id, {"attivo": True}))
        self.assertEqual(
            self._riga("ui.lista_preset", self.preset_id, "contenuto_aggiornato_il"),
            (indietro,),
        )

    def test_contenuto_si_sposta_se_cambia_il_contenuto(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE ui.lista_preset SET contenuto_aggiornato_il = now() - interval '1 day' "
                "WHERE id = %s",
                [self.preset_id],
            )
        self.assertTrue(self.repo.update_preset(
            self.preset_id, {"filtri_default": {"stato": "ATTIVO"}},
        ))
        self.assertEqual(
            self._riga("ui.lista_preset", self.preset_id, "contenuto_aggiornato_il"),
            (self._adesso(),),
        )

    # Lo snapshot (BB `fetch_preset_base_snapshot`, ramo «sistema») e
    # l'upsert della preferenza col nome nuovo della colonna.
    def test_snapshot_e_preferenza_sulla_data_del_contenuto(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO auth_user (password, is_superuser, username, first_name, "
                "last_name, email, is_staff, is_active, date_joined) "
                "VALUES ('!', false, %s, '', '', '', false, true, now()) RETURNING id",
                [_ATTORE],
            )
            auth_user_id = int(cur.fetchone()[0])
            cur.execute(
                "UPDATE ui.lista_preset SET contenuto_aggiornato_il = now() - interval '1 day' "
                "WHERE id = %s",
                [self.preset_id],
            )
        (contenuto,) = self._riga("ui.lista_preset", self.preset_id, "contenuto_aggiornato_il")
        # Un UPDATE che non tocca il contenuto non cambia lo snapshot.
        self.assertTrue(self.repo.update_preset(self.preset_id, {"descrizione": "Altra"}))
        preset_id, snapshot = fetch_preset_base_snapshot(
            "ui.lista_preset",
            entity_id=self.lista_id,
            auth_user_id=auth_user_id,
            emittente_fiscale_id=None,
        )
        self.assertEqual((preset_id, snapshot), (self.preset_id, contenuto))

        repo = UiRepository()
        repo.upsert_preferenza(
            auth_user_id=auth_user_id,
            lista_id=self.lista_id,
            configurazione={},
            preset_base_id=preset_id,
            preset_base_contenuto_aggiornato_il=snapshot,
        )
        preferenza = repo.get_preferenza(auth_user_id, self.lista_id)
        assert preferenza is not None
        self.assertEqual(preferenza["preset_base_id"], self.preset_id)
        self.assertEqual(preferenza["preset_base_contenuto_aggiornato_il"], contenuto)

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
