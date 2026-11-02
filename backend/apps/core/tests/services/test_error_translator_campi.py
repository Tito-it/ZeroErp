# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I campi da correggere nell'envelope d'errore — passo 1 del §12 del
#        `piano-be-classe-codici-errore.md`.
#
#        PERCHE' ESISTE. `ui_action = highlight_form_fields` sta su 125 codici e
#        dice «evidenzia il campo sbagliato» — senza dire QUALE. Il nome del
#        campo il backend lo sapeva gia': `ServiceError` porta un `context`, e la
#        convenzione `{"field": <nome>}` e' in 114 punti di chiamata, validator
#        centralizzati compresi. Si fermava al log: `ApiError` quel campo non ce
#        l'aveva, e il translator lo lasciava cadere un passo prima dell'uscita.
#
#        ⚠️ LA DECISIONE CHE QUESTI TEST TENGONO FERMA e' *quali* chiavi escono.
#        Il `context` e' una borsa diagnostica destinata a `dbops.error_log`:
#        dentro ci sono anche `lotto_id`, `contratto_id`, `order_dir`. Mandarle
#        tutte come «campi da correggere» direbbe al frontend di evidenziare
#        cose che sullo schermo non esistono — un dato falso al posto di un dato
#        mancante, che e' un peggioramento, non un progresso.
#
#        Gira SENZA database.
# ------------------------------------------------------------

"""Indice test previsti.

 1) test_il_campo_arriva_nellenvelope
 2) test_il_context_diagnostico_non_produce_campi     <- la decisione, sopra
 3) test_il_valore_non_esce_mai
 4) test_nome_di_campo_implausibile_scartato
 5) test_il_campo_sopravvive_alla_policy              <- il punto dove si perdeva
 6) test_senza_context_nessun_campo
"""

from __future__ import annotations

import json
from unittest import TestCase

from apps.core.api.error_responses import exception_to_error_response
from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.service_errors import ServiceError

# Un codice registrato e non tecnico: il messaggio resta quello del service e
# l'envelope non viene sanitizzato.
_CODICE = "E_CORE_VALIDATION"


class ErrorTranslatorCampiTest(TestCase):
    # Scopo: il caso dritto — la convenzione `{"field": …}` arriva al client.
    def test_il_campo_arriva_nellenvelope(self):
        exc = ServiceError(
            code=_CODICE, message="Partita IVA non valida.", context={"field": "partita_iva"}
        )
        self.assertEqual(ErrorTranslator.to_api_error(exc).fields, ("partita_iva",))

    # Scopo: ⭐ LA DECISIONE. Un `context` che identifica un'entita' non descrive
    #        un campo di un form: non deve produrre niente. Se questo test
    #        diventasse verde al contrario, il frontend riceverebbe l'ordine di
    #        evidenziare un `lotto_id` che nel form non c'e'.
    def test_il_context_diagnostico_non_produce_campi(self):
        for context in ({"lotto_id": 42}, {"contratto_id": 7, "riga_id": 3}, {"order_dir": "ASC"}):
            with self.subTest(context=context):
                exc = ServiceError(code=_CODICE, message="x", context=context)
                self.assertIsNone(ErrorTranslator.to_api_error(exc).fields)

    # Scopo: esce il NOME, mai il valore. Nel context c'e' anche quello che
    #        l'utente ha scritto, e non ha nessun motivo di tornare indietro.
    def test_il_valore_non_esce_mai(self):
        exc = ServiceError(
            code=_CODICE,
            message="Codice fiscale non valido.",
            context={"field": "codice_fiscale", "codice_fiscale": "RSSMRA80A01H501U"},
        )
        corpo = json.loads(exception_to_error_response(exc).content)
        self.assertEqual(corpo["error"]["fields"], ["codice_fiscale"])
        self.assertNotIn("RSSMRA80A01H501U", json.dumps(corpo))

    # Scopo: un nome di campo che non sembra un identificatore non esce. I nomi
    #        li scrive il service, non l'utente — ma un chiamante che passasse
    #        una chiave dinamica farebbe rimbalzare al client testo altrui.
    def test_nome_di_campo_implausibile_scartato(self):
        for nome in ("campo con spazi", "<script>", "1_inizia_per_cifra", "x" * 100, 42, None):
            with self.subTest(nome=nome):
                exc = ServiceError(code=_CODICE, message="x", context={"field": nome})
                self.assertIsNone(ErrorTranslator.to_api_error(exc).fields)

    # Scopo: ⚠️ IL PUNTO IN CUI SI PERDEVA. `_apply_policy` costruisce un
    #        `ApiError` NUOVO: quello che non viene ricopiato li' sparisce, ed e'
    #        esattamente come `fields` si perdeva prima di esistere. Il test
    #        guarda l'envelope finale, non il primo oggetto costruito.
    def test_il_campo_sopravvive_alla_policy(self):
        exc = ServiceError(code=_CODICE, message="x", context={"field": "prezzo"})
        corpo = json.loads(exception_to_error_response(exc).content)
        self.assertEqual(corpo["error"]["fields"], ["prezzo"])
        # e la policy ha comunque fatto il suo mestiere sullo stesso envelope
        self.assertIn("ui_action", corpo["error"])

    # Scopo: la chiave non compare quando non c'e' niente da dire — l'envelope
    #        non si allunga di un `null` per ogni errore che non tocca un form.
    def test_senza_context_nessun_campo(self):
        corpo = json.loads(
            exception_to_error_response(ServiceError(code=_CODICE, message="x")).content
        )
        self.assertNotIn("fields", corpo["error"])
