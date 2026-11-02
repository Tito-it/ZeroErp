# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio del verbo «togli questo documento dal giro»
#        (`fn_escludi_documento_da_giro`, brief-db-uscita-documento-dal-giro).
#
# ⛔ QUELLO CHE QUESTI TEST NON PROVANO, ed e' bene saperlo: se il documento sia
#    davvero escludibile. Quel verdetto e' di
#    `script.fn_check_documento_escludibile_da_giro`, che la funzione MADRE
#    chiama per rifiutare — la stessa da cui la lista prende il motivo del
#    pulsante spento. Riprovarlo qui vorrebbe dire una seconda sede della
#    regola, che e' esattamente cio' che il cantiere elimina.
#    Il giro sul database vero e' stato fatto in transazione annullata.
#
# ⚠️ Qui si presidia il CONFINE: che il backend non orchestri, non ricalcoli e
#    non normalizzi — e che il consuntivo arrivi intero a chi deve mostrarlo.
#
# Indice test:
#   1. test_una_sola_chiamata_alla_madre_nessuna_orchestrazione
#   2. test_il_consuntivo_arriva_intero
#   3. test_gruppi_riaperti_e_sempre_una_lista
#   4. test_lotto_id_non_valido_non_arriva_al_database
#   5. test_gruppo_key_vuota_non_arriva_al_database
#   6. test_il_motivo_non_si_valida_in_python
#   7. test_la_riga_singola_e_una_lista_di_uno
#   8. test_esito_parziale_tiene_il_codice_di_ogni_riga
#   9. test_una_chiave_ripetuta_non_si_autoinfligge_un_rifiuto
#  10. test_lista_vuota_rifiutata_non_e_tutti
#  11. test_un_motivo_non_testuale_non_diventa_un_motivo_inventato
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.error_manager import ServiceError
from apps.vendite.services.pipeline_service import (
    fn_escludi_documenti_da_giro,
    fn_escludi_documento_da_giro,
)

_PAYLOAD = {
    "lotto_id": 11221,
    "gruppo_escluso": "ORDINE_VENDITA:01a06ce4",
    "fatture_cancellate": 1,
    "attivita_riemesse": 2,
    "gruppi_riaperti": ["ORDINE_VENDITA:01a07b75"],
    "n_gruppi_riaperti": 1,
}


@patch("apps.vendite.db.pipeline_repository.call_jsonb_fn")
class EscludiDocumentoDaGiroTests(TestCase):

    # 1) ⛔ UNA SOLA CHIAMATA, e nessuna orchestrazione (§6.2 del brief). La
    #    cancellazione della bozza, il ritiro delle attivita', la marcatura e la
    #    riapertura dei trascinati stanno TUTTE dentro la funzione madre.
    #    Ricomporle qui sarebbe una seconda sede della sequenza — e una sequenza
    #    in due sedi si interrompe a meta' il giorno che una delle due cambia.
    def test_una_sola_chiamata_alla_madre_nessuna_orchestrazione(self, mock_fn) -> None:
        mock_fn.return_value = dict(_PAYLOAD)
        fn_escludi_documento_da_giro(
            lotto_id=11221, gruppo_key="ORDINE_VENDITA:01a06ce4", motivo="rotto",
        )
        self.assertEqual(mock_fn.call_count, 1)
        self.assertEqual(
            mock_fn.call_args.args,
            ("vendite.fn_escludi_documento_da_giro", 11221,
             "ORDINE_VENDITA:01a06ce4", "rotto"),
        )

    # 2) ⚠️ Il consuntivo arriva INTERO. `fatture_cancellate` e `gruppi_riaperti`
    #    sono le due conseguenze che l'operatore non si aspetta — una bozza puo'
    #    coprire piu' documenti — e chi non le mostra le nasconde (D-2b).
    def test_il_consuntivo_arriva_intero(self, mock_fn) -> None:
        mock_fn.return_value = dict(_PAYLOAD)
        esito = fn_escludi_documento_da_giro(
            lotto_id=11221, gruppo_key="ORDINE_VENDITA:01a06ce4", motivo="rotto",
        )
        self.assertEqual(esito["fatture_cancellate"], 1)
        self.assertEqual(esito["attivita_riemesse"], 2)
        self.assertEqual(esito["n_gruppi_riaperti"], 1)
        # ⭐ Le CHIAVI e non solo il numero: la conferma deve poterli NOMINARE,
        #    e un conteggio da solo non si verifica.
        self.assertEqual(esito["gruppi_riaperti"], ["ORDINE_VENDITA:01a07b75"])

    # 3) ⚠️ `null` a catalogo diventa `None` in Python, e chi conta farebbe
    #    `len(None)`. La lista resta una lista.
    def test_gruppi_riaperti_e_sempre_una_lista(self, mock_fn) -> None:
        mock_fn.return_value = {**_PAYLOAD, "gruppi_riaperti": None,
                                "n_gruppi_riaperti": None}
        esito = fn_escludi_documento_da_giro(
            lotto_id=11221, gruppo_key="X:1", motivo="rotto",
        )
        self.assertEqual(esito["gruppi_riaperti"], [])
        self.assertEqual(esito["n_gruppi_riaperti"], 0)

    # 4-5) I guard di PARAMETRO fermano prima del database: un `lotto_id <= 0` o
    #      una chiave vuota vengono da un chiamante rotto, non da una persona, e
    #      farli scoprire al database sarebbe un giro per dire la stessa cosa.
    def test_lotto_id_non_valido_non_arriva_al_database(self, mock_fn) -> None:
        with self.assertRaises(ServiceError):
            fn_escludi_documento_da_giro(lotto_id=0, gruppo_key="X:1", motivo="x")
        mock_fn.assert_not_called()

    def test_gruppo_key_vuota_non_arriva_al_database(self, mock_fn) -> None:
        with self.assertRaises(ServiceError):
            fn_escludi_documento_da_giro(lotto_id=11221, gruppo_key="   ", motivo="x")
        mock_fn.assert_not_called()

    # 6) ⛔ IL MOTIVO NON SI VALIDA QUI, ed e' deliberato: «il motivo e'
    #    obbligatorio» e' una regola di DOMINIO (D-5) che il `CHECK` di tabella
    #    possiede e che la madre solleva anche sui soli spazi. Un secondo
    #    controllo in Python sarebbe la seconda sede di quella regola — e il
    #    giorno in cui il database ammettesse un caso in piu', il backend
    #    continuerebbe a rifiutarlo senza che nessuno sappia perche'.
    # ⚠️ Il test asserisce che la stringa arriva al database COM'E': non
    #    normalizzata, non troncata. Sistemarla qui trasformerebbe un rifiuto in
    #    un motivo vuoto scritto.
    def test_il_motivo_non_si_valida_in_python(self, mock_fn) -> None:
        mock_fn.return_value = dict(_PAYLOAD)
        fn_escludi_documento_da_giro(lotto_id=11221, gruppo_key="X:1", motivo="   ")
        self.assertEqual(mock_fn.call_args.args[3], "   ")

    # 7) ⭐ UN ENDPOINT SOLO: la riga singola è una lista di uno. Due superfici
    #    per lo stesso verbo divergerebbero su permessi, conferme e forma
    #    dell'esito — è la lezione già scritta sul gemello degli accrediti.
    def test_la_riga_singola_e_una_lista_di_uno(self, mock_fn) -> None:
        mock_fn.return_value = dict(_PAYLOAD)
        esito = fn_escludi_documenti_da_giro(
            lotto_id=11221, gruppo_keys=["ORDINE_VENDITA:01a06ce4"], motivo="rotto",
        )
        self.assertEqual(esito["esito"], "COMPLETATO")
        self.assertEqual(esito["totale"], 1)
        self.assertEqual(esito["ok"], 1)
        self.assertEqual(len(esito["usciti"]), 1)
        self.assertEqual(esito["falliti"], [])

    # 8) 🔴 IL CODICE PER RIGA, e non solo la frase: è ciò su cui il frontend
    #    instrada — «già uscito» si legge diverso da «non è in errore».
    #
    #    Il difetto che questo presidia, misurato sul giro vero: dentro il
    #    fan-out l'eccezione del database è ancora quella GREZZA di psycopg —
    #    nessun `.code` — e il report usciva col codice di ripiego su OGNI
    #    documento rifiutato, cioè i due motivi diventavano la stessa cosa. Il
    #    verbo singolo non lo mostrava: lì traduce il middleware, e il giro di
    #    massa non ci passa mai.
    # ⚠️ E il giro NON si ferma al primo rifiuto: il savepoint per elemento è
    #    ciò che impedisce a un documento respinto di portarsi via le uscite
    #    già riuscite.
    def test_esito_parziale_tiene_il_codice_di_ogni_riga(self, mock_fn) -> None:
        def _risposta(_fn, _lotto, chiave, _motivo):
            if chiave == "OK:1":
                return dict(_PAYLOAD, gruppo_escluso=chiave)
            raise ServiceError(
                code="E_LOTTO_DOC_NON_IN_ERRORE",
                message="Il documento non è in errore.",
            )

        mock_fn.side_effect = _risposta
        esito = fn_escludi_documenti_da_giro(
            lotto_id=11221, gruppo_keys=["OK:1", "KO:2"], motivo="rotto",
        )
        self.assertEqual(esito["esito"], "PARZIALE")
        self.assertEqual(esito["ok"], 1)
        self.assertEqual(
            esito["falliti"],
            [{
                "gruppo_key": "KO:2",
                "codice": "E_LOTTO_DOC_NON_IN_ERRORE",
                "messaggio": "Il documento non è in errore.",
            }],
        )

    # 9) ⚠️ La stessa chiave due volte nello stesso body produrrebbe un
    #    `E_LOTTO_DOC_GIA_USCITO` AUTOINFLITTO — che a video sembra un difetto
    #    del sistema mentre è il body. Si deduplica preservando l'ordine.
    def test_una_chiave_ripetuta_non_si_autoinfligge_un_rifiuto(self, mock_fn) -> None:
        mock_fn.return_value = dict(_PAYLOAD)
        esito = fn_escludi_documenti_da_giro(
            lotto_id=11221, gruppo_keys=["A:1", "A:1", "B:2"], motivo="rotto",
        )
        self.assertEqual(esito["totale"], 2)
        self.assertEqual(
            [c.args[2] for c in mock_fn.call_args_list], ["A:1", "B:2"],
        )

    # 10) ⛔ Lista VUOTA rifiutata, non trattata come «tutti»: indovinare male
    #     qui vorrebbe dire svuotare un giro intero con una richiesta che non lo
    #     chiedeva.
    def test_lista_vuota_rifiutata_non_e_tutti(self, mock_fn) -> None:
        with self.assertRaises(ServiceError):
            fn_escludi_documenti_da_giro(lotto_id=11221, gruppo_keys=[], motivo="x")
        mock_fn.assert_not_called()

    # 11) 🔴 UN MOTIVO NON TESTUALE NON SI TRASFORMA IN UNO INVENTATO. Il
    #     confine faceva `str(payload.get("motivo") or "")`: su un body storto
    #     `str()` non fallisce, PRODUCE — e un «[1, 2]» finiva scritto come
    #     motivo dell'uscita, dove la D-5 vuole una frase che fra un mese
    #     qualcuno possa leggere. Ora è un guard di TIPO, e si ferma prima del
    #     database.
    # ⛔ Il CONTENUTO resta del database: la stringa vuota PASSA di qui e viene
    #     rifiutata dal `CHECK` con la sua frase a catalogo — «il motivo è
    #     obbligatorio» non si riscrive in Python.
    def test_un_motivo_non_testuale_non_diventa_un_motivo_inventato(
        self, mock_fn,
    ) -> None:
        with self.assertRaises(ServiceError):
            fn_escludi_documenti_da_giro(
                lotto_id=11221, gruppo_keys=["A:1"], motivo=[1, 2],
            )
        mock_fn.assert_not_called()

        mock_fn.return_value = dict(_PAYLOAD)
        fn_escludi_documenti_da_giro(
            lotto_id=11221, gruppo_keys=["A:1"], motivo="",
        )
        self.assertEqual(mock_fn.call_args.args[3], "")
