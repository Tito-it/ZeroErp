# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit del BB `giro_per_azienda` e del giro per azienda del
#        drenatore della coda lavori (`draina_coda_lavori_per_roster`, BE10).
#        Mock-only: roster e identità finti; l'identità vera la provano i test
#        `db/test_identita_annidata_db.py`.
#
# Indice test:
#   1. ogni lavoro gira DENTRO l'identità del suo badge, emittente congelato
#   2. un'azienda che fallisce non ferma le altre, e finisce in `falliti`
#   3. le aziende senza utente tecnico finiscono in `non_serviti`
#   4. roster vuoto: nessun lavoro, e l'esito lo dice
#   5. drenatore: un giro per badge, totali sommati, UN repository per tutti
#   6. drenatore: roster vuoto = niente drenato, `roster_vuoto` nell'esito
# ------------------------------------------------------------

from __future__ import annotations

from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.coda_lavori.drainer_service import (
    draina_coda_lavori_per_roster,
)
from apps.core.services.giro_per_azienda import giro_per_azienda

_BB = "apps.core.services.giro_per_azienda"
_DRAIN = "apps.core.services.coda_lavori.drainer_service"


def _badge(codice: str, n: int) -> dict:
    return {
        "auth_user_id": n, "username": f"processo@{codice}", "identita_id": n * 10,
        "emittente_fiscale_id": n * 100, "emittente_codice": codice,
        "emittente_soggetto_ruolo_id": None,
    }


def _processi(roster, non_serviti=()) -> MagicMock:
    repo = MagicMock()
    repo.roster_processo.return_value = list(roster)
    repo.emittenti_non_serviti.return_value = [
        {"emittente_fiscale_id": 1, "emittente_codice": c} for c in non_serviti
    ]
    return repo


class _IdentitaFinta:
    """Registra quale identità è aperta, e con quali argomenti."""

    def __init__(self, falliscono: set[str] = frozenset()) -> None:
        self.corrente: str | None = None
        self.aperte: list[dict] = []
        self._falliscono = falliscono

    @contextmanager
    def __call__(self, auth_user_id, *, username, identita_id, emittente_attivo_id):
        if username in self._falliscono:
            raise RuntimeError("identita' spenta")
        self.aperte.append({
            "auth_user_id": auth_user_id, "username": username,
            "identita_id": identita_id, "emittente_attivo_id": emittente_attivo_id,
        })
        self.corrente = username
        try:
            yield
        finally:
            self.corrente = None


class GiroPerAziendaTests(TestCase):

    # 1. ⭐ Il lavoro vede l'identità del suo badge, e l'emittente attivo è il
    #    suo: senza, girerebbe in modalità globale.
    def test_lavoro_dentro_l_identita_del_badge(self) -> None:
        identita = _IdentitaFinta()
        visti: list[str | None] = []
        with patch(f"{_BB}.operator_identity_context", identita):
            esito = giro_per_azienda(
                "p", lambda b: visti.append(identita.corrente) or b["emittente_codice"],
                evento="t", processi_repo=_processi([_badge("ACME", 1), _badge("BETA", 2)]),
            )
        self.assertEqual(visti, ["processo@ACME", "processo@BETA"])
        self.assertEqual(identita.aperte[0], {
            "auth_user_id": 1, "username": "processo@ACME", "identita_id": 10,
            "emittente_attivo_id": 100,
        })
        self.assertEqual([r for _b, r in esito.serviti], ["ACME", "BETA"])
        self.assertEqual(esito.falliti, [])
        self.assertFalse(esito.roster_vuoto)

    # 2. ⛔ ACME non parte: BETA è servita lo stesso, e la callback sente tutti.
    def test_un_azienda_fallita_non_ferma_le_altre(self) -> None:
        identita = _IdentitaFinta(falliscono={"processo@ACME"})
        sentiti: list[tuple[str, bool]] = []
        with patch(f"{_BB}.operator_identity_context", identita):
            esito = giro_per_azienda(
                "p", lambda b: 1, evento="t",
                on_badge=lambda b, r, e: sentiti.append((b["emittente_codice"], e is None)),
                processi_repo=_processi([_badge("ACME", 1), _badge("BETA", 2)]),
            )
        self.assertEqual([b["emittente_codice"] for b, _r in esito.serviti], ["BETA"])
        self.assertEqual(esito.falliti, [{"emittente_codice": "ACME", "errore": "identita' spenta"}])
        self.assertEqual(sentiti, [("ACME", False), ("BETA", True)])

    # 3. Le aziende senza badge: il numero che rompe il silenzio.
    def test_non_serviti(self) -> None:
        with patch(f"{_BB}.operator_identity_context", _IdentitaFinta()):
            esito = giro_per_azienda(
                "p", lambda b: 1, evento="t",
                processi_repo=_processi([_badge("ACME", 1)], non_serviti=["GAMMA"]),
            )
        self.assertEqual(esito.non_serviti, ["GAMMA"])

    # 4. Roster vuoto: nessun lavoro, e l'esito lo dice.
    def test_roster_vuoto(self) -> None:
        lavoro = MagicMock()
        esito = giro_per_azienda(
            "p", lavoro, evento="t", processi_repo=_processi([], non_serviti=["ACME"]),
        )
        lavoro.assert_not_called()
        self.assertTrue(esito.roster_vuoto)
        self.assertEqual(esito.non_serviti, ["ACME"])


class DrenatoreCodaLavoriPerAziendaTests(TestCase):

    # 5. ⭐ BE10 (b): un giro del motore per badge, dentro la sua identità; i
    #    totali sommati; lo STESSO repository per tutti (il `job_run_id` del
    #    claim e quello della `mark_*` devono essere uguali).
    def test_un_giro_per_badge(self) -> None:
        identita = _IdentitaFinta()
        backend = MagicMock()
        visti: list[tuple[str | None, object]] = []

        def _drena(**kwargs):
            visti.append((identita.corrente, kwargs["backend"]))
            return {"recuperate": 1, "claimate": 2, "fatto": 2, "errore": 0, "riprovabili": 0}

        with patch(f"{_BB}.operator_identity_context", identita), \
                patch(f"{_DRAIN}.draina_coda_lavori", side_effect=_drena):
            esito = draina_coda_lavori_per_roster(
                backend=backend,
                processi_repo=_processi([_badge("ACME", 1), _badge("BETA", 2)], non_serviti=["GAMMA"]),
            )
        self.assertEqual(visti, [("processo@ACME", backend), ("processo@BETA", backend)])
        self.assertEqual(esito["claimate"], 4)
        self.assertEqual(esito["recuperate"], 2)
        self.assertEqual(esito["emittenti_serviti"], 2)
        self.assertEqual(esito["emittenti_non_serviti"], ["GAMMA"])
        self.assertFalse(esito["roster_vuoto"])
        self.assertEqual(
            [e["emittente_codice"] for e in esito["per_emittente"]], ["ACME", "BETA"],
        )

    # 6. ⚠️ Senza utenti tecnici non si drena niente, nemmeno i lavori SISTEMA
    #    (li vede solo un utente tecnico del drenatore): l'esito lo dice.
    def test_roster_vuoto_niente_drenato(self) -> None:
        with patch(f"{_DRAIN}.draina_coda_lavori") as core:
            esito = draina_coda_lavori_per_roster(
                backend=MagicMock(), processi_repo=_processi([], non_serviti=["ACME"]),
            )
        core.assert_not_called()
        self.assertTrue(esito["roster_vuoto"])
        self.assertEqual(esito["claimate"], 0)
        self.assertEqual(esito["emittenti_non_serviti"], ["ACME"])
