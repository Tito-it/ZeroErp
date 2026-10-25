# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari service preventivi vendita (CRUD, stato, righe, integrazione).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_crea_preventivo_ok — creazione con campi minimi
2) test_crea_preventivo_utility_mancante — validazione utility obbligatoria
3) test_aggiorna_preventivo_ok — aggiornamento in BOZZA
4) test_aggiorna_preventivo_fuori_bozza_decide_il_db — EMESSO: nessun guard Python, decide il lock DB
4b) test_aggiorna_preventivo_colonne_ferme_sul_campo — utility ed emittente: 400 sul campo (R-BE-10)
4c) test_aggiorna_preventivo_chiave_ignota_rifiutata — una chiave fuori whitelist e' un 400, non uno scarto
5) test_gestisci_riga_ok — aggiunta riga in BOZZA con ricalcolo totali
5b) test_gestisci_riga_padre_composito_prezzo_default_zero — composito senza prezzo → 0 placeholder
5c) test_gestisci_riga_non_composito_senza_prezzo_solleva — non composito + prezzo None → E_PREV_VALIDAZIONE
5d) test_gestisci_riga_prezzo_nan_e_un_400_col_campo — 2026-09-18: `NaN` sul prezzo era un 500 (`NaN >= 0` solleva), ora E_PREV_VALIDAZIONE col campo
5e) test_gestisci_riga_quantita_nan_e_un_400_col_campo — `NaN` sulla quantita' passava fino al DB (`NaN != 0` e' vero), ora E_PREV_VALIDAZIONE col campo
6) test_gestisci_riga_stato_non_modificabile — guard riga su stato EMESSO
7) test_gestisci_riga_articolo_mancante — validazione articolo_id obbligatorio
8) test_elimina_riga_ok — soft delete riga
9) test_elimina_riga_not_found — riga inesistente
9b) test_riga_di_un_altro_preventivo_rifiutata — aggiorna/elimina_riga di una riga di un altro preventivo: 404, il repository non e' toccato
10) test_push_a_commessa_ok — push preventivo ACCETTATO con righe eleggibili; lo stato lo proietta il DB (D-10)
10b) test_push_a_commessa_propaga_fatturazione_immediata — flag testata nel payload
10c) test_push_a_commessa_parziale_propaga_e_non_evade — all-or-nothing: ServiceError, niente transizione
10d) (ritirato 2026-10-12: la transizione EVASO non e' piu' del backend)
10e) (ritirato 2026-10-12: il gate EVASO bi-ramo e' del DB, pgTAP test-annullo-commessa-v1)
10f) test_push_a_commessa_selettivo_propaga_righe_ids — push righe_ids parziale: il sottoinsieme arriva all'orchestratore
10g) test_smistamento_ok — aggregato + righe dalle viste smistamento
10h) test_smistamento_senza_righe_aggregato_none — aggregato None senza fallback
10i) test_smistamento_not_found — 404 semantico
11) test_push_a_commessa_stato_non_ammesso — guard su stato BOZZA
12) test_push_a_commessa_nessuna_riga — guard nessuna riga eleggibile
13) test_genera_pratica_ok — genera pratica da ACCETTATO via BB crea_pratica
14) test_genera_pratica_stato_non_ammesso — guard su stato BOZZA
15) test_genera_pratica_ba_mancante — guard billing_account_id obbligatorio
16) test_get_preventivo_not_found — preventivo inesistente
16b) test_get_preventivo_include_capabilities — Fase 1: capabilities + righe + indirizzi nel detail
17) test_list_preventivi_paginazione_invalida — page < 1
18) test_gestisci_riga_auto_fill_da_resolver — prezzo popolato da resolver se assente
19) test_gestisci_riga_prezzo_uguale_resolver_ok — payload = resolver ok senza permesso
20) test_gestisci_riga_override_non_autorizzato — L1 blocca override senza permesso
21) test_gestisci_riga_override_superuser_ok — superuser bypassa L1, meta MANUALE
22) test_gestisci_riga_L2_sconto_entro_limite_ok — L1 ok + sconto 10% <= limite 15%
23) test_gestisci_riga_L2_sconto_oltre_limite_bloccato — sconto 20% > limite 15% -> E_PRICING_SCONTO_ECCESSIVO
24) test_gestisci_riga_L2_maggiorazione_oltre_limite_bloccato — +10% > limite 5% -> E_PRICING_MAGGIORAZIONE_ECCESSIVA
25) test_gestisci_riga_L2_superuser_bypass — superuser salta anche L2
26) test_list_riepilogo_iva_delega_a_repo — facade lettura riepilogo IVA aggregato
27) test_list_preventivi_default_solo_ultima_revisione_true — filtro lista default
28) test_list_preventivi_solo_ultima_revisione_false — toggle "Mostra storico"
29) test_gestisci_riga_deriva_qta_operativa_da_factor — qta_op = quantita*factor
30) test_gestisci_riga_deriva_qta_operativa_factor_default_1 — fallback factor=1
31) test_repository_list_righe_filtra_solo_attive — righe soft-delete escluse
32) test_gestisci_riga_init_componenti_chiamato — post-create_riga la fn init e' invocata
33) test_gestisci_riga_init_componenti_skip_admin_globale — admin globale (no emittente) salta init
33b) test_gestisci_riga_init_componenti_usa_emittente_preventivo — admin + emittente esplicito sul preventivo OK
33c) test_gestisci_riga_init_componenti_overrides_passati — form atomic: componenti_overrides nel payload → init
33d) test_gestisci_riga_componenti_overrides_unauthorized — gating L1 senza override → 403 E_PRICING_OVERRIDE_NON_AUTORIZZATO
33e) test_gestisci_riga_init_componenti_attivazioni_passate — modello unificato: componenti_attivazioni propagato a repo.init
33f) test_gestisci_riga_init_componenti_bom_vuota_propaga — repo solleva E_DOC_COMPOSITO_BOM_VUOTA → service propaga
33g) test_gestisci_riga_init_componenti_obbligatorio_disattivazione_bloccata — repo solleva E_DOC_COMPONENTE_OBBLIGATORIO → service propaga
33h) test_gestisci_riga_init_componenti_obbligatorio_prezzo_zero — repo solleva E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO → service propaga
34) test_aggiorna_riga_non_tocca_componenti — articolo_id immutabile, componenti stabili
34b) test_aggiorna_riga_rifiuta_componenti_overrides — PATCH con componenti_overrides → 422
34c) test_aggiorna_riga_rifiuta_componenti_attivazioni — PATCH con componenti_attivazioni → 422
35) test_list_componenti_riga_ok — lista componenti riga padre
36) test_list_componenti_riga_not_found — riga padre inesistente
37) test_list_componenti_riga_scope_violation — riga padre di altro preventivo
38) test_update_componente_ok — modifica prezzo componente
39) test_update_componente_not_found — componente inesistente
40) test_update_componente_url_tampering_riga_id — anti-tampering URL riga falsa
41) test_update_componente_scope_violation — componente di altro preventivo
42) test_update_componente_stato_non_modificabile — guard preventivo EMESSO
43) test_delete_componente_ok — soft delete componente
44) test_delete_componente_not_found — componente inesistente
45) test_preview_componenti_riga_ok — happy path preview (form atomic)
46) test_preview_componenti_riga_not_found — preventivo inesistente → 404
47) test_preview_componenti_riga_data_mancante — data NULL → 422
48) test_preview_componenti_riga_utility_mancante — utility NULL → 422 (no fallback 0)
49) test_preview_componenti_riga_emittente_non_risolvibile — admin globale + no emittente → 422
50) test_preview_componenti_riga_usa_emittente_preventivo — precedenza emittente preventivo
51) test_list_righe_preventivo_non_trovato_e_404 — «leggi prima la testata» (2026-09-21): E_PREV_NOT_FOUND
52) test_list_riepilogo_iva_preventivo_non_trovato_e_404 — idem sul riepilogo IVA
53) test_list_revisioni_preventivo_non_trovato_e_404 — idem sulle revisioni
54) test_list_righe_con_testata_delega_al_repo — caso felice: delega invariata
55) test_annullo_passa_dal_verbo — ANNULLATO via fn_annulla_preventivo, con e senza dichiarazione
56) test_annullo_dichiarazione_non_numerica — legami_confermati non intero → E_PREV_VALIDAZIONE col campo
57) test_annullo_preventivo_inesistente — E_PREV_NOT_FOUND prima del verbo
58) test_annullo_con_legami_codice_del_db — il rifiuto del verbo esce col suo codice (confirm_and_retry)
59) test_cambia_stato_errore_db_senza_codice — errore DB senza codice → 400 del dominio
60) test_get_legami_dopo_la_testata — «leggi prima la testata», poi il BB legami_del_documento

TestNormalizeComponentiOverrides:
- test_none_ritorna_none, test_dict_vuoto_ritorna_none
- test_decimal_string_normalizzato, test_numero_python_normalizzato,
  test_decimal_native_normalizzato
- test_valore_none_solleva, test_valore_stringa_vuota_solleva,
  test_valore_non_numerico_solleva, test_overrides_non_dict_solleva

TestNormalizeComponentiAttivazioni:
- test_none_ritorna_none, test_dict_vuoto_ritorna_none
- test_dict_bool_normalizzato
- test_valore_non_bool_solleva, test_attivazioni_non_dict_solleva
"""

import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.tests._helpers.modello_documento_mockato import ModelloDocumentoMockatoMixin
from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.service_errors import ServiceError
from apps.vendite.services._componenti_service_helpers import (
    normalize_componenti_attivazioni,
    normalize_componenti_overrides,
)


# Wrapper helper test-only: i `TestNormalizeComponenti*` chiamano l'helper
# fissando `error_code='E_PREV_VALIDAZIONE'` (semantica dominio preventivi).
# Evitano di replicare `error_code=...` sui ~15 callsite mantenendo la
# storica firma `(payload, *, function_name)` dei test pre-Fase H.
def _normalize_componenti_overrides(  # test helper
    overrides: Any, *, function_name: str,
) -> dict[str, str] | None:
    return normalize_componenti_overrides(
        overrides, function_name=function_name,
        error_code="E_PREV_VALIDAZIONE",
    )


def _normalize_componenti_attivazioni(
    attivazioni: Any, *, function_name: str,
) -> dict[str, bool] | None:
    return normalize_componenti_attivazioni(
        attivazioni, function_name=function_name,
        error_code="E_PREV_VALIDAZIONE",
    )


# Il dettaglio porta i `contatori` dei badge (BB `contatori_documento`), che
# contano le note sul DB: qui si sostituisce, o ogni test che passa dal
# dettaglio farebbe una query vera senza dirlo.
_SENZA_CONTATORI_DB = patch(
    "apps.vendite.services.preventivi_service.contatori_documento",
    new=lambda *_a, **_k: {"note": 0},
)


@_SENZA_CONTATORI_DB
class TestPreventiviService(ModelloDocumentoMockatoMixin, unittest.TestCase):

    def setUp(self):
        # Scopo: Prepara mock del repository per tutti i test.
        super().setUp()
        self.repo_patcher = patch(
            "apps.vendite.services.preventivi_service.PreventiviRepository"
        )
        self.MockRepoClass = self.repo_patcher.start()
        self.mock_repo = MagicMock()
        self.MockRepoClass.return_value = self.mock_repo
        # Default: preventivo NON agganciato a una pratica (push standalone). Il
        # ramo aggancio-commessa di push_a_commessa (rev.3) resta no-op — i test
        # pratica-aware lo sovrascrivono esplicitamente.
        self.mock_repo.get_pratica_id_by_preventivo_root.return_value = None

        # ⭐ Risolutore IVA (I3, 2026-08-31): collaboratore nuovo di
        # `gestisci_riga`. Mockato come il repository, e per la stessa ragione —
        # senza, questi test aprirebbero una connessione vera e in CI, dove il
        # DB non c'e', fallirebbero per un motivo che non c'entra con cio' che
        # verificano.
        # ⚠️ Il default risponde «nessun `iva_id`, nessun meta»: i casi che qui
        # non parlano di IVA restano identici a prima.
        # ⚠️ Si patcha `_risolvi_iva_riga` e non il BB: e' costruito da una
        #    FACTORY, quindi il service non nomina piu' `IvaResolverService`.
        self.iva_patcher = patch(
            "apps.vendite.services.preventivi_service._risolvi_iva_riga"
        )
        self.MockIva = self.iva_patcher.start()
        self.MockIva.return_value = (None, {})
        self.addCleanup(self.iva_patcher.stop)

        # Mock del repository BA usato dal BB `risolvi_cliente_coppia`: il
        # cliente del preventivo e' la coppia (istanza, utility) col suo BA
        # (brief-db-istanza-nasce-col-ba, R-2). Default: BA → istanza id=100,
        # la coppia ha il BA id=42.
        self.ba_repo_patcher = patch(
            "apps.vendite.services._cliente_coppia_documento.BillingAccountRepository"
        )
        self.MockBaRepoClass = self.ba_repo_patcher.start()
        self.mock_ba_repo = MagicMock()
        self.MockBaRepoClass.return_value = self.mock_ba_repo
        self.mock_ba_repo.get_istanza_utility_id.return_value = 100
        self.mock_ba_repo.get_id_by_coppia.return_value = 42
        # Lo stesso repository visto dal BB `istanza_del_billing_account`, che
        # legge l'istanza del BA nel suo modulo.
        self.ba_bb_patcher = patch(
            "apps.anagrafiche.services.billing_account_service.BillingAccountRepository",
            self.MockBaRepoClass,
        )
        self.ba_bb_patcher.start()

        # Default: capabilities vuote per i test che non si interessano del blob
        # (Fase 1 refactor frontend vendite: get_preventivo invoca la fn DB).
        self.mock_repo.get_capabilities.return_value = {}

        # Mock transaction.atomic → no-op context manager (test mock-only,
        # no DB connection). Necessario per cambia_stato accettazione che
        # avvolge update_preventivo + cambia_stato in transaction.atomic.
        self.atomic_patcher = patch(
            "apps.vendite.services.preventivi_service.transaction.atomic"
        )
        mock_atomic = self.atomic_patcher.start()
        mock_atomic.return_value.__enter__ = MagicMock(return_value=None)
        mock_atomic.return_value.__exit__ = MagicMock(return_value=False)

        # Mock degli helper che fanno user_model.objects.get(pk=...): senza
        # DB reale (test unit) la query fallirebbe. I test che vogliono
        # testare la logica emittente specifica possono ri-patcharli
        # localmente con side_effect/return_value.
        self.emittente_patcher = patch(
            "apps.vendite.services.preventivi_service._resolve_emittente_sr_id_or_raise",
            return_value=100,
        )
        self.emittente_patcher.start()
        # Variante safe chiamata da gestisci_riga per init componenti CASO A
        # (mockata a 100; i test che testano admin globale possono override
        # localmente a None).
        self.emittente_safe_patcher = patch(
            "apps.vendite.services._componenti_service_helpers.resolve_emittente_sr_id_safe",
            return_value=100,
        )
        self.emittente_safe_patcher.start()
        # validate_componenti_overrides_authorization (BB condiviso, importato
        # nel namespace preventivi_service) chiama PermissionResolver.check_azione
        # (SQL diretto con user.id) quando il payload contiene
        # componenti_overrides. Per i test unit senza DB, mocco il validator a
        # no-op per default. Test specifici che vogliono esercitare il gating L1
        # ri-patchano localmente.
        self.gating_overrides_patcher = patch(
            "apps.vendite.services.preventivi_service.validate_componenti_overrides_authorization",
            return_value=None,
        )
        self.gating_overrides_patcher.start()

    def tearDown(self):
        self.repo_patcher.stop()
        self.ba_repo_patcher.stop()
        self.ba_bb_patcher.stop()
        self.atomic_patcher.stop()
        self.emittente_patcher.stop()
        self.emittente_safe_patcher.stop()
        self.gating_overrides_patcher.stop()

    # ── Creazione ──

    # Scopo: Verifica creazione preventivo con campi minimi: con la sola istanza
    # il BA e' quello della coppia (istanza, utility), letto per chiave.
    def test_crea_preventivo_ok(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        self.mock_repo.create_preventivo.return_value = {
            "id": 1, "uid": "abc-123", "numero": "P-0001",
        }
        result = crea_preventivo({
            "utility_id": 5, "istanza_utility_id": 100,
        })
        self.assertEqual(result["id"], 1)
        self.mock_ba_repo.get_id_by_coppia.assert_called_once_with(100, 5)
        kwargs = self.mock_repo.create_preventivo.call_args.kwargs
        self.assertEqual(kwargs["billing_account_id"], 42)
        self.assertEqual(kwargs["istanza_utility_id"], 100)
        # Lo stato non si passa: lo mette il DB, lo stato iniziale del
        # vocabolario (brief-modello-documento-vendita P-2).
        self.assertNotIn("stato_doc_preventivo_id", kwargs)
        # Lo slot di default lo riempie il DB, nella transazione della
        # creazione (brief-db-indirizzi-documento-seguono-il-cliente, R-BE-1).
        self.mock_repo.riempi_indirizzo_default.assert_called_once_with(1)

    # Scopo: Verifica errore se utility_id mancante.
    def test_crea_preventivo_utility_mancante(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        with self.assertRaises(ServiceError) as ctx:
            crea_preventivo({})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    # Scopo: Verifica errore se ne' BA ne' istanza: il cliente del preventivo
    # non si ricava da niente.
    def test_crea_preventivo_istanza_mancante(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        with self.assertRaises(ServiceError) as ctx:
            crea_preventivo({"utility_id": 5})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.assertIn("istanza_utility_id", ctx.exception.message)
        # Repo INSERT non viene chiamato.
        self.mock_repo.create_preventivo.assert_not_called()

    # Scopo: Quando il payload ha solo BA (no istanza), il service deriva
    # l'istanza dal BA via BillingAccountRepository.get_istanza_utility_id.
    def test_crea_preventivo_istanza_derivata_da_ba(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        self.mock_ba_repo.get_istanza_utility_id.return_value = 200
        self.mock_repo.create_preventivo.return_value = {
            "id": 1, "uid": "abc-123", "numero": "P-0001",
        }
        crea_preventivo({"utility_id": 5, "billing_account_id": 42})
        self.mock_ba_repo.get_istanza_utility_id.assert_called_once_with(42)
        # La coerenza della coppia si legge con l'istanza derivata.
        self.mock_ba_repo.get_id_by_coppia.assert_called_once_with(200, 5)
        kwargs = self.mock_repo.create_preventivo.call_args.kwargs
        self.assertEqual(kwargs["istanza_utility_id"], 200)
        self.assertEqual(kwargs["billing_account_id"], 42)

    # Scopo: la coppia (istanza, utility) senza BA: la utility non e'
    # dichiarata sull'istanza → errore parlante PRIMA del trigger DB.
    def test_crea_preventivo_utility_istanza_incoerente(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        self.mock_ba_repo.get_id_by_coppia.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            crea_preventivo({
                "utility_id": 5, "istanza_utility_id": 100,
            })
        self.assertEqual(ctx.exception.code, "E_PREV_UTILITY_ISTANZA_INCOERENTE")
        self.mock_repo.create_preventivo.assert_not_called()

    # Scopo: BA che non e' quello della coppia (istanza, utility) → errore sul
    # campo del BA, prima dell'INSERT. Anche quando la coppia non ha BA: e'
    # il BA a essere fuori posto, non la utility.
    def test_crea_preventivo_ba_fuori_coppia_rifiutato(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        for ba_della_coppia in (42, None):
            with self.subTest(ba_della_coppia=ba_della_coppia):
                self.mock_ba_repo.get_id_by_coppia.return_value = ba_della_coppia
                with self.assertRaises(ServiceError) as ctx:
                    crea_preventivo({
                        "utility_id": 5, "istanza_utility_id": 100, "billing_account_id": 7,
                    })
                self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
                self.assertEqual(ctx.exception.context.get("field"), "billing_account_id")
        self.mock_repo.create_preventivo.assert_not_called()

    # Scopo: BA di un'istanza diversa da quella indicata → errore sul BA (BB
    # `istanza_del_billing_account`, lo stesso della pratica), senza leggere
    # la coppia. Prima della regola del 2 il preventivo non lo controllava.
    def test_crea_preventivo_ba_di_altra_istanza_rifiutato(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        with self.assertRaises(ServiceError) as ctx:
            crea_preventivo({
                "utility_id": 5, "istanza_utility_id": 999, "billing_account_id": 42,
            })
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.assertEqual(ctx.exception.context.get("field"), "billing_account_id")
        self.mock_ba_repo.get_id_by_coppia.assert_not_called()
        self.mock_repo.create_preventivo.assert_not_called()

    # Scopo: la FK composta fk_preventivi_ba_coppia, se scatta comunque (il BA
    # cambia coppia fra la lettura e l'INSERT), arriva come errore parlante sul
    # campo del BA, non come 500.
    def test_crea_preventivo_ba_di_altra_coppia_tradotto(self):
        from django.db import IntegrityError

        from apps.vendite.services.preventivi_service import crea_preventivo

        self.mock_ba_repo.get_id_by_coppia.return_value = 7
        self.mock_repo.create_preventivo.side_effect = IntegrityError(
            'insert or update on table "preventivi" violates foreign key '
            'constraint "fk_preventivi_ba_coppia"'
        )
        with self.assertRaises(ServiceError) as ctx:
            crea_preventivo({
                "utility_id": 5, "istanza_utility_id": 100, "billing_account_id": 7,
            })
        self.assertEqual(ctx.exception.code, "E_VENDITE_FK")
        self.assertEqual(ctx.exception.context.get("field"), "billing_account_id")

    # Scopo: emittente_fiscale_id esplicito (caso admin globale) viene passato
    # al repository senza alterazioni. Il trigger DB BEFORE INSERT lo lascia
    # invariato (skip auto-fill quando NEW.emittente_fiscale_id IS NOT NULL).
    def test_crea_preventivo_emittente_esplicito_admin_globale(self):
        from apps.vendite.services.preventivi_service import crea_preventivo

        self.mock_repo.create_preventivo.return_value = {
            "id": 1, "uid": "abc-123", "numero": "P-0001",
        }
        crea_preventivo({
            "utility_id": 5, "istanza_utility_id": 100,
            "emittente_fiscale_id": 77,
        })
        kwargs = self.mock_repo.create_preventivo.call_args.kwargs
        self.assertEqual(kwargs["emittente_fiscale_id"], 77)

    # ── Eliminazione bozza (abbandono drawer) ──

    # Scopo: hard-delete preventivo BOZZA senza righe ne' pratiche.
    def test_elimina_preventivo_bozza_orfana_ok(self):
        from apps.vendite.services.preventivi_service import elimina_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT",
        }
        self.mock_repo.count_righe.return_value = 0
        self.mock_repo.list_pratiche.return_value = []
        self.mock_repo.delete_preventivo.return_value = True

        result = elimina_preventivo(1)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["preventivo_id"], 1)
        self.mock_repo.delete_preventivo.assert_called_once_with(1)

    # Scopo: preventivo inesistente → E_PREV_NOT_FOUND, no DELETE.
    def test_elimina_preventivo_not_found(self):
        from apps.vendite.services.preventivi_service import elimina_preventivo

        self.mock_repo.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            elimina_preventivo(999)
        self.assertEqual(ctx.exception.code, "E_PREV_NOT_FOUND")
        self.mock_repo.delete_preventivo.assert_not_called()

    # Scopo: stato non DRAFT → E_PREV_STATO_NON_MODIFICABILE.
    def test_elimina_preventivo_stato_non_bozza_bloccato(self):
        from apps.vendite.services.preventivi_service import elimina_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO",
        }
        with self.assertRaises(ServiceError) as ctx:
            elimina_preventivo(1)
        self.assertEqual(ctx.exception.code, "E_PREV_STATO_NON_MODIFICABILE")
        self.mock_repo.delete_preventivo.assert_not_called()

    # Scopo: BOZZA con almeno una riga → E_PREV_STATO_NON_MODIFICABILE.
    def test_elimina_preventivo_con_righe_bloccato(self):
        from apps.vendite.services.preventivi_service import elimina_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT",
        }
        self.mock_repo.count_righe.return_value = 1
        with self.assertRaises(ServiceError) as ctx:
            elimina_preventivo(1)
        self.assertEqual(ctx.exception.code, "E_PREV_STATO_NON_MODIFICABILE")
        self.mock_repo.delete_preventivo.assert_not_called()

    # ── Cambio stato → ACCETTATO (modalita' fatturazione) ──

    # Scopo: ACCETTATO con immediata=True forza competenza al primo del mese.
    def test_cambia_stato_accettato_immediata_force_competenza(self):
        from datetime import date
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "EMESSO",
        }
        self.mock_repo.cambia_stato.return_value = {"status": "ok"}
        cambia_stato(1, "ACCETTATO", fatturazione_immediata=True,
                     competenza_mese=date(2026, 7, 15))  # ignorata
        # update_preventivo deve essere chiamato con immediata=True e
        # competenza=primo del mese corrente (oggi.replace(day=1)).
        kwargs = self.mock_repo.update_preventivo.call_args.kwargs
        self.assertTrue(kwargs["fatturazione_immediata"])
        expected = oggi_aziendale().replace(day=1)
        self.assertEqual(kwargs["competenza_mese"], expected)
        self.mock_repo.cambia_stato.assert_called_once_with(1, "ACCETTATO")

    # Scopo: ACCETTATO con immediata=False richiede competenza esplicita.
    def test_cambia_stato_accettato_non_immediata_con_competenza_ok(self):
        from datetime import date
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "EMESSO",
        }
        self.mock_repo.cambia_stato.return_value = {"status": "ok"}
        cambia_stato(1, "ACCETTATO", fatturazione_immediata=False,
                     competenza_mese=date(2026, 8, 1))
        kwargs = self.mock_repo.update_preventivo.call_args.kwargs
        self.assertFalse(kwargs["fatturazione_immediata"])
        self.assertEqual(kwargs["competenza_mese"], date(2026, 8, 1))

    # Scopo: ACCETTATO senza fatturazione_immediata → E_PREV_VALIDAZIONE.
    def test_cambia_stato_accettato_senza_immediata_bloccato(self):
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "EMESSO",
        }
        with self.assertRaises(ServiceError) as ctx:
            cambia_stato(1, "ACCETTATO")
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.update_preventivo.assert_not_called()
        self.mock_repo.cambia_stato.assert_not_called()

    # Scopo: ACCETTATO con immediata=False senza competenza → E_PREV_VALIDAZIONE.
    def test_cambia_stato_accettato_non_immediata_senza_competenza_bloccato(self):
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "EMESSO",
        }
        with self.assertRaises(ServiceError) as ctx:
            cambia_stato(1, "ACCETTATO", fatturazione_immediata=False,
                         competenza_mese=None)
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.update_preventivo.assert_not_called()

    # Scopo: M-2 — cambia_stato non porta allo stato di emissione.
    # L'invariante "EMESSO => almeno una versione PDF" e' garantita dal
    # flusso `ApiPreventivoEmetti` che orchestra atomic
    # state+genera_documento+allegati nella view. Quale stato sia l'emissione
    # lo dice il vocabolario: la domanda va al BB con la testata del
    # preventivo, e il 400 porta il campo del corpo.
    def test_cambia_stato_rifiuta_emesso(self):
        from apps.vendite.services.preventivi_service import cambia_stato

        self.stato_chiesto_di_emissione()
        with self.assertRaises(ServiceError) as ctx:
            cambia_stato(1, "EMESSO")
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.assertEqual(ctx.exception.context.get("field"), "nuovo_stato")
        self.modello_documento.e_stato_di_emissione.assert_called_once_with(
            "vendite.preventivi", "EMESSO",
        )
        # Nessuna chiamata al repo: il guard scatta prima di qualsiasi I/O.
        self.mock_repo.cambia_stato.assert_not_called()
        self.mock_repo.update_preventivo.assert_not_called()

    # Scopo: §8.7 punto 5 — su un preventivo gia' ACCETTATO la richiesta
    # aggiorna la sola modalita' di fatturazione e NON chiama il verbo: la
    # matrice non ha ACCETTATO → ACCETTATO, e il verbo risponderebbe
    # E_PREV_TRANSIZIONE_NON_AMMESSA.
    def test_cambia_stato_accettato_su_accettato_non_chiama_il_verbo(self):
        from datetime import date
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO",
        }
        out = cambia_stato(1, "ACCETTATO", fatturazione_immediata=False,
                           competenza_mese=date(2026, 9, 1))
        kwargs = self.mock_repo.update_preventivo.call_args.kwargs
        self.assertFalse(kwargs["fatturazione_immediata"])
        self.assertEqual(kwargs["competenza_mese"], date(2026, 9, 1))
        self.mock_repo.cambia_stato.assert_not_called()
        self.assertEqual(out, {
            "preventivo_id": 1,
            "stato_precedente": "ACCETTATO",
            "stato_nuovo": "ACCETTATO",
        })

    # brief-db-annullo-documento-con-legami: ANNULLATO passa SEMPRE dal verbo,
    # con la dichiarazione della conferma (assente al primo tentativo), e la
    # risposta ha la forma di `fn_cambia_stato_preventivo`.
    def test_annullo_passa_dal_verbo(self):
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.get_stato_codice.return_value = "EMESSO"
        out = cambia_stato(7, "ANNULLATO")
        self.mock_repo.annulla.assert_called_once_with(7, None)
        self.mock_repo.cambia_stato.assert_not_called()
        self.assertEqual(out, {
            "preventivo_id": 7,
            "stato_precedente": "EMESSO",
            "stato_nuovo": "ANNULLATO",
        })
        cambia_stato(7, "ANNULLATO", legami_confermati="3")
        self.mock_repo.annulla.assert_called_with(7, 3)

    def test_annullo_dichiarazione_non_numerica(self):
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.get_stato_codice.return_value = "EMESSO"
        with self.assertRaises(ServiceError) as cm:
            cambia_stato(7, "ANNULLATO", legami_confermati="tre")
        self.assertEqual(cm.exception.code, "E_PREV_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("field"), "legami_confermati")
        self.mock_repo.annulla.assert_not_called()

    def test_annullo_preventivo_inesistente(self):
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.get_stato_codice.return_value = None
        with self.assertRaises(ServiceError) as cm:
            cambia_stato(99, "ANNULLATO")
        self.assertEqual(cm.exception.code, "E_PREV_NOT_FOUND")
        self.mock_repo.annulla.assert_not_called()

    # ⭐ Il rifiuto del verbo arriva col SUO codice, tradotto dal BB del
    #    dominio: e' il comportamento che la finestra riconosce.
    def test_annullo_con_legami_codice_del_db(self):
        from django.db import DatabaseError

        from apps.core.services.error_policies import ErrorPolicyRegistry
        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.get_stato_codice.return_value = "ACCETTATO"
        self.mock_repo.annulla.side_effect = DatabaseError(
            "E_DOC_ANNULLO_CON_LEGAMI: annullando Preventivo 12 si riaprono 2 legami",
        )
        with self.assertRaises(ServiceError) as cm:
            cambia_stato(7, "ANNULLATO")
        self.assertEqual(cm.exception.code, "E_DOC_ANNULLO_CON_LEGAMI")
        self.assertEqual(cm.exception.context.get("op"), "vendite.preventivi_service.cambia_stato")
        policy = ErrorPolicyRegistry.resolve("E_DOC_ANNULLO_CON_LEGAMI")
        self.assertEqual(policy.ui_action, "confirm_and_retry")

    # Le altre transizioni passano dallo stesso traduttore: un errore DB senza
    # codice e' il 400 del dominio, non un 500 generico.
    def test_cambia_stato_errore_db_senza_codice(self):
        from django.db import DatabaseError

        from apps.vendite.services.preventivi_service import cambia_stato

        self.mock_repo.cambia_stato.side_effect = DatabaseError("qualcosa e' andato storto")
        with self.assertRaises(ServiceError) as cm:
            cambia_stato(7, "RIFIUTATO")
        self.assertEqual(cm.exception.code, "E_PREV_VALIDAZIONE")

    def test_get_legami_dopo_la_testata(self):
        from apps.vendite.services import preventivi_service

        with patch.object(
            preventivi_service, "legami_del_documento", return_value={"legami": 0},
        ) as bb:
            self.mock_repo.get_stato_codice.return_value = None
            with self.assertRaises(ServiceError) as cm:
                preventivi_service.get_legami(99)
            self.assertEqual(cm.exception.code, "E_PREV_NOT_FOUND")
            bb.assert_not_called()
            self.mock_repo.get_stato_codice.return_value = "EMESSO"
            preventivi_service.get_legami(7)
            bb.assert_called_once_with("PREVENTIVO", 7)

    # Scopo: `emetti()` e' un thin wrapper sul repo che bypassa il guard
    # di cambia_stato (l'orchestrazione atomic state+genera_documento+
    # allegati vive nella view ApiPreventivoEmetti).
    def test_emetti_delega_a_repo(self):
        from apps.vendite.services.preventivi_service import emetti

        self.mock_repo.cambia_stato.return_value = {"status": "ok"}
        # Preventivo non agganciato a un flusso → l'auto-completamento e' no-op
        # (emetti resta un thin wrapper sul repo).
        self.mock_repo.get_flusso_id_by_preventivo_root.return_value = None
        result = emetti(42)
        self.assertEqual(result, {"status": "ok"})
        self.mock_repo.cambia_stato.assert_called_once_with(42, "EMESSO")
        self.mock_repo.get_flusso_id_by_preventivo_root.assert_called_once_with(42)

    # Scopo: emettendo un preventivo agganciato a un flusso IN_CORSO, quel flusso
    # (aggancio per-flusso, reverse diretto) viene auto-completato POSITIVO.
    @patch("apps.pratiche.services.pratiche_service.completa_flusso")
    @patch("apps.pratiche.db.pratiche_repository.PraticheRepository")
    def test_emetti_autocompleta_flusso_preventivazione(self, MockPratRepo, mock_completa):
        from apps.vendite.services.preventivi_service import emetti

        self.mock_repo.cambia_stato.return_value = {"status": "ok"}
        self.mock_repo.get_flusso_id_by_preventivo_root.return_value = 315
        MockPratRepo.return_value.get_flusso.return_value = {
            "stato_codice_interno": "IN_CORSO",
        }

        emetti(7, user="giacomo")

        self.mock_repo.get_flusso_id_by_preventivo_root.assert_called_once_with(7)
        MockPratRepo.return_value.get_flusso.assert_called_once_with(315)
        mock_completa.assert_called_once_with(315, esito="POSITIVO", user="giacomo")

    # Scopo: emettendo un preventivo il cui flusso NON e' IN_CORSO (gia'
    # completato o non avviato) → nessun completamento, idempotente.
    @patch("apps.pratiche.services.pratiche_service.completa_flusso")
    @patch("apps.pratiche.db.pratiche_repository.PraticheRepository")
    def test_emetti_flusso_non_in_corso_no_completa(self, MockPratRepo, mock_completa):
        from apps.vendite.services.preventivi_service import emetti

        self.mock_repo.cambia_stato.return_value = {"status": "ok"}
        self.mock_repo.get_flusso_id_by_preventivo_root.return_value = 315
        MockPratRepo.return_value.get_flusso.return_value = {
            "stato_codice_interno": "COMPLETATO",
        }

        emetti(7)

        mock_completa.assert_not_called()

    # ── completa_smistamento — bivio-per-esito rev.3 ──

    # completa_smistamento e' testato al SUO confine: risoluzione pratica + guard
    # residuo + esito di ramo, delegando l'idempotenza/transizione al BB motore
    # `pratiche_service.completa_step_pratica` (mockato qui, testato in pratiche).
    _STEP = "apps.pratiche.services.pratiche_service.completa_step_pratica"

    def _mock_pratica(self, MockPratRepo, *, pratica_id=290):
        # preventivo → pratica dal link ROOT (per _resolve_pratica_id_da_preventivo).
        self.mock_repo.get_pratica_id_by_preventivo_root.return_value = pratica_id

    def _no_residuo(self):
        self.mock_repo.preventivo_ha_residuo_ordine.return_value = False
        self.mock_repo.preventivo_ha_residuo_commessa.return_value = False

    @staticmethod
    def _mock_ordine_origine(MockOrd, *, esiste):
        # Esito di ramo = STESSO lookup dell'handler (get_ordine_by_documento_origine):
        # ordine presente → MERCE_PRESENTE, assente → SOLO_SERVIZI.
        MockOrd.return_value.get_ordine_by_documento_origine.return_value = (
            {"id": 1, "numero": "ORD1"} if esiste else None
        )

    # Scopo: ramo MERCE — e' nato un ordine → esito MERCE_PRESENTE (9013/9014 dovuti).
    @patch("apps.vendite.db.ordini_repository.OrdiniRepository")
    @patch(_STEP)
    @patch("apps.pratiche.db.pratiche_repository.PraticheRepository")
    def test_completa_smistamento_merce(self, MockPratRepo, mock_step, MockOrd):
        from apps.vendite.services.preventivi_service import completa_smistamento

        self._mock_pratica(MockPratRepo)
        self._no_residuo()
        self._mock_ordine_origine(MockOrd, esiste=True)
        mock_step.return_value = {"flusso_id": 500, "stato_precedente": "IN_CORSO", "completato": True}

        out = completa_smistamento(7, user="op")

        self.assertEqual(out["esito"], "MERCE_PRESENTE")
        self.assertFalse(out["gia_completato"])
        mock_step.assert_called_once_with(
            290, template_codice="SMISTAMENTO", esito="MERCE_PRESENTE", user="op",
        )

    # Scopo: ramo SERVIZI — nessun ordine → esito SOLO_SERVIZI (ramo ordine morto).
    @patch("apps.vendite.db.ordini_repository.OrdiniRepository")
    @patch(_STEP)
    @patch("apps.pratiche.db.pratiche_repository.PraticheRepository")
    def test_completa_smistamento_servizi(self, MockPratRepo, mock_step, MockOrd):
        from apps.vendite.services.preventivi_service import completa_smistamento

        self._mock_pratica(MockPratRepo)
        self._no_residuo()
        self._mock_ordine_origine(MockOrd, esiste=False)
        mock_step.return_value = {"flusso_id": 500, "stato_precedente": "IN_CORSO", "completato": True}

        out = completa_smistamento(7)

        self.assertEqual(out["esito"], "SOLO_SERVIZI")
        mock_step.assert_called_once_with(
            290, template_codice="SMISTAMENTO", esito="SOLO_SERVIZI", user=None,
        )

    # Scopo: step gia' terminale (BB completato=False) → gia_completato=True.
    @patch("apps.vendite.db.ordini_repository.OrdiniRepository")
    @patch(_STEP)
    @patch("apps.pratiche.db.pratiche_repository.PraticheRepository")
    def test_completa_smistamento_idempotente(self, MockPratRepo, mock_step, MockOrd):
        from apps.vendite.services.preventivi_service import completa_smistamento

        self._mock_pratica(MockPratRepo)
        self._no_residuo()
        self._mock_ordine_origine(MockOrd, esiste=True)
        mock_step.return_value = {"flusso_id": 500, "stato_precedente": "COMPLETATO", "completato": False}

        out = completa_smistamento(7)

        self.assertTrue(out["gia_completato"])

    # Scopo: SMISTAMENTO non istanziato (BB flusso_id=None) → E_PREV_VALIDAZIONE.
    @patch("apps.vendite.db.ordini_repository.OrdiniRepository")
    @patch(_STEP)
    @patch("apps.pratiche.db.pratiche_repository.PraticheRepository")
    def test_completa_smistamento_step_non_istanziato(self, MockPratRepo, mock_step, MockOrd):
        from apps.vendite.services.preventivi_service import completa_smistamento

        self._mock_pratica(MockPratRepo)
        self._no_residuo()
        self._mock_ordine_origine(MockOrd, esiste=False)
        mock_step.return_value = {"flusso_id": None, "stato_precedente": None, "completato": False}

        with self.assertRaises(ServiceError) as ctx:
            completa_smistamento(7)
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    # Scopo: preventivo non in una pratica → E_VENDITA_PREVENTIVO_NON_COLLEGATO.
    @patch("apps.pratiche.db.pratiche_repository.PraticheRepository")
    def test_completa_smistamento_no_pratica(self, MockPratRepo):
        from apps.vendite.services.preventivi_service import completa_smistamento

        self.mock_repo.get_pratica_id_by_preventivo_root.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            completa_smistamento(7)
        self.assertEqual(ctx.exception.code, "E_VENDITA_PREVENTIVO_NON_COLLEGATO")

    # Scopo: residuo merce non smistato → E_VENDITA_SMISTAMENTO_NON_ESEGUITO
    # (guard PRIMA del BB: il BB non viene chiamato).
    @patch(_STEP)
    @patch("apps.pratiche.db.pratiche_repository.PraticheRepository")
    def test_completa_smistamento_residuo_blocca(self, MockPratRepo, mock_step):
        from apps.vendite.services.preventivi_service import completa_smistamento

        self._mock_pratica(MockPratRepo)
        self.mock_repo.preventivo_ha_residuo_ordine.return_value = True

        with self.assertRaises(ServiceError) as ctx:
            completa_smistamento(7)
        self.assertEqual(ctx.exception.code, "E_VENDITA_SMISTAMENTO_NON_ESEGUITO")
        mock_step.assert_not_called()

    # Scopo: push_a_commessa in contesto pratica → aggancia la commessa-servizi
    # come COLLEGATO (ramo servizi dello split, rev.3).
    @patch("apps.vendite.db.commesse_repository.CommesseRepository")
    @patch("apps.pratiche.db.pratiche_repository.PraticheRepository")
    @patch("apps.vendite.services.commesse_service.pr_run_commesse_push_one")
    def test_push_a_commessa_aggancia_a_pratica(self, mock_push_one, MockPratRepo, MockCommRepo):
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc",
        }
        self.mock_repo.count_righe_pushable.return_value = 2
        # preventivo in una pratica → aggancio commessa attivo.
        self.mock_repo.get_pratica_id_by_preventivo_root.return_value = 290
        MockCommRepo.return_value.get_commessa_viva_by_sorgente.return_value = 77
        mock_push_one.return_value = {
            "stato": "COMPLETATO", "dry_run": False, "push_log_id": 42,
            "durata_ms": 5, "handlers": [],
        }

        push_a_commessa(1)

        MockPratRepo.return_value.upsert_pratica_sorgente.assert_called_once_with(
            pratica_id=290, sorgente_codice="COMMESSA",
            sorgente_uid="77", ruolo_link="COLLEGATO",
        )
        # La commessa si cerca APERTA, con l'uid del preventivo come chiave.
        MockCommRepo.return_value.get_commessa_viva_by_sorgente.assert_called_once_with(
            sorgente_codice="PREVENTIVO", sorgente_chiave="abc",
        )

    # ── Eliminazione bozza (abbandono drawer) ──

    # Scopo: BOZZA senza righe ma con pratica collegata → bloccato.
    def test_elimina_preventivo_con_pratiche_bloccato(self):
        from apps.vendite.services.preventivi_service import elimina_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT",
        }
        self.mock_repo.count_righe.return_value = 0
        self.mock_repo.list_pratiche.return_value = [{"id": 50}]
        with self.assertRaises(ServiceError) as ctx:
            elimina_preventivo(1)
        self.assertEqual(ctx.exception.code, "E_PREV_STATO_NON_MODIFICABILE")
        self.mock_repo.delete_preventivo.assert_not_called()

    # ── Aggiornamento ──

    # Scopo: Verifica aggiornamento in stato BOZZA.
    def test_aggiorna_preventivo_ok(self):
        from apps.vendite.services.preventivi_service import aggiorna_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        self.mock_repo.update_preventivo.return_value = True
        result = aggiorna_preventivo(1, {"validita_dal": "2026-04-01"})
        self.assertEqual(result["status"], "ok")
        # Il cliente non e' nel payload: la coppia non si rilegge.
        self.mock_ba_repo.get_id_by_coppia.assert_not_called()

    # Scopo: il cliente si cambia per coppia — col solo BA nel payload l'istanza
    # e' la sua, con la utility (immutabile) della testata. Senza, l'UPDATE
    # lascerebbe l'istanza vecchia e la FK composta lo rifiuterebbe.
    def test_aggiorna_preventivo_cambio_ba_porta_l_istanza(self):
        from apps.vendite.services.preventivi_service import aggiorna_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc", "utility_id": 5,
        }
        self.mock_ba_repo.get_istanza_utility_id.return_value = 300
        aggiorna_preventivo(1, {"billing_account_id": 42})
        self.mock_ba_repo.get_id_by_coppia.assert_called_once_with(300, 5)
        kwargs = self.mock_repo.update_preventivo.call_args.kwargs
        self.assertEqual(kwargs["billing_account_id"], 42)
        self.assertEqual(kwargs["istanza_utility_id"], 300)

    # Scopo: in modifica la utility e' immutabile: un BA di un'altra utility
    # (la coppia della testata non ha BA) e' un errore sul BA, mai «utility non
    # coerente» su un campo che l'operatore non puo' toccare.
    def test_aggiorna_preventivo_ba_altra_utility_errore_sul_ba(self):
        from apps.vendite.services.preventivi_service import aggiorna_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc", "utility_id": 5,
        }
        self.mock_ba_repo.get_istanza_utility_id.return_value = 300
        self.mock_ba_repo.get_id_by_coppia.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            aggiorna_preventivo(1, {"billing_account_id": 42})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.assertEqual(ctx.exception.context.get("field"), "billing_account_id")
        self.mock_repo.update_preventivo.assert_not_called()

    # Scopo: utility ed emittente non si cambiano in modifica (R-BE-10,
    #        2026-10-19): un 400 sul campo, con la frase del lock del DB, prima
    #        di leggere la testata. Fino ad allora si SCARTAVANO in silenzio.
    def test_aggiorna_preventivo_colonne_ferme_sul_campo(self):
        from apps.core.services.error_policies import ErrorPolicyRegistry
        from apps.vendite.services.preventivi_service import aggiorna_preventivo

        for chiave, codice_db in (
            ("utility_id", "E_DOC_UTILITY_IMMUTABILE"),
            ("emittente_fiscale_id", "E_DOC_EMITTENTE_IMMUTABILE"),
        ):
            with self.subTest(chiave=chiave), self.assertRaises(ServiceError) as ctx:
                aggiorna_preventivo(1, {chiave: 7, "validita_dal": "2026-04-01"})
            self.assertEqual(
                (ctx.exception.code, ctx.exception.context.get("field"), ctx.exception.message),
                ("E_PREV_VALIDAZIONE", chiave, ErrorPolicyRegistry.resolve(codice_db).user_message),
            )
        self.mock_repo.update_preventivo.assert_not_called()

    # Scopo: una chiave fuori dalla whitelist e' un 400 (R-BE-10, 2026-10-19):
    #        prima si scartava e la risposta era ok.
    def test_aggiorna_preventivo_chiave_ignota_rifiutata(self):
        from apps.vendite.services.preventivi_service import aggiorna_preventivo

        with self.assertRaises(ServiceError) as ctx:
            aggiorna_preventivo(1, {"numero": "X"})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.assertEqual(ctx.exception.context.get("unknown_keys"), ["numero"])
        self.mock_repo.update_preventivo.assert_not_called()

    # Scopo: Preventivo EMESSO: quali colonne si cambiano lo dice il lock di
    #        testata del DB (brief-db-testata-dopo-emissione, D-0): il service
    #        non ha piu' un «solo in DRAFT» e passa la scrittura.
    def test_aggiorna_preventivo_fuori_bozza_decide_il_db(self):
        from apps.vendite.services.preventivi_service import aggiorna_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "EMESSO", "uid": "abc", "utility_id": 3,
        }
        aggiorna_preventivo(1, {"meta": {"nota": "x"}})
        self.mock_repo.update_preventivo.assert_called_once_with(1, meta={"nota": "x"})

    # ── Righe ──

    # Scopo: Verifica aggiunta riga in BOZZA con ricalcolo totali.
    def test_gestisci_riga_ok(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        # ⚠️ La testata porta ora anche emittente e data: dal 2026-08-31 la
        #    creazione riga risolve l'IVA, e senza quei due il risolutore non
        #    saprebbe rispondere. La proprieta' provata resta la stessa — la
        #    riga si crea — cambia il veicolo.
        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "emittente_fiscale_id": 3, "data": "2026-08-31",
        }
        self.mock_repo.create_riga.return_value = {"id": 10}
        result = gestisci_riga(1, {"articolo_id": "uuid-art-1"})
        self.assertEqual(result["id"], 10)
        self.mock_repo.create_riga.assert_called_once()

    # Scopo: ⭐ IL CABLAGGIO E' VISIBILE. Col risolutore mockato nessun altro
    #        test si accorgerebbe se qualcuno lo staccasse.
    def test_gestisci_riga_iva_dal_risolutore(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "emittente_fiscale_id": 3, "data": "2026-08-31",
            "billing_account_id": 100, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 10}
        self.MockIva.return_value = (9, {"iva_origine": "TITOLO", "iva_titolo_id": 4})

        gestisci_riga(1, {"articolo_id": "uuid-art-1"})

        # ⭐ Il cablaggio: la testata arriva al risolutore, il suo esito alla riga.
        self.assertEqual(self.MockIva.call_args.kwargs["articolo_id"], "uuid-art-1")
        scritta = self.mock_repo.create_riga.call_args.kwargs
        self.assertEqual(scritta["iva_id"], 9)
        self.assertEqual(scritta["meta"]["iva_origine"], "TITOLO")

    # Scopo: ⛔ `I6` — LA CASELLA E' CHIUSA. Un client che manda ancora `iva_id`
    #        deve vederlo IGNORATO: a decidere e' il risolutore.
    # ⚠️ Il valore non viene RESPINTO ma SCARTATO, e senza questo caso la
    #        chiusura sarebbe invisibile: la suite e' restata verde quando e'
    #        stata fatta, perche' nessun presidio copriva «il payload vince».
    # ⛔ E il risolutore va interrogato con `payload_iva_id=None`: passargli il
    #        valore del client lo farebbe scendere sul ramo di AUDIT, dove gli
    #        errori sono best-effort — cioe' la riga si salverebbe anche quando
    #        l'IVA non e' determinabile.
    def test_i6_iva_del_payload_ignorata(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "emittente_fiscale_id": 3, "data": "2026-08-31",
            "billing_account_id": 100, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 10}
        self.MockIva.return_value = (9, {"iva_origine": "TITOLO"})

        # ⛔ Dal 2026-10-20 `iva_id` nel payload e' un 400, non uno scarto.
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(1, {"articolo_id": "uuid-art-1", "iva_id": 999})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.create_riga.assert_not_called()

        gestisci_riga(1, {"articolo_id": "uuid-art-1"})
        self.assertIsNone(self.MockIva.call_args.kwargs["payload_iva_id"])
        self.assertEqual(self.mock_repo.create_riga.call_args.kwargs["iva_id"], 9)

    # Scopo: ⛔ `I6` sull'AGGIORNAMENTO: la chiave e' fuori dalla tupla inline,
    #        quindi un `iva_id` nel payload non raggiunge il repository.
    # ⚠️ Qui NON si ri-risolve, ed e' corretto: `articolo_id` non e' aggiornabile
    #        su una riga, quindi non c'e' niente che possa spostare la risposta.
    def test_i6_iva_non_aggiornabile(self):
        from apps.vendite.services.preventivi_service import aggiorna_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        self.mock_repo.update_riga.return_value = {"id": 10}

        # ⛔ Dal 2026-10-20 `iva_id` e' un 400, non uno scarto.
        with self.assertRaises(ServiceError) as ctx:
            aggiorna_riga(1, 10, {"descrizione": "nuova", "iva_id": 999})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.update_riga.assert_not_called()

        aggiorna_riga(1, 10, {"descrizione": "nuova"})

        # ⛔ I campi arrivano come **kwargs sparsi** (`update_riga(id, **campi)`),
        #    non dentro una chiave `update_fields`: la prima stesura di questo
        #    test guardava li' dentro, trovava un dizionario vuoto e passava
        #    SEMPRE — un presidio vacuo, verde anche rimettendo la chiave.
        campi = self.mock_repo.update_riga.call_args.kwargs
        self.assertIn("descrizione", campi)          # il test ha davvero morso
        self.assertNotIn("iva_id", campi)

    # Scopo: Verifica guard riga su stato EMESSO: il codice e' quello del DB, E_RIGA_DOC_NON_BOZZA.
    def test_gestisci_riga_stato_non_modificabile(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "EMESSO", "uid": "abc", "rev": 0,
        }
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(1, {"articolo_id": "uuid-art-1"})
        self.assertEqual(ctx.exception.code, "E_RIGA_DOC_NON_BOZZA")

    # Scopo: padre composito con payload senza prezzo_unitario → BE usa
    # placeholder 0 (sara' sovrascritto dal trigger DB _z90_ricalcola_padre
    # post fn_preventivo_riga_componenti_init). Verifica che repo.create_riga
    # riceva prezzo_unitario != None per non violare il NOT NULL DB.
    def test_gestisci_riga_padre_composito_prezzo_default_zero(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT",
            "emittente_fiscale_id": 3, "data": "2026-08-31", "uid": "abc",
        }
        self.mock_repo.is_articolo_composito.return_value = True
        self.mock_repo.create_riga.return_value = {"id": 10}

        gestisci_riga(1, {"articolo_id": "uuid-art-composito"})

        self.mock_repo.create_riga.assert_called_once()
        kwargs = self.mock_repo.create_riga.call_args.kwargs
        # Decimal(0) come placeholder, NON None
        self.assertIsNotNone(kwargs["prezzo_unitario"])
        self.assertEqual(Decimal(kwargs["prezzo_unitario"]), Decimal("0"))

    # Scopo: articolo NON composito + payload senza prezzo_unitario + resolver
    # che non valorizza → E_PREV_VALIDAZIONE parlante (defense-in-depth: FE
    # `canSave` blocca prima, ma il BE deve dare errore comprensibile invece
    # di lasciare passare None → E_DATABASE su NOT NULL violation).
    def test_gestisci_riga_non_composito_senza_prezzo_solleva(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            # missing_resolver_ctx: no BA/utility/data → resolver skip,
            # prezzo_finale=None propagato.
        }
        self.mock_repo.is_articolo_composito.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(1, {"articolo_id": "uuid-art-semplice"})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: Verifica errore se articolo_id mancante.
    def test_gestisci_riga_articolo_mancante(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(1, {"quantita": "10"})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    # Scopo: Verifica che prezzo negativo venga bloccato lato BE con messaggio
    #        parlante (E_PREV_VALIDAZIONE) invece di lasciare il CHECK DB
    #        (chk_prevrighe_quantita_prezzo) sollevare un errore generico.
    def test_gestisci_riga_prezzo_negativo_ko(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(1, {"articolo_id": "uuid-art-1", "prezzo_unitario": "-5.00"})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        # Repo non deve essere chiamato: validazione blocca PRIMA dell'INSERT.
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: Verifica che qta_operativa (sorgente) zero/negativa venga bloccata
    #        lato BE con messaggio parlante prima del CHECK DB.
    def test_gestisci_riga_quantita_non_positiva_ko(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(1, {"articolo_id": "uuid-art-1", "qta_operativa": "0"})
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: ⭐ Il caso che la copia inline non vedeva (2026-09-18): un JSON puo'
    #        portare `"NaN"`, `Decimal("NaN")` si costruisce senza protestare e
    #        `NaN >= 0` solleva `InvalidOperation` — fuori da ogni `except`, cioe'
    #        un 500 per un valore scritto da una persona. Ora e' un 400 col
    #        campo, dal BB `PayloadValidator`, e il repository non si tocca.
    def test_gestisci_riga_prezzo_nan_e_un_400_col_campo(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        for raw in ("NaN", "Infinity", "dieci", True):
            with self.subTest(raw=raw):
                with self.assertRaises(ServiceError) as ctx:
                    gestisci_riga(1, {"articolo_id": "uuid-art-1", "prezzo_unitario": raw})
                self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
                self.assertEqual(ctx.exception.context["field"], "prezzo_unitario")
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: ⭐ L'altra meta', ed e' la peggiore: `NaN != 0` e' VERO, quindi una
    #        quantita' NaN superava il guard e arrivava al DB, dove `NaN > 0` e'
    #        vero e il CHECK la lascia entrare. Ora e' un 400 col campo.
    def test_gestisci_riga_quantita_nan_e_un_400_col_campo(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        for raw in ("NaN", "-Infinity", "tre", False):
            with self.subTest(raw=raw):
                with self.assertRaises(ServiceError) as ctx:
                    gestisci_riga(1, {"articolo_id": "uuid-art-1", "qta_operativa": raw})
                self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
                self.assertEqual(ctx.exception.context["field"], "qta_operativa")
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: Verifica soft delete riga.
    def test_elimina_riga_ok(self):
        from apps.vendite.services.preventivi_service import elimina_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        self.mock_repo.delete_riga.return_value = True
        result = elimina_riga(1, 10)
        self.assertEqual(result["status"], "ok")

    # Scopo: Verifica errore riga inesistente.
    def test_elimina_riga_not_found(self):
        from apps.vendite.services.preventivi_service import elimina_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        self.mock_repo.delete_riga.return_value = False
        with self.assertRaises(ServiceError) as ctx:
            elimina_riga(1, 999)
        self.assertEqual(ctx.exception.code, "E_PREV_RIGA_NOT_FOUND")

    # Scopo: ⛔ una riga di UN ALTRO preventivo, chiesta con l'URL di questo,
    #        e' un 404 e non arriva al repository. La bozza si verifica sul
    #        preventivo dell'URL, l'UPDATE e il DELETE vanno per il solo
    #        `riga_id`: senza il guard di appartenenza la riga di B si
    #        modificava (o cancellava) col controllo di stato fatto su A.
    def test_riga_di_un_altro_preventivo_rifiutata(self):
        from apps.vendite.services.preventivi_service import aggiorna_riga, elimina_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        self.mock_repo.get_riga.return_value = {"id": 10, "preventivo_id": 2}

        for nome, chiamata in (
            ("aggiorna_riga", lambda: aggiorna_riga(1, 10, {"descrizione": "nuova"})),
            ("elimina_riga", lambda: elimina_riga(1, 10)),
        ):
            with self.subTest(nome), self.assertRaises(ServiceError) as ctx:
                chiamata()
            self.assertEqual(ctx.exception.code, "E_PREV_RIGA_NOT_FOUND")
        self.mock_repo.update_riga.assert_not_called()
        self.mock_repo.delete_riga.assert_not_called()

    # ── Componenti BoM CASO A ──

    # Scopo: post-create riga, init_componenti_riga viene chiamato col
    # set di parametri attesi (emittente_sr_id dal helper safe, data dalla
    # testata). Refactor componenti 2026-05-11.
    def test_gestisci_riga_init_componenti_chiamato(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        gestisci_riga(
            1, {"articolo_id": "uuid-art-1", "uom_operativa_id": 1},
            auth_user_id=100,
        )
        self.mock_repo.init_componenti_riga.assert_called_once()
        kwargs = self.mock_repo.init_componenti_riga.call_args.kwargs
        self.assertEqual(kwargs["riga_id"], 42)
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 100)

    # Scopo: admin globale (helper safe ritorna None) e preventivo SENZA
    # emittente_fiscale_id esplicito NON triggera init. Caso edge: skip
    # silenzioso perche' non sappiamo come pricing.
    def test_gestisci_riga_init_componenti_skip_admin_globale(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
            "emittente_fiscale_id": None,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        # Sovrascrivi mock setUp: emittente safe = None (admin globale)
        with patch(
            "apps.vendite.services._componenti_service_helpers.resolve_emittente_sr_id_safe",
            return_value=None,
        ):
            gestisci_riga(
                1, {"articolo_id": "uuid-art-1", "uom_operativa_id": 1},
                auth_user_id=100,
            )
        self.mock_repo.init_componenti_riga.assert_not_called()

    # Scopo: form atomic 2026-05-12 — il payload puo' includere
    # `componenti_overrides` (mappa componente_id → prezzo) raccolti dal
    # drawer FE. Il service li passa alla fn DB init, che applica gli
    # override invece del resolver. Gating L1 mockato (default no-op nei
    # test unit), il caso "unauthorized" e' coperto dal test apposito sotto.
    def test_gestisci_riga_init_componenti_overrides_passati(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        overrides = {"019d57c1-b2b2-7d3a-9ebb-421addc5f393": "75.00"}
        gestisci_riga(
            1, {
                "articolo_id": "uuid-art-1", "uom_operativa_id": 1,
                "componenti_overrides": overrides,
            },
            auth_user_id=100,
        )
        self.mock_repo.init_componenti_riga.assert_called_once()
        kwargs = self.mock_repo.init_componenti_riga.call_args.kwargs
        self.assertEqual(kwargs["componenti_overrides"], overrides)

    # Scopo: gating L1 — payload con componenti_overrides ma operatore
    # senza `prezzo_override_manuale` solleva E_PRICING_OVERRIDE_NON_AUTORIZZATO
    # (ServiceError 403) PRIMA di qualsiasi tocco DB.
    def test_gestisci_riga_componenti_overrides_unauthorized(self):
        from apps.vendite.services.preventivi_service import gestisci_riga
        from apps.core.services.error_manager import ServiceError

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        # Sovrascrivi mock setUp: rimetti il vero validator + mock check_azione
        # a False (operatore senza azione prezzo_override_manuale).
        self.gating_overrides_patcher.stop()
        try:
            with patch(
                "apps.vendite.services.preventivi_service.PermissionResolver.check_azione",
                return_value=False,
            ), patch(
                "apps.vendite.services.preventivi_service.get_user_model",
            ) as mock_user_model:
                mock_user_model.return_value.objects.get.return_value = MagicMock()
                with self.assertRaises(ServiceError) as ctx:
                    gestisci_riga(
                        1, {
                            "articolo_id": "uuid-art-1", "uom_operativa_id": 1,
                            "componenti_overrides": {"uuid-c1": "10.00"},
                        },
                        auth_user_id=100,
                    )
                self.assertEqual(ctx.exception.code, "E_PRICING_OVERRIDE_NON_AUTORIZZATO")
        finally:
            # Ripristina patcher per i test successivi (il setUp sara' rieseguito
            # ma per non rompere questo test specifico ricominciamo il patch).
            self.gating_overrides_patcher.start()

    # Scopo: modello unificato 2026-05-13 — il payload puo' includere
    # `componenti_attivazioni` (mappa componente_id → bool) per attivare
    # opzionali (default DB inserisce opzionali con `attivo=FALSE`) o
    # disattivare opzionali in re-init. Il service li propaga al repo;
    # il guard DB blocca tentativi su obbligatori.
    def test_gestisci_riga_init_componenti_attivazioni_passate(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        attivazioni = {
            "019d57c1-b2b2-7d3a-9ebb-421addc5f393": True,
            "019d57c1-b2b2-7d3a-9ebb-421addc5f394": False,
        }
        gestisci_riga(
            1, {
                "articolo_id": "uuid-art-1", "uom_operativa_id": 1,
                "componenti_attivazioni": attivazioni,
            },
            auth_user_id=100,
        )
        self.mock_repo.init_componenti_riga.assert_called_once()
        kwargs = self.mock_repo.init_componenti_riga.call_args.kwargs
        self.assertEqual(kwargs["componenti_attivazioni"], attivazioni)

    # Scopo: padre composito con BoM scaduta/non configurata alla data:
    # la fn DB solleva `E_DOC_COMPOSITO_BOM_VUOTA` e il service NON deve
    # ingoiare l'errore (no try/except attorno a init_componenti_riga).
    # Verifichiamo via side_effect sul mock repo.
    def test_gestisci_riga_init_componenti_bom_vuota_propaga(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        self.mock_repo.init_componenti_riga.side_effect = ServiceError(
            code="E_DOC_COMPOSITO_BOM_VUOTA",
            message="BoM vuota",
        )
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1, {"articolo_id": "uuid-art-1", "uom_operativa_id": 1},
                auth_user_id=100,
            )
        self.assertEqual(ctx.exception.code, "E_DOC_COMPOSITO_BOM_VUOTA")

    # Scopo: opzionale disattivato tramite componenti_attivazioni e' OK
    # via repo; obbligatorio disattivato fa scattare il trigger DB con
    # E_DOC_COMPONENTE_OBBLIGATORIO che si propaga al service.
    def test_gestisci_riga_init_componenti_obbligatorio_disattivazione_bloccata(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        self.mock_repo.init_componenti_riga.side_effect = ServiceError(
            code="E_DOC_COMPONENTE_OBBLIGATORIO",
            message="Componente obbligatorio: non disattivabile",
        )
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1, {
                    "articolo_id": "uuid-art-1", "uom_operativa_id": 1,
                    "componenti_attivazioni": {"uuid-c1": False},
                },
                auth_user_id=100,
            )
        self.assertEqual(ctx.exception.code, "E_DOC_COMPONENTE_OBBLIGATORIO")

    # Scopo: override prezzo=0 su componente obbligatorio e' bloccato dalla
    # fn DB con E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO; il service deve
    # propagare l'errore (no swallow).
    def test_gestisci_riga_init_componenti_obbligatorio_prezzo_zero(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        self.mock_repo.init_componenti_riga.side_effect = ServiceError(
            code="E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO",
            message="Componente obbligatorio: prezzo deve essere <> 0",
        )
        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1, {
                    "articolo_id": "uuid-art-1", "uom_operativa_id": 1,
                    "componenti_overrides": {"uuid-c1": "0.00"},
                },
                auth_user_id=100,
            )
        self.assertEqual(
            ctx.exception.code, "E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO",
        )

    # Scopo: admin globale CON `emittente_fiscale_id` esplicito sul
    # preventivo triggera init usando quell'emittente (precedenza
    # preventivo > operatore). Risolve bug "admin non puo' creare CASO A
    # via API" — refactor componenti rev 2026-05-12.
    def test_gestisci_riga_init_componenti_usa_emittente_preventivo(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
            "emittente_fiscale_id": 99,  # PK emittente del preventivo
        }
        self.mock_repo.create_riga.return_value = {"id": 42}
        self.mock_repo.get_emittente_sr_id_by_fiscale_id.return_value = 200
        with patch(
            "apps.vendite.services._componenti_service_helpers.resolve_emittente_sr_id_safe",
            return_value=None,  # operatore admin globale, no emittente proprio
        ):
            gestisci_riga(
                1, {"articolo_id": "uuid-art-1", "uom_operativa_id": 1},
                auth_user_id=100,
            )
        self.mock_repo.get_emittente_sr_id_by_fiscale_id.assert_called_once_with(99)
        self.mock_repo.init_componenti_riga.assert_called_once()
        kwargs = self.mock_repo.init_componenti_riga.call_args.kwargs
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 200)

    # Scopo: `aggiorna_riga` NON ammette cambio articolo (whitelist update
    # exclude `articolo_id`). I componenti CASO A iniziali dell'init
    # restano stabili: nessun purge/re-init scatta dal flusso update.
    # Verifica defense-in-depth: se il caller passa `articolo_id` nel
    # payload e' un 400 (dal 2026-10-20; prima veniva scartato in silenzio),
    # e i componenti non vengono toccati.
    def test_aggiorna_riga_non_tocca_componenti(self):
        from apps.vendite.services.preventivi_service import aggiorna_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        self.mock_repo.update_riga.return_value = True

        # Payload con articolo_id (rifiutato) + descrizione (ammessa)
        with self.assertRaises(ServiceError) as ctx:
            aggiorna_riga(
                1, 10,
                {"articolo_id": "uuid-new-art", "descrizione": "nuova"},
                auth_user_id=100,
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.update_riga.assert_not_called()
        self.mock_repo.purge_componenti_riga.assert_not_called()
        self.mock_repo.init_componenti_riga.assert_not_called()

    # Scopo: PATCH riga con `componenti_overrides` o `componenti_attivazioni`
    # nel payload deve fallire rumorosamente (422 E_PREV_VALIDAZIONE) invece
    # di scartare i campi silenziosamente. Modifica componenti via endpoint
    # dedicato `/righe/<riga_id>/componenti/<componente_id>/`.
    def test_aggiorna_riga_rifiuta_componenti_overrides(self):
        from apps.vendite.services.preventivi_service import aggiorna_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        with self.assertRaises(ServiceError) as ctx:
            aggiorna_riga(
                1, 10,
                {"componenti_overrides": {"uuid-c1": "10.00"}},
                auth_user_id=100,
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.update_riga.assert_not_called()

    def test_aggiorna_riga_rifiuta_componenti_attivazioni(self):
        from apps.vendite.services.preventivi_service import aggiorna_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 5,
        }
        with self.assertRaises(ServiceError) as ctx:
            aggiorna_riga(
                1, 10,
                {"componenti_attivazioni": {"uuid-c1": True}},
                auth_user_id=100,
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.update_riga.assert_not_called()

    # Scopo: list_componenti_riga ritorna la lista dal repo.
    def test_list_componenti_riga_ok(self):
        from apps.vendite.services.preventivi_service import list_componenti_riga

        self.mock_repo.get_riga.return_value = {
            "id": 10, "preventivo_id": 1,
            "articolo_id": "uuid-art", "meta": {},
        }
        self.mock_repo.list_componenti_riga.return_value = [
            {"id": 1, "componente_id": "c1", "prezzo_unitario": "200"},
            {"id": 2, "componente_id": "c2", "prezzo_unitario": "75"},
        ]
        result = list_componenti_riga(1, 10)
        self.assertEqual(len(result), 2)
        self.mock_repo.list_componenti_riga.assert_called_once_with(
            10, solo_attivi=True,
        )

    # Scopo: list su riga inesistente -> E_PREV_RIGA_NOT_FOUND.
    def test_list_componenti_riga_not_found(self):
        from apps.vendite.services.preventivi_service import list_componenti_riga

        self.mock_repo.get_riga.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            list_componenti_riga(1, 999)
        self.assertEqual(ctx.exception.code, "E_PREV_RIGA_NOT_FOUND")

    # Scopo: defense-in-depth — riga padre di altro preventivo -> 404.
    def test_list_componenti_riga_scope_violation(self):
        from apps.vendite.services.preventivi_service import list_componenti_riga

        self.mock_repo.get_riga.return_value = {
            "id": 10, "preventivo_id": 999,  # altro preventivo
            "articolo_id": "uuid-art", "meta": {},
        }
        with self.assertRaises(ServiceError) as ctx:
            list_componenti_riga(1, 10)
        self.assertEqual(ctx.exception.code, "E_PREV_RIGA_NOT_FOUND")

    # Scopo: update componente in BOZZA -> ok, delegato a repo.
    def test_update_componente_ok(self):
        from apps.vendite.services.preventivi_service import update_componente

        # 1-JOIN restituisce scope completo + stato in colpo unico.
        self.mock_repo.load_componente_with_scope.return_value = {
            "componente_id": 50,
            "riga_preventivo_id": 10,
            "preventivo_id": 1,
            "stato_codice_interno": "DRAFT",
        }
        self.mock_repo.update_componente.return_value = True

        # Un prezzo scritto passa dal gate L1 con l'utente (2026-10-20).
        with patch(
            "apps.vendite.services._componenti_service_helpers.check_permesso_override_prezzo",
        ) as gate:
            result = update_componente(1, 10, 50, {"prezzo_unitario": "150.00"}, auth_user_id=42)
        gate.assert_called_once()
        self.assertEqual(gate.call_args.args[0], 42)
        self.assertEqual(result["componente_id"], 50)
        # `origine_prezzo` la scrive il server: un prezzo dell'operatore e'
        # MANUALE per definizione (contratto PATCH, 2026-09-26).
        self.mock_repo.update_componente.assert_called_once_with(
            50, prezzo_unitario="150.00", origine_prezzo="MANUALE",
        )

    # Scopo: ⛔ l'operatore NON puo' approvarsi un prezzo L3. Fino al 2026-09-26
    #        la PATCH validava contro la whitelist del repository, che contiene
    #        `stato_approvazione_prezzo`: `{"stato_approvazione_prezzo":
    #        "APPROVED"}` su un componente PENDING passava anche il guard DB.
    #        Stesso rifiuto per la pratica e per un'origine dichiarata dal client.
    def test_update_componente_campi_del_workflow_rifiutati(self):
        from apps.core.services.service_errors import ServiceError
        from apps.vendite.services.preventivi_service import update_componente

        self.mock_repo.load_componente_with_scope.return_value = {
            "componente_id": 50,
            "riga_preventivo_id": 10,
            "preventivo_id": 1,
            "stato_codice_interno": "DRAFT",
        }
        for payload in (
            {"stato_approvazione_prezzo": "APPROVED"},
            {"pratica_approvazione_prezzo_id": 7},
            {"prezzo_unitario": "1.00", "origine_prezzo": "CONTRATTO_LISTINO"},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ServiceError) as ctx:
                    update_componente(1, 10, 50, payload)
                self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.update_componente.assert_not_called()

    # Scopo: chiave fuori `COMPONENTE_UPDATE_ALLOWED` -> 400 che la nomina,
    #        repository non chiamato. ⛔ Fino al 2026-09-26 il mixin la
    #        scartava in silenzio e la PATCH «riusciva».
    def test_update_componente_chiave_fuori_whitelist_400(self):
        from apps.vendite.services.preventivi_service import update_componente

        self.mock_repo.load_componente_with_scope.return_value = {
            "componente_id": 50,
            "riga_preventivo_id": 10,
            "preventivo_id": 1,
            "stato_codice_interno": "DRAFT",
        }
        with self.assertRaises(ServiceError) as ctx:
            update_componente(
                1, 10, 50, {"prezzo_unitario": "150.00", "coeff_qta_snapshot": 2},
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.assertEqual(ctx.exception.context["unknown_keys"], ["coeff_qta_snapshot"])
        self.mock_repo.update_componente.assert_not_called()

    # Scopo: componente inesistente -> 404.
    def test_update_componente_not_found(self):
        from apps.vendite.services.preventivi_service import update_componente

        self.mock_repo.load_componente_with_scope.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            update_componente(1, 10, 999, {"prezzo_unitario": "100"})
        self.assertEqual(ctx.exception.code, "E_PREV_COMPONENTE_NOT_FOUND")

    # Scopo: anti-tampering URL — `riga_id` URL non matcha la riga padre
    # reale del componente -> 404. Defense-in-depth contro URL forgiati.
    def test_update_componente_url_tampering_riga_id(self):
        from apps.vendite.services.preventivi_service import update_componente

        # 1-JOIN: componente esiste ma appartiene a riga 10, URL chiede 999.
        self.mock_repo.load_componente_with_scope.return_value = {
            "componente_id": 50,
            "riga_preventivo_id": 10,  # riga reale = 10
            "preventivo_id": 1,
            "stato_codice_interno": "DRAFT",
        }
        with self.assertRaises(ServiceError) as ctx:
            update_componente(1, 999, 50, {"prezzo_unitario": "100"})
        self.assertEqual(ctx.exception.code, "E_PREV_COMPONENTE_NOT_FOUND")

    # Scopo: defense-in-depth — componente su altro preventivo -> 404.
    def test_update_componente_scope_violation(self):
        from apps.vendite.services.preventivi_service import update_componente

        # 1-JOIN: componente vive su preventivo 999, URL chiede 1.
        self.mock_repo.load_componente_with_scope.return_value = {
            "componente_id": 50,
            "riga_preventivo_id": 10,
            "preventivo_id": 999,  # altro preventivo
            "stato_codice_interno": "DRAFT",
        }
        with self.assertRaises(ServiceError) as ctx:
            update_componente(1, 10, 50, {"prezzo_unitario": "100"})
        self.assertEqual(ctx.exception.code, "E_PREV_COMPONENTE_NOT_FOUND")

    # Scopo: guard stato preventivo non modificabile sui componenti (E_RIGA_DOC_NON_BOZZA, come le righe).
    def test_update_componente_stato_non_modificabile(self):
        from apps.vendite.services.preventivi_service import update_componente

        self.mock_repo.load_componente_with_scope.return_value = {
            "componente_id": 50,
            "riga_preventivo_id": 10,
            "preventivo_id": 1,
            "stato_codice_interno": "EMESSO",  # non modificabile
            "rev": 0,  # l'etichetta del rifiuto porta la revisione
        }
        with self.assertRaises(ServiceError) as ctx:
            update_componente(1, 10, 50, {"prezzo_unitario": "100"})
        self.assertEqual(ctx.exception.code, "E_RIGA_DOC_NON_BOZZA")

    # Scopo: soft delete componente in BOZZA.
    def test_delete_componente_ok(self):
        from apps.vendite.services.preventivi_service import delete_componente

        self.mock_repo.load_componente_with_scope.return_value = {
            "componente_id": 50,
            "riga_preventivo_id": 10,
            "preventivo_id": 1,
            "stato_codice_interno": "DRAFT",
        }
        self.mock_repo.delete_componente.return_value = True
        result = delete_componente(1, 10, 50)
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["deleted"])
        self.mock_repo.delete_componente.assert_called_once_with(50)

    # Scopo: delete componente inesistente -> 404.
    def test_delete_componente_not_found(self):
        from apps.vendite.services.preventivi_service import delete_componente

        self.mock_repo.load_componente_with_scope.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            delete_componente(1, 10, 999)
        self.assertEqual(ctx.exception.code, "E_PREV_COMPONENTE_NOT_FOUND")

    # ── Push commessa ──

    # Scopo: Verifica push preventivo ACCETTATO con righe eleggibili: il service
    # delega al CommessaPushOrchestrator filtrato (pr_run_commesse_push_one) e
    # restituisce il report aumentato di righe_pushable diagnostico.
    @patch("apps.vendite.services.commesse_service.pr_run_commesse_push_one")
    def test_push_a_commessa_ok(self, mock_push_one):
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc",
        }
        self.mock_repo.count_righe_pushable.return_value = 3
        mock_push_one.return_value = {
            "stato": "COMPLETATO",
            "dry_run": False,
            "push_log_id": 42,
            "durata_ms": 12,
            "handlers": [{"handler_name": "HandlerPreventivi", "errors": []}],
        }

        result = push_a_commessa(1)

        # Orchestrator chiamato con codice + uid corretti (righe_ids=None:
        # push completo, nessun sottoinsieme selettivo).
        mock_push_one.assert_called_once_with(
            sorgente_codice="PREVENTIVO",
            sorgente_uid=1,
            righe_ids=None,
        )
        # Payload completo: campi orchestrator + righe_pushable diagnostico
        # + flag fatturazione_immediata dalla testata (per hint UX FE).
        self.assertEqual(result["preventivo_id"], 1)
        self.assertEqual(result["stato"], "COMPLETATO")
        self.assertEqual(result["push_log_id"], 42)
        self.assertEqual(result["durata_ms"], 12)
        self.assertEqual(result["righe_pushable"], 3)
        self.assertEqual(len(result["handlers"]), 1)
        # testata mock non ha "fatturazione_immediata" -> default False (no hint UX).
        self.assertFalse(result["fatturazione_immediata"])
        # ⭐ ACCETTATO → EVASO lo proietta il DB (trigger delle righe di
        #    commessa, D-10 / R-8 di brief-db-annullo-a-valle-riapre-a-monte):
        #    il backend non tocca lo stato, ne' legge i residui.
        self.mock_repo.cambia_stato.assert_not_called()
        self.mock_repo.preventivo_ha_residuo_ordine.assert_not_called()
        self.mock_repo.preventivo_ha_residuo_commessa.assert_not_called()

    # Scopo: post all-or-nothing, pr_run_commesse_push_one solleva
    # E_COMMESSA_PUSH_PARZIALE_VIETATO su PARZIALE/ERRORE rollando ogni
    # scrittura. push_a_commessa propaga l'eccezione e NON transita stato:
    # il preventivo resta ACCETTATO, niente righe orfane in commessa.
    @patch("apps.vendite.services.commesse_service.pr_run_commesse_push_one")
    def test_push_a_commessa_parziale_propaga_e_non_evade(self, mock_push_one):
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc",
        }
        self.mock_repo.count_righe_pushable.return_value = 4
        mock_push_one.side_effect = ServiceError(
            code="E_COMMESSA_PUSH_PARZIALE_VIETATO",
            message="Push fallito: nessuna riga inviata.",
            detail="Errore riga segment_key=PREVENTIVO:abc:R:3: ...",
        )

        with self.assertRaises(ServiceError) as ctx:
            push_a_commessa(1)

        self.assertEqual(ctx.exception.code, "E_COMMESSA_PUSH_PARZIALE_VIETATO")
        # All-or-nothing: nessuna transizione stato, nessuna chiamata DB.
        self.mock_repo.cambia_stato.assert_not_called()

    # Scopo: payload include flag `fatturazione_immediata=True` se settato in
    # testata: serve al FE per mostrare hint warn "emit AF al prossimo lotto"
    # (placeholder per PR2 servizio emissione immediata).
    @patch("apps.vendite.services.commesse_service.pr_run_commesse_push_one")
    def test_push_a_commessa_propaga_fatturazione_immediata(self, mock_push_one):
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1,
            "stato_codice_interno": "ACCETTATO",
            "uid": "abc",
            "fatturazione_immediata": True,
        }
        self.mock_repo.count_righe_pushable.return_value = 1
        mock_push_one.return_value = {
            "stato": "COMPLETATO", "dry_run": False,
            "push_log_id": 7, "durata_ms": 5, "handlers": [],
        }

        result = push_a_commessa(1)

        self.assertTrue(result["fatturazione_immediata"])

    # Scopo: push SELETTIVO (righe_ids sottoinsieme, Pannello Smistamento): il
    # sottoinsieme arriva all'orchestratore. Che il preventivo resti ACCETTATO
    # finche' resta un residuo (sottoinsieme parziale, o merce da ordinare nel
    # preventivo misto) lo decide il DB (`fn_preventivo_proietta_stato_smistamento`):
    # il backend non tocca lo stato.
    @patch("apps.vendite.services.commesse_service.pr_run_commesse_push_one")
    def test_push_a_commessa_selettivo_propaga_righe_ids(self, mock_push_one):
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc",
        }
        self.mock_repo.count_righe_pushable.return_value = 3
        mock_push_one.return_value = {
            "stato": "COMPLETATO", "dry_run": False,
            "push_log_id": 9, "durata_ms": 4, "handlers": [],
        }

        result = push_a_commessa(1, righe_ids=[10, 11])

        mock_push_one.assert_called_once_with(
            sorgente_codice="PREVENTIVO",
            sorgente_uid=1,
            righe_ids=[10, 11],
        )
        self.assertEqual(result["stato"], "COMPLETATO")
        self.mock_repo.cambia_stato.assert_not_called()

    # ── Smistamento (pannello) ──

    # Scopo: smistamento() ritorna aggregato + righe dalla coppia di viste
    # vw_preventivi_smistamento / _righe (fonte dati del Pannello Smistamento).
    def test_smistamento_ok(self):
        from apps.vendite.services.preventivi_service import smistamento

        self.mock_repo.get_preventivo.return_value = {"id": 1, "uid": "abc"}
        self.mock_repo.stato_smistamento.return_value = {
            "preventivo_id": 1, "righe_totali": 3, "righe_merce": 2,
            "righe_servizi": 1, "righe_a_ordine": 1, "righe_in_commessa": 0,
            "righe_emesse_af": 0, "righe_fatturate": 0, "righe_residue": 2,
        }
        self.mock_repo.list_righe_smistamento.return_value = [
            {"riga_id": 10, "destinazione_tipo": "ORDINE_VENDITA", "stato_smistamento": "A_ORDINE"},
            {"riga_id": 11, "destinazione_tipo": "ORDINE_VENDITA", "stato_smistamento": "RESIDUA"},
            {"riga_id": 12, "destinazione_tipo": "COMMESSA", "stato_smistamento": "RESIDUA"},
        ]

        result = smistamento(1)

        self.assertEqual(result["aggregato"]["righe_residue"], 2)
        self.assertEqual(len(result["righe"]), 3)
        self.mock_repo.list_righe_smistamento.assert_called_once_with(1)

    # Scopo: preventivo senza righe attive → aggregato None propagato cosi'
    # com'e' (la vista GROUP BY non produce la riga; nessun fallback fabbricato
    # che duplicherebbe lo schema della vista), righe = [].
    def test_smistamento_senza_righe_aggregato_none(self):
        from apps.vendite.services.preventivi_service import smistamento

        self.mock_repo.get_preventivo.return_value = {"id": 1, "uid": "abc"}
        self.mock_repo.stato_smistamento.return_value = None
        self.mock_repo.list_righe_smistamento.return_value = []

        result = smistamento(1)

        self.assertIsNone(result["aggregato"])
        self.assertEqual(result["righe"], [])

    # Scopo: smistamento su preventivo inesistente → 404 semantico.
    def test_smistamento_not_found(self):
        from apps.vendite.services.preventivi_service import smistamento

        self.mock_repo.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            smistamento(999)
        self.assertEqual(ctx.exception.code, "E_PREV_NOT_FOUND")

    # Scopo: Verifica guard su stato non ACCETTATO.
    def test_push_a_commessa_stato_non_ammesso(self):
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
        }
        with self.assertRaises(ServiceError) as ctx:
            push_a_commessa(1)
        self.assertEqual(ctx.exception.code, "E_PREV_STATO_TRANSIZIONE")

    # Scopo: Verifica guard nessuna riga eleggibile.
    def test_push_a_commessa_nessuna_riga(self):
        from apps.vendite.services.preventivi_service import push_a_commessa

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc",
        }
        self.mock_repo.count_righe_pushable.return_value = 0
        with self.assertRaises(ServiceError) as ctx:
            push_a_commessa(1)
        self.assertEqual(ctx.exception.code, "E_PREV_NESSUNA_RIGA")

    # ── Genera pratica ──

    # Scopo: Verifica generazione pratica da preventivo ACCETTATO via fn madre
    #        atomica vendite.fn_genera_pratica_da_preventivo (fix #3). Il BE guarda
    #        stato/billing e delega crea-pratica + link ROOT alla fn (una statement).
    def test_genera_pratica_ok(self):
        from apps.vendite.services.preventivi_service import genera_pratica

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc-uid",
            "billing_account_id": 10, "istanza_utility_id": 5,
        }
        self.mock_repo.genera_pratica_da_preventivo.return_value = 42

        result = genera_pratica(1, tipo_prestazione_id=3, priorita_id=1)
        self.assertEqual(result["pratica_id"], 42)
        self.assertEqual(result["preventivo_id"], 1)
        # Contesto anagrafico + link ROOT sono risolti DENTRO la fn madre: il BE
        # passa solo preventivo + tipo prestazione + priorita + descrizione.
        self.mock_repo.genera_pratica_da_preventivo.assert_called_once_with(
            preventivo_id=1,
            tipo_prestazione_id=3,
            priorita_id=1,
            descrizione=None,
        )

    # Scopo: Verifica guard su stato non ACCETTATO.
    def test_genera_pratica_stato_non_ammesso(self):
        from apps.vendite.services.preventivi_service import genera_pratica

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "billing_account_id": 10,
        }
        with self.assertRaises(ServiceError) as ctx:
            genera_pratica(1, tipo_prestazione_id=3, priorita_id=1)
        self.assertEqual(ctx.exception.code, "E_PREV_PRATICA_STATO")

    # Scopo: Verifica guard billing_account_id obbligatorio per genera pratica.
    def test_genera_pratica_ba_mancante(self):
        from apps.vendite.services.preventivi_service import genera_pratica

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "ACCETTATO", "uid": "abc",
            "billing_account_id": None,
        }
        with self.assertRaises(ServiceError) as ctx:
            genera_pratica(1, tipo_prestazione_id=3, priorita_id=1)
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    # ── Not found ──

    # Scopo: Verifica errore preventivo non trovato.
    def test_get_preventivo_not_found(self):
        from apps.vendite.services.preventivi_service import get_preventivo

        self.mock_repo.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            get_preventivo(999)
        self.assertEqual(ctx.exception.code, "E_PREV_NOT_FOUND")

    # Scopo: righe smistabili a ordine — guard NOT_FOUND + delega al repository.
    def test_list_righe_smistabili_ordine_not_found(self):
        from apps.vendite.services.preventivi_service import (
            list_righe_smistabili_ordine,
        )

        self.mock_repo.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            list_righe_smistabili_ordine(999)
        self.assertEqual(ctx.exception.code, "E_PREV_NOT_FOUND")

    def test_list_righe_smistabili_ordine_ok(self):
        from apps.vendite.services.preventivi_service import (
            list_righe_smistabili_ordine,
        )

        self.mock_repo.get_preventivo.return_value = {"id": 1}
        self.mock_repo.list_righe_smistabili_ordine.return_value = [{"id": 10}]
        out = list_righe_smistabili_ordine(1)
        self.assertEqual(out, [{"id": 10}])
        self.mock_repo.list_righe_smistabili_ordine.assert_called_once_with(1)

    # Scopo: Verifica che get_preventivo includa capabilities + righe_count + indirizzi
    #        senza embeddare le righe (Fase 3.F6 refactor frontend vendite: il FE
    #        legge le righe via endpoint /righe/ autonomo).
    def test_get_preventivo_include_capabilities(self):
        from apps.vendite.services.preventivi_service import get_preventivo

        self.mock_repo.get_preventivo.return_value = {
            "id": 42, "uid": "abc", "numero": "P-0042",
            "stato_codice": "ACCETTATO", "stato_codice_interno": "ACCETTATO",
            "billing_account_id": 10, "utility_id": 3,
        }
        # righe_count da una COUNT sulle righe attive, senza caricare l'elenco.
        self.mock_repo.count_righe.return_value = 2
        self.mock_repo.list_indirizzi.return_value = []
        self.mock_repo.get_capabilities.return_value = {
            "stato_codice": "ACCETTATO",
            "available_actions": [{"key": "annulla", "target_state": "ANNULLATO",
                                    "label_key": "preventivi.azione_annulla",
                                    "severity": "danger",
                                    "requires_confirm": True}],
            "can_edit_testata": False,
            "can_edit_righe": False,
            "can_create_revisione": True,
            "can_push_commessa": True,
            "can_push_commessa_reason": None,
            "non_editable_fields": ["billing_account_id", "utility_id"],
        }

        result = get_preventivo(42)

        # Testata + capability (SOTTO `capabilities`, api.md §«Il blob sta
        # SOTTO `capabilities`») + summary leggero. NO `righe` embeddate.
        self.assertEqual(result["id"], 42)
        caps = result["capabilities"]
        self.assertEqual(caps, self.mock_repo.get_capabilities.return_value)
        self.assertEqual(caps["can_edit_testata"], False)
        self.assertEqual(caps["can_edit_righe"], False)
        self.assertEqual(caps["can_create_revisione"], True)
        self.assertEqual(caps["can_push_commessa"], True)
        self.assertEqual(len(caps["available_actions"]), 1)
        self.assertEqual(caps["available_actions"][0]["key"], "annulla")
        self.assertIn("billing_account_id", caps["non_editable_fields"])
        for chiave in ("available_actions", "can_edit_testata", "can_push_commessa",
                       "non_editable_fields"):
            self.assertNotIn(chiave, result)
        # Fase 3.F6: detail non include `righe` ma solo `righe_count` (summary).
        self.assertNotIn("righe", result)
        self.assertEqual(result["righe_count"], 2)
        self.assertEqual(result["indirizzi"], [])
        self.mock_repo.get_capabilities.assert_called_once_with(42)

    # ── Paginazione ──

    # Scopo: Verifica errore paginazione invalida.
    def test_list_preventivi_paginazione_invalida(self):
        from apps.vendite.services.preventivi_service import list_preventivi

        for finestra in ({"limit": 0}, {"limit": 201}, {"offset": -1}):
            with self.subTest(**finestra), self.assertRaises(ServiceError) as ctx:
                list_preventivi(**finestra)
            self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    # ── Sprint 2: wiring pricing v5 + L1 override ──

    # Helper: testata completa (BA+utility+data) per attivare il resolver.
    def _testata_completa(self):
        return {
            "id": 1,
            "stato_codice_interno": "DRAFT",
            "uid": "abc",
            "billing_account_id": 10,
            "utility_id": 3,
            "data": "2026-04-17",
        }

    # Scopo: Auto-fill prezzo dal resolver quando payload non specifica
    #        prezzo_unitario e testata ha BA+utility+data validi.
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_auto_fill_da_resolver(self, mock_suggerisci):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 11}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": "PERCENTUALE",
            "valore_variazione_applicata": "-5.00",
        }

        gestisci_riga(
            1,
            {"articolo_id": "uuid-art-1", "uom_operativa_id": 1},
            auth_user_id=42,
        )

        call = self.mock_repo.create_riga.call_args.kwargs
        # Prezzo popolato dal resolver
        self.assertIsNotNone(call["prezzo_unitario"])
        # Meta audit con origine = valore resolver
        self.assertEqual(call["meta"]["origine_prezzo"], "CATEGORIA")
        self.assertEqual(call["meta"]["prezzo_resolver_context"]["listino_id"], 100)

    # Scopo: Override prezzo ammesso se payload == resolver (no check permesso).
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_prezzo_uguale_resolver_ok(self, mock_suggerisci):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 12}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }

        # Prezzo passato uguale a quello del resolver -> accettato
        gestisci_riga(
            1,
            {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "50.00"},
            auth_user_id=42,
        )

        call = self.mock_repo.create_riga.call_args.kwargs
        self.assertEqual(str(call["prezzo_unitario"]), "50.00")
        # Origine = resolver (non MANUALE)
        self.assertEqual(call["meta"]["origine_prezzo"], "CATEGORIA")

    # Scopo: L1 — override prezzo (payload != resolver) bloccato se l'utente
    #        non ha permesso azione prezzo_override_manuale.
    @patch("apps.vendite.services._pricing_gate_helpers.get_user_model")
    @patch("apps.vendite.services._pricing_gate_helpers.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_override_non_autorizzato(
        self, mock_suggerisci, mock_perm, mock_user_model
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        # User non superuser, azione NON abilitata
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1,
                {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "45.00"},
                auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_PRICING_OVERRIDE_NON_AUTORIZZATO")
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: L1 — override prezzo ammesso per superuser (bypass).
    @patch("apps.vendite.services._pricing_gate_helpers.get_user_model")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_override_superuser_ok(
        self, mock_suggerisci, mock_user_model
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 13}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        # Superuser bypassa il check
        mock_user = MagicMock()
        mock_user.is_superuser = True
        mock_user_model.return_value.objects.get.return_value = mock_user

        gestisci_riga(
            1,
            {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "45.00"},
            auth_user_id=42,
        )

        call = self.mock_repo.create_riga.call_args.kwargs
        self.assertEqual(str(call["prezzo_unitario"]), "45.00")
        # Meta audit con origine MANUALE + delta tracciato
        self.assertEqual(call["meta"]["origine_prezzo"], "MANUALE")
        self.assertEqual(call["meta"]["prezzo_base_resolver"], "50.00")
        self.assertEqual(call["meta"]["delta_override"], "-5.00")

    # Scopo: L2 — sconto entro il limite VENDITE_MAX_SCONTO_PCT passa.
    #        Resolver 50, manuale 45 = -10% sconto, limite 15% -> OK.
    @patch("apps.vendite.services._pricing_gate_helpers.ParameterService")
    @patch("apps.vendite.services._pricing_gate_helpers.get_user_model")
    @patch("apps.vendite.services._pricing_gate_helpers.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_L2_sconto_entro_limite_ok(
        self, mock_suggerisci, mock_perm, mock_user_model, mock_param_service
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 30}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True  # L1 ok
        # L2: limite sconto 15% -> sconto 10% ammesso.
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("15")

        gestisci_riga(
            1,
            {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "45.00"},
            auth_user_id=42,
        )

        call = self.mock_repo.create_riga.call_args.kwargs
        self.assertEqual(str(call["prezzo_unitario"]), "45.00")
        self.assertEqual(call["meta"]["origine_prezzo"], "MANUALE")

    # Scopo: L2 — sconto oltre il limite blocca con E_PRICING_SCONTO_ECCESSIVO.
    #        Resolver 50, manuale 40 = -20% sconto, limite 15% -> bloccato.
    @patch("apps.vendite.services._pricing_gate_helpers.ParameterService")
    @patch("apps.vendite.services._pricing_gate_helpers.get_user_model")
    @patch("apps.vendite.services._pricing_gate_helpers.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_L2_sconto_oltre_limite_bloccato(
        self, mock_suggerisci, mock_perm, mock_user_model, mock_param_service
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True  # L1 ok
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("15")  # limite

        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1,
                {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "40.00"},
                auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_PRICING_SCONTO_ECCESSIVO")
        # Fase 5.B2: errore L2 retryable=True (utente puo' ritentare con
        # flag richiesta_approvazione=true per attivare workflow L3).
        self.assertTrue(ctx.exception.retryable)
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: L2 — maggiorazione oltre il limite blocca con
    #        E_PRICING_MAGGIORAZIONE_ECCESSIVA. Resolver 50, manuale 55 = +10%,
    #        limite 5% -> bloccato.
    @patch("apps.vendite.services._pricing_gate_helpers.ParameterService")
    @patch("apps.vendite.services._pricing_gate_helpers.get_user_model")
    @patch("apps.vendite.services._pricing_gate_helpers.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_L2_maggiorazione_oltre_limite_bloccato(
        self, mock_suggerisci, mock_perm, mock_user_model, mock_param_service
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True  # L1 ok
        # Maggiorazione: limite 5% per il secondo parametro.
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("5")

        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1,
                {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "55.00"},
                auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_PRICING_MAGGIORAZIONE_ECCESSIVA")
        # Fase 5.B2: errore L2 retryable=True (vedi commento test sconto).
        self.assertTrue(ctx.exception.retryable)
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: L2 — superuser salta sia L1 che L2 anche con limiti a 0.
    # Verifica anche che il lookup BA (categoria_cliente) NON venga eseguito
    # in caso di superuser bypass: ottimizzazione 2026-05-15, evita
    # round-trip DB inutile.
    @patch("apps.vendite.services._pricing_gate_helpers.BillingAccountRepository")
    @patch("apps.vendite.services._pricing_gate_helpers.ParameterService")
    @patch("apps.vendite.services._pricing_gate_helpers.get_user_model")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_L2_superuser_bypass(
        self, mock_suggerisci, mock_user_model, mock_param_service, mock_ba_repo
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 31}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = True  # bypass L1 e L2
        mock_user_model.return_value.objects.get.return_value = mock_user

        gestisci_riga(
            1,
            {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "30.00"},
            auth_user_id=99,
        )

        # ParameterService MAI chiamato (bypass L2 avviene prima).
        mock_param_service.return_value.get_parameter_decimal.assert_not_called()
        # BillingAccountRepository MAI chiamato (ottimizzazione 2026-05-15:
        # il lookup categoria viene dopo l'early-return superuser).
        mock_ba_repo.return_value.get_categoria_cliente_id.assert_not_called()
        call = self.mock_repo.create_riga.call_args.kwargs
        self.assertEqual(str(call["prezzo_unitario"]), "30.00")

    # Scopo: L2 — categoria_cliente del BA viene recuperata e propagata a
    # ParameterService come livello della cascata estesa (refactor 2026-05-15).
    # Verifica che _check_limite_variazione_prezzo (post early-return) chiami
    # BillingAccountRepository.get_categoria_cliente_id sull'id della testata
    # e passi il risultato come kwarg `categoria_cliente_id` al risolutore.
    @patch("apps.vendite.services._pricing_gate_helpers.BillingAccountRepository")
    @patch("apps.vendite.services._pricing_gate_helpers.ParameterService")
    @patch("apps.vendite.services._pricing_gate_helpers.get_user_model")
    @patch("apps.vendite.services._pricing_gate_helpers.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_L2_propaga_categoria_cliente(
        self, mock_suggerisci, mock_perm, mock_user_model,
        mock_param_service, mock_ba_repo,
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 32}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("15")
        # BA 10 (vedi _testata_completa) ha categoria 42 (PREMIUM).
        mock_ba_repo.return_value.get_categoria_cliente_id.return_value = 42

        gestisci_riga(
            1,
            {"articolo_id": "uuid-art-1", "uom_operativa_id": 1, "prezzo_unitario": "45.00"},
            auth_user_id=42,
        )

        # 1. BA repo chiamato con id 10 (da _testata_completa).
        mock_ba_repo.return_value.get_categoria_cliente_id.assert_called_once_with(10)
        # 2. get_parameter_decimal chiamato con categoria_cliente_id=42.
        _, kwargs = mock_param_service.return_value.get_parameter_decimal.call_args
        self.assertEqual(kwargs.get("categoria_cliente_id"), 42)

    # ── Sprint E: hook L3 richiesta_approvazione ──

    # Scopo: L3 — flag richiesta_approvazione=True + violazione L2 -> NON
    #        solleva, crea pratica via service e salva riga PENDING con FK
    #        pratica. Verifica che create_riga riceva i nuovi campi corretti.
    @patch("apps.vendite.services.approvazioni_prezzo_service.link_riga_a_pratica")
    @patch("apps.vendite.services._pricing_gate_helpers.ParameterService")
    @patch("apps.vendite.services._pricing_gate_helpers.get_user_model")
    @patch("apps.vendite.services._pricing_gate_helpers.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_richiesta_approvazione")
    def test_gestisci_riga_L3_violazione_con_richiesta_crea_pratica_pending(
        self, mock_crea_pratica, mock_suggerisci, mock_perm, mock_user_model,
        mock_param_service, mock_link_riga,
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 999}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True  # L1 ok
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("15")
        mock_crea_pratica.return_value = 7777  # pratica_id ritornato dal service

        result = gestisci_riga(
            1,
            {
                "articolo_id": "uuid-art-1",
                "uom_operativa_id": 1,
                "prezzo_unitario": "40.00",  # -20% sconto, fuori limite 15%
                "richiesta_approvazione": True,
            },
            auth_user_id=42,
        )

        self.assertEqual(result["id"], 999)
        mock_crea_pratica.assert_called_once()
        crea_kwargs = mock_crea_pratica.call_args.kwargs
        self.assertEqual(crea_kwargs["preventivo_id"], 1)
        self.assertEqual(crea_kwargs["articolo_id"], "uuid-art-1")
        self.assertEqual(crea_kwargs["prezzo_resolver"], Decimal("50.00"))
        self.assertEqual(crea_kwargs["prezzo_manuale"], Decimal("40.00"))
        self.assertEqual(crea_kwargs["violazione"]["tipo_violazione"], "SCONTO")

        call = self.mock_repo.create_riga.call_args.kwargs
        self.assertEqual(call["stato_approvazione_prezzo"], "PENDING")
        self.assertEqual(call["pratica_approvazione_prezzo_id"], 7777)

    # Scopo: L3 — flag richiesta_approvazione=False (default): violazione L2
    #        solleva normalmente, NESSUNA pratica creata.
    @patch("apps.vendite.services._pricing_gate_helpers.ParameterService")
    @patch("apps.vendite.services._pricing_gate_helpers.get_user_model")
    @patch("apps.vendite.services._pricing_gate_helpers.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_richiesta_approvazione")
    def test_gestisci_riga_L3_default_no_pratica_solo_errore_l2(
        self, mock_crea_pratica, mock_suggerisci, mock_perm, mock_user_model, mock_param_service
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("15")

        with self.assertRaises(ServiceError) as ctx:
            gestisci_riga(
                1,
                {
                    "articolo_id": "uuid-art-1",
                    "uom_operativa_id": 1,
                    "prezzo_unitario": "40.00",
                    # Niente richiesta_approvazione (default False)
                },
                auth_user_id=42,
            )

        self.assertEqual(ctx.exception.code, "E_PRICING_SCONTO_ECCESSIVO")
        mock_crea_pratica.assert_not_called()
        self.mock_repo.create_riga.assert_not_called()

    # Scopo: L3 — sotto limite L2 anche con richiesta_approvazione=True:
    #        pratica NON creata (violazione assente), riga normale (no PENDING).
    @patch("apps.vendite.services._pricing_gate_helpers.ParameterService")
    @patch("apps.vendite.services._pricing_gate_helpers.get_user_model")
    @patch("apps.vendite.services._pricing_gate_helpers.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_richiesta_approvazione")
    def test_gestisci_riga_L3_sotto_limite_no_pratica(
        self, mock_crea_pratica, mock_suggerisci, mock_perm, mock_user_model, mock_param_service
    ):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 100}
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("20")

        gestisci_riga(
            1,
            {
                "articolo_id": "uuid-art-1",
                "uom_operativa_id": 1,
                "prezzo_unitario": "45.00",  # -10%, sotto limite 20%
                "richiesta_approvazione": True,
            },
            auth_user_id=42,
        )

        mock_crea_pratica.assert_not_called()
        call = self.mock_repo.create_riga.call_args.kwargs
        self.assertIsNone(call["stato_approvazione_prezzo"])
        self.assertIsNone(call["pratica_approvazione_prezzo_id"])

    # Scopo: L3 — aggiorna_riga supporta lo stesso flag richiesta_approvazione.
    #        Modifica prezzo oltre L2 con flag -> crea pratica + UPDATE riga
    #        con stato_approvazione_prezzo=PENDING.
    @patch("apps.vendite.services.approvazioni_prezzo_service.link_riga_a_pratica")
    @patch("apps.vendite.services._pricing_gate_helpers.ParameterService")
    @patch("apps.vendite.services._pricing_gate_helpers.get_user_model")
    @patch("apps.vendite.services._pricing_gate_helpers.PermissionResolver")
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    @patch("apps.vendite.services.approvazioni_prezzo_service.crea_richiesta_approvazione")
    def test_aggiorna_riga_L3_violazione_con_richiesta_crea_pratica(
        self, mock_crea_pratica, mock_suggerisci, mock_perm, mock_user_model,
        mock_param_service, mock_link_riga,
    ):
        from apps.vendite.services.preventivi_service import aggiorna_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.list_righe.return_value = [
            {"id": 50, "articolo_id": "uuid-art-1", "uom_operativa_id": 1, "meta": {}}
        ]
        self.mock_repo.update_riga.return_value = True
        mock_suggerisci.return_value = {
            "prezzo_finale": "50.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None,
            "valore_variazione_applicata": None,
        }
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user_model.return_value.objects.get.return_value = mock_user
        mock_perm.check_azione.return_value = True
        mock_param_service.return_value.get_parameter_decimal.return_value = Decimal("15")
        mock_crea_pratica.return_value = 8888

        aggiorna_riga(
            1, 50,
            {"prezzo_unitario": "40.00", "richiesta_approvazione": True},
            auth_user_id=42,
        )

        mock_crea_pratica.assert_called_once()
        call = self.mock_repo.update_riga.call_args
        # update_riga(riga_id, **kwargs) — verifica kwargs.
        self.assertEqual(call.kwargs["stato_approvazione_prezzo"], "PENDING")
        self.assertEqual(call.kwargs["pratica_approvazione_prezzo_id"], 8888)

    # ── Sprint riepilogo IVA + filtri lista (sessione 03-05-2026) ──

    # Scopo: list_riepilogo_iva e' un thin facade su repo: verifica solo
    #        delegation + pass-through del payload.
    def test_list_riepilogo_iva_delega_a_repo(self):
        from apps.vendite.services.preventivi_service import list_riepilogo_iva

        self.mock_repo.list_riepilogo_iva.return_value = [
            {"iva_id": 1, "iva_aliquota": 22, "imponibile": "100.00", "imposta": "22.00",
             "arrotondamento": "0.0001"},
            {"iva_id": 2, "iva_aliquota": 10, "imponibile": "50.00", "imposta": "5.00",
             "arrotondamento": "-0.0002"},
        ]

        result = list_riepilogo_iva(42)

        self.mock_repo.list_riepilogo_iva.assert_called_once_with(42)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["iva_aliquota"], 22)

    # Scopo: filtro solo_ultima_revisione default True. Verifica che il
    #        service propaghi True al repo quando il parametro non e' passato.
    def test_list_preventivi_default_solo_ultima_revisione_true(self):
        from apps.vendite.services.preventivi_service import list_preventivi

        self.mock_repo.list_preventivi.return_value = ([], 0)

        list_preventivi(limit=10)

        kwargs = self.mock_repo.list_preventivi.call_args.kwargs
        self.assertTrue(kwargs["solo_ultima_revisione"])

    # Scopo: filtro solo_ultima_revisione pass-through esplicito False
    #        (il FE col toggle "Mostra storico" passa false).
    def test_list_preventivi_solo_ultima_revisione_false(self):
        from apps.vendite.services.preventivi_service import list_preventivi

        self.mock_repo.list_preventivi.return_value = ([], 0)

        list_preventivi(limit=10, solo_ultima_revisione=False)

        kwargs = self.mock_repo.list_preventivi.call_args.kwargs
        self.assertFalse(kwargs["solo_ultima_revisione"])

    # Scopo: modello qta_operativa-sorgente (refactor 2026-05-31). Il FE invia
    #        `qta_operativa` (UoM operativa scelta) + `uom_operativa_id`; il BE
    #        li inoltra al repo SENZA derivare nulla e SENZA inviare `quantita`
    #        (colonna base derivata dal trigger DB `trgfn_qta_from_operativa`).
    @patch("apps.vendite.services.preventivi_service.suggerisci_prezzo_riga")
    def test_gestisci_riga_inoltra_qta_operativa_senza_derivare(self, mock_suggerisci):
        from apps.vendite.services.preventivi_service import gestisci_riga

        self.mock_repo.get_preventivo.return_value = self._testata_completa()
        self.mock_repo.create_riga.return_value = {"id": 99}
        mock_suggerisci.return_value = {
            "prezzo_finale": "5.00", "origine": "CATEGORIA",
            "listino_id": 100, "contratto_id": None, "promo_id": None,
            "tipo_variazione_applicata": None, "valore_variazione_applicata": None,
        }

        gestisci_riga(
            1, {"articolo_id": "art-uuid", "uom_operativa_id": 8,
                "qta_operativa": "3"},
            auth_user_id=42,
        )

        call = self.mock_repo.create_riga.call_args.kwargs
        # qta_operativa inoltrata tale e quale (sorgente operatore)
        self.assertEqual(call["qta_operativa"], "3")
        # `quantita` NON inviata dal BE: la calcola il trigger DB
        self.assertIsNone(call["quantita"])

    # ===========================================================
    # Prezzi non autorizzati: il blob si consegna COM'E'.
    # Fino al 2026-09-24 get_preventivo riscriveva available_actions e
    # can_edit_* in Python quando c'erano righe PENDING/REJECTED; la regola
    # ora sta a DB (script.fn_check_prezzi_autorizzati, letto da guard e
    # capability) — brief-db-preventivi-congelamento-pricing §6.1.
    # ===========================================================

    # Scopo: DRAFT con un prezzo in attesa e uno rifiutato, come lo emette
    #        fn_available_actions_preventivo: «Emetti» spento coi due motivi,
    #        «Annulla» acceso (D-2), testata e righe modificabili (D-3).
    def _blob_draft_prezzi_non_autorizzati(self):
        motivi = [
            {"codice": "E_DOC_PREZZO_PENDENTE", "reason": "PREZZO_PENDENTE",
             "reason_key": "common.azione_reason.prezzo_pendente",
             "dettaglio": {"n_prezzi": 1, "riga_id": 7, "componente_id": None},
             "valori": ["1"]},
            {"codice": "E_DOC_PREZZO_RIFIUTATO", "reason": "PREZZO_RIFIUTATO",
             "reason_key": "common.azione_reason.prezzo_rifiutato",
             "dettaglio": {"n_prezzi": 2, "riga_id": 8, "componente_id": None},
             "valori": ["2"]},
        ]
        return {
            "stato_codice": "DRAFT",
            "available_actions": [
                {"key": "emetti", "target_state": "EMESSO", "enabled": False,
                 "reason": "PREZZO_PENDENTE",
                 "reason_key": "common.azione_reason.prezzo_pendente",
                 "reasons": motivi},
                {"key": "annulla", "target_state": "ANNULLATO", "enabled": True,
                 "reason": None, "reason_key": None, "reasons": []},
            ],
            "can_edit_testata": True,
            "can_edit_righe": True,
            "non_editable_fields": [],
        }

    def test_get_preventivo_consegna_il_blob_senza_riscriverlo(self):
        """Prezzi PENDING e REJECTED: il BE non tocca il blob — azioni,
        motivi e flag di modifica sono quelli del database."""
        from apps.vendite.services.preventivi_service import get_preventivo
        self.mock_repo.get_preventivo.return_value = {
            "id": 42, "uid": "abc", "numero": "P-0042",
            "stato_codice": "DRAFT", "stato_codice_interno": "DRAFT",
            "billing_account_id": 10, "utility_id": 3,
        }
        self.mock_repo.list_indirizzi.return_value = []
        self.mock_repo.count_righe.return_value = 5
        blob = self._blob_draft_prezzi_non_autorizzati()
        self.mock_repo.get_capabilities.return_value = blob

        out = get_preventivo(42)
        caps = out["capabilities"]

        self.assertEqual(caps, self._blob_draft_prezzi_non_autorizzati())
        azioni = {a["key"]: a for a in caps["available_actions"]}
        self.assertFalse(azioni["emetti"]["enabled"])
        self.assertEqual(azioni["emetti"]["reason_key"], "common.azione_reason.prezzo_pendente")
        self.assertTrue(azioni["annulla"]["enabled"])
        self.assertTrue(caps["can_edit_testata"])
        self.assertTrue(caps["can_edit_righe"])
        self.assertEqual(out["righe_count"], 5)

    def test_get_preventivo_non_emette_riepiloghi_del_congelamento(self):
        """I quattro riepiloghi Python (frozen_for_*, *_pricing_count) sono
        ritirati: contavano solo le righe, il database conta anche i
        componenti attivi. Il perche' (col conteggio) sta nelle `reasons`
        delle azioni del blob."""
        from apps.vendite.services.preventivi_service import get_preventivo
        self.mock_repo.get_preventivo.return_value = {
            "id": 42, "stato_codice_interno": "DRAFT",
            "billing_account_id": 10, "utility_id": 3,
        }
        self.mock_repo.list_indirizzi.return_value = []
        self.mock_repo.count_righe.return_value = 5
        self.mock_repo.get_capabilities.return_value = self._blob_draft_prezzi_non_autorizzati()

        out = get_preventivo(42)

        for chiave in ("frozen_for_pending_pricing", "frozen_for_rejected_pricing",
                       "pending_pricing_count", "rejected_pricing_count"):
            self.assertNotIn(chiave, out)
            self.assertNotIn(chiave, out["capabilities"])

    # ===========================================================
    # aggiorna_riga: auto-reset stato approvazione su correzione
    # prezzo (REJECTED/APPROVED → null se nuovo prezzo non viola L2).
    # ===========================================================

    def test_aggiorna_riga_rejected_reset_su_prezzo_corretto(self):
        """Riga REJECTED + nuovo prezzo entro L2 → reset stato + cleanup meta."""
        from apps.vendite.services.preventivi_service import aggiorna_riga
        # Setup: testata BOZZA, riga esistente REJECTED, nuovo prezzo = resolver.
        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT",
            "billing_account_id": 10, "utility_id": 3,
        }
        riga_esistente = {
            "id": 50, "preventivo_id": 1, "articolo_id": "art-uuid", "uom_operativa_id": 7,
            "stato_approvazione_prezzo": "REJECTED",
            "pratica_approvazione_prezzo_id": 99,
            "meta": {
                "approvazione_rifiuto": {"motivazione": "test"},
                "altro_campo": "preserve",
            },
        }
        self.mock_repo.get_riga.return_value = riga_esistente

        # Mock _resolve_or_check_override_prezzo: ritorna prezzo allineato al
        # resolver (nessun override → no richiesta_approvazione_pending).
        with patch(
            "apps.vendite.services.preventivi_service._resolve_or_check_override_prezzo",
            return_value=(Decimal("10"), {"origine_prezzo": "CATEGORIA"}),
        ):
            aggiorna_riga(1, 50, {"prezzo_unitario": "10"}, auth_user_id=42)

        kwargs = self.mock_repo.update_riga.call_args.kwargs
        # Stato resettato a None.
        self.assertIsNone(kwargs["stato_approvazione_prezzo"])
        self.assertIsNone(kwargs["pratica_approvazione_prezzo_id"])
        # Meta cleanup: approvazione_rifiuto rimossa, altri campi preservati.
        self.assertNotIn("approvazione_rifiuto", kwargs["meta"])
        self.assertEqual(kwargs["meta"].get("altro_campo"), "preserve")

    def test_aggiorna_riga_no_reset_se_richiede_nuova_approvazione(self):
        """REJECTED + nuovo prezzo che richiede L3 → stato torna a PENDING,
        non viene resettato a None."""
        from apps.vendite.services.preventivi_service import aggiorna_riga
        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT",
            "billing_account_id": 10, "utility_id": 3,
        }
        self.mock_repo.get_riga.return_value = {
            "id": 50, "preventivo_id": 1, "articolo_id": "art-uuid", "uom_operativa_id": 7,
            "stato_approvazione_prezzo": "REJECTED",
            "pratica_approvazione_prezzo_id": 99,
            "meta": {},
        }
        with patch(
            "apps.vendite.services.preventivi_service._resolve_or_check_override_prezzo",
            return_value=(Decimal("13"), {
                "origine_prezzo": "MANUALE",
                "richiesta_approvazione_pending": True,
                "violazione_l2": {"tipo_violazione": "MAGGIORAZIONE",
                                   "variazione_abs_pct": "30", "limite_pct": "5"},
            }),
        ), patch(
            "apps.vendite.services.preventivi_service._orchestrate_l3_request",
            return_value=200,
        ):
            aggiorna_riga(
                1, 50,
                {"prezzo_unitario": "13", "richiesta_approvazione": True},
                auth_user_id=42,
            )
        kwargs = self.mock_repo.update_riga.call_args.kwargs
        self.assertEqual(kwargs["stato_approvazione_prezzo"], "PENDING")
        self.assertEqual(kwargs["pratica_approvazione_prezzo_id"], 200)

    # ── preview_componenti_riga (form atomic 2026-05-12) ──

    # Scopo: happy path — testata valida → repo invocato con args corretti.
    def test_preview_componenti_riga_ok(self):
        from apps.vendite.services.preventivi_service import preview_componenti_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 7,
            "emittente_fiscale_id": None,
        }
        self.mock_repo.preview_componenti_riga.return_value = [
            {"componente_id": "uuid-c1", "prezzo_suggerito": "10.00"},
        ]

        out = preview_componenti_riga(
            1, articolo_id="uuid-art", uom_operativa_id=2, quantita="3",
            auth_user_id=42,
        )
        self.assertEqual(len(out), 1)
        kwargs = self.mock_repo.preview_componenti_riga.call_args.kwargs
        self.assertEqual(kwargs["articolo_id"], "uuid-art")
        self.assertEqual(kwargs["uom_id"], 2)
        self.assertEqual(kwargs["utility_id"], 7)
        self.assertEqual(kwargs["ba_id"], 5)
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 100)

    # Scopo: preventivo inesistente → E_PREV_NOT_FOUND.
    def test_preview_componenti_riga_not_found(self):
        from apps.vendite.services.preventivi_service import preview_componenti_riga

        self.mock_repo.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            preview_componenti_riga(
                999, articolo_id="uuid", uom_operativa_id=1, quantita="1",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_NOT_FOUND")
        self.mock_repo.preview_componenti_riga.assert_not_called()

    # Scopo: data preventivo NULL → E_PREV_VALIDAZIONE.
    def test_preview_componenti_riga_data_mancante(self):
        from apps.vendite.services.preventivi_service import preview_componenti_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "data": None,
            "billing_account_id": 5, "utility_id": 7,
        }
        with self.assertRaises(ServiceError) as ctx:
            preview_componenti_riga(
                1, articolo_id="uuid", uom_operativa_id=1, quantita="1",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.preview_componenti_riga.assert_not_called()

    # Scopo: utility_id NULL → E_PREV_VALIDAZIONE (guard A2: niente fallback
    # silente a 0).
    def test_preview_componenti_riga_utility_mancante(self):
        from apps.vendite.services.preventivi_service import preview_componenti_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": None,
        }
        with self.assertRaises(ServiceError) as ctx:
            preview_componenti_riga(
                1, articolo_id="uuid", uom_operativa_id=1, quantita="1",
                auth_user_id=42,
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.mock_repo.preview_componenti_riga.assert_not_called()

    # Scopo: emittente non risolvibile (no emittente sul preventivo + admin
    # globale senza emittenti assegnati) → E_PREV_VALIDAZIONE.
    def test_preview_componenti_riga_emittente_non_risolvibile(self):
        from apps.vendite.services.preventivi_service import preview_componenti_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 7,
            "emittente_fiscale_id": None,
        }
        # Sovrascrivi mock setUp: admin globale → safe ritorna None.
        self.emittente_safe_patcher.stop()
        try:
            with patch(
                "apps.vendite.services._componenti_service_helpers.resolve_emittente_sr_id_safe",
                return_value=None,
            ):
                with self.assertRaises(ServiceError) as ctx:
                    preview_componenti_riga(
                        1, articolo_id="uuid", uom_operativa_id=1,
                        quantita="1", auth_user_id=None,
                    )
                self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        finally:
            self.emittente_safe_patcher.start()
        self.mock_repo.preview_componenti_riga.assert_not_called()

    # Scopo: emittente esplicito sul preventivo ha precedenza sul fallback
    # operatore — verifica helper di risoluzione condiviso.
    def test_preview_componenti_riga_usa_emittente_preventivo(self):
        from apps.vendite.services.preventivi_service import preview_componenti_riga

        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "data": "2026-05-11",
            "billing_account_id": 5, "utility_id": 7,
            "emittente_fiscale_id": 77,
        }
        self.mock_repo.get_emittente_sr_id_by_fiscale_id.return_value = 999
        self.mock_repo.preview_componenti_riga.return_value = []

        preview_componenti_riga(
            1, articolo_id="uuid", uom_operativa_id=1, quantita="1",
            auth_user_id=42,
        )
        kwargs = self.mock_repo.preview_componenti_riga.call_args.kwargs
        # 999 dal preventivo, NON 100 dall'operatore (precedenza preventivo).
        self.assertEqual(kwargs["emittente_soggetto_ruolo_id"], 999)


class TestNormalizeComponentiOverrides(unittest.TestCase):
    """Form atomic 2026-05-12: validazione/normalizzazione overrides
    prima del cast jsonb lato repo. Decimal-safe.
    """

    def test_none_ritorna_none(self):
        self.assertIsNone(_normalize_componenti_overrides(None, function_name="t"))

    def test_dict_vuoto_ritorna_none(self):
        self.assertIsNone(_normalize_componenti_overrides({}, function_name="t"))

    def test_decimal_string_normalizzato(self):
        out = _normalize_componenti_overrides(
            {"uuid-c1": "12.500"}, function_name="t",
        )
        self.assertEqual(out, {"uuid-c1": "12.500"})

    def test_numero_python_normalizzato(self):
        out = _normalize_componenti_overrides(
            {"uuid-c1": 75}, function_name="t",
        )
        self.assertEqual(out, {"uuid-c1": "75"})

    def test_decimal_native_normalizzato(self):
        out = _normalize_componenti_overrides(
            {"uuid-c1": Decimal("3.14")}, function_name="t",
        )
        self.assertEqual(out, {"uuid-c1": "3.14"})

    def test_valore_none_solleva(self):
        with self.assertRaises(ServiceError) as ctx:
            _normalize_componenti_overrides(
                {"uuid-c1": None}, function_name="t",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    def test_valore_stringa_vuota_solleva(self):
        with self.assertRaises(ServiceError) as ctx:
            _normalize_componenti_overrides(
                {"uuid-c1": ""}, function_name="t",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    def test_valore_non_numerico_solleva(self):
        with self.assertRaises(ServiceError) as ctx:
            _normalize_componenti_overrides(
                {"uuid-c1": "abc"}, function_name="t",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    def test_overrides_non_dict_solleva(self):
        with self.assertRaises(ServiceError) as ctx:
            _normalize_componenti_overrides(
                ["uuid-c1", "10"], function_name="t",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")


class TestNormalizeComponentiAttivazioni(unittest.TestCase):
    """Modello unificato 2026-05-13: validazione/normalizzazione mappa
    {componente_id: bool}. Bool-only, no coercion da int/str."""

    def test_none_ritorna_none(self):
        self.assertIsNone(
            _normalize_componenti_attivazioni(None, function_name="t"),
        )

    def test_dict_vuoto_ritorna_none(self):
        self.assertIsNone(
            _normalize_componenti_attivazioni({}, function_name="t"),
        )

    def test_dict_bool_normalizzato(self):
        out = _normalize_componenti_attivazioni(
            {"uuid-c1": True, "uuid-c2": False}, function_name="t",
        )
        self.assertEqual(out, {"uuid-c1": True, "uuid-c2": False})

    def test_valore_non_bool_solleva(self):
        with self.assertRaises(ServiceError) as ctx:
            _normalize_componenti_attivazioni(
                {"uuid-c1": "true"}, function_name="t",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")

    def test_attivazioni_non_dict_solleva(self):
        with self.assertRaises(ServiceError) as ctx:
            _normalize_componenti_attivazioni(
                ["uuid-c1", True], function_name="t",
            )
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")


class TestCoerceMetaToDict(unittest.TestCase):
    """Test edge case `_coerce_meta_to_dict`: helper difensivo contro
    psycopg jsonb deserializzato come stringa."""

    def test_dict_passthrough(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        out = _coerce_meta_to_dict({"a": 1})
        self.assertEqual(out, {"a": 1})

    def test_none_to_empty(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        self.assertEqual(_coerce_meta_to_dict(None), {})

    def test_empty_string_to_empty(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        self.assertEqual(_coerce_meta_to_dict(""), {})

    def test_empty_dict_passthrough(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        self.assertEqual(_coerce_meta_to_dict({}), {})

    def test_json_string_dict(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        out = _coerce_meta_to_dict('{"foo": "bar"}')
        self.assertEqual(out, {"foo": "bar"})

    def test_json_string_malformed(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        self.assertEqual(_coerce_meta_to_dict("{not json"), {})

    def test_json_string_list_to_empty(self):
        # Una lista JSON deserializzata non e' un dict — ritorna {}.
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        self.assertEqual(_coerce_meta_to_dict('[1,2,3]'), {})

    def test_unexpected_type_to_empty(self):
        from apps.vendite.services.preventivi_service import _coerce_meta_to_dict
        self.assertEqual(_coerce_meta_to_dict(123), {})
        self.assertEqual(_coerce_meta_to_dict(True), {})


class TestPreventiviRepository(unittest.TestCase):
    # Scopo: Verifica che la lettura righe escluda le righe soft-delete
    #        (`attivo=false`), evitando che la UI mostri righe gia' eliminate.
    # ⚠️ La query nasce nel BB core `RigheListaCompletaMixin` (2026-10-04):
    #    la connessione si sostituisce la', non nel modulo del repository.
    @patch("apps.core.db.righe_lista_mixin.connection")
    def test_repository_list_righe_filtra_solo_attive(self, mock_connection):
        from apps.vendite.db.preventivi_repository import PreventiviRepository

        cursor = MagicMock()
        cursor.description = [SimpleNamespace(name="id")]
        cursor.fetchall.return_value = []
        mock_connection.cursor.return_value.__enter__.return_value = cursor

        PreventiviRepository().list_righe(40)

        sql, params = cursor.execute.call_args.args
        self.assertIn("attivo IS TRUE", sql)
        self.assertEqual(params, [40])


# Scopo: La DATA DI CONSEGNA RICHIESTA sulla riga di preventivo (Blocco A di
#        brief-db-modifiche-certe-ciclo-vendita-e-articolo). Sul preventivo
#        c'e' solo la richiesta: la conferma nasce sull'ordine. Si prova il
#        trasporto intero — arriva a `create_riga` come `date`, una malformata
#        e' 400 col campo, in PATCH `null` azzera e l'assenza non tocca.
#
# Indice:
#  1. test_la_data_richiesta_arriva_a_create_riga_come_date
#  2. test_data_richiesta_malformata_e_400_col_campo
#  3. test_in_patch_null_azzera_e_assenza_non_tocca
class TestPreventiviRigaDataConsegna(unittest.TestCase):
    def setUp(self):
        self.repo_patcher = patch(
            "apps.vendite.services.preventivi_service.PreventiviRepository"
        )
        self.mock_repo = self.repo_patcher.start().return_value
        self.addCleanup(self.repo_patcher.stop)
        self.iva_patcher = patch(
            "apps.vendite.services.preventivi_service._risolvi_iva_riga",
            return_value=(None, {}),
        )
        self.iva_patcher.start()
        self.addCleanup(self.iva_patcher.stop)
        self.mock_repo.get_preventivo.return_value = {
            "id": 1, "stato_codice_interno": "DRAFT", "uid": "abc",
            "emittente_fiscale_id": 3, "data": "2026-08-31",
            "billing_account_id": 100, "utility_id": 5,
        }
        self.mock_repo.create_riga.return_value = {"id": 10}
        self.mock_repo.update_riga.return_value = True

    def test_la_data_richiesta_arriva_a_create_riga_come_date(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        gestisci_riga(1, {
            "articolo_id": "uuid-art-1", "prezzo_unitario": "1",
            "data_consegna_richiesta_cliente": "2026-11-15",
        })
        scritta = self.mock_repo.create_riga.call_args.kwargs
        self.assertEqual(scritta["data_consegna_richiesta_cliente"], date(2026, 11, 15))

    def test_data_richiesta_malformata_e_400_col_campo(self):
        from apps.vendite.services.preventivi_service import gestisci_riga

        # ⭐ La forma della data si controlla PRIMA del resolver del prezzo (e
        #    quindi prima del gate L2 e della richiesta L3, che manda un'email
        #    fuori dalla transazione): un 400 sul payload non deve aver mosso
        #    niente. Senza questo mock il test resterebbe verde anche con la
        #    validazione in fondo, perche' `create_riga` e' comunque mockata.
        with patch(
            "apps.vendite.services.preventivi_service._resolve_or_check_override_prezzo"
        ) as resolver, self.assertRaises(ServiceError) as ctx:
            gestisci_riga(1, {
                "articolo_id": "uuid-art-1", "prezzo_unitario": "1",
                "data_consegna_richiesta_cliente": "15/11/2026",
            })
        self.assertEqual(ctx.exception.code, "E_PREV_VALIDAZIONE")
        self.assertEqual(ctx.exception.context.get("field"), "data_consegna_richiesta_cliente")
        resolver.assert_not_called()
        self.mock_repo.create_riga.assert_not_called()

    def test_in_patch_null_azzera_e_assenza_non_tocca(self):
        from apps.vendite.services.preventivi_service import aggiorna_riga

        aggiorna_riga(1, 10, {"descrizione": "x", "data_consegna_richiesta_cliente": None})
        campi = self.mock_repo.update_riga.call_args.kwargs
        self.assertIn("data_consegna_richiesta_cliente", campi)
        self.assertIsNone(campi["data_consegna_richiesta_cliente"])

        self.mock_repo.update_riga.reset_mock()
        aggiorna_riga(1, 10, {"descrizione": "y"})
        self.assertNotIn(
            "data_consegna_richiesta_cliente", self.mock_repo.update_riga.call_args.kwargs,
        )


# Scopo: I satelliti «leggono prima la testata» (2026-09-21, allineamento a
#        api.md §Scope emittente): un preventivo fuori perimetro RLS — `None`
#        dal repository, come un id inesistente — e' un 404, non un 200 vuoto.
#
# Indice:
# 51) test_list_righe_preventivo_non_trovato_e_404
# 52) test_list_riepilogo_iva_preventivo_non_trovato_e_404
# 53) test_list_revisioni_preventivo_non_trovato_e_404
# 54) test_list_righe_con_testata_delega_al_repo
class PreventiviSatellitiTestataTests(SimpleTestCase):
    def setUp(self):
        self.repo_patcher = patch(
            "apps.vendite.services.preventivi_service.PreventiviRepository"
        )
        self.mock_repo = self.repo_patcher.start().return_value
        self.addCleanup(self.repo_patcher.stop)

    def test_list_righe_preventivo_non_trovato_e_404(self):
        from apps.vendite.services.preventivi_service import list_righe

        self.mock_repo.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as cm:
            list_righe(99)
        self.assertEqual(cm.exception.code, "E_PREV_NOT_FOUND")
        self.mock_repo.list_righe.assert_not_called()

    def test_list_riepilogo_iva_preventivo_non_trovato_e_404(self):
        from apps.vendite.services.preventivi_service import list_riepilogo_iva

        self.mock_repo.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as cm:
            list_riepilogo_iva(99)
        self.assertEqual(cm.exception.code, "E_PREV_NOT_FOUND")
        self.mock_repo.list_riepilogo_iva.assert_not_called()

    def test_list_revisioni_preventivo_non_trovato_e_404(self):
        from apps.vendite.services.preventivi_service import list_revisioni

        self.mock_repo.get_preventivo.return_value = None
        with self.assertRaises(ServiceError) as cm:
            list_revisioni(99)
        self.assertEqual(cm.exception.code, "E_PREV_NOT_FOUND")
        self.mock_repo.list_revisioni.assert_not_called()

    def test_list_righe_con_testata_delega_al_repo(self):
        from apps.vendite.services.preventivi_service import list_righe

        self.mock_repo.get_preventivo.return_value = {"id": 7, "stato_codice_interno": "DRAFT"}
        self.mock_repo.list_righe.return_value = [{"id": 31}]
        self.assertEqual(list_righe(7), [{"id": 31}])
        self.mock_repo.list_righe.assert_called_once_with(7)
