# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del filtro che mette il `request_id` su ogni riga di log
#        (`apps/core/logging_filters.py`) — consegna BE-8, Passo 2 di
#        `analisi-osservabilita-log.md`.
#
#        ⭐ IL TEST CHE CONTA E' IL 3, e non e' sul filtro: e' sulla
#        CONFIGURAZIONE. Il formato cita `%(request_id)s`, quindi un handler
#        che usasse quel formatter SENZA il filtro non stamperebbe una riga
#        sbagliata — la perderebbe, perche' la formattazione fallisce. Ed e' un
#        difetto che si presenta solo a runtime, sulla riga che serviva.
# ------------------------------------------------------------

"""Indice test previsti.

 1) test_dentro_una_richiesta_il_filtro_mette_il_request_id
       il caso normale.
 2) test_fuori_da_una_richiesta_mette_il_segnaposto
       worker, comandi, shell: `-`, che e' l'informazione giusta e non un
       ripiego — «questa riga non appartiene a nessuna richiesta».
 3) test_ogni_handler_col_formato_verbose_ha_il_filtro
       ⭐ il presidio della configurazione: senza filtro il record non ha
       l'attributo e la riga di log si PERDE.
 4) test_il_formato_verbose_cita_il_request_id
       il verso opposto del 3: se qualcuno togliesse `req=%(request_id)s` dal
       formato, i test 1 e 2 resterebbero verdi e la correlazione sparirebbe
       in silenzio.
 5) test_un_contesto_rotto_non_fa_perdere_la_riga
       un log non deve mai far fallire chi lo scrive.
"""

import logging
from unittest import TestCase
from unittest.mock import patch

from django.conf import settings

from apps.core.logging_filters import NESSUNA_RICHIESTA, RequestIdFilter
from apps.core.services.request_context import (
    clear_request_context,
    set_request_context,
)



def _record() -> logging.LogRecord:
    """Scopo: un LogRecord nudo, come quello che arriva a un handler."""
    return logging.LogRecord(
        name="apps.prova", level=logging.INFO, pathname=__file__, lineno=1,
        msg="messaggio", args=(), exc_info=None,
    )


class RequestIdFilterTests(TestCase):
    def setUp(self):
        self.addCleanup(clear_request_context)

    # Scopo: dentro una richiesta, il record porta il request_id corrente.
    def test_dentro_una_richiesta_il_filtro_mette_il_request_id(self):
        set_request_context(
            request_id="7f3a1c22-0000-4000-8000-000000000001", idempotency_key=None
        )
        record = _record()

        self.assertTrue(RequestIdFilter().filter(record))
        self.assertEqual(record.request_id, "7f3a1c22-0000-4000-8000-000000000001")

    # Scopo: fuori da una richiesta (worker della coda, comandi di management,
    #        shell) il valore e' il segnaposto — non la stringa vuota, che in
    #        una riga a campi separati da spazi sposterebbe le colonne.
    def test_fuori_da_una_richiesta_mette_il_segnaposto(self):
        clear_request_context()
        record = _record()

        RequestIdFilter().filter(record)
        self.assertEqual(record.request_id, NESSUNA_RICHIESTA)

    # Scopo: ⭐ IL PRESIDIO DELLA CONFIGURAZIONE. Ogni handler che usa il
    #        formatter `verbose` deve avere il filtro `request_id`: quel formato
    #        cita `%(request_id)s`, e un record senza l'attributo fa fallire la
    #        formattazione — la riga si PERDE, proprio mentre si sta cercando di
    #        capire cosa e' successo.
    #
    # ⚠️ E' il test che serve davvero, perche' il difetto non lo introduce chi
    #    tocca il filtro: lo introduce chi aggiunge un handler nuovo mesi dopo.
    def test_ogni_handler_col_formato_verbose_ha_il_filtro(self):
        logging_conf = settings.LOGGING
        senza_filtro = [
            nome
            for nome, conf in logging_conf["handlers"].items()
            if conf.get("formatter") == "verbose"
            and "request_id" not in (conf.get("filters") or [])
        ]
        self.assertEqual(
            senza_filtro, [],
            "handler col formatter 'verbose' e senza il filtro 'request_id': "
            "i loro record non hanno l'attributo e la riga di log si perde",
        )

    # Scopo: il verso opposto. Se qualcuno togliesse il campo dal formato, i
    #        test 1 e 2 resterebbero verdi e la correlazione sparirebbe senza
    #        che nessun rosso lo dicesse.
    def test_il_formato_verbose_cita_il_request_id(self):
        formato = settings.LOGGING["formatters"]["verbose"]["format"]
        self.assertIn("%(request_id)s", formato)

    # Scopo: un log non deve MAI far fallire chi lo scrive. Se il contesto
    #        richiesta si rompe, la riga esce col segnaposto.
    def test_un_contesto_rotto_non_fa_perdere_la_riga(self):
        record = _record()
        # ⚠️ Si patcha la funzione NELLA SUA SEDE, non nel modulo del filtro:
        #    il filtro la importa DENTRO il metodo (per non tirare dentro le
        #    settings mentre Django si configura), quindi nel suo namespace non
        #    esiste un nome da sostituire.
        with patch(
            "apps.core.services.request_context.get_request_id",
            side_effect=RuntimeError("contesto rotto"),
        ):
            self.assertTrue(RequestIdFilter().filter(record))
        self.assertEqual(record.request_id, NESSUNA_RICHIESTA)
