# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test dell'auto-assegnazione indirizzo di default alla creazione del
#        documento (BB `_indirizzi_documento_helpers`), condivisa da 5 domini:
#        preventivi, offerte, ordini, DDT, contratti.
#
# PERCHE' ESISTE. Fino al 2026-07-31 questo percorso — che gira su OGNI
# creazione di documento in cinque domini — **non aveva un solo test**. È il
# motivo per cui il difetto C-14c (la catena ignorava l'istanza del documento e
# preferiva l'indirizzo generico) è vissuto inosservato: nessuno asseriva quale
# indirizzo venisse scelto.
#
# Il test presidia il CABLAGGIO, non la catena: la catena vive ora in
# `script.fn_resolve_indirizzo_documento` ed è verificata dai pgTAP del team DB
# e dallo smoke `smoke-indirizzi-documento-catena.py`. Qui si asserisce che il
# service la interroghi nel modo giusto — con l'istanza del documento — e che
# usi le origini che riceve.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) AutoAssegnaIndirizzoTests.test_istanza_del_documento_passata_alla_risoluzione ← C-14c
2) AutoAssegnaIndirizzoTests.test_layer_ruolo_upsert_con_origine_indirizzo
3) AutoAssegnaIndirizzoTests.test_layer_soggetto_upsert_senza_origine_indirizzo
4) AutoAssegnaIndirizzoTests.test_priorita_tipi_con_prima_di_fatt
5) AutoAssegnaIndirizzoTests.test_fallback_a_fatt_se_con_non_risolve
6) AutoAssegnaIndirizzoTests.test_nessun_indirizzo_nessun_upsert
7) AutoAssegnaIndirizzoTests.test_slot_default_gia_valorizzato_non_si_tocca
8) AutoAssegnaIndirizzoTests.test_best_effort_non_propaga_eccezioni
9) AutoAssegnaIndirizzoTests.test_soggetto_ruolo_non_risolvibile_esce_senza_scrivere
"""

from unittest import TestCase
from unittest.mock import MagicMock

from apps.vendite.services._indirizzi_documento_helpers import (
    IndirizziDocumentoConfig,
    auto_assegna_indirizzo_default,
)

_TIPI_AMMESSI = [
    {"tipo_indirizzo_id": 10, "tipo_indirizzo_codice": "CON", "obbligatorio": False},
    {"tipo_indirizzo_id": 8, "tipo_indirizzo_codice": "FATT", "obbligatorio": True},
]

_SNAP_RUOLO = {
    "snapshot": {"via": "Via Roma 1", "cap": "20100", "citta": "Milano"},
    "origine_indirizzo_id": 555,
    "origine_soggetto_ruolo_id": 77,
}
_SNAP_SOGGETTO = {
    "snapshot": {"via": "Via Verdi 9", "cap": "10100", "citta": "Torino"},
    "origine_indirizzo_id": None,
    "origine_soggetto_ruolo_id": 77,
}


class AutoAssegnaIndirizzoTests(TestCase):
    """Auto-assegnazione best-effort dell'indirizzo di default.

    Il repo è un mock: l'obiettivo è verificare COME il service usa il
    building block, non cosa risponde il database.
    """

    def _cfg(self, repo):
        return IndirizziDocumentoConfig(
            repo_factory=lambda: repo,
            stati_modificabili=frozenset({"BOZZA"}),
            not_found_code="E_TEST_NOT_FOUND",
            stato_error_code="E_TEST_STATO",
            error_code="E_TEST",
            fn_prefix="vendite.test",
        )

    def _repo(self, *, ancora=(77, 42), risolti=None, esistenti=()):
        repo = MagicMock()
        repo.list_tipi_indirizzo_ammessi.return_value = list(_TIPI_AMMESSI)
        repo.list_indirizzi.return_value = [
            {"tipo_indirizzo_id": t} for t in esistenti
        ]
        repo.get_ancora_indirizzi_documento.return_value = ancora
        # `risolti`: dict {tipo_codice: risultato} — assente ⇒ None (non risolto)
        risolti = risolti or {}
        repo.resolve_indirizzo_documento.side_effect = (
            lambda *, soggetto_ruolo_id, istanza_utility_id, tipo_codice:
            risolti.get(tipo_codice)
        )
        return repo

    # Scopo: ⚠️ IL TEST DI C-14c. L'istanza del documento deve arrivare alla
    #        risoluzione: è ciò che fa scegliere l'indirizzo di QUELLA fornitura
    #        invece del generico. Prima del 2026-07-31 non veniva passata
    #        affatto, e un soggetto con più istanze prendeva l'indirizzo
    #        sbagliato senza che nulla lo segnalasse.
    def test_istanza_del_documento_passata_alla_risoluzione(self):
        repo = self._repo(ancora=(77, 42), risolti={"CON": _SNAP_RUOLO})

        auto_assegna_indirizzo_default(self._cfg(repo), 1)

        repo.resolve_indirizzo_documento.assert_called_once_with(
            soggetto_ruolo_id=77, istanza_utility_id=42, tipo_codice="CON",
        )

    # Scopo: layer RUOLO → l'upsert porta `origine_indirizzo_id` (riga
    #        anagrafica agganciabile) e l'origine soggetto risolta dal DB.
    def test_layer_ruolo_upsert_con_origine_indirizzo(self):
        repo = self._repo(risolti={"CON": _SNAP_RUOLO})

        auto_assegna_indirizzo_default(self._cfg(repo), 1)

        repo.upsert_indirizzo.assert_called_once_with(
            documento_id=1,
            tipo_indirizzo_id=10,
            snapshot=_SNAP_RUOLO["snapshot"],
            origine_indirizzo_id=555,
            origine_soggetto_ruolo_id=77,
        )

    # Scopo: layer SOGGETTO → `origine_indirizzo_id` NULL ma
    #        `origine_soggetto_ruolo_id` valorizzato: è la coppia che distingue
    #        «derivato dall'anagrafica del soggetto» da un una-tantum digitato
    #        (che non ha nessuna delle due origini).
    def test_layer_soggetto_upsert_senza_origine_indirizzo(self):
        repo = self._repo(risolti={"CON": _SNAP_SOGGETTO})

        auto_assegna_indirizzo_default(self._cfg(repo), 1)

        kwargs = repo.upsert_indirizzo.call_args.kwargs
        self.assertIsNone(kwargs["origine_indirizzo_id"])
        self.assertEqual(kwargs["origine_soggetto_ruolo_id"], 77)

    # Scopo: priorità di tipo (regola UX): se CON risolve, FATT non si chiede.
    def test_priorita_tipi_con_prima_di_fatt(self):
        repo = self._repo(risolti={"CON": _SNAP_RUOLO, "FATT": _SNAP_SOGGETTO})

        auto_assegna_indirizzo_default(self._cfg(repo), 1)

        self.assertEqual(repo.resolve_indirizzo_documento.call_count, 1)
        self.assertEqual(
            repo.upsert_indirizzo.call_args.kwargs["snapshot"],
            _SNAP_RUOLO["snapshot"],
        )

    # Scopo: se CON non risolve si prova FATT — ma lo slot scritto resta quello
    #        di DEFAULT dell'ambito (qui CON, id 10): il tipo cercato in
    #        anagrafica e lo slot di destinazione sono cose diverse.
    def test_fallback_a_fatt_se_con_non_risolve(self):
        repo = self._repo(risolti={"FATT": _SNAP_RUOLO})

        auto_assegna_indirizzo_default(self._cfg(repo), 1)

        self.assertEqual(repo.resolve_indirizzo_documento.call_count, 2)
        self.assertEqual(repo.upsert_indirizzo.call_args.kwargs["tipo_indirizzo_id"], 10)

    # Scopo: nessuna fonte → nessuna scrittura. Il documento nasce senza
    #        indirizzo e l'obbligo lo impone il guard DB all'emissione.
    def test_nessun_indirizzo_nessun_upsert(self):
        repo = self._repo(risolti={})

        auto_assegna_indirizzo_default(self._cfg(repo), 1)

        repo.upsert_indirizzo.assert_not_called()

    # Scopo: slot default già valorizzato (es. cascata dal documento sorgente):
    #        non si tocca, e non si interroga nemmeno l'anagrafica.
    def test_slot_default_gia_valorizzato_non_si_tocca(self):
        repo = self._repo(risolti={"CON": _SNAP_RUOLO}, esistenti=(10,))

        auto_assegna_indirizzo_default(self._cfg(repo), 1)

        repo.resolve_indirizzo_documento.assert_not_called()
        repo.upsert_indirizzo.assert_not_called()

    # Scopo: BEST-EFFORT. Un errore qui non deve impedire la creazione del
    #        documento: si logga e si prosegue. È la politica dei 5 domini
    #        interattivi — diversa da quella del task fattura, che è fail-loud.
    def test_best_effort_non_propaga_eccezioni(self):
        repo = self._repo()
        repo.resolve_indirizzo_documento.side_effect = RuntimeError("DB giù")

        auto_assegna_indirizzo_default(self._cfg(repo), 1)  # non solleva

        repo.upsert_indirizzo.assert_not_called()

    # Scopo: documento senza soggetto_ruolo risolvibile → si esce prima di
    #        interrogare l'anagrafica (niente query inutili, niente scritture).
    def test_soggetto_ruolo_non_risolvibile_esce_senza_scrivere(self):
        repo = self._repo(ancora=(None, None))

        auto_assegna_indirizzo_default(self._cfg(repo), 1)

        repo.resolve_indirizzo_documento.assert_not_called()
        repo.upsert_indirizzo.assert_not_called()
