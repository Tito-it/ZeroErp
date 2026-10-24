# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del management command `run_fatturazione_batch` — che dal
#        2026-09-05 e' un PRODUTTORE, non piu' un esecutore.
#
# ⭐ Riscritti insieme al comando. I test vecchi verificavano che il batch
#    FATTURASSE (una corsa sola, dentro il canale `BYPASSRLS`, un lotto per
#    coppia): quelle cose non le fa piu' nessuno qui. Il comando adesso accoda un
#    lavoro per azienda servita, e il lavoro lo esegue la coda con l'identita'
#    dell'utente tecnico di quell'azienda.
# ⛔ Il pezzo che il test vecchio presidiava e che NON si perde e' l'anti-overlap
#    (lock per corsia) e la registrazione del run: restano, e sono qui.
#
# Indice test:
#   1) accoda UN lavoro per ogni badge del roster, con la corsia nel payload
#   2) ⭐ la CORSIA e' nella chiave di dedup — senza, immediata e differita dello
#      stesso mese/azienda sarebbero lo stesso lavoro e una sparirebbe in silenzio
#   3) ⛔ NIENTE canale di sistema: il gateway BYPASSRLS non esiste piu' qui
#   4) le aziende senza utente tecnico finiscono a video, non nel silenzio
#   5) registrazione run-level: attore, lock per corsia, meta
#   6) skip anti-overlap: lock occupato → non si accoda niente
#   7) un accodamento fallito non ferma gli altri, e la corsa chiude rossa
#      con E_JOB_ELEMENTI_NON_COMPLETATI (D9) dopo aver scritto il meta
# ------------------------------------------------------------

from __future__ import annotations

from io import StringIO
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.core.management import call_command

from apps.core.services.job_run import E_JOB_ELEMENTI_NON_COMPLETATI
from apps.core.services.service_errors import ServiceError
from apps.core.tests.job_run_fakes import fake_registered_job

_CMD = "apps.vendite.management.commands.run_fatturazione_batch"
_PROD = "apps.vendite.services.fatturazione_produttore_service"


# Scopo: un badge del roster, nella forma che `ProcessiRepository` consegna.
def _badge(codice: str, *, auth_user_id: int, emittente_id: int) -> dict:
    return {
        "auth_user_id": auth_user_id,
        "username": f"run_fatturazione_batch@{codice}",
        "identita_id": auth_user_id * 10,
        "emittente_fiscale_id": emittente_id,
        "emittente_codice": codice,
        "emittente_soggetto_ruolo_id": emittente_id * 100,
    }


# Scopo: monta i due repository del produttore con un roster dato.
def _patch_produttore(roster, *, non_serviti=(), accoda=None):
    processi = MagicMock()
    processi.roster_processo.return_value = list(roster)
    processi.emittenti_non_serviti.return_value = [
        {"emittente_fiscale_id": 99, "emittente_codice": c} for c in non_serviti
    ]
    coda = MagicMock()
    coda.accoda.side_effect = accoda or (lambda **_kw: 4242)
    return (
        patch(f"{_PROD}.ProcessiRepository", return_value=processi),
        patch(f"{_PROD}.CodaLavoriRepository", return_value=coda),
        processi,
        coda,
    )


class RunFatturazioneBatchProduttoreTests(TestCase):

    # 1. Un lavoro per badge, con la corsia nel payload.
    def test_accoda_un_lavoro_per_azienda(self):
        cm, _h, _catturato = fake_registered_job()
        p_proc, p_coda, _proc, coda = _patch_produttore([
            _badge("ACME", auth_user_id=7, emittente_id=3),
            _badge("BETA", auth_user_id=8, emittente_id=4),
        ])
        with p_proc, p_coda, patch(f"{_CMD}.registered_job", cm):
            call_command(
                "run_fatturazione_batch", "--modalita", "differita",
                "--competenza", "2026-06-15", stdout=StringIO(),
            )

        self.assertEqual(coda.accoda.call_count, 2)
        primo = coda.accoda.call_args_list[0].kwargs
        self.assertEqual(primo["job_type"], "FATTURAZIONE_GIRO")
        self.assertEqual(primo["run_as"], "OPERATORE")
        # La competenza e' normalizzata al 1° del mese.
        self.assertEqual(primo["payload"]["competenza_mese"], "2026-06-01")
        # ⭐ La corsia viaggia nel payload: l'handler la legge da li' invece di
        #    dedurla, cosi' cio' che e' stato deduplicato e cio' che verra'
        #    eseguito sono la stessa cosa.
        self.assertEqual(primo["payload"]["modalita"], "differita")
        # Lo scope porta l'identita' COMPLETA dell'utente tecnico: senza,
        # `operator_identity_context` rifiuta il job a meta' strada.
        self.assertEqual(primo["scope"]["auth_user_id"], 7)
        self.assertEqual(primo["scope"]["username"], "run_fatturazione_batch@ACME")
        self.assertEqual(primo["scope"]["identita_id"], 70)
        self.assertEqual(primo["scope"]["emittente_attivo_id"], 3)

    # 2. ⭐ La corsia e' nella chiave: e' il difetto che il lotto 3 chiude.
    def test_la_corsia_distingue_la_chiave_di_dedup(self):
        chiavi = {}
        for modalita in ("immediata", "differita"):
            cm, _h, _catturato = fake_registered_job()
            p_proc, p_coda, _proc, coda = _patch_produttore([
                _badge("ACME", auth_user_id=7, emittente_id=3),
            ])
            with p_proc, p_coda, patch(f"{_CMD}.registered_job", cm):
                call_command(
                    "run_fatturazione_batch", "--modalita", modalita,
                    "--competenza", "2026-06-01", stdout=StringIO(),
                )
            chiavi[modalita] = coda.accoda.call_args.kwargs["idempotency_key"]

        self.assertNotEqual(
            chiavi["immediata"], chiavi["differita"],
            "Le due corsie hanno la stessa chiave di dedup: la seconda verrebbe "
            "scartata in silenzio e quella corsia non fatturerebbe.",
        )
        self.assertIn("immediata", chiavi["immediata"])
        self.assertIn("differita", chiavi["differita"])

    # 3. ⛔ Nessun canale di sistema.
    def test_nessun_canale_di_sistema(self):
        import apps.vendite.management.commands.run_fatturazione_batch as modulo

        self.assertFalse(hasattr(modulo, "system_process_context"))
        self.assertFalse(hasattr(modulo, "SYSTEM_FATTURAZIONE_DB_ALIAS"))

    # 4. Le aziende scoperte si vedono: «2 accodati» da solo sembrerebbe completo.
    def test_aziende_non_servite_finiscono_a_video(self):
        cm, _h, _catturato = fake_registered_job()
        p_proc, p_coda, _proc, _coda = _patch_produttore(
            [_badge("ACME", auth_user_id=7, emittente_id=3)],
            non_serviti=("BETA", "GAMMA"),
        )
        err = StringIO()
        with p_proc, p_coda, patch(f"{_CMD}.registered_job", cm):
            call_command(
                "run_fatturazione_batch", "--modalita", "differita",
                stdout=StringIO(), stderr=err,
            )

        testo = err.getvalue()
        self.assertIn("BETA", testo)
        self.assertIn("GAMMA", testo)
        self.assertIn("senza utente tecnico", testo)

    # 5. Attore, lock per corsia, meta.
    def test_registra_il_run_con_attore_e_lock_per_corsia(self):
        # ⭐ Stessa fabbrica degli altri test: `catturato` porta gia' job_id e
        #    kwargs, quindi non serve un secondo context manager scritto a mano.
        cm, handle, catturato = fake_registered_job()

        p_proc, p_coda, _proc, _coda = _patch_produttore([
            _badge("ACME", auth_user_id=7, emittente_id=3),
        ])
        with p_proc, p_coda, patch(f"{_CMD}.registered_job", cm):
            call_command(
                "run_fatturazione_batch", "--modalita", "immediata",
                stdout=StringIO(),
            )

        # ⚠️ Il jobname porta la CORSIA, il codice processo no: sono due cose
        #    diverse, ed e' il motivo per cui il BB non deriva l'attore dal nome.
        self.assertEqual(catturato["job_id"], "run_fatturazione_batch:immediata")
        self.assertEqual(catturato["kwargs"]["lock_key"], "run_fatturazione_batch:immediata")
        self.assertEqual(
            catturato["kwargs"]["processo_codice"], "run_fatturazione_batch",
        )
        handle.set_rows_affected.assert_called_once_with(1)

    # 6. Lock occupato → non si accoda niente.
    def test_skip_su_lock_occupato(self):
        cm, _h, _catturato = fake_registered_job(acquired=False)
        p_proc, p_coda, _proc, coda = _patch_produttore([
            _badge("ACME", auth_user_id=7, emittente_id=3),
        ])
        out = StringIO()
        with p_proc, p_coda, patch(f"{_CMD}.registered_job", cm):
            call_command(
                "run_fatturazione_batch", "--modalita", "differita", stdout=out,
            )

        coda.accoda.assert_not_called()
        self.assertIn("skip", out.getvalue())

    # 7. ⭐ Un'azienda che fallisce non porta via le altre: il loro lavoro e' gia'
    #    buono, e buttarlo sarebbe peggio del difetto.
    def test_un_accodamento_fallito_non_ferma_gli_altri(self):
        def _accoda(**kwargs):
            if kwargs["scope"]["emittente_attivo_id"] == 3:
                raise RuntimeError("coda irraggiungibile")
            return 99

        cm, handle, _catturato = fake_registered_job()
        p_proc, p_coda, _proc, coda = _patch_produttore(
            [
                _badge("ACME", auth_user_id=7, emittente_id=3),
                _badge("BETA", auth_user_id=8, emittente_id=4),
            ],
            accoda=_accoda,
        )
        err = StringIO()
        with p_proc, p_coda, patch(f"{_CMD}.registered_job", cm):
            # ⭐ D9: l'azienda non accodata non lascia una riga in coda, quindi
            #    la corsa chiude rossa — DOPO aver accodato l'altra.
            with self.assertRaises(ServiceError) as ctx:
                call_command(
                    "run_fatturazione_batch", "--modalita", "differita",
                    stdout=StringIO(), stderr=err,
                )

        self.assertEqual(ctx.exception.code, E_JOB_ELEMENTI_NON_COMPLETATI)
        self.assertIn("ACME", ctx.exception.detail or "")
        self.assertEqual(coda.accoda.call_count, 2)
        self.assertIn("ACME", err.getvalue())
        # Il meta col dettaglio e' scritto PRIMA del rosso: arriva al giornale.
        meta = handle.set_meta.call_args.args[0]
        self.assertEqual([f["emittente_codice"] for f in meta["falliti"]], ["ACME"])
