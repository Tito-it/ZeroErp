# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La creazione di un contatto (del soggetto e del ruolo) sul DATABASE
#        VERO, attraverso il BB `crea_contatto_validato`, e la sua modifica: i
#        rifiuti arrivano col codice parlante e il campo da accendere, non come
#        `E_DATABASE`.
# Note: ⛔ Fino al 2026-10-09 il contatto del soggetto senza tipo arrivava al
#       NOT NULL, e un secondo contatto dello stesso tipo all'indice unico:
#       tutti e due uscivano `400 E_DATABASE` generico (trovato dallo smoke
#       soggetti).
#       ⭐ Dal 2026-11-25 il doppione della CREAZIONE lo traduce il verbo del DB
#       `fn_crea_contatto` (`E_CONTATTO_TIPO_DUPLICATO`, D-T7b-5,
#       brief-db-revisione-anagrafiche §22.6 voce 3); quello della MODIFICA,
#       un UPDATE diretto, resta del backend (`VINCOLI_CONTATTO`): qui si prova
#       che i NOMI VERI degli indici (`uq_contatti_*`) arrivano al traduttore,
#       i mock non lo vedono.
#       ⚠️ Il mondo si COSTRUISCE (`fn_pgtap_crea_soggetto_pg`, che crea anche
#       il contatto di default), in transazione ANNULLATA.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ContattiCreazioneDbTests.test_soggetto_tipo_gia_usato_409_col_campo
2) ContattiCreazioneDbTests.test_soggetto_senza_tipo_400_col_campo
3) ContattiCreazioneDbTests.test_ruolo_tipo_gia_usato_409_col_campo
4) ContattiCreazioneDbTests.test_modifica_tipo_gia_usato_409_col_campo
"""
from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any

from django.db import connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto


class ContattiCreazioneDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            apri_contesto_operatore(cur)
            cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Soggetto contatti creazione')")
            self.soggetto_id = str(cur.fetchone()[0])
            # Il tipo del contatto di default creato dal builder: il secondo
            # contatto con lo stesso tipo urta l'unicita'.
            cur.execute(
                "SELECT tipo_contatto_id FROM anagrafiche.contatti "
                " WHERE soggetto_id = %s AND soggetto_ruolo_id IS NULL LIMIT 1",
                [self.soggetto_id],
            )
            self.tipo_usato = cur.fetchone()[0]
            # Il guard degli indirizzi del ruolo resta al COMMIT (mai, qui).
            cur.execute("SET CONSTRAINTS ALL DEFERRED")

    # Scopo: il rifiuto atteso, tradotto come lo traduce il middleware.
    def _rifiuto(self, fn: Callable[[], Any], codice: str, status: int) -> None:
        try:
            with transaction.atomic():
                fn()
        except Exception as exc:  # la strada e' cio' che si prova
            api = ErrorTranslator.to_api_error(exc)
            self.assertEqual(api.code, codice, f"{api.message} — {exc!r}")
            self.assertIn("tipo_contatto_id", api.fields or (), "campo non acceso")
            self.assertEqual(ErrorTranslator.get_http_status(api), status)
            return
        self.fail(f"atteso {codice}, accettato")

    # 1. Secondo contatto del soggetto con lo stesso tipo: 409 sul tipo.
    def test_soggetto_tipo_gia_usato_409_col_campo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        payload = {"nominativo": "Secondo", "tipo_contatto_id": self.tipo_usato}
        self._rifiuto(
            lambda: SoggettiService().create_contatto(self.soggetto_id, payload),
            "E_CONTATTO_TIPO_DUPLICATO", 409,
        )

    # 2. Contatto senza tipo: 400 prima del DB, col campo.
    def test_soggetto_senza_tipo_400_col_campo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        self._rifiuto(
            lambda: SoggettiService().create_contatto(self.soggetto_id, {"nominativo": "Senza tipo"}),
            "E_CONTATTO_INCOMPLETO", 400,
        )

    # 3. Contatto del ruolo: il primo passa, il secondo dello stesso tipo e' 409.
    def test_ruolo_tipo_gia_usato_409_col_campo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        with connection.cursor() as cur:
            cur.execute("SELECT script.fn_get_or_create_soggetto_ruolo(%s::uuid, 'CL')", [self.soggetto_id])
            ruolo_id = cur.fetchone()[0]
        payload = {"nominativo": "Del ruolo", "tipo_contatto_id": self.tipo_usato}
        creato = SoggettiService().create_contatto_ruolo(ruolo_id, payload)
        self.assertEqual(creato["soggetto_ruolo_id"], ruolo_id)
        self._rifiuto(
            lambda: SoggettiService().create_contatto_ruolo(ruolo_id, payload),
            "E_CONTATTO_TIPO_DUPLICATO", 409,
        )

    # 4. La modifica che porta il tipo di un altro contatto del contesto: 409
    #    sul tipo, dal backend (l'UPDATE diretto non passa dal verbo).
    def test_modifica_tipo_gia_usato_409_col_campo(self):
        from apps.anagrafiche.services.soggetti_service import SoggettiService

        with connection.cursor() as cur:
            cur.execute(
                "SELECT id FROM config.tipi_contatti WHERE id <> %s ORDER BY id LIMIT 1",
                [self.tipo_usato],
            )
            altro_tipo = cur.fetchone()[0]
        secondo = SoggettiService().create_contatto(
            self.soggetto_id, {"nominativo": "Secondo", "tipo_contatto_id": altro_tipo},
        )["id"]
        self._rifiuto(
            lambda: SoggettiService().update_contatto(
                secondo, {"tipo_contatto_id": self.tipo_usato}, soggetto_id=self.soggetto_id,
            ),
            "E_ANAG_DUPLICATO", 409,
        )
