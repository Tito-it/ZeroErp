# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per PricingService (F2-BE-09 + F2-BE-10). Mock del
#        repository (nessuna chiamata al DB). Verifica validazione input,
#        propagazione risultato, traduzione DatabaseError -> ServiceError
#        con codice preservato per i marker noti.
# ------------------------------------------------------------

"""
Indice test:
 1) test_resolve_ok                             — delega al repo e ritorna dict
 2) test_resolve_uuid_invalido                  — articolo non UUID -> VALIDATION
 3) test_resolve_uom_zero                       — uom_id=0 -> VALIDATION
 4) test_resolve_ba_negativo                    — ba_id<0 -> VALIDATION
 5) test_resolve_data_non_date                  — data_riferimento string -> VALIDATION
 6) test_resolve_classe_utenza_opzionale        — classe None ok
 7) test_resolve_classe_utenza_zero_ko          — classe=0 -> VALIDATION
 8) test_resolve_db_error_categoria_non_mappata — preserva codice E_CATEGORIA_LISTINO_NON_MAPPATA
 9) (ritirato il 2026-10-07 col marker di E_PREZZO_LISTINO_NON_TROVATO, codice ritirato)
10) test_resolve_db_error_generico              — fallback E_VENDITE_PRICING_FAILED
11) test_composito_ok                           — ritorna lista di righe
12) test_composito_uuid_invalido                — UUID invalido -> VALIDATION
13) test_composito_db_error                     — propaga codice noto
14) test_contesto_loggato_completo              — il diario riceve classe_utenza_id
                                                  e listino_versione_id_preferito
15) test_esito_risolto                          — nucleo che risolve: esito_codice None
16) test_esito_non_risolto_non_solleva          — nucleo che NON risolve: nessuna eccezione
17) test_esito_riga_assente                     — repo che alza -> codice preservato
18) test_esito_parametro_invalido_solleva       — DatabaseError tradotto come sempre
19) test_esito_valida_gli_input                 — l'helper estratto vale anche qui
"""

from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from django.db import DatabaseError

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.pricing_service import PricingService


_REPO = "apps.vendite.services.pricing_service.PricingRepository"
_UUID = "019bac81-3f96-7ce8-a086-7e0bd0a2fec1"


def _base_kwargs(**overrides):
    kw = {
        "articolo_id": _UUID,
        "uom_id": 5,
        "data_riferimento": date(2026, 6, 1),
        "ba_id": 100,
        "utility_id": 7,
        "emittente_soggetto_ruolo_id": 42,
    }
    kw.update(overrides)
    return kw


class TestResolvePrezzo(TestCase):
    @patch(_REPO, autospec=True)
    def test_resolve_ok(self, mock_repo):
        mock_repo.return_value.resolve_prezzo_listino_v2.return_value = {
            "prezzo_finale": Decimal("12.50"),
            "origine": "PROMO",
        }
        result = PricingService().resolve_prezzo(**_base_kwargs())
        self.assertEqual(result["origine"], "PROMO")
        kwargs = mock_repo.return_value.resolve_prezzo_listino_v2.call_args.kwargs
        # UUID stringa normalizzata.
        self.assertEqual(kwargs["articolo_id"], _UUID)

    @patch(_REPO, autospec=True)
    def test_resolve_uuid_invalido(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PricingService().resolve_prezzo(**_base_kwargs(articolo_id="xxx"))
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO, autospec=True)
    def test_resolve_uom_zero(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PricingService().resolve_prezzo(**_base_kwargs(uom_id=0))
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO, autospec=True)
    def test_resolve_ba_negativo(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PricingService().resolve_prezzo(**_base_kwargs(ba_id=-1))
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO, autospec=True)
    def test_resolve_data_non_date(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PricingService().resolve_prezzo(**_base_kwargs(data_riferimento="2026-01-01"))
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO, autospec=True)
    def test_resolve_classe_utenza_opzionale(self, mock_repo):
        mock_repo.return_value.resolve_prezzo_listino_v2.return_value = {"origine": "CATEGORIA"}
        PricingService().resolve_prezzo(**_base_kwargs(classe_utenza_id=None))
        kwargs = mock_repo.return_value.resolve_prezzo_listino_v2.call_args.kwargs
        self.assertIsNone(kwargs["classe_utenza_id"])

    @patch(_REPO, autospec=True)
    def test_resolve_classe_utenza_zero_ko(self, mock_repo):
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PricingService().resolve_prezzo(**_base_kwargs(classe_utenza_id=0))
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    @patch(_REPO, autospec=True)
    def test_resolve_db_error_categoria_non_mappata(self, mock_repo):
        mock_repo.return_value.resolve_prezzo_listino_v2.side_effect = DatabaseError(
            "Nessuna mappa categoria 3 -> listino per utility 5 emittente 42 (classe NULL) al 2026-06-01."
        )
        with self.assertRaises(ServiceError) as ctx:
            PricingService().resolve_prezzo(**_base_kwargs())
        self.assertEqual(ctx.exception.code, "E_CATEGORIA_LISTINO_NON_MAPPATA")

    @patch(_REPO, autospec=True)
    def test_resolve_db_error_non_negoziato_corto_non_matcha_generico(self, mock_repo):
        # Review B4 2026-04-15: il marker "non negoziato" e' comune.
        # Un messaggio che contiene "non negoziato" MA non il prefisso
        # "modalita' C:" NON deve matchare E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C
        # (evita falsi positivi su errori futuri non correlati).
        mock_repo.return_value.resolve_prezzo_listino_v2.side_effect = DatabaseError(
            "Un errore qualunque che contiene non negoziato come frase libera"
        )
        with self.assertRaises(ServiceError) as ctx:
            PricingService().resolve_prezzo(**_base_kwargs())
        self.assertEqual(ctx.exception.code, "E_VENDITE_PRICING_FAILED")

    @patch(_REPO, autospec=True)
    def test_resolve_db_error_non_negoziato_matcha_con_contesto_C(self, mock_repo):
        mock_repo.return_value.resolve_prezzo_listino_v2.side_effect = DatabaseError(
            "Contratto 7 modalita' C: articolo X/uom 3 non negoziato."
        )
        with self.assertRaises(ServiceError) as ctx:
            PricingService().resolve_prezzo(**_base_kwargs())
        self.assertEqual(ctx.exception.code, "E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C")

    @patch(_REPO, autospec=True)
    def test_resolve_db_error_generico(self, mock_repo):
        mock_repo.return_value.resolve_prezzo_listino_v2.side_effect = DatabaseError(
            "Errore sconosciuto del DB"
        )
        with self.assertRaises(ServiceError) as ctx:
            PricingService().resolve_prezzo(**_base_kwargs())
        self.assertEqual(ctx.exception.code, "E_VENDITE_PRICING_FAILED")
        # detail deve contenere il messaggio originale.
        self.assertIn("sconosciuto", ctx.exception.detail or "")

    # Scopo: il contesto scritto nel diario deve portare i DUE parametri che
    #        cambiano lo stadio a cui il resolver fallisce. Senza, due tentativi
    #        diversi lasciano nel log righe IDENTICHE e non si distinguono piu'
    #        a posteriori: e' l'ambiguita' che il 2026-08-19 ha fatto perdere
    #        tempo al team DB (brief-be-pricing-codice-errore-fantasma.md §6.3).
    @patch("apps.core.services.error_manager.ErrorManager.log_error_only")
    @patch(_REPO, autospec=True)
    def test_contesto_loggato_completo(self, mock_repo, mock_log):
        mock_repo.return_value.resolve_prezzo_listino_v2.side_effect = DatabaseError(
            "Errore sconosciuto del DB"
        )
        with self.assertRaises(ServiceError):
            PricingService().resolve_prezzo(
                **_base_kwargs(classe_utenza_id=3, listino_versione_id_preferito=77)
            )
        contesto = mock_log.call_args.kwargs["context"]
        self.assertEqual(contesto["classe_utenza_id"], 3)
        self.assertEqual(contesto["listino_versione_id_preferito"], 77)
        # E i campi storici non devono essere spariti nel frattempo.
        self.assertEqual(contesto["ba_id"], 100)
        self.assertEqual(contesto["utility_id"], 7)


# `TestResolveComposito` rimosso col cleanup legacy 2026-05-14: la fn DB
# `fn_resolve_prezzo_composito` + `PricingService.resolve_prezzo_composito`
# erano DEPRECATED dal modello unificato BoM 2026-05-13 e mai realmente
# invocate in produzione (preventivi usa snapshot loader, ordini/ddt non
# esistono). Per i test del nuovo path: `test_commesse_source_handlers.py`
# `BoMComponentExpanderTests` (snapshot loader).


# ══════════════════════════════════════════════════════════
#  BE-A5 — il resolver «a esito» (nucleo)
# ══════════════════════════════════════════════════════════
# Scopo: presidiare la differenza che giustifica il metodo nuovo: quando il
#        prezzo non e' risolvibile il nucleo **non solleva**. Se un giorno
#        tornasse a sollevare, il DDT ricomincerebbe a rifiutare le righe in
#        conto visione — e il difetto si vedrebbe in-app, non qui.
class TestResolvePrezzoEsito(TestCase):
    @patch(_REPO, autospec=True)
    def test_esito_risolto(self, mock_repo):
        mock_repo.return_value.resolve_prezzo_listino_v2_esito.return_value = {
            "prezzo_finale": Decimal("12.50"),
            "origine": "CATEGORIA",
            "esito_codice": None,
            "esito_context": None,
            "esito_valori": None,
        }
        out = PricingService().resolve_prezzo_esito(**_base_kwargs())
        self.assertEqual(out["prezzo_finale"], Decimal("12.50"))
        self.assertIsNone(out["esito_codice"])

    @patch(_REPO, autospec=True)
    def test_esito_non_risolto_non_solleva(self, mock_repo):
        # E' IL test di questa slice: prezzo assente, motivo valorizzato,
        # nessuna eccezione. Il guscio `resolve_prezzo` qui solleverebbe.
        mock_repo.return_value.resolve_prezzo_listino_v2_esito.return_value = {
            "prezzo_finale": None,
            "origine": None,
            "esito_codice": "E_CATEGORIA_LISTINO_NON_MAPPATA",
            "esito_context": {"utility_id": 7},
            "esito_valori": ["3", "7"],
        }
        out = PricingService().resolve_prezzo_esito(**_base_kwargs())
        self.assertIsNone(out["prezzo_finale"])
        self.assertEqual(out["esito_codice"], "E_CATEGORIA_LISTINO_NON_MAPPATA")

    @patch(_REPO, autospec=True)
    def test_esito_riga_assente(self, mock_repo):
        # Il guard vive nel repository (BE-A2): qui si presidia che il service
        # non addomestichi quell'errore trasformandolo in un prezzo mancante.
        mock_repo.return_value.resolve_prezzo_listino_v2_esito.side_effect = ServiceError(
            code="E_VENDITE_PRICING_ESITO_ASSENTE",
            message="Errore interno del calcolo prezzi.",
        )
        with self.assertRaises(ServiceError) as ctx:
            PricingService().resolve_prezzo_esito(**_base_kwargs())
        self.assertEqual(ctx.exception.code, "E_VENDITE_PRICING_ESITO_ASSENTE")

    @patch(_REPO, autospec=True)
    def test_esito_parametro_invalido_solleva(self, mock_repo):
        # Il nucleo non solleva per «prezzo non risolto», ma solleva ancora per
        # parametri invalidi: la traduzione deve restare.
        mock_repo.return_value.resolve_prezzo_listino_v2_esito.side_effect = DatabaseError(
            "Errore sconosciuto del DB"
        )
        with self.assertRaises(ServiceError) as ctx:
            PricingService().resolve_prezzo_esito(**_base_kwargs())
        self.assertEqual(ctx.exception.code, "E_VENDITE_PRICING_FAILED")

    @patch(_REPO, autospec=True)
    def test_esito_valida_gli_input(self, mock_repo):
        # DEC-7: i guard sono estratti in `_valida_input_resolver`, quindi
        # valgono identici sui due metodi. Se l'estrazione si scollegasse da
        # uno dei due, il repo verrebbe chiamato con input non validati.
        del mock_repo
        with self.assertRaises(ServiceError) as ctx:
            PricingService().resolve_prezzo_esito(**_base_kwargs(ba_id=-1))
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
