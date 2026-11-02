# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il vocabolario di `config.email_log.stato` specchiato nel backend
#        (`STATI_EMAIL_LOG`, `core/services/email_constants.py`) deve seguire il
#        `CHECK` che lo possiede. ⚠️ Fino al 2026-09-26 il vocabolario (e questo
#        test) stavano in `amm_software`: scesi in `core` quando la lista del log
#        si e' aperta a ogni operatore.
#
# ⛔ PERCHE' MANCAVA E PERCHE' CONTA. Quel `frozenset` alimenta il lookup che il
#    frontend usa per filtrare il giornale delle email (`EmailLogStatoSelect`),
#    e fino al 2026-09-11 NIENTE lo confrontava col database: un valore in meno
#    qui e' uno stato che esiste nel giornale e che nessuno puo' filtrare —
#    righe che ci sono e non si vedono, senza che niente fallisca. Un valore in
#    piu' e' una voce di filtro che non trova mai nulla.
#
# ⭐ E SERVE ADESSO, non un giorno. E' aperta la richiesta al team DB di
#    aggiungere lo stato di chi e' stato STAMPATO A VIDEO invece che spedito
#    (`brief-db-stato-email-console-non-e-inviata.md`): il giorno dell'apply
#    questo test diventa rosso e dice di allineare il backend — che e' lo stesso
#    verso di ritiro che ha funzionato per il debito del catalogo dei presidi.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#    NON SCRIVE NULLA.
# ------------------------------------------------------------

"""Indice test previsti (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_il_mirror_degli_stati_segue_il_check
2. test_ogni_stato_ammesso_ha_la_sua_descrizione
"""

from __future__ import annotations

from unittest import TestCase

from apps.core.services.email_constants import (
    STATI_EMAIL_LOG,
    STATI_EMAIL_LOG_DESCRIZIONI,
)
from apps.core.tests.db_e2e import richiedi_db_provvisto, valori_check


class EmailLogStatiGuardrail(TestCase):
    """Il mirror del vocabolario contro il CHECK che lo possiede."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # 1. ⛔ Il confronto e' di UGUAGLIANZA, non di inclusione: un valore in piu'
    #    nel backend e' una voce di filtro che il database non produrra' mai, e
    #    sembra coperta.
    def test_il_mirror_degli_stati_segue_il_check(self) -> None:
        self.assertEqual(
            set(STATI_EMAIL_LOG),
            valori_check("config.email_log", "chk_email_log_stato"),
            "il vocabolario degli stati email nel backend non segue il CHECK del "
            "database: allineare `STATI_EMAIL_LOG_DESCRIZIONI` in "
            "apps/core/services/email_constants.py.",
        )

    # 2. ⚠️ La descrizione e' cio' che l'operatore LEGGE nel filtro: uno stato
    #    ammesso e senza frase esce dal select come codice grezzo, o non esce.
    #    Il test gemello senza DB (`test_email_log_stati_lookup`) confronta
    #    le descrizioni col mirror; qui il mirror e' gia' quello del database,
    #    quindi la catena si chiude fino al CHECK.
    def test_ogni_stato_ammesso_ha_la_sua_descrizione(self) -> None:
        descritti = {codice for codice, _testo, _ordine in STATI_EMAIL_LOG_DESCRIZIONI}
        dal_database = valori_check("config.email_log", "chk_email_log_stato")
        self.assertEqual(
            descritti, dal_database,
            "uno stato ammesso dal database non ha una descrizione, o ne ha una "
            "che il database non ammette.",
        )
