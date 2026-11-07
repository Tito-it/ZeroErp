# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del service di gestione code (brief-be-fe-gestione-
#        code-lavori-stampa, FASE BE). Mock dei repository (nessun DB).
#
# Indice test:
#   1) conteggi_code_scoped_operatore — owner filter = aziende del perimetro, worker attivi
#   2) conteggi_code_worker_mai_girato — liveness assente → worker giù
#   3) elenca_coda_lavori_operatore — filtro owner + perimetro del chiamante per is_mio
#   4) elenca_coda_lavori_tutti_aperto_senza_permesso — visibilità libera
#   5) elenca_coda_lavori_tutti_con_permesso — owner filter None
#   6) elenca_coda_stampa_ambito_per_operatore — miei=user_insert, tutti=None
#   7) dettaglio_job_non_trovato_404
#   8) dettaglio_job_admin_code_manage_vede_tutto — owner filter None
#   9) annulla_job_ok
#  10) annulla_job_fuori_scope_404
#  11) annulla_job_non_pending_409
#  12) requeue_job_ok — extra_tentativi propagato
#  13) requeue_job_stato_non_riaccodabile_409
#  14) requeue_job_extra_tentativi_fuori_range_400
#  15) scope_key_da_emittenti — formato canonico (ALL / ordinati)
#  16) elenca_coda_lavori_archiviate_nascoste_di_default — flag + envelope
#  17) elenca_coda_stampa_archiviate_nascoste_di_default — gemello, simmetria
#  18) archivia_e_ripristina_job_passano_la_direzione
#  19) archivia_job_riga_inesistente_conta_come_fallita
#  19-bis) archiviazione_parziale_non_affonda_le_riuscite — esito a tre stati
#  19-ter) validazione_elenco_righe — vuoto/tipi/tetto/dedup
#  20) archivia_stampa_passa_auth_user_id — filtro applicativo oltre la RLS
#  20-bis) perimetro_emittente_risolto_una_volta_sola — niente N+1 nel giro
#  20-ter) superuser_non_risolve_il_perimetro — None = vede tutto
#  21) archivia_stampa_fuori_perimetro_non_trovata — no-leak
#  22) archiviazione_senza_code_manage_403 — il gate e' nel SERVICE, non in
#      `post_permission` (che salterebbe il controllo di area)
#  23) archiviazione_non_ricopia_il_criterio_di_stato — il guard resta a DB
# ------------------------------------------------------------

from __future__ import annotations

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.coda_lavori import gestione_service as svc
from apps.core.services.coda_lavori.scope import scope_key_da_emittenti
from apps.core.services.service_errors import ServiceError

_SVC = "apps.core.services.coda_lavori.gestione_service"


# Scopo: patch standard dei collaboratori del service (resolver + repo code +
#        repo maintenance + catalogo processi). Ritorna i mock per le assert.
# ⚠️ Il catalogo dei processi va mockato ANCHE SE il test non lo guarda: dal
#    2026-09-11 `_liveness_worker` legge la tolleranza da `dbops.processi` e
#    non piu' da `sveglie.json`, e sotto `SimpleTestCase` una lettura vera del
#    database fallisce. I due drainer rispondono col contratto del seed (10).
def _patch_all(
    *,
    emittenti=None,
    super_admin=False,
    code_manage=False,
):
    p_resolver = patch(f"{_SVC}.PermissionResolver")
    p_repo = patch(f"{_SVC}.CodaLavoriRepository")
    p_maint = patch(f"{_SVC}.MaintenanceRepository")
    p_proc = patch(f"{_SVC}.ProcessiRepository")
    resolver = p_resolver.start()
    repo_cls = p_repo.start()
    maint_cls = p_maint.start()
    proc_cls = p_proc.start()
    proc_cls.return_value.contratti_liveness.return_value = {
        svc.JOBNAME_WORKER_CODA_LAVORI: {"tolleranza_minuti": 10, "segno_di_vita": "GIORNALE"},
        svc.JOBNAME_WORKER_CODA_STAMPA: {"tolleranza_minuti": 10, "segno_di_vita": "GIORNALE"},
    }
    resolver.get_emittenti_pk_ids.return_value = emittenti
    resolver.is_super_admin.return_value = super_admin
    resolver.check_azione.return_value = code_manage
    return (p_resolver, p_repo, p_maint, p_proc), resolver, repo_cls, maint_cls


class ConteggiCodeTests(SimpleTestCase):

    # 1. Operatore scoped: coda lavori filtrata per azienda del lavoro, coda stampa per
    #    auth_user_id; worker con run recente → attivo.
    def test_conteggi_code_scoped_operatore(self) -> None:
        patches, _resolver, repo_cls, maint_cls = _patch_all(emittenti=[4, 3])
        try:
            repo_cls.return_value.count_per_stato.return_value = {
                "PENDING": 2, "IN_CORSO": 1, "FATTO": 9,
            }
            maint_cls.return_value.job_liveness.return_value = {
                "draina_coda_lavori": {
                    "last_run_at": "2026-07-21T22:00:00+02:00", "attivo": True,
                    "in_corso": False,
                    "ultima_conclusa": {
                        "started_at": "2026-07-21T22:00:00+02:00",
                        "ended_at": "2026-07-21T22:00:01+02:00", "ok": True,
                    },
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
            owner_emittenti=[4, 3],
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
            owner_emittenti=None,
        )
        # Stessa forma di `job_liveness` (2026-09-14): ne' un segno di vita ne'
        # una corsa conclusa — non un `last_ok` che di una corsa inesistente
        # direbbe l'esito.
        self.assertEqual(
            esito["worker"]["coda_stampa"],
            {
                "last_run_at": None, "attivo": False, "in_corso": False,
                "ultima_conclusa": None,
            },
        )


class ElencaCodaLavoriTests(SimpleTestCase):

    # 3. Operatore: righe filtrate per le sue aziende, il suo perimetro per is_mio.
    def test_elenca_coda_lavori_operatore(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(emittenti=[7])
        try:
            repo_cls.return_value.elenca.return_value = {
                "items": [{"id": 1, "is_mio": True}], "total": 1,
                "archiviate": 2,
            }
            esito = svc.elenca_coda_lavori(MagicMock(), stato="ERRORE", limit=10)
        finally:
            for p in patches:
                p.stop()

        kwargs = repo_cls.return_value.elenca.call_args.kwargs
        self.assertEqual(kwargs["owner_emittenti"], [7])
        self.assertEqual(kwargs["caller_emittenti"], [7])
        self.assertEqual(kwargs["stati"], ["ERRORE"])
        # ⭐ Default ordinamento (2026-09-07): l'ultimo lavoro ENTRATO in coda in
        #    testa. Era `started_at` — «l'ultimo AVVIATO» — e un lavoro in
        #    ATTESA `started_at` non ce l'ha: con `NULLS LAST` finiva dopo ogni
        #    lavoro mai avviato, cioe' sepolto in ultima pagina invece che
        #    filtrato. `data_insert` e' NOT NULL: ogni lavoro ha una posizione
        #    dal momento in cui entra.
        # ⛔ Questo valore concorda con altre DUE sedi — `ordinamento_default`
        #    del preset in `ui.lista_preset` e `orderBy` dello store FE — e la
        #    divergenza non darebbe nessun errore: darebbe una lista che si
        #    riordina da sola al primo tocco dell'operatore.
        self.assertEqual(kwargs["sort_by"], "data_insert")
        self.assertEqual(kwargs["sort_dir"], "DESC")
        # ⭐ `archiviate_count` viaggia nell'envelope accanto alla lista: senza
        #    quel numero «coda pulita» e «due righe messe via» si leggono uguali.
        self.assertEqual(esito, {
            "count": 1,
            "results": [{"id": 1, "is_mio": True}],
            "archiviate_count": 2,
        })

    # 3-bis. `sort_by`/`sort_dir` espliciti: normalizzati (dir upper) e passati
    #    al repo; fuori whitelist → E_SEARCH_VALIDATION, repo non chiamato.
    def test_elenca_coda_lavori_ordinamento_esplicito_e_whitelist(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(emittenti=[7])
        try:
            repo_cls.return_value.elenca.return_value = {"items": [], "total": 0, "archiviate": 0}
            svc.elenca_coda_lavori(MagicMock(), sort_by="ended_at", sort_dir="asc")
            kwargs = repo_cls.return_value.elenca.call_args.kwargs
            self.assertEqual(kwargs["sort_by"], "ended_at")
            self.assertEqual(kwargs["sort_dir"], "ASC")

            repo_cls.return_value.elenca.reset_mock()
            with self.assertRaises(ServiceError) as ctx:
                svc.elenca_coda_lavori(MagicMock(), sort_by="payload")
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(ctx.exception.code, "E_SEARCH_VALIDATION")
        repo_cls.return_value.elenca.assert_not_called()

    # 4. `tutti` è aperto anche SENZA code_manage (2026-07-23, decisione Tid):
    #    la lista è visibilità di una risorsa condivisa, non gestione — chi
    #    aspetta deve poter vedere il lavoro altrui che impegna la coda. Le
    #    AZIONI e il DETTAGLIO restano gated (test dedicati sotto).
    def test_elenca_coda_lavori_tutti_aperto_senza_permesso(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(emittenti=[7])
        try:
            repo_cls.return_value.elenca.return_value = {"items": [], "total": 0, "archiviate": 0}
            svc.elenca_coda_lavori(MagicMock(), tutti=True)
        finally:
            for p in patches:
                p.stop()
        kwargs = repo_cls.return_value.elenca.call_args.kwargs
        # Nessun filtro righe; la caller key resta per marcare `is_mio`.
        self.assertIsNone(kwargs["owner_emittenti"])
        self.assertEqual(kwargs["caller_emittenti"], [7])

    # 5. `tutti` con code_manage → identico (owner filter None, caller resta).
    def test_elenca_coda_lavori_tutti_con_permesso(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(
            emittenti=[7], code_manage=True,
        )
        try:
            repo_cls.return_value.elenca.return_value = {"items": [], "total": 0, "archiviate": 0}
            svc.elenca_coda_lavori(MagicMock(), tutti=True)
        finally:
            for p in patches:
                p.stop()
        kwargs = repo_cls.return_value.elenca.call_args.kwargs
        self.assertIsNone(kwargs["owner_emittenti"])
        self.assertEqual(kwargs["caller_emittenti"], [7])


class ElencaCodaStampaTests(SimpleTestCase):

    # 6. Ambito PER-OPERATORE (2026-07-23, decisione Tid): «miei» filtra su
    #    user_insert = username del chiamante; «tutti» nessun filtro. In
    #    entrambi i casi caller_username marca is_mio. Stessa semantica della
    #    coda lavori: mai due comportamenti diversi per la stessa UI.
    def test_elenca_coda_stampa_ambito_per_operatore(self) -> None:
        patches, _resolver, _repo, _maint = _patch_all(emittenti=[7])
        user = MagicMock()
        user.username = "pochi"
        try:
            with patch(
                "apps.vendite.db.pipeline_repository.VenditePipelineRepository"
            ) as pipe_cls:
                pipe_cls.return_value.elenca_coda_stampa.return_value = {
                    "items": [], "total": 0, "archiviate": 0,
                }
                svc.elenca_coda_stampa(user, tutti=False)
                kwargs_miei = (
                    pipe_cls.return_value.elenca_coda_stampa.call_args.kwargs
                )
                svc.elenca_coda_stampa(user, tutti=True)
                kwargs_tutti = (
                    pipe_cls.return_value.elenca_coda_stampa.call_args.kwargs
                )
        finally:
            for p in patches:
                p.stop()
        # «miei» = solo le righe innescate da me; «tutti» = nessun filtro.
        self.assertEqual(kwargs_miei["operatore"], "pochi")
        self.assertIsNone(kwargs_tutti["operatore"])
        # is_mio marcato in entrambe le viste.
        self.assertEqual(kwargs_miei["caller_username"], "pochi")
        self.assertEqual(kwargs_tutti["caller_username"], "pochi")
        # ⭐ Default ordinamento (2026-09-07): allineato alla coda lavori —
        #    «l'ultima stampa ENTRATA in coda in testa». Era `data_update`, che
        #    funzionava per COINCIDENZA: su una riga mai toccata vale quanto
        #    `data_insert`. Le due code hanno una semantica sola per decisione
        #    (Tid, 2026-07-23), e due default diversi erano una simmetria che
        #    reggeva finche' nessuno aggiornava una riga in attesa.
        self.assertEqual(kwargs_tutti["sort_by"], "data_insert")
        self.assertEqual(kwargs_tutti["sort_dir"], "DESC")


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
            5, owner_emittenti=None, caller_emittenti=[7],
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
            5, owner_emittenti=[7],
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
            5, extra_tentativi=2, owner_emittenti=[7],
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


class ArchiviazioneCodeTests(SimpleTestCase):
    """L'archiviazione: togliere una riga dall'ELENCO senza toccarne lo stato.

    ⛔ Cio' che questi test NON verificano, di proposito: che una riga VIVA non
    si archivi. Quel criterio ha una sede sola — il trigger
    `_a10_archiviazione_upd` piu' il `CHECK` gemello — e un test in Python che
    lo ripetesse sarebbe la prova che ne esiste una seconda copia. Qui si
    guarda l'opposto: che il service NON ne tenga una (test 23).
    """

    # Scopo: `run_fan_out` isola OGNI riga in un savepoint, e qui non c'e'
    #        database (`SimpleTestCase`): senza questo, il `transaction.atomic`
    #        fallirebbe PRIMA di entrare nella funzione, ogni riga risulterebbe
    #        fallita e i test sarebbero rossi per un motivo che non c'entra.
    # ⚠️ Non si sta spegnendo un presidio: l'isolamento e' del BB e ha i test
    #    suoi — qui si guarda la logica del service (direzione, validazione,
    #    aggregazione dell'esito, gate).
    def setUp(self) -> None:
        patcher = patch(
            "apps.core.services.fan_out.transaction.atomic", nullcontext,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        # Il perimetro emittente della coda stampa: e' una query, e qui non
        # c'e' database. Il mock serve anche al test 20-bis, che CONTA quante
        # volte viene risolto.
        scope = patch(f"{_SVC}.fetch_emittenti_scope_ids", return_value=[7])
        self._scope_fn = scope.start()
        self.addCleanup(scope.stop)

    # 16. Le archiviate sono NASCOSTE di default e il conteggio di cio' che
    #     resta fuori viaggia nell'envelope. `includi_archiviate` le chiede.
    def test_elenca_coda_lavori_archiviate_nascoste_di_default(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(emittenti=[7])
        try:
            repo_cls.return_value.elenca.return_value = {
                "items": [], "total": 0, "archiviate": 3,
            }
            esito = svc.elenca_coda_lavori(MagicMock())
            kwargs_default = repo_cls.return_value.elenca.call_args.kwargs
            svc.elenca_coda_lavori(MagicMock(), includi_archiviate=True)
            kwargs_incluse = repo_cls.return_value.elenca.call_args.kwargs
        finally:
            for p in patches:
                p.stop()
        self.assertFalse(kwargs_default["includi_archiviate"])
        self.assertTrue(kwargs_incluse["includi_archiviate"])
        self.assertEqual(esito["archiviate_count"], 3)

    # 17. Il gemello sulla coda stampa. Le due code sono simmetriche per
    #     costruzione: un comportamento diverso qui sarebbe la prima divergenza.
    def test_elenca_coda_stampa_archiviate_nascoste_di_default(self) -> None:
        patches, _resolver, _repo, _maint = _patch_all(emittenti=[7])
        user = MagicMock()
        user.username = "pochi"
        try:
            with patch(
                "apps.vendite.db.pipeline_repository.VenditePipelineRepository"
            ) as pipe_cls:
                pipe_cls.return_value.elenca_coda_stampa.return_value = {
                    "items": [], "total": 0, "archiviate": 2,
                }
                esito = svc.elenca_coda_stampa(user)
                kwargs_default = (
                    pipe_cls.return_value.elenca_coda_stampa.call_args.kwargs
                )
                svc.elenca_coda_stampa(user, includi_archiviate=True)
                kwargs_incluse = (
                    pipe_cls.return_value.elenca_coda_stampa.call_args.kwargs
                )
        finally:
            for p in patches:
                p.stop()
        self.assertFalse(kwargs_default["includi_archiviate"])
        self.assertTrue(kwargs_incluse["includi_archiviate"])
        self.assertEqual(esito["archiviate_count"], 2)

    # 18. I due verbi differiscono per la sola DIREZIONE, e la direzione deve
    #     arrivare al repository: e' l'unica cosa che li distingue. ⚠️ Il verbo
    #     prende sempre un ELENCO, anche per una riga sola.
    def test_archivia_e_ripristina_job_passano_la_direzione(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(
            emittenti=[7], code_manage=True,
        )
        try:
            repo_cls.return_value.imposta_archiviato.return_value = True
            esito_su = svc.imposta_archiviazione_job(
                MagicMock(), [12], archiviato=True,
            )
            kwargs_su = repo_cls.return_value.imposta_archiviato.call_args.kwargs
            esito_giu = svc.imposta_archiviazione_job(
                MagicMock(), [12], archiviato=False,
            )
            kwargs_giu = repo_cls.return_value.imposta_archiviato.call_args.kwargs
        finally:
            for p in patches:
                p.stop()
        self.assertTrue(kwargs_su["archiviato"])
        self.assertFalse(kwargs_giu["archiviato"])
        self.assertEqual(esito_su["esito"], "COMPLETATO")
        self.assertEqual(esito_su["riuscite"], 1)
        self.assertTrue(esito_su["archiviato"])
        self.assertFalse(esito_giu["archiviato"])

    # 19. Riga inesistente: NON solleva — conta come fallita, col suo codice.
    #     ⭐ E' la differenza fra un verbo di massa e uno singolo: venti
    #     archiviazioni buone non si perdono per una riga che non c'e' piu'.
    def test_archivia_job_riga_inesistente_conta_come_fallita(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(
            emittenti=[7], code_manage=True,
        )
        try:
            repo_cls.return_value.imposta_archiviato.return_value = False
            esito = svc.imposta_archiviazione_job(
                MagicMock(), [999], archiviato=True,
            )
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(esito["esito"], "ERRORE")
        self.assertEqual(esito["riuscite"], 0)
        self.assertEqual(esito["falliti"][0]["id"], 999)
        self.assertEqual(esito["falliti"][0]["code"], "E_JOB_NON_TROVATO")

    # 19-bis. ⭐ L'ESITO PARZIALE, che e' la ragione per cui questo verbo non e'
    #     tutto-o-niente: una riga rifiutata non porta con se' le altre, e chi
    #     legge sa QUALE ha fallito e PERCHE'.
    def test_archiviazione_parziale_non_affonda_le_riuscite(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(
            emittenti=[7], code_manage=True,
        )
        try:
            repo_cls.return_value.imposta_archiviato.side_effect = (
                lambda riga_id, **_k: riga_id != 2
            )
            esito = svc.imposta_archiviazione_job(
                MagicMock(), [1, 2, 3], archiviato=True,
            )
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(esito["esito"], "PARZIALE")
        self.assertEqual(esito["richieste"], 3)
        self.assertEqual(esito["riuscite"], 2)
        self.assertEqual([f["id"] for f in esito["falliti"]], [2])

    # 19-ter. Validazione dell'elenco: vuoto, non interi, oltre il tetto — e il
    #     DEDUP, che non e' cosmetico (il database tratterebbe due volte lo
    #     stesso id come una riga sola, ma il conteggio a video direbbe un
    #     numero diverso da quello spuntato).
    def test_validazione_elenco_righe(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(
            emittenti=[7], code_manage=True,
        )
        try:
            repo_cls.return_value.imposta_archiviato.return_value = True
            for cattivo in ([], "12", [0], [1.5], [True],
                            list(range(1, svc.MAX_RIGHE_ARCHIVIAZIONE + 2))):
                with self.assertRaises(ServiceError) as ctx:
                    svc.imposta_archiviazione_job(
                        MagicMock(), cattivo, archiviato=True,
                    )
                self.assertEqual(ctx.exception.code, "E_VALIDATION_INPUT")
            esito = svc.imposta_archiviazione_job(
                MagicMock(), [5, 5, 5], archiviato=True,
            )
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(esito["richieste"], 1)
        self.assertEqual(esito["riuscite"], 1)

    # 20. Sulla coda stampa il filtro APPLICATIVO di emittente va passato lo
    #     stesso: la RLS armata il 2026-09-04 si SOMMA ai filtri, non li
    #     sostituisce.
    def test_archivia_stampa_passa_auth_user_id(self) -> None:
        patches, _resolver, _repo, _maint = _patch_all(
            emittenti=[7], code_manage=True,
        )
        try:
            with patch(
                "apps.vendite.db.pipeline_repository.VenditePipelineRepository"
            ) as pipe_cls:
                pipe_cls.return_value.imposta_archiviato_stampa.return_value = True
                esito = svc.imposta_archiviazione_stampa(
                    MagicMock(), [5], archiviato=True, auth_user_id=42,
                )
                kwargs = (
                    pipe_cls.return_value.imposta_archiviato_stampa.call_args.kwargs
                )
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(kwargs["emittenti_sr_ids"], [7])
        self.assertTrue(kwargs["archiviato"])
        self.assertEqual(esito["riuscite"], 1)

    # 20-bis. ⭐ IL PERIMETRO SI RISOLVE UNA VOLTA PER RICHIESTA, non per riga.
    #     `fetch_emittenti_scope_ids` e' una QUERY, e dentro una richiesta il
    #     perimetro dell'operatore non cambia: risolverlo dentro il giro
    #     significava 200 query inutili su un verbo che accetta 200 righe.
    #     Nessun errore, nessun test rosso — solo un verbo che costa il doppio
    #     di quanto dovrebbe. Questo test e' il presidio di quella correzione.
    def test_perimetro_emittente_risolto_una_volta_sola(self) -> None:
        patches, _resolver, _repo, _maint = _patch_all(
            emittenti=[7], code_manage=True,
        )
        try:
            with patch(
                "apps.vendite.db.pipeline_repository.VenditePipelineRepository"
            ) as pipe_cls:
                pipe_cls.return_value.imposta_archiviato_stampa.return_value = True
                svc.imposta_archiviazione_stampa(
                    MagicMock(), [1, 2, 3, 4, 5], archiviato=True, auth_user_id=42,
                )
                n_righe = (
                    pipe_cls.return_value.imposta_archiviato_stampa.call_count
                )
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(n_righe, 5)
        self.assertEqual(self._scope_fn.call_count, 1)

    # 20-ter. Superuser: nessuna restrizione, e il perimetro NON si interroga
    #     nemmeno — `None` significa «vede tutto», non «lista vuota».
    def test_superuser_non_risolve_il_perimetro(self) -> None:
        patches, _resolver, _repo, _maint = _patch_all(
            emittenti=None, code_manage=True,
        )
        try:
            with patch(
                "apps.vendite.db.pipeline_repository.VenditePipelineRepository"
            ) as pipe_cls:
                pipe_cls.return_value.imposta_archiviato_stampa.return_value = True
                svc.imposta_archiviazione_stampa(
                    MagicMock(), [1], archiviato=True, auth_user_id=None,
                )
                kwargs = (
                    pipe_cls.return_value.imposta_archiviato_stampa.call_args.kwargs
                )
        finally:
            for p in patches:
                p.stop()
        self.assertIsNone(kwargs["emittenti_sr_ids"])
        self.assertEqual(self._scope_fn.call_count, 0)

    # 21. Fuori perimetro → 0 righe → riga «non trovata», indistinguibile da
    #     inesistente: un esito diverso confermerebbe l'esistenza di una riga
    #     di un altro emittente.
    def test_archivia_stampa_fuori_perimetro_non_trovata(self) -> None:
        patches, _resolver, _repo, _maint = _patch_all(
            emittenti=[7], code_manage=True,
        )
        try:
            with patch(
                "apps.vendite.db.pipeline_repository.VenditePipelineRepository"
            ) as pipe_cls:
                pipe_cls.return_value.imposta_archiviato_stampa.return_value = False
                esito = svc.imposta_archiviazione_stampa(
                    MagicMock(), [5], archiviato=True, auth_user_id=42,
                )
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(esito["esito"], "ERRORE")
        self.assertEqual(esito["falliti"][0]["code"], "E_JOB_NON_TROVATO")

    # 22. ⭐ IL GATE E' NEL SERVICE, su ENTRAMBE le code: senza `code_manage`
    #     l'archiviazione e' 403 e il repository non viene toccato.
    #     ⛔ Perche' qui e non in un `post_permission` sulla view: quel campo fa
    #     RITORNARE alla catena dei permessi l'esito dell'azione di processo,
    #     SALTANDO il controllo di area — un operatore con `code_manage` e area
    #     `strumenti` in sola lettura passerebbe, mentre annulla e requeue, che
    #     quel campo non lo dichiarano, cadono su `METHOD_REQUIRES['POST']` e
    #     pretendono `TUTTO`. Due POST adiacenti nella stessa schermata con due
    #     contratti d'area diversi sono la forma in cui un permesso «funziona»
    #     finche' qualcuno non lo restringe e non capisce perche' non ha effetto.
    def test_archiviazione_senza_code_manage_403(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(
            emittenti=[7], code_manage=False,
        )
        try:
            with patch(
                "apps.vendite.db.pipeline_repository.VenditePipelineRepository"
            ) as pipe_cls:
                with self.assertRaises(ServiceError) as ctx_job:
                    svc.imposta_archiviazione_job(
                        MagicMock(), [12], archiviato=True,
                    )
                with self.assertRaises(ServiceError) as ctx_stampa:
                    svc.imposta_archiviazione_stampa(
                        MagicMock(), [5], archiviato=True, auth_user_id=42,
                    )
                pipe_cls.return_value.imposta_archiviato_stampa.assert_not_called()
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(ctx_job.exception.code, "E_PERMESSO_NEGATO")
        self.assertEqual(ctx_stampa.exception.code, "E_PERMESSO_NEGATO")
        repo_cls.return_value.imposta_archiviato.assert_not_called()

    # 23. ⭐ IL PRESIDIO CHE CONTA: il service NON guarda lo stato della riga.
    #     Con un job che il repository dichiara PENDING, l'archiviazione passa
    #     comunque — perche' a rifiutarla e' il DATABASE. Se un domani qualcuno
    #     aggiungesse un controllo di stato qui, questo test diventerebbe rosso
    #     e direbbe perche': sarebbe la seconda copia di un criterio che ne
    #     ammette una sola.
    def test_archiviazione_non_ricopia_il_criterio_di_stato(self) -> None:
        patches, _resolver, repo_cls, _maint = _patch_all(
            emittenti=[7], code_manage=True,
        )
        try:
            repo_cls.return_value.get_stato.return_value = {"stato": "PENDING"}
            repo_cls.return_value.imposta_archiviato.return_value = True
            esito = svc.imposta_archiviazione_job(MagicMock(), [7], archiviato=True)
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(esito["riuscite"], 1)
        repo_cls.return_value.get_stato.assert_not_called()
