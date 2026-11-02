# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB `_indirizzi_documento_helpers` sull'upsert di uno slot,
#        condiviso da 5 domini: preventivi, offerte, ordini, DDT, contratti.
#
# Il test presidia il CABLAGGIO: che il service passi al repository le origini
# che riceve, e che NON giudichi piu' da se' se un indirizzo e' del cliente
# del documento. Quella regola sta nel guard DB
# `vendite.trgfn_doc_indirizzi_guard_cliente` dal 2026-10-11 (brief
# brief-db-indirizzi-documento-seguono-il-cliente, R-BE-2), ed e' provata dai
# pgTAP del team DB e da `tests/db/test_indirizzi_seguono_cliente_db.py`, che
# prova anche il rifiuto col campo.
# ⚠️ Il repository e' un mock con `spec`: il giorno in cui il service tornasse
#    a chiedere al repository il cliente del documento, il metodo non c'e' piu'
#    e il test va rosso invece di restare verde su un MagicMock che accetta
#    tutto.
#
# Fino al 2026-10-12 qui si provava `auto_assegna_indirizzo_default` (9 test):
# l'auto-assegnazione e' passata intera nel DB (`vendite.fn_doc_indirizzo_default`,
# D-2), e i suoi casi sono nei pgTAP del brief.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) UpsertIndirizzoDocumentoTests.test_picker_snapshot_dal_db_e_origini_al_repository
2) UpsertIndirizzoDocumentoTests.test_picker_solo_i_contatti_dal_payload
3) UpsertIndirizzoDocumentoTests.test_origine_soggetto_dichiarata_passa_al_repository
4) UpsertIndirizzoDocumentoTests.test_una_tantum_senza_origini
5) UpsertIndirizzoDocumentoTests.test_una_tantum_vuoto_rifiutato
6) UpsertIndirizzoDocumentoTests.test_id_non_interi_rifiutati
"""

from django.test import SimpleTestCase
from unittest.mock import MagicMock

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.ddt_repository import DdtRepository
from apps.vendite.services._indirizzi_documento_helpers import (
    IndirizziDocumentoConfig,
    upsert_indirizzo_documento,
)

_SNAP_RUOLO = {
    "snapshot": {"via": "Via Roma 1", "cap": "20100", "citta": "Milano"},
    "origine_soggetto_ruolo_id": 77,
}


class UpsertIndirizzoDocumentoTests(SimpleTestCase):
    """Upsert di uno slot: il service compone, il DB giudica."""

    def _cfg(self, repo):
        return IndirizziDocumentoConfig(
            repo_factory=lambda: repo,
            not_found_code="E_TEST_NOT_FOUND",
            error_code="E_TEST",
            fn_prefix="vendite.test",
            get_stato=lambda r, i: "DRAFT",
        )

    def _repo(self):
        repo = MagicMock(spec=DdtRepository)
        repo.snapshot_from_origine.return_value = {
            "snapshot": dict(_SNAP_RUOLO["snapshot"]),
            "origine_soggetto_ruolo_id": _SNAP_RUOLO["origine_soggetto_ruolo_id"],
        }
        repo.upsert_indirizzo.return_value = {"id": 1}
        return repo

    # Scopo: flusso picker → lo snapshot lo compone il DB, e le due origini
    #        arrivano al repository cosi' come sono: e' su di esse che il
    #        guard DB decide se l'indirizzo e' del cliente.
    def test_picker_snapshot_dal_db_e_origini_al_repository(self):
        repo = self._repo()

        upsert_indirizzo_documento(self._cfg(repo), 1, {
            "tipo_indirizzo_id": 10, "origine_indirizzo_id": 555,
        })

        repo.snapshot_from_origine.assert_called_once_with(555)
        repo.upsert_indirizzo.assert_called_once_with(
            documento_id=1,
            tipo_indirizzo_id=10,
            snapshot=_SNAP_RUOLO["snapshot"],
            origine_indirizzo_id=555,
            origine_soggetto_ruolo_id=77,
        )

    # Scopo: nel picker il payload aggiunge i soli contatti; una `via` mandata
    #        dal client non sostituisce quella dell'anagrafica.
    def test_picker_solo_i_contatti_dal_payload(self):
        repo = self._repo()

        upsert_indirizzo_documento(self._cfg(repo), 1, {
            "tipo_indirizzo_id": 10, "origine_indirizzo_id": 555,
            "snapshot": {"email": "a@b.it", "via": "Via Falsa 0"},
        })

        snapshot = repo.upsert_indirizzo.call_args.kwargs["snapshot"]
        self.assertEqual(snapshot["email"], "a@b.it")
        self.assertEqual(snapshot["via"], "Via Roma 1")

    # Scopo: «anagrafica soggetto» → l'origine dichiarata dal client passa al
    #        repository (normalizzata a int): che sia il cliente del documento
    #        lo dice il guard DB, non un confronto Python.
    def test_origine_soggetto_dichiarata_passa_al_repository(self):
        repo = self._repo()

        upsert_indirizzo_documento(self._cfg(repo), 1, {
            "tipo_indirizzo_id": 10,
            "origine_soggetto_ruolo_id": "77",
            "snapshot": {"via": "Via Verdi 9", "citta": "Torino"},
        })

        kwargs = repo.upsert_indirizzo.call_args.kwargs
        self.assertIsNone(kwargs["origine_indirizzo_id"])
        self.assertEqual(kwargs["origine_soggetto_ruolo_id"], 77)

    # Scopo: un vero una-tantum non ha nessuna delle due origini.
    def test_una_tantum_senza_origini(self):
        repo = self._repo()

        upsert_indirizzo_documento(self._cfg(repo), 1, {
            "tipo_indirizzo_id": 10,
            "snapshot": {"via": "Via Terzi 3", "citta": "Consegna", "x": "scartata"},
        })

        kwargs = repo.upsert_indirizzo.call_args.kwargs
        self.assertIsNone(kwargs["origine_indirizzo_id"])
        self.assertIsNone(kwargs["origine_soggetto_ruolo_id"])
        self.assertEqual(kwargs["snapshot"], {"via": "Via Terzi 3", "citta": "Consegna"})

    # Scopo: un una-tantum senza sostanza (ne' via, ne' citta', ne' display)
    #        si rifiuta prima di scrivere.
    def test_una_tantum_vuoto_rifiutato(self):
        repo = self._repo()

        with self.assertRaises(ServiceError) as cm:
            upsert_indirizzo_documento(self._cfg(repo), 1, {
                "tipo_indirizzo_id": 10, "snapshot": {"email": "a@b.it"},
            })

        self.assertEqual(cm.exception.code, "E_TEST")
        repo.upsert_indirizzo.assert_not_called()

    # Scopo: gli id del payload non interi sono un errore di validazione del
    #        dominio, non un 500 da un `int()` grezzo; e non si scrive niente.
    #        Vale anche per l'origine soggetto, che dal 2026-10-12 va al DB
    #        senza piu' passare da un confronto Python.
    def test_id_non_interi_rifiutati(self):
        casi = (
            {"tipo_indirizzo_id": "abc", "snapshot": {"via": "Via Verdi 9"}},
            {"tipo_indirizzo_id": 10, "origine_indirizzo_id": "abc"},
            {"tipo_indirizzo_id": 10, "origine_soggetto_ruolo_id": "abc",
             "snapshot": {"via": "Via Verdi 9"}},
            {"tipo_indirizzo_id": 10, "origine_soggetto_ruolo_id": True,
             "snapshot": {"via": "Via Verdi 9"}},
        )
        for payload in casi:
            with self.subTest(payload=payload):
                repo = self._repo()
                with self.assertRaises(ServiceError) as cm:
                    upsert_indirizzo_documento(self._cfg(repo), 1, payload)
                self.assertEqual(cm.exception.code, "E_TEST")
                repo.upsert_indirizzo.assert_not_called()
