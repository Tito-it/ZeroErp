# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del service di gestione code (brief-be-fe-gestione-
#        code-lavori-stampa, FASE BE). Mock dei repository (nessun DB).
#
# Indice test:
#   1) conteggi_code_scoped_operatore — owner filter = scope_key, worker attivi
#   2) conteggi_code_worker_mai_girato — liveness assente → worker giù
#   3) elenca_coda_lavori_operatore — filtro owner + caller key per is_mio
#   4) elenca_coda_lavori_tutti_richiede_permesso — 403 senza code_manage
#   5) elenca_coda_lavori_tutti_con_permesso — owner filter None
#   6) elenca_coda_stampa_tutti_con_permesso — auth_user_id None
#   7) dettaglio_job_non_trovato_404
#   8) dettaglio_job_admin_code_manage_vede_tutto — owner filter None
#   9) annulla_job_ok
#  10) annulla_job_fuori_scope_404
#  11) annulla_job_non_pending_409
#  12) requeue_job_ok — extra_tentativi propagato
#  13) requeue_job_stato_non_riaccodabile_409
#  14) requeue_job_extra_tentativi_fuori_range_400
#  15) scope_key_da_emittenti — formato canonico (ALL / ordinati)
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.coda_lavori import gestione_service as svc
from apps.core.services.coda_lavori.scope import scope_key_da_emittenti
from apps.core.services.service_errors import ServiceError

_SVC = "apps.core.services.coda_lavori.gestione_service"


# Scopo: patch standard dei collaboratori del service (resolver + repo code +
#        repo maintenance). Ritorna i mock per le assert.
def _patch_all(
    *,
    emittenti=None,
    super_admin=False,
    code_manage=False,
):
    p_resolver = patch(f"{_SVC}.PermissionResolver")
    p_repo = patch(f"{_SVC}.CodaLavoriRepository")
    p_maint = patch(f"{_SVC}.MaintenanceRepository")
    resolver = p_resolver.start()
    repo_cls = p_repo.start()
    maint_cls = p_maint.start()
    resolver.get_emittenti_ids.return_value = emittenti
    resolver.is_super_admin.return_value = super_admin
    resolver.check_azione.return_value = code_manage
    return (p_resolver, p_repo, p_maint), resolver, repo_cls, maint_cls


class ConteggiCodeTests(SimpleTestCase):

    # 1. Operatore scoped: coda lavori filtrata per scope_key, coda stampa per
    #    auth_user_id; worker con run recente → attivo.
    def test_conteggi_code_scoped_operatore(self) -> None:
        patches, _resolver, repo_cls, maint_cls = _patch_all(emittenti=[4, 3])
        try:
            repo_cls.return_value.count_per_stato.return_value = {
                "PENDING": 2, "IN_CORSO": 1, "FATTO": 9,
            }
            maint_cls.return_value.job_liveness.return_value = {
                "draina_coda_lavori": {
                    "last_run_at": "2026-07-21 22:00:00+02", "attivo": True,
                    "last_ok": True,
                },
            }
            with patch(
                "apps.vendite.db.pipeline_repository.VenditePipelineRepository"
            ) as pipe_cls:
                pipe_cls.return_value.count_coda_stampa_per_stato.return_value = {
                    "PENDING": 5,
                }
                esito = svc.conteggi_code(MagicMock(), auth_user_id=9)
                pipe_cls.return_value.count_coda_stampa_per_stato\
                    .assert_called_once_with(auth_user_id=9)
        finally:
            for p in patches:
                p.stop()

        repo_cls.return_value.count_per_stato.assert_called_once_with(
            owner_scope_key="3,4",
        )
        self.assertEqual(esito["coda_lavori"], {"pending": 2, "in_corso": 1})
        self.assertEqual(esito["coda_stampa"], {"pending": 5, "in_corso": 0})
        self.assertTrue(esito["worker"]["coda_lavori"]["attivo"])

    # 2. Worker MAI girato (assente da job_run_log) → blocco "giù" esplicito
    #    (fail-visible), non una chiave mancante.
    def test_conteggi_code_worker_mai_girato(self) -> None:
        patches, _resolver, repo_cls, maint_cls = _patch_all(emittenti=None)
        try:
            repo_cls.return_value.count_per_stato.return_value = {}
            maint_cls.return_value.job_liveness.return_value = {}
            with patch(
                "apps.vendite.db.pipeline_repository.VenditePipelineRepository"
            ) as pipe_cls:
                pipe_cls.return_value.count_coda_stampa_per_stato.return_value = {}
                esito = svc.conteggi_code(MagicMock(), auth_user_id=None)
        finally:
            for p in patches:
                p.stop()

        # Admin globale (whitelist None) → nessun filtro sulla coda lavori.
        repo_cls.return_value.count_per_stato.assert_called_once_with(
            owner_scope_key=None,
        )
        self.assertEqual(
            esito["worker"]["coda_stampa"],
            {"last_run_at": None, "attivo": False, "last_ok": None},
        )


class ElencaCodaLavoriTests(SimpleTestCase):

    # 3. Operatore: righe filtrate per la propria scope_key, caller key per is_mio.
    def test_elenca_coda_lavori_operatore(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(emittenti=[7])
        try:
            repo_cls.return_value.elenca.return_value = {
                "items": [{"id": 1, "is_mio": True}], "total": 1,
            }
            esito = svc.elenca_coda_lavori(MagicMock(), stato="ERRORE", limit=10)
        finally:
            for p in patches:
                p.stop()

        kwargs = repo_cls.return_value.elenca.call_args.kwargs
        self.assertEqual(kwargs["owner_scope_key"], "7")
        self.assertEqual(kwargs["caller_scope_key"], "7")
        self.assertEqual(kwargs["stati"], ["ERRORE"])
        self.assertEqual(esito, {"count": 1, "results": [{"id": 1, "is_mio": True}]})

    # 4. `tutti` senza code_manage/SUPER_ADMIN → 403 parlante, repo non chiamato.
    def test_elenca_coda_lavori_tutti_richiede_permesso(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(emittenti=[7])
        try:
            with self.assertRaises(ServiceError) as ctx:
                svc.elenca_coda_lavori(MagicMock(), tutti=True)
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(ctx.exception.code, "E_PERMESSO_NEGATO")
        repo_cls.return_value.elenca.assert_not_called()

    # 5. `tutti` con code_manage → owner filter None, caller key resta (is_mio).
    def test_elenca_coda_lavori_tutti_con_permesso(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(
            emittenti=[7], code_manage=True,
        )
        try:
            repo_cls.return_value.elenca.return_value = {"items": [], "total": 0}
            svc.elenca_coda_lavori(MagicMock(), tutti=True)
        finally:
            for p in patches:
                p.stop()
        kwargs = repo_cls.return_value.elenca.call_args.kwargs
        self.assertIsNone(kwargs["owner_scope_key"])
        self.assertEqual(kwargs["caller_scope_key"], "7")


class ElencaCodaStampaTests(SimpleTestCase):

    # 6. `tutti` con code_manage → auth_user_id None al repo (nessuno scope).
    def test_elenca_coda_stampa_tutti_con_permesso(self) -> None:
        patches, _resolver, _repo, _maint = _patch_all(
            emittenti=[7], code_manage=True,
        )
        try:
            with patch(
                "apps.vendite.db.pipeline_repository.VenditePipelineRepository"
            ) as pipe_cls:
                pipe_cls.return_value.elenca_coda_stampa.return_value = {
                    "items": [], "total": 0,
                }
                svc.elenca_coda_stampa(MagicMock(), auth_user_id=9, tutti=True)
                kwargs = pipe_cls.return_value.elenca_coda_stampa.call_args.kwargs
        finally:
            for p in patches:
                p.stop()
        self.assertIsNone(kwargs["auth_user_id"])


class DettaglioJobTests(SimpleTestCase):

    # 7. Job inesistente/fuori scope → 404 unificato.
    def test_dettaglio_job_non_trovato_404(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(emittenti=[7])
        try:
            repo_cls.return_value.get_dettaglio.return_value = None
            with self.assertRaises(ServiceError) as ctx:
                svc.dettaglio_job(MagicMock(), 999)
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(ctx.exception.code, "E_JOB_NON_TROVATO")

    # 8. Operatore con code_manage → dettaglio senza filtro owner (vede tutto),
    #    caller key preservata per is_mio.
    def test_dettaglio_job_admin_code_manage_vede_tutto(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(
            emittenti=[7], code_manage=True,
        )
        try:
            repo_cls.return_value.get_dettaglio.return_value = {"id": 5}
            esito = svc.dettaglio_job(MagicMock(), 5)
        finally:
            for p in patches:
                p.stop()
        repo_cls.return_value.get_dettaglio.assert_called_once_with(
            5, owner_scope_key=None, caller_scope_key="7",
        )
        self.assertEqual(esito, {"id": 5})


class AzioniJobTests(SimpleTestCase):

    # 9. Annullo di un job PENDING proprio → ANNULLATO.
    def test_annulla_job_ok(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(emittenti=[7])
        try:
            repo_cls.return_value.get_stato.return_value = {"id": 5, "stato": "PENDING"}
            repo_cls.return_value.annulla.return_value = True
            esito = svc.annulla_job(MagicMock(), 5)
        finally:
            for p in patches:
                p.stop()
        repo_cls.return_value.annulla.assert_called_once_with(
            5, owner_scope_key="7",
        )
        self.assertEqual(esito, {"job_id": 5, "stato": "ANNULLATO"})

    # 10. Job fuori scope (get_stato None) → 404, nessun UPDATE.
    def test_annulla_job_fuori_scope_404(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(emittenti=[7])
        try:
            repo_cls.return_value.get_stato.return_value = None
            with self.assertRaises(ServiceError) as ctx:
                svc.annulla_job(MagicMock(), 999)
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(ctx.exception.code, "E_JOB_NON_TROVATO")
        repo_cls.return_value.annulla.assert_not_called()

    # 11. Job non piu' PENDING (claim concorrente) → 409 parlante.
    def test_annulla_job_non_pending_409(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(emittenti=[7])
        try:
            repo_cls.return_value.get_stato.return_value = {"id": 5, "stato": "IN_CORSO"}
            repo_cls.return_value.annulla.return_value = False
            with self.assertRaises(ServiceError) as ctx:
                svc.annulla_job(MagicMock(), 5)
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(ctx.exception.code, "E_JOB_NON_ANNULLABILE")

    # 12. Requeue ok con extra_tentativi propagato al repo.
    def test_requeue_job_ok(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(emittenti=[7])
        try:
            repo_cls.return_value.get_stato.return_value = {"id": 5, "stato": "ERRORE"}
            repo_cls.return_value.requeue.return_value = True
            esito = svc.requeue_job(MagicMock(), 5, extra_tentativi=2)
        finally:
            for p in patches:
                p.stop()
        repo_cls.return_value.requeue.assert_called_once_with(
            5, extra_tentativi=2, owner_scope_key="7",
        )
        self.assertEqual(esito, {"job_id": 5, "stato": "PENDING"})

    # 13. Requeue su stato non riaccodabile (es. FATTO) → 409.
    def test_requeue_job_stato_non_riaccodabile_409(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(emittenti=[7])
        try:
            repo_cls.return_value.get_stato.return_value = {"id": 5, "stato": "FATTO"}
            repo_cls.return_value.requeue.return_value = False
            with self.assertRaises(ServiceError) as ctx:
                svc.requeue_job(MagicMock(), 5)
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(ctx.exception.code, "E_JOB_NON_RIACCODABILE")

    # 14. extra_tentativi fuori range (0 o >10) → 400, nessuna query.
    def test_requeue_job_extra_tentativi_fuori_range_400(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(emittenti=[7])
        try:
            with self.assertRaises(ServiceError) as ctx:
                svc.requeue_job(MagicMock(), 5, extra_tentativi=0)
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
        repo_cls.return_value.get_stato.assert_not_called()


class ScopeKeyTests(SimpleTestCase):

    # 15. Formato canonico: None → ALL; lista → ordinata e joinata.
    def test_scope_key_da_emittenti(self) -> None:
        self.assertEqual(scope_key_da_emittenti(None), "ALL")
        self.assertEqual(scope_key_da_emittenti([4, 3]), "3,4")
        self.assertEqual(scope_key_da_emittenti([]), "")
