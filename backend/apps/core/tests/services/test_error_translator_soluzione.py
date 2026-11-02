# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: LA SOLUZIONE nell'envelope d'errore — `hint`, cioe' l'unica frase che
#        dice all'operatore *cosa fare adesso*.
#
#        PERCHE' ESISTE, ed e' il gemello esatto di `test_error_translator_campi`.
#        Il team DB scrive la `soluzione` a catalogo per ogni codice;
#        `script.fn_log_and_raise_error` la consegna nel canale `HINT`
#        dell'eccezione; `diagnostica_db` la legge; i cinque punti di traduzione
#        la trasportano. Dal 2026-09-09 il frontend la RENDE, sotto il messaggio
#        — e da quel momento questi test smettono di presidiare un contratto e
#        cominciano a presidiare una cosa che si vede.
#
#        ⚠️ LA DECISIONE CHE QUESTI TEST TENGONO FERMA e' la sola riga
#        `hint=None if is_technical else api_error.hint` di `_apply_policy`: su
#        `E_DATABASE`, `E_PIPELINE` ed `E_GENERICO` il canale `HINT` non porta la
#        soluzione di nessun catalogo — porta cio' che PostgreSQL scrive per lo
#        sviluppatore, in inglese. Sono gli stessi tre codici in cui `message` e'
#        gia' sostituito dalla policy e `detail` da `_sanitize_public_detail`:
#        *il suggerimento accompagna il messaggio, e li' il messaggio non e' piu'
#        quello dell'errore.*
#
#        ⚠️ E la regola NON e' quella del bersaglio, che guarda anche lo status:
#        su un codice di classe `TECNICO` **registrato a catalogo** la soluzione
#        esce. Un gesto su un 500 non c'e'; una frase che dice «segnala al
#        supporto» si'.
#
#        Gira SENZA database.
# ------------------------------------------------------------

"""Indice test previsti.

 1) test_la_soluzione_arriva_nellenvelope
 2) test_senza_soluzione_la_chiave_non_esce           (assenza = chiave assente)
 3) test_la_soluzione_sopravvive_alla_policy          <- il punto dove si perde
 4) test_la_soluzione_del_database_arriva_dal_canale_hint
 5) test_su_un_codice_tecnico_la_soluzione_non_esce   <- la decisione, sopra
 6) test_su_un_tecnico_a_catalogo_la_soluzione_esce   <- il verso opposto del 5,
    con la PREMESSA sul catalogo asserita invece che assunta
 7) test_il_messaggio_del_tecnico_resta_quello_della_policy
"""

from __future__ import annotations

import json
from unittest import TestCase

from apps.core.api.error_responses import exception_to_error_response
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.error_translator import ErrorTranslator
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_error_fakes import make_db_error

# Un codice registrato e non tecnico: il messaggio resta quello del service e
# l'envelope non viene sanitizzato.
_CODICE = "E_CORE_VALIDATION"

# La soluzione com'e' scritta a catalogo: un'ISTRUZIONE, non una spiegazione.
_SOLUZIONE = "Numerare prima i documenti che questo rettifica, poi ripetere."


class SoluzioneNellEnvelopeTest(TestCase):
    """Il caso dritto: la frase esce, e quando non c'e' non lascia una chiave."""

    # Scopo: Verifica il caso `test_la_soluzione_arriva_nellenvelope`.
    def test_la_soluzione_arriva_nellenvelope(self):
        exc = ServiceError(code=_CODICE, message="Non numerabile.", hint=_SOLUZIONE)
        payload = json.loads(exception_to_error_response(exc).content)
        self.assertEqual(payload["error"]["hint"], _SOLUZIONE)

    # Scopo: ⚠️ L'assenza si esprime TOGLIENDO la chiave, non mandandola vuota:
    #        una chiave presente e vuota dice «guardami», e chi la riceve deve
    #        interrogarla prima di usarla. Stessa disciplina di `targets`.
    def test_senza_soluzione_la_chiave_non_esce(self):
        exc = ServiceError(code=_CODICE, message="Non numerabile.")
        payload = json.loads(exception_to_error_response(exc).content)
        self.assertNotIn("hint", payload["error"])

    # Scopo: ⭐ IL PUNTO IN CUI SI PERDE. `_apply_policy` costruisce un `ApiError`
    #        NUOVO: cio' che non viene ricopiato li' sparisce, senza errori e
    #        senza test rossi. E' il difetto che `fields` ha gia' pagato una
    #        volta (§12 del piano) — qui e' presidiato prima.
    def test_la_soluzione_sopravvive_alla_policy(self):
        exc = ServiceError(code=_CODICE, message="x", hint=_SOLUZIONE)
        self.assertEqual(ErrorTranslator.to_api_error(exc).hint, _SOLUZIONE)

    # Scopo: ⭐ La strada VERA: la soluzione nasce nel canale `HINT` che
    #        `script.fn_log_and_raise_error` scrive, non in un parametro Python.
    #        Un test che la costruisse solo a mano proverebbe il trasporto e non
    #        la LETTURA.
    def test_la_soluzione_del_database_arriva_dal_canale_hint(self):
        exc = make_db_error(
            "Non si puo' numerare il documento.",
            codice="E_FATTURA_RETTIFICATA_SENZA_NUMERO",
            hint=_SOLUZIONE,
        )
        self.assertEqual(ErrorTranslator.to_api_error(exc).hint, _SOLUZIONE)


class SoluzioneSuErroreTecnicoTest(TestCase):
    """La decisione: su quali codici la frase NON esce, e su quali si'."""

    # Scopo: ⛔ I TRE codici di `is_technical_code`. Li' il canale `HINT` non
    #        porta una soluzione a catalogo: porta il testo che PostgreSQL (o il
    #        runtime) ha scritto per lo sviluppatore. Mostrarlo a video vorrebbe
    #        dire dare all'operatore un'istruzione in inglese su un oggetto che
    #        non conosce — un dato falso al posto di un dato mancante.
    def test_su_un_codice_tecnico_la_soluzione_non_esce(self):
        for codice in ("E_DATABASE", "E_PIPELINE", "E_GENERICO"):
            with self.subTest(codice=codice):
                exc = ServiceError(
                    code=codice,
                    message="rotto",
                    hint="Perhaps you meant to reference the column \"t.numero\".",
                )
                self.assertIsNone(ErrorTranslator.to_api_error(exc).hint)

    # Scopo: ⚠️ IL VERSO OPPOSTO, o il test sopra passerebbe anche se la
    #        soluzione non uscisse MAI. E qui la regola DIVERGE da quella del
    #        bersaglio: `E_ALLEGATO_INSERT` e' di classe `TECNICO` (500) e il
    #        bersaglio non esce — la soluzione si', perche' e' scritta a catalogo
    #        per quel codice ed e' l'unica cosa che chi legge un 500 puo' fare.
    #
    #        ⛔ LA PREMESSA SI ASSERISCE, non si assume. Il caso vive su una
    #        proprieta' del CATALOGO — «questo codice e' di classe TECNICO ma non
    #        e' fra i tre di `is_technical_code`» — e il catalogo lo scrive il
    #        team DB. Il giorno in cui quel codice cambiasse classe, senza le due
    #        righe qui sotto il test resterebbe **verde smettendo di provare il
    #        caso**: e' la forma del «verde per sottrazione» che `AGENTS.md`
    #        insegue, e costa due asserzioni.
    def test_su_un_tecnico_a_catalogo_la_soluzione_esce(self):
        self.assertEqual(
            ErrorPolicyRegistry.classe_di("E_ALLEGATO_INSERT"),
            "TECNICO",
            "il caso di questo test e' un codice di CLASSE tecnica: se il"
            " catalogo e' cambiato, va scelto un altro codice — non tolta"
            " l'asserzione",
        )
        self.assertFalse(
            ErrorTranslator.is_technical_code("E_ALLEGATO_INSERT"),
            "e che NON sia fra i tre di `is_technical_code`: e' l'intera"
            " differenza fra le due regole",
        )
        exc = ServiceError(
            code="E_ALLEGATO_INSERT",
            message="rotto",
            hint="Segnalare al supporto citando il request_id.",
        )
        errore = ErrorTranslator.to_api_error(exc)
        self.assertEqual(errore.hint, "Segnalare al supporto citando il request_id.")
        # ⚠️ E il gemello resta com'era: due regole diverse sullo stesso codice.
        self.assertIsNone(errore.targets)

    # Scopo: ⚠️ La ragione della regola, provata invece che spiegata: sui tre
    #        codici il messaggio a video NON e' piu' quello dell'errore — lo
    #        sostituisce la policy. Una soluzione accanto a quella frase
    #        risponderebbe a una domanda che nessuno ha fatto.
    def test_il_messaggio_del_tecnico_resta_quello_della_policy(self):
        exc = ServiceError(code="E_DATABASE", message="ERROR: column t.x does not exist")
        errore = ErrorTranslator.to_api_error(exc)
        # ⚠️ Uguale a quello della policy, non «diverso dall'originale»: un
        #    `assertNotIn` passerebbe anche se il messaggio diventasse una
        #    stringa vuota, cioe' proprio il modo in cui questo test smetterebbe
        #    di dire qualcosa.
        self.assertEqual(
            errore.message, ErrorPolicyRegistry.resolve("E_DATABASE").user_message
        )
        self.assertNotIn("column t.x", errore.message)
