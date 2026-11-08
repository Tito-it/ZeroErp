# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit dell'accodamento per azienda dei lavori di fatturazione
#        (BE10 a di brief-db-revisione-dbops): la divisione della selezione e
#        l'insieme delle aziende. Mock-only; il flusso HTTP lo coprono
#        `test_fatturazione_run_api` e `test_fatturazione_numera_api`.
#
# Indice test:
#   1. atto di mese: un lavoro per ogni azienda, perimetro intero
#   2. gruppi divisi per azienda, nell'ordine delle aziende; chi non ha righe
#      non riceve un lavoro
#   3. ⛔ un gruppo con DUE aziende non si indovina: 400
#   3b. ⛔ un gruppo col ruolo NULL (dalla vista) è orfano: 400, mai un 500
#   4. ⛔ nessuna azienda nel perimetro: 403 prima di accodare
#   5. il giro mirato per azienda porta corsia «mirata» e i soli suoi gruppi
#   6. ⭐ lo stato è quello VERO: la dedup restituisce un lavoro IN_CORSO
#   (l'id che chi accoda non vede: `stati_dopo_accodamento`, test del repository)
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.fatturazione_accodamento_service import (
    accoda_per_azienda,
    ripartisci_per_azienda,
)

_ACME = {"emittente_fiscale_id": 3, "codice": "ACME", "soggetto_ruolo_id": 30}
_BETA = {"emittente_fiscale_id": 4, "codice": "BETA", "soggetto_ruolo_id": 40}
_GAMMA = {"emittente_fiscale_id": 5, "codice": "GAMMA", "soggetto_ruolo_id": 50}
_MESE = date(2026, 6, 1)
_SCOPE = "apps.core.services.coda_lavori.scope.EmittenteAttivoRepository"
_SCOPE_OPERATORE = {
    "auth_user_id": 9, "username": "op9", "identita_id": 5,
    "emittente_attivo_id": None, "emittente_ids": [3, 4], "scope_key": "3,4",
}


class RipartisciPerAziendaTests(TestCase):

    # 1. Senza selezione ogni azienda ha il suo lavoro, e il repository non si
    #    interroga nemmeno.
    def test_atto_di_mese(self) -> None:
        repo = MagicMock()
        esito = ripartisci_per_azienda([_ACME, _BETA], competenza=_MESE, repo=repo)
        self.assertEqual(esito, [(_ACME, None, None), (_BETA, None, None)])
        repo.aziende_dei_gruppi.assert_not_called()

    # 2. ⭐ Ogni azienda riceve le sue righe; GAMMA, senza righe, niente.
    def test_gruppi_divisi_per_azienda(self) -> None:
        repo = MagicMock()
        repo.aziende_dei_gruppi.return_value = {"g1": [40], "g2": [30], "g3": [40]}
        esito = ripartisci_per_azienda(
            [_ACME, _BETA, _GAMMA], competenza=_MESE, gruppi=("g1", "g2", "g3"), repo=repo,
        )
        self.assertEqual(esito, [(_ACME, ("g2",), None), (_BETA, ("g1", "g3"), None)])
        repo.aziende_dei_gruppi.assert_called_once_with(
            competenza_mese=_MESE, chiavi=("g1", "g2", "g3"),
        )

    # 3. ⛔ Una riga con due aziende è un difetto da dire, non una scelta.
    def test_gruppo_con_due_aziende_400(self) -> None:
        repo = MagicMock()
        repo.aziende_dei_gruppi.return_value = {"g1": [30, 40]}
        with self.assertRaises(ServiceError) as cm:
            ripartisci_per_azienda([_ACME, _BETA], competenza=_MESE, gruppi=("g1",), repo=repo)
        self.assertEqual(cm.exception.code, "E_VALIDATION_INPUT")
        self.assertIn("g1", str(cm.exception.detail))


    # 3b. ⛔ La vista può dare un ruolo NULL: il gruppo è orfano, 400 parlante.
    #     Anche accanto a un ruolo valido non si sceglie quello: è un'azienda
    #     non attribuibile, non «l'unica che c'è».
    def test_gruppo_con_ruolo_null_400(self) -> None:
        repo = MagicMock()
        repo.aziende_dei_gruppi.return_value = {"g1": [None], "g2": [None, 30]}
        with self.assertRaises(ServiceError) as cm:
            ripartisci_per_azienda(
                [_ACME, _BETA], competenza=_MESE, gruppi=("g1", "g2"), repo=repo,
            )
        self.assertEqual(cm.exception.code, "E_VALIDATION_INPUT")
        self.assertIn("g1", str(cm.exception.detail))
        self.assertIn("g2", str(cm.exception.detail))


class AccodaPerAziendaTests(TestCase):

    # 4. ⛔ Zero aziende: 403 subito, nessun lavoro.
    @patch(_SCOPE, autospec=True)
    def test_nessuna_azienda_403(self, aziende_cls) -> None:
        aziende_cls.return_value.list_selezionabili.return_value = []
        coda = MagicMock()
        with self.assertRaises(ServiceError) as cm:
            accoda_per_azienda(
                {"auth_user_id": 9, "emittente_attivo_id": None},
                job_type="FATTURAZIONE_GIRO", competenza=_MESE, payload={},
                coda_repo=coda,
            )
        self.assertEqual(cm.exception.code, "E_PERMISSION_DENIED")
        coda.accoda.assert_not_called()

    # 5. Il giro mirato di ciascuna azienda: corsia «mirata», i soli suoi
    #    gruppi nel payload, e la chiave con la sua azienda.
    @patch(_SCOPE, autospec=True)
    def test_giro_mirato_per_azienda(self, aziende_cls) -> None:
        aziende_cls.return_value.list_selezionabili.return_value = [_ACME, _BETA]
        vendite = MagicMock()
        vendite.aziende_dei_gruppi.return_value = {"g1": [40], "g2": [30]}
        coda = MagicMock()
        coda.accoda.side_effect = [1, 2]
        coda.stati_dopo_accodamento.return_value = {1: "PENDING", 2: "PENDING"}
        lavori = accoda_per_azienda(
            {"auth_user_id": 9, "username": "op9", "identita_id": 5,
             "emittente_attivo_id": None, "emittente_ids": [3, 4], "scope_key": "3,4"},
            job_type="FATTURAZIONE_GIRO", competenza=_MESE,
            payload={"competenza_mese": "2026-06-01"}, gruppi=("g1", "g2"),
            coda_repo=coda, vendite_repo=vendite,
        )
        self.assertEqual(
            [(lv["emittente_codice"], lv["gruppi"]) for lv in lavori],
            [("ACME", ["g2"]), ("BETA", ["g1"])],
        )
        chiamate = [c.kwargs for c in coda.accoda.call_args_list]
        self.assertEqual([c["payload"]["gruppi"] for c in chiamate], [["g2"], ["g1"]])
        for c, azienda in zip(chiamate, ("3", "4"), strict=True):
            self.assertTrue(c["idempotency_key"].startswith(f"FATTURAZIONE_GIRO:mirata:2026-06-01:{azienda}:"))

    # 6. ⭐ La dedup restituisce l'id di un lavoro già vivo, che può essere
    #    IN_CORSO: la risposta dice quello, non «PENDING» per costruzione.
    @patch(_SCOPE, autospec=True)
    def test_stato_vero_dalla_dedup(self, aziende_cls) -> None:
        aziende_cls.return_value.list_selezionabili.return_value = [_ACME, _BETA]
        coda = MagicMock()
        coda.accoda.side_effect = [1, 2]
        coda.stati_dopo_accodamento.return_value = {1: "IN_CORSO", 2: "PENDING"}
        lavori = accoda_per_azienda(
            _SCOPE_OPERATORE, job_type="FATTURAZIONE_GIRO", competenza=_MESE,
            payload={"competenza_mese": "2026-06-01"}, coda_repo=coda,
        )
        self.assertEqual([lv["stato"] for lv in lavori], ["IN_CORSO", "PENDING"])
        coda.stati_dopo_accodamento.assert_called_once_with([1, 2])
