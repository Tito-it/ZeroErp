# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del pezzo D di D19 — «righe da rate»: N rate scelte nel picker
#        diventano N righe della distinta in un Salva, con esito PARZIALE per
#        riga. Con `crea_riga` FINTO: si prova la lettura dell'elenco, la
#        composizione del payload per riga e l'esito a tre stati — non i guard
#        del database, che il test sul DB provvisto attraversa per intero.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1)  RigheDaRateTests.test_elenco_vuoto_rifiutato
2)  RigheDaRateTests.test_tetto_di_duecento
3)  RigheDaRateTests.test_rata_duplicata_rifiutata_col_campo
4)  RigheDaRateTests.test_chiave_sconosciuta_sulla_riga_rifiutata
5)  RigheDaRateTests.test_motivo_senza_forzatura_rifiutato
5b) RigheDaRateTests.test_fatto_comune_malformato_e_un_400_non_n_righe_fallite
6)  RigheDaRateTests.test_i_fatti_comuni_viaggiano_su_ogni_riga
7)  RigheDaRateTests.test_esito_completato
8)  RigheDaRateTests.test_esito_parziale_con_errore_intero_per_riga
9)  RigheDaRateTests.test_esito_errore_quando_falliscono_tutte
10) RigheDaRateTests.test_rata_fuori_perimetro_fallisce_solo_lei
11) RigheDaRateTests.test_la_capienza_risale_confermabile_per_riga
11-bis) RigheDaRateTests.test_un_guasto_su_una_riga_e_un_errore_tecnico_senza_hint
12) RigheDaRateTests.test_distinta_inesistente_404_prima_di_tutto
"""

from contextlib import nullcontext
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.error_manager import ServiceError
from apps.pagamenti.services import pagamenti_service

_DISTINTA = {"id": 7, "stato_codice": "BOZZA", "origine": "MANUALE"}


def _payload(righe, **comuni):
    return {"data_pagamento": "2026-09-17", "riferimento_ente": "TRN 1", **comuni, "righe": righe}


class RigheDaRateTests(SimpleTestCase):
    # Scopo: `run_fan_out` isola OGNI riga in un savepoint, e qui non c'e'
    #        database (`SimpleTestCase`): senza questo il `transaction.atomic`
    #        fallirebbe PRIMA di entrare in `_process`, ogni riga risulterebbe
    #        fallita per un motivo che non c'entra. ⚠️ Non si spegne un
    #        presidio: l'isolamento e' del BB e ha i test suoi (`test_fan_out`);
    #        qui si guarda la logica del service. Stesso patch dei test
    #        dell'archiviazione delle code.
    def setUp(self) -> None:
        savepoint = patch("apps.core.services.fan_out.transaction.atomic", nullcontext)
        savepoint.start()
        self.addCleanup(savepoint.stop)
        self.repo = MagicMock()
        self.repo.get_distinta.return_value = dict(_DISTINTA)
        # Ogni rata risolve alla fattura 10 + il suo id, salvo diversa istruzione.
        self.repo.get_fattura_id_di_rata.side_effect = lambda sid: 1000 + int(sid)
        patcher = patch.object(pagamenti_service, "PagamentiRepository", return_value=self.repo)
        patcher.start()
        self.addCleanup(patcher.stop)
        # La nascita della riga e' FINTA: risponde la riga con l'id della rata.
        self.crea = patch.object(
            pagamenti_service, "crea_riga",
            side_effect=lambda cid, p: {"riga": {"id": 500 + p["scadenza_id"], **p}},
        ).start()
        self.addCleanup(patch.stopall)

    # ── la lettura dell'elenco ──────────────────────────────────────

    def test_elenco_vuoto_rifiutato(self):
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.crea_righe_da_rate(7, _payload([]))
        self.assertEqual(ctx.exception.code, "E_PAGAMENTI_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "righe")
        self.crea.assert_not_called()

    def test_tetto_di_duecento(self):
        righe = [{"scadenza_id": i, "importo": "1.00"} for i in range(1, 202)]
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.crea_righe_da_rate(7, _payload(righe))
        self.assertEqual(ctx.exception.code, "E_PAGAMENTI_VALIDATION")
        self.crea.assert_not_called()

    # Scopo: ⛔ Da un picker un duplicato e' un difetto del client: si dice, con
    #        il campo — deduplicare in silenzio butterebbe via un importo.
    def test_rata_duplicata_rifiutata_col_campo(self):
        righe = [{"scadenza_id": 1, "importo": "10"}, {"scadenza_id": 1, "importo": "20"}]
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.crea_righe_da_rate(7, _payload(righe))
        self.assertEqual(ctx.exception.code, "E_PAGAMENTI_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "righe")
        self.crea.assert_not_called()

    def test_chiave_sconosciuta_sulla_riga_rifiutata(self):
        righe = [{"scadenza_id": 1, "importo": "10", "fattura_id": 99}]
        with self.assertRaises(ServiceError):
            pagamenti_service.crea_righe_da_rate(7, _payload(righe))
        self.crea.assert_not_called()

    def test_motivo_senza_forzatura_rifiutato(self):
        righe = [{"scadenza_id": 1, "importo": "10", "motivo_forzatura": "x"}]
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.crea_righe_da_rate(7, _payload(righe))
        self.assertEqual(ctx.exception.context.get("field"), "motivo_forzatura")

    # Scopo: 🔴 Un fatto COMUNE sbagliato e' un difetto della RICHIESTA: un 400
    #        col campo, prima del giro — non un 200 `ERRORE` con N fallite
    #        identiche (la forma che aveva la prima stesura, e che a video
    #        avrebbe messo la stessa frase su ogni rata dell'area).
    def test_fatto_comune_malformato_e_un_400_non_n_righe_fallite(self):
        righe = [{"scadenza_id": 1, "importo": "1"}, {"scadenza_id": 2, "importo": "2"}]
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.crea_righe_da_rate(
                7, _payload(righe, data_pagamento="17/09/2026")
            )
        self.assertEqual(ctx.exception.context.get("field"), "data_pagamento")
        self.crea.assert_not_called()

    # ── la composizione per riga ────────────────────────────────────

    # Scopo: ⭐ Nessuna seconda strada: ogni riga nasce da `crea_riga` con i
    #        fatti comuni, la fattura risolta dalla rata, la rata e il suo
    #        importo — e la forzatura solo dove e' stata chiesta.
    def test_i_fatti_comuni_viaggiano_su_ogni_riga(self):
        righe = [
            {"scadenza_id": 1, "importo": "500.00"},
            {"scadenza_id": 2, "importo": "620.00", "forzata": True, "motivo_forzatura": "doppio"},
        ]
        pagamenti_service.crea_righe_da_rate(7, _payload(righe, data_valuta="2026-09-18"))
        self.assertEqual(self.crea.call_count, 2)
        primo = self.crea.call_args_list[0].args[1]
        secondo = self.crea.call_args_list[1].args[1]
        # I fatti comuni arrivano gia' LETTI (una `date`, non la stringa): la
        # lettura e' una, prima del giro, e `crea_riga` la ritrova fatta.
        for p in (primo, secondo):
            self.assertEqual(p["data_pagamento"], date(2026, 9, 17))
            self.assertEqual(p["data_valuta"], date(2026, 9, 18))
            self.assertEqual(p["riferimento_ente"], "TRN 1")
        self.assertEqual((primo["fattura_id"], primo["scadenza_id"]), (1001, 1))
        self.assertEqual(primo["importo"], "500.00")
        self.assertIs(primo["forzata"], False)
        self.assertNotIn("motivo_forzatura", primo)
        self.assertIs(secondo["forzata"], True)
        self.assertEqual(secondo["motivo_forzatura"], "doppio")

    # ── l'esito a tre stati ─────────────────────────────────────────

    def test_esito_completato(self):
        esito = pagamenti_service.crea_righe_da_rate(
            7, _payload([{"scadenza_id": 1, "importo": "1"}, {"scadenza_id": 2, "importo": "2"}])
        )
        self.assertEqual(esito["esito"], "COMPLETATO")
        self.assertEqual((esito["richieste"], esito["riuscite"]), (2, 2))
        self.assertEqual([c["scadenza_id"] for c in esito["creati"]], [1, 2])
        self.assertEqual([c["indice"] for c in esito["creati"]], [0, 1])
        self.assertEqual(esito["falliti"], [])

    # Scopo: ⭐ Venti righe buone non si perdono per una: la riga rifiutata
    #        torna in `falliti` col suo INDICE e l'errore INTERO nella forma
    #        dell'envelope; le altre sono in `creati`.
    def test_esito_parziale_con_errore_intero_per_riga(self):
        def _crea(cid, p):
            if p["scadenza_id"] == 2:
                raise ServiceError(
                    code="E_RIGA_CONTABILE_CAPIENZA_SUPERATA",
                    message="Sulla rata restano 400,00: 620,00 non ci stanno.",
                )
            return {"riga": {"id": 500 + p["scadenza_id"]}}
        self.crea.side_effect = _crea
        esito = pagamenti_service.crea_righe_da_rate(
            7, _payload([
                {"scadenza_id": 1, "importo": "1"},
                {"scadenza_id": 2, "importo": "620"},
                {"scadenza_id": 3, "importo": "3"},
            ]),
        )
        self.assertEqual(esito["esito"], "PARZIALE")
        self.assertEqual((esito["richieste"], esito["riuscite"]), (3, 2))
        self.assertEqual([c["scadenza_id"] for c in esito["creati"]], [1, 3])
        self.assertEqual(len(esito["falliti"]), 1)
        fallita = esito["falliti"][0]
        self.assertEqual((fallita["indice"], fallita["scadenza_id"]), (1, 2))
        errore = fallita["errore"]
        self.assertEqual(errore["code"], "E_RIGA_CONTABILE_CAPIENZA_SUPERATA")
        self.assertIn("620", errore["message"])
        # La forma dell'envelope, con le sue politiche: `ui_action` c'e'.
        self.assertIn("ui_action", errore)

    def test_esito_errore_quando_falliscono_tutte(self):
        self.crea.side_effect = ServiceError(code="E_PAGAMENTI_VALIDATION", message="no")
        esito = pagamenti_service.crea_righe_da_rate(
            7, _payload([{"scadenza_id": 1, "importo": "1"}])
        )
        self.assertEqual(esito["esito"], "ERRORE")
        self.assertEqual(esito["riuscite"], 0)
        self.assertEqual(esito["falliti"][0]["errore"]["code"], "E_PAGAMENTI_VALIDATION")

    # Scopo: una rata fuori perimetro (o inesistente) fallisce da SOLA con
    #        `E_RATA_NON_TROVATA`, e non ferma il giro.
    def test_rata_fuori_perimetro_fallisce_solo_lei(self):
        self.repo.get_fattura_id_di_rata.side_effect = lambda sid: None if sid == 9 else 1000 + sid
        esito = pagamenti_service.crea_righe_da_rate(
            7, _payload([{"scadenza_id": 9, "importo": "1"}, {"scadenza_id": 1, "importo": "1"}])
        )
        self.assertEqual(esito["esito"], "PARZIALE")
        self.assertEqual(esito["falliti"][0]["errore"]["code"], "E_RATA_NON_TROVATA")
        self.assertEqual(esito["falliti"][0]["errore"]["fields"], ["scadenza_id"])
        self.assertEqual(self.crea.call_count, 1)

    # Scopo: 🔴 Il secondo tempo e' PER RIGA: il rifiuto della capienza porta
    #        `ui_action = confirm_and_retry` nell'errore della sola riga
    #        rifiutata — il frontend ramifica li', cieco ai codici.
    def test_la_capienza_risale_confermabile_per_riga(self):
        self.crea.side_effect = ServiceError(
            code="E_RIGA_CONTABILE_CAPIENZA_SUPERATA", message="non ci sta"
        )
        esito = pagamenti_service.crea_righe_da_rate(
            7, _payload([{"scadenza_id": 1, "importo": "1"}])
        )
        self.assertEqual(esito["falliti"][0]["errore"]["ui_action"], "confirm_and_retry")

    # Scopo: ⚠️ Un GUASTO su una riga (non un `ServiceError`) passa dalla stessa
    #        porta di tutti gli altri — `to_api_error` sull'eccezione che il BB
    #        ha catturato — e ne esce come errore TECNICO con la frase della
    #        policy: niente codice di dominio inventato, niente `hint` grezzo,
    #        e le altre righe passano lo stesso.
    def test_un_guasto_su_una_riga_e_un_errore_tecnico_senza_hint(self):
        def _crea(cid, p):
            if p["scadenza_id"] == 2:
                raise RuntimeError("cursore chiuso")
            return {"riga": {"id": 500 + p["scadenza_id"]}}
        self.crea.side_effect = _crea
        esito = pagamenti_service.crea_righe_da_rate(
            7, _payload([{"scadenza_id": 1, "importo": "1"}, {"scadenza_id": 2, "importo": "2"}])
        )
        self.assertEqual(esito["esito"], "PARZIALE")
        errore = esito["falliti"][0]["errore"]
        self.assertEqual(errore["code"], "E_GENERICO")
        self.assertNotIn("cursore chiuso", errore["message"])
        self.assertIsNone(errore.get("hint"))

    # Scopo: la distinta si legge UNA volta, prima del giro: se non c'e' (o
    #        non si vede) e' un 404 secco, non N righe fallite.
    def test_distinta_inesistente_404_prima_di_tutto(self):
        self.repo.get_distinta.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            pagamenti_service.crea_righe_da_rate(
                7, _payload([{"scadenza_id": 1, "importo": "1"}])
            )
        self.assertEqual(ctx.exception.code, "E_CONTABILE_NON_TROVATA")
        self.crea.assert_not_called()
