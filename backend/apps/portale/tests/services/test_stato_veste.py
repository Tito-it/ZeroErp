# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari di `stato_veste`, lo stato accessi di una veste che
#        esiste. ⭐ Il caso NON_SPEDITO si COSTRUISCE qui (link pendente,
#        email mai partita dopo la sua emissione): i dati di oggi non lo
#        contengono, perche' fino al 2026-09-28 `invito_inviato_at` si
#        scriveva anche a email fallita (F-3). Funzione pura: niente DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) StatoVesteTests.test_attiva_vince_su_tutto
2) StatoVesteTests.test_senza_token_pendente_e_disattivo
3) StatoVesteTests.test_email_partita_dopo_il_token_e_pending
4) StatoVesteTests.test_email_mai_partita_e_non_spedito
5) StatoVesteTests.test_email_di_un_invito_precedente_non_conta
6) StatoVesteTests.test_stesso_istante_e_pending
"""

from datetime import datetime, timedelta, timezone
from unittest import TestCase

from apps.portale.db.portale_repository import stato_veste

_T0 = datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc)
_SCADE = _T0 + timedelta(hours=72)


class StatoVesteTests(TestCase):

    # Scopo: Una veste accesa e' ATTIVO, qualunque cosa dica il token.
    def test_attiva_vince_su_tutto(self):
        self.assertEqual(
            stato_veste(attivo=True, token_scade_at=_SCADE, token_emesso_at=_T0,
                        invito_inviato_at=None),
            "ATTIVO",
        )

    # Scopo: Spenta e senza link pendente: DISATTIVO.
    def test_senza_token_pendente_e_disattivo(self):
        self.assertEqual(
            stato_veste(attivo=False, token_scade_at=None, token_emesso_at=None,
                        invito_inviato_at=_T0),
            "DISATTIVO",
        )

    # Scopo: Link pendente e email partita dopo la sua emissione: PENDING.
    def test_email_partita_dopo_il_token_e_pending(self):
        self.assertEqual(
            stato_veste(attivo=False, token_scade_at=_SCADE, token_emesso_at=_T0,
                        invito_inviato_at=_T0 + timedelta(seconds=2)),
            "PENDING",
        )

    # Scopo: ⭐ Link pendente e nessuna email mai partita: NON_SPEDITO, non
    # «invito inviato».
    def test_email_mai_partita_e_non_spedito(self):
        self.assertEqual(
            stato_veste(attivo=False, token_scade_at=_SCADE, token_emesso_at=_T0,
                        invito_inviato_at=None),
            "NON_SPEDITO",
        )

    # Scopo: ⭐ Un reinvio fallito dopo un invito riuscito: la data del primo
    # e' precedente al link di adesso, e non dice niente di lui.
    def test_email_di_un_invito_precedente_non_conta(self):
        self.assertEqual(
            stato_veste(attivo=False, token_scade_at=_SCADE, token_emesso_at=_T0,
                        invito_inviato_at=_T0 - timedelta(days=1)),
            "NON_SPEDITO",
        )

    # Scopo: Emissione e spedizione nella stessa transazione hanno lo stesso
    # `now()`: e' spedito.
    def test_stesso_istante_e_pending(self):
        self.assertEqual(
            stato_veste(attivo=False, token_scade_at=_SCADE, token_emesso_at=_T0,
                        invito_inviato_at=_T0),
            "PENDING",
        )
