# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: LE NOTE DI CATALOGO SUL BB DELLE NOTE, dal service fino al DB vero
#        (brief-db-revisione-catalogo, giro 4: BE26, BE27, BE28; 2026-11-11).
#        Dal giro 4 `catalogo.note` ha la forma delle note degli altri schemi,
#        e il backend la scrive con lo stesso `PartitionedNoteService` di
#        `vendite.note`: la chiave del padre e' un UUID, e l'ancora e' solo
#        DOCUMENTO (`chk_note_catalogo_ancora_documento`).
# Note: ⭐ Il mondo si COSTRUISCE (un articolo dalla fixture del DB), in una
#       transazione annullata. Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
#       ⭐ BE28: `user_insert`/`user_update` sono `text` dal giro 4; la nota
#       letta li porta come stringhe, nessuna conversione nel backend.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) NoteCatalogoDbTests.test_nota_dell_articolo_crea_legge_modifica_cancella
2) NoteCatalogoDbTests.test_ancora_riga_rifiutata_col_campo
3) NoteCatalogoDbTests.test_nota_senza_testo_rifiutata
4) NoteCatalogoDbTests.test_nota_di_un_altro_articolo_non_si_trova
5) NoteCatalogoDbTests.test_articolo_con_note_si_spegne_e_la_nota_si_scrive
6) NoteCatalogoDbTests.test_articolo_inesistente_404
"""
from __future__ import annotations

import unittest
from uuid import uuid4

from django.db import connection

from apps.catalogo.db.note_repositories import NOTE_REPO_ARTICOLO
from apps.catalogo.services import catalogo_service
from apps.core.services.partitioned_note_service import PartitionedNoteService
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


class NoteCatalogoDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.svc = PartitionedNoteService(repo=NOTE_REPO_ARTICOLO)
        self.articolo = self._crea_articolo("NOTA")

    @staticmethod
    def _crea_articolo(prefisso: str) -> str:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_articolo(%s)::text",
                [f"{prefisso}-{uuid4().hex[:8].upper()}"],
            )
            return cur.fetchone()[0]

    # 1) Il giro intero dalla porta del service, con la chiave UUID.
    def test_nota_dell_articolo_crea_legge_modifica_cancella(self) -> None:
        nota = self.svc.crea_nota(target_id=self.articolo, payload={"testo": "Prima"})
        self.assertEqual(str(nota["target_id"]), self.articolo)
        self.assertEqual(nota["target_tipo"], "ARTICOLO")
        self.assertEqual(nota["anchor_tipo"], "DOCUMENTO")
        self.assertIsNone(nota["target_riga_id"])
        self.assertIsInstance(nota["user_insert"], (str, type(None)))  # BE28: text

        rows, total = self.svc.list_note(target_id=self.articolo)
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["id"], nota["id"])

        modificata = self.svc.aggiorna_nota(
            note_id=nota["id"], target_id=self.articolo, patch={"testo": "Dopo"},
        )
        self.assertEqual(modificata["testo"], "Dopo")

        self.svc.elimina_nota(note_id=nota["id"], target_id=self.articolo)
        self.assertEqual(self.svc.count_per_target(target_id=self.articolo), 0)

    # 2) BE26: l'ancora RIGA non esiste a catalogo, ne' in creazione ne' in
    #    modifica. La frase la da' il service, prima del CHECK del DB.
    def test_ancora_riga_rifiutata_col_campo(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.svc.crea_nota(target_id=self.articolo, payload={"testo": "x", "anchor_tipo": "RIGA"})
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "anchor_tipo")

        nota = self.svc.crea_nota(target_id=self.articolo, payload={"testo": "x"})
        with self.assertRaises(ServiceError) as ctx:
            self.svc.aggiorna_nota(
                note_id=nota["id"], target_id=self.articolo, patch={"anchor_tipo": "RIGA"},
            )
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")

    # 3) BE26: senza testo ne' testo_md la nota non nasce.
    def test_nota_senza_testo_rifiutata(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.svc.crea_nota(target_id=self.articolo, payload={"testo": "   "})
        self.assertEqual(ctx.exception.code, "E_NOTA_VALIDATION")

    # 4) La nota di un altro articolo non si legge, non si modifica e non si
    #    cancella dal percorso di questo (anti-tampering su `target_id`).
    def test_nota_di_un_altro_articolo_non_si_trova(self) -> None:
        altro = self._crea_articolo("NOTB")
        nota = self.svc.crea_nota(target_id=altro, payload={"testo": "x"})
        for nome, chiama in (
            ("get", lambda: self.svc.get_nota(note_id=nota["id"], target_id=self.articolo)),
            ("patch", lambda: self.svc.aggiorna_nota(
                note_id=nota["id"], target_id=self.articolo, patch={"testo": "y"},
            )),
            ("delete", lambda: self.svc.elimina_nota(note_id=nota["id"], target_id=self.articolo)),
        ):
            with self.subTest(nome), self.assertRaises(ServiceError) as ctx:
                chiama()
            self.assertEqual(ctx.exception.code, "E_NOTA_NOT_FOUND")

    # 5) BE27 (Q12): la nota non tiene acceso il suo bersaglio e non chiede
    #    che sia acceso. Un articolo con una nota si spegne, e su un articolo
    #    spento una nota si scrive.
    def test_articolo_con_note_si_spegne_e_la_nota_si_scrive(self) -> None:
        self.svc.crea_nota(target_id=self.articolo, payload={"testo": "prima"})
        spento = catalogo_service.fn_disattiva_articolo(self.articolo)
        self.assertFalse(spento["attivo"])
        nota = self.svc.crea_nota(target_id=self.articolo, payload={"testo": "dopo"})
        self.assertEqual(nota["testo"], "dopo")

    # 6) Un articolo che non c'e': 404 prima di qualunque scrittura.
    def test_articolo_inesistente_404(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.svc.crea_nota(target_id=str(uuid4()), payload={"testo": "x"})
        self.assertEqual(ctx.exception.code, "E_NOTA_PARENT_NOT_FOUND")
