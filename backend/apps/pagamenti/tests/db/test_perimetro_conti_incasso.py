# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il perimetro emittente sull'elenco dei conti agganciabili a un canale
#        di incasso — l'unica lettura del dominio che ESCE dalla row security.
#
#        PERCHE' ESISTE. `anagrafiche.soggetti_ruoli_conti_bancari` ha la row
#        security **spenta di proposito** (lo dice il commento di
#        `trgfn_enti_incasso_guard_conto_incasso`): su questa lettura il
#        database non filtra niente. Se il perimetro non lo mette il backend,
#        non lo mette nessuno.
#
#        ⛔ IL DIFETTO CHE PRESIDIA E' STATO MISURATO, non immaginato. Il
#        2026-08-28 (passo E-4) l'operatore dell'emittente 32 ha letto l'IBAN di
#        incasso dell'emittente 44 passando il suo `soggetto_ruolo_id`: nessun
#        errore, un elenco pieno. Il conto e' il punto da cui il database ricava
#        DI CHI SONO i soldi arrivati prima della fattura.
#
#        ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI),
#        e non e' una scelta di comodo: il perimetro vive nelle GUC
#        dell'identita' e in `script.fn_scope_ef_whitelist_via_sr` — **un doppio
#        non ha un perimetro**, risponde quello che gli si dice. E' lo stesso
#        motivo per cui il nome della GUC (`app.current_user_id`, non
#        `app.auth_user_id`) si e' potuto sbagliare con i test verdi.
#        ⛔ NON SCRIVE NULLA: solo SELECT, in transazione annullata.
# ------------------------------------------------------------

"""Indice test previsti (opt-in `ZEROERP_TEST_DB_E2E=1`).

- test_ogni_operatore_vede_solo_il_proprio_emittente: dentro passa, fuori e'
  un rifiuto — e sono due emittenti diversi, non lo stesso guardato due volte.
- test_senza_contesto_non_si_legge: nessuna GUC -> rifiuto. ⛔ La canonica
  `fn_check_user_emittente_scope` risponde TRUE su utente NULL («job batch»):
  senza questo test, un percorso senza contesto passerebbe.
- test_il_rifiuto_e_un_403: il codice da solo non basta — uno non a catalogo
  cadrebbe su E_GENERICO, cioe' su un 500, col test verde lo stesso.
"""

from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.api.jwt_audit_authentication import set_jwt_gucs
from apps.core.services.error_manager import ServiceError
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.pagamenti.db.pagamenti_repository import PagamentiRepository

# ⛔ I NOMI VERI delle GUC, presi da `JWT_IDENTITY_GUCS` e dalle policy RLS di
#    `pagamenti` — non da come «dovrebbero» chiamarsi. Azzerarne di sbagliate
#    lascerebbe in piedi il contesto di prima, e il caso «senza contesto»
#    passerebbe coi permessi dell'utente precedente.
_GUC = (
    "app.jwt_user",
    "app.current_user_id",
    "app.current_identita_id",
    "app.ruolo_applicativo",
    "app.soggetto_ruolo_id",
    "app.current_emittente_id",
)


# Scopo: due operatori di DUE emittenti diversi, scoperti dal database.
# ⚠️ Non si cablano id: un test che nomina l'identita' 20 muore alla prima
#    ricarica del dato, e muore dicendo «perimetro rotto» invece di «dato
#    cambiato».
def _due_operatori_di_due_emittenti() -> list[dict[str, int]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT ON (uef.emittente_fiscale_id)
                   i.id            AS identita_id,
                   i.auth_user_id,
                   u.username,
                   ef.soggetto_ruolo_id
              FROM anagrafiche.identita_digitali i
              JOIN auth_user u  ON u.id = i.auth_user_id
              JOIN config.user_emittenti_fiscali uef
                    ON uef.auth_user_id = i.auth_user_id
              JOIN anagrafiche.emittenti_fiscali ef
                    ON ef.id = uef.emittente_fiscale_id
             WHERE i.attivo IS TRUE
               AND i.ruolo_applicativo = 'OPERATORE'
               AND ef.attivo IS TRUE
               AND ef.soggetto_ruolo_id IS NOT NULL
             ORDER BY uef.emittente_fiscale_id, i.id
            """
        )
        colonne = [c[0] for c in cursor.description]
        return [dict(zip(colonne, r, strict=True)) for r in cursor.fetchall()]


def _azzera_gucs() -> None:
    with connection.cursor() as cursor:
        for guc in _GUC:
            cursor.execute("SELECT set_config(%s, NULL, false)", [guc])


class PerimetroContiIncassoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()
        cls.operatori = _due_operatori_di_due_emittenti()
        if len(cls.operatori) < 2:
            raise unittest.SkipTest(
                "Servono due operatori di due emittenti diversi: il dato non c'e'."
            )

    def setUp(self) -> None:
        # ⚠️ Le GUC si azzerano DOPO ogni prova: sono di sessione
        #    (`set_config(..., is_local => false)`), quindi restano appese alla
        #    connessione e il test successivo le troverebbe gia' pronte — cioe'
        #    proverebbe un contesto che non ha impostato lui.
        self.addCleanup(_azzera_gucs)
        self.repo = PagamentiRepository()

    # Scopo: esegue una lettura dentro una transazione ANNULLATA.
    # ⚠️ Qui non si scrive niente, ma il giro resta annullato per principio: un
    #    test che tocca il database di sviluppo non deve lasciare tracce nemmeno
    #    quando crede di non lasciarne.
    def _in_transazione_annullata(self, azione):
        with transaction.atomic():
            try:
                return azione()
            finally:
                transaction.set_rollback(True)

    def _entra_come(self, operatore: dict) -> None:
        _azzera_gucs()
        ok = set_jwt_gucs(
            username=operatore["username"],
            user_id=operatore["auth_user_id"],
            identita_id=operatore["identita_id"],
        )
        self.assertTrue(ok, "le GUC dell'identita' non sono state impostate")

    # Scopo: dentro si legge, fuori si viene rifiutati — su DUE emittenti veri.
    def test_ogni_operatore_vede_solo_il_proprio_emittente(self):
        primo, secondo = self.operatori[0], self.operatori[1]
        self.assertNotEqual(primo["soggetto_ruolo_id"], secondo["soggetto_ruolo_id"])

        for mio, altrui in ((primo, secondo), (secondo, primo)):
            with self.subTest(username=mio["username"]):
                self._entra_come(mio)
                # Il proprio: passa. ⚠️ L'elenco puo' essere VUOTO — quel
                # soggetto potrebbe non avere conti di incasso — e va bene: qui
                # si prova che non viene RIFIUTATO, non che ci sia del dato.
                self._in_transazione_annullata(
                    lambda mio=mio: self.repo.list_conti_incasso(mio["soggetto_ruolo_id"])
                )
                # L'altrui: rifiutato.
                with self.assertRaises(ServiceError) as ctx:
                    self._in_transazione_annullata(
                        lambda altrui=altrui: self.repo.list_conti_incasso(
                            altrui["soggetto_ruolo_id"]
                        )
                    )
                self.assertEqual(ctx.exception.code, "E_SCOPE_EMITTENTE")

    # ⛔ Senza contesto NON si legge. La canonica risponde TRUE su utente NULL
    #    (regola «job batch»): senza questo test un percorso senza GUC — un
    #    comando `manage.py`, un job di servizio — passerebbe il cancello.
    def test_senza_contesto_non_si_legge(self):
        _azzera_gucs()
        with self.assertRaises(ServiceError) as ctx:
            self._in_transazione_annullata(
                lambda: self.repo.list_conti_incasso(
                    self.operatori[0]["soggetto_ruolo_id"]
                )
            )
        self.assertEqual(ctx.exception.code, "E_SCOPE_EMITTENTE")

    # ⚠️ Il codice da solo non basta: quello che l'operatore riceve e' lo STATO.
    def test_il_rifiuto_e_un_403(self):
        self.assertEqual(
            ErrorPolicyRegistry.resolve("E_SCOPE_EMITTENTE").http_status, 403
        )
