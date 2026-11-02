# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La pratica porta il cliente a grana fine (`billing_account_id`, D-9 di
#        brief-db-istanza-nasce-col-ba): il service lo scrive e il dettaglio lo
#        rilegge dalla colonna, provato sul DATABASE VERO.
# Note: ⛔ Il binding dell'INSERT (una colonna e un segnaposto in piu') e la
#       lettura della colonna al posto di `script.fn_get_billing_account_by_istanza`
#       i test col repository mockato non li vedono.
#       ⚠️ Il mondo si COSTRUISCE (`_mondo_cliente`), in transazione ANNULLATA.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) PraticaBillingAccountDbTests.test_il_ba_si_scrive_e_si_rilegge
2) PraticaBillingAccountDbTests.test_il_ba_di_un_altro_ruolo_e_rifiutato
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.anagrafiche.tests.db.test_ricerca_liste_db import _mondo_cliente
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto


# Scopo: un tipo di prestazione con cui una pratica nasce: attivo, con una
#        definizione pubblicata, e ammesso a prescindere dallo stato del BA
#        (pre = post), cosi' il guard di attivazione del service non decide.
def _tipo_prestazione(cur) -> int:
    cur.execute(
        "SELECT tp.id FROM pratiche.tipi_prestazione tp "
        " WHERE tp.attivo "
        "   AND (tp.obsoleto_dal IS NULL OR tp.obsoleto_dal > script.fn_data_operativa()) "
        "   AND tp.pre_attivazione = tp.post_attivazione "
        "   AND pratiche.fn_risolvi_definizione(tp.id, NULL) IS NOT NULL "
        " ORDER BY tp.id LIMIT 1"
    )
    riga = cur.fetchone()
    if riga is None:
        raise unittest.SkipTest("nessun tipo di prestazione con una definizione pubblicata")
    return int(riga[0])


class PraticaBillingAccountDbTests(unittest.TestCase):

    def setUp(self):
        richiedi_db_provvisto()

    # 1. Col solo BA la pratica prende la sua istanza, e il dettaglio legge il
    #    BA dalla colonna.
    def test_il_ba_si_scrive_e_si_rilegge(self):
        from apps.pratiche.db.pratiche_repository import PraticheRepository
        from apps.pratiche.services import pratiche_service

        try:
            with transaction.atomic(), connection.cursor() as cur:
                mondo, _cliente_id = _mondo_cliente(cur)
                cli = mondo["cliente"]
                pratica_id = pratiche_service.crea_pratica(
                    emittente_fiscale_id=mondo["emittente_fiscale_id"],
                    tipo_prestazione_id=_tipo_prestazione(cur),
                    soggetto_id=str(cli["soggetto_id"]),
                    soggetto_ruolo_id=cli["soggetto_ruolo_id"],
                    billing_account_id=cli["billing_account_id"],
                )
                dettaglio = PraticheRepository().get_pratica(pratica_id)
                assert dettaglio is not None
                self.assertEqual(dettaglio["billing_account_id"], cli["billing_account_id"])
                self.assertEqual(dettaglio["istanza_utility_id"], cli["istanza_utility_id"])
                raise Annulla
        except Annulla:
            pass

    # 2. Il BA deve essere del ruolo della pratica: senza ruolo il trigger
    #    rifiuta con E_PRATICHE_BA_NON_COERENTE (regola 5), che il service
    #    lascia passare col suo codice.
    def test_il_ba_di_un_altro_ruolo_e_rifiutato(self):
        from apps.pratiche.services import pratiche_service

        try:
            with transaction.atomic(), connection.cursor() as cur:
                mondo, _cliente_id = _mondo_cliente(cur)
                cli = mondo["cliente"]
                tipo_id = _tipo_prestazione(cur)
                with self.assertRaises(Exception) as ctx, transaction.atomic():
                    pratiche_service.crea_pratica(
                        emittente_fiscale_id=mondo["emittente_fiscale_id"],
                        tipo_prestazione_id=tipo_id,
                        soggetto_id=str(cli["soggetto_id"]),
                        billing_account_id=cli["billing_account_id"],
                    )
                self.assertIn("E_PRATICHE_BA_NON_COERENTE", _codice(ctx.exception))
                raise Annulla
        except Annulla:
            pass


# Scopo: il codice dell'errore, che arrivi come ServiceError o come errore del
#        DB nudo (il service rilancia nudo i codici che non dichiara, e li
#        traduce il middleware).
def _codice(exc: BaseException) -> str:
    if isinstance(exc, ServiceError):
        return exc.code
    from apps.core.services.db_error_fields import diagnostica_db

    return diagnostica_db(exc).codice or str(exc)
