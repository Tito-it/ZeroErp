# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del comando `e_dovuto`, l'`ExecCondition` delle sveglie
#        calendariali: i tre codici d'uscita che systemd legge (0 lavora,
#        1 salta senza errore, 255 guasto). Brief un-solo-fuso-aziendale T-9.
#        Repository e dichiarato finti: nessun DB.
# ------------------------------------------------------------
"""Indice test.

1. test_prima_delle_dalle_aziendali_non_e_dovuto            exit 1
2. test_dopo_le_dalle_senza_corsa_riuscita_e_dovuto          exit 0
3. test_con_una_corsa_riuscita_nel_periodo_e_gia_fatto       exit 1
4. test_una_sveglia_senza_dovuto_lavora_sempre               exit 0
5. test_una_sveglia_sconosciuta_e_un_guasto                  exit 255
6. test_un_guasto_del_db_e_255_non_1                         exit 255  ⭐
7. test_un_commanderror_di_django_e_255_non_1               exit 255  ⭐
8. test_un_argomento_mancante_e_255_non_2                   exit 255
"""

from __future__ import annotations

from datetime import UTC, datetime, time
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase

from apps.core.management.commands import e_dovuto
from apps.core.services.fuso_aziendale import fuso_aziendale_forzato
from apps.core.services.sveglie import Dovuto, Sveglia

_DIGEST = Sveglia(
    unit="zeroerp-digest-presidi-giornaliero", processo_codice="digest_presidi",
    forma="timer", comando=("digest_presidi", "--cadenza", "giornaliera"),
    oncalendar="*:00", abilita=True, avvio_manuale=True, nota="",
    dovuto=Dovuto("giorno", time(7, 0), None, "digest_presidi:giornaliera"),
)
_DRENATORE = Sveglia(
    unit="zeroerp-coda-lavori", processo_codice="draina_coda_lavori", forma="timer",
    comando=("draina_coda_lavori",), oncalendar="*:0/1", abilita=True,
    avvio_manuale=False, nota="",
)


class EDovutoTests(SimpleTestCase):
    """I codici d'uscita dell'ExecCondition."""

    # Scopo: dichiarato finto, fuso dell'azienda a Roma, repository finto.
    def setUp(self) -> None:
        self.enterContext(fuso_aziendale_forzato("Europe/Rome"))
        self.enterContext(patch.object(e_dovuto, "carica_sveglie", return_value=(_DIGEST, _DRENATORE)))
        self.repo = self.enterContext(patch.object(e_dovuto, "MaintenanceRepository")).return_value
        self.repo.corsa_riuscita_dal.return_value = False

    # Scopo: lancia il comando come lo lancia systemd (`run_from_argv`) e
    #        ritorna il codice d'uscita.
    def _esegui(self, unit: str, adesso: datetime) -> int:
        with patch("django.utils.timezone.now", return_value=adesso), \
                self.assertRaises(SystemExit) as ctx:
            e_dovuto.Command().run_from_argv(["manage.py", "e_dovuto", unit])
        return int(ctx.exception.code or 0)

    # 1. Le 06:30 di Roma (04:30 UTC): il giorno aziendale del digest non e' cominciato.
    def test_prima_delle_dalle_aziendali_non_e_dovuto(self) -> None:
        self.assertEqual(self._esegui(_DIGEST.unit, datetime(2026, 9, 14, 4, 30, tzinfo=UTC)), 1)
        self.repo.corsa_riuscita_dal.assert_not_called()

    # 2. Le 07:05 di Roma, nessuna corsa riuscita da oggi alle 07:00: lavora.
    def test_dopo_le_dalle_senza_corsa_riuscita_e_dovuto(self) -> None:
        self.assertEqual(self._esegui(_DIGEST.unit, datetime(2026, 9, 14, 5, 5, tzinfo=UTC)), 0)
        jobname, dal = self.repo.corsa_riuscita_dal.call_args.args
        self.assertEqual(jobname, "digest_presidi:giornaliera")
        self.assertEqual(dal, datetime(2026, 9, 14, 5, 0, tzinfo=UTC))

    # 3. Una corsa riuscita nel periodo: salta (il pulsante «Esegui ora» non passa di qui).
    def test_con_una_corsa_riuscita_nel_periodo_e_gia_fatto(self) -> None:
        self.repo.corsa_riuscita_dal.return_value = True
        self.assertEqual(self._esegui(_DIGEST.unit, datetime(2026, 9, 14, 13, 0, tzinfo=UTC)), 1)

    # 4. Una sveglia non calendariale lavora a ogni sveglia.
    def test_una_sveglia_senza_dovuto_lavora_sempre(self) -> None:
        self.assertEqual(self._esegui(_DRENATORE.unit, datetime(2026, 9, 14, 4, 30, tzinfo=UTC)), 0)

    # 5. Un refuso nella unit dell'ExecCondition e' un guasto, non un «salta».
    def test_una_sveglia_sconosciuta_e_un_guasto(self) -> None:
        self.assertEqual(self._esegui("zeroerp-refuso", datetime(2026, 9, 14, 9, 0, tzinfo=UTC)), 255)

    # 6. ⭐ Un guasto del DB esce 255: con l'uscita di default di Python (1)
    #    systemd salterebbe il lavoro in silenzio.
    def test_un_guasto_del_db_e_255_non_1(self) -> None:
        self.repo.corsa_riuscita_dal.side_effect = RuntimeError("DB giu'")
        self.assertEqual(self._esegui(_DIGEST.unit, datetime(2026, 9, 14, 9, 0, tzinfo=UTC)), 255)
        # E `call_command` (la strada dei test, non di systemd) propaga il guasto.
        with self.assertRaises(RuntimeError):
            with patch("django.utils.timezone.now", return_value=datetime(2026, 9, 14, 9, 0, tzinfo=UTC)):
                call_command("e_dovuto", _DIGEST.unit)

    # 7. ⭐ Django converte un `CommandError` (per esempio i system check) in
    #    `sys.exit(1)`: per systemd sarebbe un «salta» silenzioso.
    def test_un_commanderror_di_django_e_255_non_1(self) -> None:
        with patch.object(e_dovuto.Command, "handle", side_effect=CommandError("check falliti")):
            self.assertEqual(self._esegui(_DIGEST.unit, datetime(2026, 9, 14, 9, 0, tzinfo=UTC)), 255)

    # 8. Un'`ExecCondition=` senza la unit: argparse uscirebbe 2, cioe' «salta».
    def test_un_argomento_mancante_e_255_non_2(self) -> None:
        with patch("django.utils.timezone.now", return_value=datetime(2026, 9, 14, 9, 0, tzinfo=UTC)), \
                patch("sys.stderr"), self.assertRaises(SystemExit) as ctx:
            e_dovuto.Command().run_from_argv(["manage.py", "e_dovuto"])
        self.assertEqual(ctx.exception.code, 255)
