# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I DUE lettori del ponte risorsa umana ↔ utente, spostati dalla vista
#        col nome vecchio (`anagrafiche.risorse_umane_auth_user`) alla MADRE
#        (`identita_digitali` → `risorse_umane` per `soggetto_ruolo_id`), il
#        2026-09-12 — analisi-software-per-dati-morti §2.1, «strato 2»:
#        `endpoint_helpers.get_risorsa_umana_id` e
#        `permissions_cache.invalidate_department`.
#
# ⭐ PERCHE' UN TEST SUL DB VERO. La vista faceva DUE cose che il suo nome non
#    diceva — filtrava `ruolo_applicativo = 'OPERATORE'` e proiettava
#    `risorsa_umana_id` con un LEFT JOIN «di compatibilita'» — e chi la
#    sostituisce deve riprodurle ESATTAMENTE, altrimenti la coda di lavoro
#    delle pratiche cambia proprietario in silenzio. La misura di riferimento
#    e' `script.fn_get_user_profile`, che quel JOIN lo fa gia' per il blocco
#    `risorse_umane` del profilo: se le due letture divergono, una delle due
#    sta raccontando un modello diverso. Un mock sul cursore qui proverebbe
#    solo che la stringa e' quella scritta, non che leghi
#    ([[feedback_rinomina_db_binding_mockato]]).
#    ⚠️ Il confronto e' su un operatore con identita' E risorsa umana ATTIVE:
#    l'helper filtra entrambe (come `fn_get_uo_id_for_user`), il profilo no —
#    su una risorsa umana spenta risponderebbero cose diverse di proposito.
#
# ⛔ E IL TERZO TEST E' IL PRESIDIO DEL RITIRO: la vista sparira' dal
#    database (passo 2 del cantiere, team DB). La lezione del 12-09 e' che il
#    DROP e' passato PRIMA della consegna BE e l'endpoint e' andato a 500 — il
#    grep a zero sul sorgente e' cio' che impedisce a un lettore nuovo di
#    rinascere sul nome vecchio mentre nessuno guarda.
#    ⭐ Il registro `_DEBITO_DICHIARATO` e' IN PARI (vuoto) dal 2026-09-12
#    stesso: il terzo lettore, `AnagraficheRepository.list_expired_auth_user_ids`
#    (la `WHERE` di `fn_sync_auth_user_expired` ricopiata a meta' in Python),
#    non e' stato riscritto sulla madre ma TOLTO — il repository legge ora
#    l'EFFETTO della funzione DB (`sync_auth_user_expired`, differenza degli
#    attivi prima/dopo), e la regola «chi e' scaduto» ha una sede sola. Il
#    meccanismo del registro resta, come `dbops.codici_errore_senza_policy`:
#    un registro vuoto e' un registro in pari, e il giorno che un lettore
#    rientra e' qui che si vede.
#
# ⚠️ I test 1, 2 e 4 richiedono il DB vero (opt-in `ZEROERP_TEST_DB_E2E=1`,
#    accesa in CI) e NON LASCIANO NIENTE: tutto in transazione annullata.
#    Il test 3 gira sempre, senza database.
#
# Indice test:
#   1. test_get_risorsa_umana_id_coincide_con_fn_get_user_profile
#   2. test_utente_inesistente_risponde_none
#   3. test_il_backend_non_nomina_piu_la_vista
#   4. test_invalidate_department_lega_sulla_madre
# ------------------------------------------------------------

from __future__ import annotations

import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from django.db import connection, transaction

import apps
from apps.core.api.endpoint_helpers import get_risorsa_umana_id
from apps.core.services import permissions_cache
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto
from apps.core.tests._repo import sorgente_senza_commenti

# La radice dei sorgenti del backend, dal package e non da un conteggio di
# `parents[...]`, che si rompe in silenzio se questo file cambia cartella.
_APPS_DIR = Path(apps.__file__).resolve().parent

# I due nomi che il backend NON deve piu' pronunciare come lettore: la vista
# qualificata e il model che la avvolgeva. ⚠️ Volutamente NON
# `risorse_umane_auth_user` nudo: quel token vive ancora, legittimamente, in
# `storico._legacy_risorse_umane_auth_user` (una fixture che DEVE divergere dal
# codice, in `test_audit_log_from_storico_table`) e nel nome della chiave del
# profilo, che ritira il DB.
_NOMI_VIETATI = (
    re.compile(r"anagrafiche\.risorse_umane_auth_user\b"),
    re.compile(r"\bRisorseUmaneAuthUser\b"),
)

# REGISTRO DEL DEBITO — file relativo ad `apps/` → occorrenze ammesse. ⛔ Puo'
# solo calare: un'occorrenza in piu' e' un lettore nuovo (rosso), una in meno
# e' debito pagato e la riga va tolta (rosso, perche' un registro che non cala
# non registra niente). Chiavato sul conteggio e non sul numero di riga, che
# farebbe rosso per il motivo sbagliato.
_DEBITO_DICHIARATO: dict[str, int] = {}


# Scopo: una richiesta finta con il solo contratto che `get_risorsa_umana_id`
#        legge — `request.user.id`, `is_authenticated` — e su cui possa
#        appendere la cache per-request.
def _richiesta(auth_user_id: int) -> SimpleNamespace:
    return SimpleNamespace(
        user=SimpleNamespace(id=auth_user_id, is_authenticated=True),
    )


class RisorsaUmanaDallaMadreTests(TestCase):
    """I lettori del ponte RU↔utente leggono la madre, e leggono giusto."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # Senza database i test 1, 2 e 4 saltano; il 3 non ha bisogno di niente.
        # ⚠️ Si intercetta SOLO lo skip: qualunque altro errore e' un difetto
        #    dell'ambiente di test e deve vedersi, non diventare tre skip muti.
        try:
            richiedi_db_provvisto()
            cls._db = True
        except unittest.SkipTest:
            cls._db = False

    # Scopo: un operatore con identita' ATTIVA che HA una risorsa umana, letto
    #        dalla madre. Salta se il database non ne ha (condizione
    #        d'ambiente, non difetto).
    def _un_operatore_con_risorsa_umana(self, cur) -> int:
        cur.execute(
            """
            SELECT id.auth_user_id
              FROM anagrafiche.identita_digitali id
              JOIN anagrafiche.risorse_umane ru
                ON ru.soggetto_ruolo_id = id.soggetto_ruolo_id
             WHERE id.ruolo_applicativo = %s
               AND id.attivo = true
               AND ru.attivo = true
             ORDER BY id.auth_user_id
             LIMIT 1
            """,
            [RUOLO_APPLICATIVO_OPERATORE],
        )
        riga = cur.fetchone()
        if riga is None:
            self.skipTest("nessuna identita OPERATORE legata a una risorsa umana")
        return int(riga[0])

    # Scopo: la lettura BE e quella del DB (`fn_get_user_profile`) danno lo
    #        stesso `risorsa_umana_id` per lo stesso utente.
    def test_get_risorsa_umana_id_coincide_con_fn_get_user_profile(self) -> None:
        if not self._db:
            self.skipTest("DB non provvisto")
        with transaction.atomic():
            with connection.cursor() as cur:
                apri_contesto_operatore(cur)
                auth_user_id = self._un_operatore_con_risorsa_umana(cur)
                cur.execute(
                    "SELECT (script.fn_get_user_profile(%s) -> 'risorse_umane' "
                    "->> 'risorsa_umana_id')::bigint",
                    [auth_user_id],
                )
                riga = cur.fetchone()
                assert riga is not None
                atteso = riga[0]

            self.assertIsNotNone(atteso, "il profilo DB non risolve la risorsa umana")
            self.assertEqual(get_risorsa_umana_id(_richiesta(auth_user_id)), int(atteso))
            transaction.set_rollback(True)

    # Scopo: il contrario — un utente che non c'e' non ha una risorsa umana, e
    #        la risposta e' `None`, non un'eccezione ne' un id di qualcun altro.
    def test_utente_inesistente_risponde_none(self) -> None:
        if not self._db:
            self.skipTest("DB non provvisto")
        with transaction.atomic():
            with connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute("SELECT COALESCE(MAX(id), 0) + 100000 FROM auth_user")
                riga = cur.fetchone()
                assert riga is not None
                inesistente = int(riga[0])
            self.assertIsNone(get_risorsa_umana_id(_richiesta(inesistente)))
            transaction.set_rollback(True)

    # Scopo: il presidio del ritiro — nessun sorgente del backend (test esclusi)
    #        nomina la vista o il model, fuori dai commenti.
    def test_il_backend_non_nomina_piu_la_vista(self) -> None:
        trovati: dict[str, int] = {}
        for percorso in sorted(_APPS_DIR.rglob("*.py")):
            if "/tests/" in percorso.as_posix():
                continue
            testo = sorgente_senza_commenti(percorso.read_text(encoding="utf-8"))
            n = sum(len(regola.findall(testo)) for regola in _NOMI_VIETATI)
            if n:
                trovati[percorso.relative_to(_APPS_DIR).as_posix()] = n
        self.assertEqual(
            trovati,
            _DEBITO_DICHIARATO,
            "il backend nomina la vista col nome vecchio o il suo model in un "
            "punto che il registro non dichiara (lettore NUOVO: il DB la ritira, "
            "e qui risponderebbe 500 il giorno del DROP — lezione del "
            "2026-09-12), oppure un lettore dichiarato e' sparito: debito "
            "pagato, togli la riga dal registro",
        )

    # Scopo: `invalidate_department` lega reparto → utente sulla madre, e la
    #        query ORM sui model `managed=False` LEGA davvero al database:
    #        per l'UO di una risorsa umana con identita', la cache viene
    #        invalidata proprio per quell'`auth_user_id`.
    def test_invalidate_department_lega_sulla_madre(self) -> None:
        if not self._db:
            self.skipTest("DB non provvisto")
        with transaction.atomic():
            with connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute(
                    """
                    SELECT ru.unita_organizzativa_id, id.auth_user_id
                      FROM anagrafiche.risorse_umane ru
                      JOIN anagrafiche.identita_digitali id
                        ON id.soggetto_ruolo_id = ru.soggetto_ruolo_id
                     WHERE ru.unita_organizzativa_id IS NOT NULL
                     ORDER BY ru.id
                     LIMIT 1
                    """
                )
                riga = cur.fetchone()
            if riga is None:
                self.skipTest("nessuna risorsa umana con reparto e identita'")
            uo_id, auth_user_id = int(riga[0]), int(riga[1])

            with patch("apps.core.services.permissions_cache.cache") as cache_finta:
                permissions_cache.invalidate_department(uo_id)

            # Dal 2026-09-24 (M-1) si invalida per GENERAZIONE: una generazione
            # nuova per ogni utente del reparto, non piu' `delete_many` delle
            # chiavi (che col contesto di sessione non sono piu' una per utente).
            cache_finta.set_many.assert_called_once()
            chiavi = cache_finta.set_many.call_args[0][0]
            # La chiave la compone il BB, non questo test: ricopiarne il formato
            # renderebbe verde-per-caso un cambio di prefisso.
            self.assertIn(permissions_cache._gen_key(auth_user_id), chiavi)
            transaction.set_rollback(True)
