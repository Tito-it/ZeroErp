# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Un magazzino che ha un trasferimento non si spegne, da entrambi i
#        lati (`magazzino_id_from`, `magazzino_id_to`): le due FK sono legate
#        dalla regola ATTIVO dal giro DB del 2026-11-22
#        (brief-db-attivo-fk-senza-suffisso-id §6). Sul DB vero, dal service
#        delle anagrafiche di magazzino, che traduce col suo
#        `make_db_errors_translator`: il codice arriva col suo nome e col
#        testo del catalogo.
#
# ⭐ `E_ATTIVO_BLOCK_CHILDREN_EXIST` e non `_ACTIVE`: `magazzino.trasferimenti`
#    non ha `attivo`, quindi conta OGNI riga. Il rimedio non e' «spegni il
#    trasferimento», che non si puo': un magazzino che ne ha uno resta acceso.
#
# ⚠️ CASI COSTRUITI in una transazione SEMPRE annullata, coi builder
#    `dbops.fn_pgtap_*` (gli stessi di `test_anagrafiche_magazzino_db.py`). Il
#    trasferimento si inserisce in SQL: nessun verbo lo crea ancora
#    (brief-db-magazzino-tutte-le-scritture-dal-verbo §5.1, D-M7).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) MagazzinoSpentoConTrasferimentiDbTests.test_il_magazzino_con_un_trasferimento_non_si_spegne
   Il magazzino di partenza e quello d'arrivo: `E_ATTIVO_BLOCK_CHILDREN_EXIST`,
   409, col messaggio del catalogo. Un terzo magazzino, senza trasferimenti,
   si spegne.
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import Annulla, apri_operatore_con_aree, richiedi_db_provvisto
from apps.magazzino.services import anagrafiche_magazzino_service as svc

_CODICE = "E_ATTIVO_BLOCK_CHILDREN_EXIST"


class MagazzinoSpentoConTrasferimentiDbTests(unittest.TestCase):

    def setUp(self) -> None:
        # La sonda e' il builder piu' recente che il test usa (`20261123-11`).
        richiedi_db_provvisto("dbops.fn_pgtap_crea_trasferimento(bigint, bigint, jsonb)")

    # Scopo: Esegue `azione` in un savepoint e ne ritorna il ServiceError.
    def _rifiuto(self, azione) -> ServiceError:
        try:
            with transaction.atomic():
                azione()
        except ServiceError as exc:
            return exc
        self.fail("lo spegnimento doveva essere rifiutato")

    def test_il_magazzino_con_un_trasferimento_non_si_spegne(self) -> None:
        try:
            with transaction.atomic(), connection.cursor() as cur:
                # Lo spegnimento passa dal verbo, che chiede TUTTO sull'oggetto
                # (R-1 di brief-db-magazzino-tutte-le-scritture-dal-verbo).
                apri_operatore_con_aree(
                    cur, aree=("magazzino",),
                )
                cur.execute(
                    "SELECT dbops.fn_pgtap_crea_magazzino('BE-ATT-DA', false),"
                    "       dbops.fn_pgtap_crea_magazzino('BE-ATT-A', false),"
                    "       dbops.fn_pgtap_crea_magazzino('BE-ATT-LIBERO', false)"
                )
                da, a, libero = (int(x) for x in cur.fetchone())
                # Il trasferimento dal BUILDER sul verbo (`20261123-11`): alla
                # chiusura delle tabelle dei documenti interni (P-5c) l'app
                # non le scrive piu'.
                cur.execute(
                    "SELECT dbops.fn_pgtap_crea_trasferimento(%s, %s, '{}'::jsonb)",
                    [da, a],
                )
                cur.execute(
                    "SELECT messaggio FROM config.messaggi_errore WHERE codice = %s AND lingua = 'it'",
                    [_CODICE],
                )
                messaggio = str(cur.fetchone()[0])

                for magazzino in (da, a):
                    with self.subTest(magazzino=magazzino):
                        exc = self._rifiuto(
                            lambda m=magazzino: svc.aggiorna_magazzino(m, {"attivo": False}),
                        )
                        self.assertEqual(exc.code, _CODICE)
                        self.assertEqual(exc.message, messaggio)
                        self.assertEqual(ErrorTranslator.get_http_status(ErrorTranslator.to_api_error(exc)), 409)

                # Il controesempio: senza trasferimenti il magazzino si spegne.
                self.assertFalse(svc.aggiorna_magazzino(libero, {"attivo": False})["attivo"])
                raise Annulla
        except Annulla:
            pass
