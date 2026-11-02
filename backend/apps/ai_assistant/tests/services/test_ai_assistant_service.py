# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per il servizio principale AI assistant.
#        Verifica il flusso completo con provider mock:
#        input → tool_call → tool_result → risposta finale.
# ------------------------------------------------------------

# Indice test:
# 1. test_query_returns_ai_query_result
# 2. test_query_empty_message_raises
# 3. test_query_too_long_raises
# 4. test_query_with_tool_call
# 5. test_query_conversation_reuse
# 6. test_query_max_iterations
# 7. test_conversation_scope_isolates_users (post-fix 23-04-2026 data leak cross-user)
# 8. test_conversation_scope_isolates_identita (stessa persona, veste diversa)
# 9. test_query_tool_call_not_permitted_is_refused (ri-check permessi nel loop)
# 10. test_execute_confirmation_refused_when_permission_lost (ri-check TOCTOU alla conferma)
# 11. TestAuditLogReliability.test_reliable_failure_logs_error / _best_effort_failure_logs_warning
# 12. TestSolaLetturaNelCiclo.test_il_tool_che_legge_gira_in_sola_lettura
# 13. TestSolaLetturaNelCiclo.test_l_anteprima_si_e_l_esecuzione_confermata_no

import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock, patch

from django.core.cache.backends.locmem import LocMemCache

from apps.ai_assistant.providers.mock_provider import MockProvider
from apps.ai_assistant.services import ai_assistant_service
from apps.ai_assistant.services import tool_registry
from apps.core.services.permissions_resolver import PermissionResolver
from apps.ai_assistant.tools.base import AITool, EndpointGemello
from apps.core.api.base_views import DomainAPIView
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE
from apps.ai_assistant.types import ToolCall
from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova


# Gemello fabbricato: il permesso dei tool di test e' quello di questa view,
# decisa dalla regola di `ZeroERPPermission` (GET → view, POST → add).
class _PraticheView(DomainAPIView):
    area_funzionale = "pratiche"


class _DummySearchTool(AITool):
    """Tool di test che restituisce risultati fissi."""

    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        return {
            "count": 1,
            "results": [
                {"id": 42, "codice": "PRA-001", "descrizione": "Test pratica", "stato": "APERTA"}
            ],
        }


# Scopo: al posto di `transazione_sola_lettura` nei test unitari: non apre
#        transazioni (niente DB) e dice se il codice sta girando DENTRO il
#        blocco. Che il blocco fermi davvero una scrittura lo prova il test su
#        DB vero (`core/tests/db/test_sola_lettura_db.py`).
class _SpiaSolaLettura:
    def __init__(self) -> None:
        self.dentro = False
        self.aperture = 0

    # Stessa firma del BB: `chi` (chi legge, per il log) e' keyword-only.
    @contextmanager
    def __call__(self, *, chi: str = "(non dichiarato)") -> Iterator[None]:
        self.aperture += 1
        self.chi = chi
        self.dentro = True
        try:
            yield
        finally:
            self.dentro = False


class TestAIAssistantService(unittest.TestCase):
    """Test ai_assistant_service.query()."""

    def setUp(self):
        # Cache conferme isolata in-process (no Redis: regola CI "test senza servizi").
        patcher = patch.object(ai_assistant_service, "cache", LocMemCache("ai-test-service", {}))
        patcher.start()
        self.addCleanup(patcher.stop)

        # La sola lettura a DB non si apre in un test unitario.
        self.spia_sola_lettura = _SpiaSolaLettura()
        patcher = patch.object(
            ai_assistant_service, "transazione_sola_lettura", self.spia_sola_lettura,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        ai_assistant_service.clear_conversations()
        tool_registry.clear_registry()

        for nome, valore in (
            ("get_ruolo_applicativo", RUOLO_APPLICATIVO_OPERATORE),
            ("is_super_admin", False),
        ):
            patcher = patch.object(PermissionResolver, nome, return_value=valore)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.user = operatore_di_prova(user_id=1)
        self.user.first_name = "Test"
        self.user.last_name = "User"
        self.user.username = "testuser"

        self.request = MagicMock()
        self.request.user = self.user

    def tearDown(self):
        ai_assistant_service.clear_conversations()
        tool_registry.clear_registry()

    # Scopo: Verifica che una query semplice restituisca AIQueryResult.
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area", return_value="BLOCCATO")
    def test_query_returns_ai_query_result(self, mock_perms, mock_disabled, mock_log, mock_provider):
        mock_provider.return_value = MockProvider(default_response="Ciao, sono l'assistente.")

        result = ai_assistant_service.query(
            user=self.user,
            request=self.request,
            message="ciao",
        )

        self.assertIn("conversation_id", result)
        self.assertIn("response", result)
        self.assertEqual(result["response"], "Ciao, sono l'assistente.")
        self.assertIsInstance(result["tools_used"], list)
        self.assertIsInstance(result["actions"], list)

    # Scopo: Messaggio vuoto deve sollevare ServiceError.
    def test_query_empty_message_raises(self):
        with self.assertRaises(ServiceError) as ctx:
            ai_assistant_service.query(
                user=self.user,
                request=self.request,
                message="",
            )
        self.assertEqual(ctx.exception.code, "E_AI_QUERY_EMPTY")

    # Scopo: Messaggio troppo lungo deve sollevare ServiceError.
    def test_query_too_long_raises(self):
        with self.assertRaises(ServiceError) as ctx:
            ai_assistant_service.query(
                user=self.user,
                request=self.request,
                message="x" * 2001,
            )
        self.assertEqual(ctx.exception.code, "E_AI_QUERY_TOO_LONG")

    # Scopo: Verifica il flusso completo con tool_call:
    #        provider simula tool_call → service esegue tool →
    #        provider risponde con testo finale.
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area", return_value="LETTURA")
    def test_query_with_tool_call(self, mock_perms, mock_disabled, mock_log, mock_provider):
        # Registra tool di test
        tool = _DummySearchTool(
            name="cerca_pratiche", description="d", input_schema={},
            endpoint=EndpointGemello(_PraticheView, "GET"),
            route_template={"name": "pratiche-dettaglio", "params": {"id": "{id}"}},
        )
        tool_registry.register_tool(tool)

        # Provider mock che simula tool_call alla prima chiamata
        provider = MockProvider(
            tool_response=ToolCall(
                id="tc_1", name="cerca_pratiche", input={"stato": "APERTA"}
            ),
            default_response="Ho trovato 1 pratica aperta.",
        )
        mock_provider.return_value = provider

        result = ai_assistant_service.query(
            user=self.user,
            request=self.request,
            message="mostrami le pratiche aperte",
        )

        self.assertIn("cerca_pratiche", result["tools_used"])
        self.assertEqual(result["response"], "Ho trovato 1 pratica aperta.")
        # Verifica azioni di navigazione estratte
        self.assertTrue(len(result["actions"]) > 0)
        self.assertEqual(result["actions"][0]["type"], "navigate")

    # Scopo: Verifica che la stessa conversation_id riusi i messaggi.
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area", return_value="BLOCCATO")
    def test_query_conversation_reuse(self, mock_perms, mock_disabled, mock_log, mock_provider):
        provider = MockProvider(default_response="Risposta 1")
        mock_provider.return_value = provider

        r1 = ai_assistant_service.query(
            user=self.user, request=self.request, message="prima domanda",
        )
        conv_id = r1["conversation_id"]

        provider2 = MockProvider(default_response="Risposta 2")
        mock_provider.return_value = provider2

        r2 = ai_assistant_service.query(
            user=self.user, request=self.request, message="seconda domanda",
            conversation_id=conv_id,
        )
        self.assertEqual(r2["conversation_id"], conv_id)

        # Il provider deve aver ricevuto i messaggi precedenti
        # (user + assistant dalla prima query + user dalla seconda)
        self.assertTrue(len(provider2.last_messages) >= 3)

    # Scopo: Verifica che il limite iterazioni produca risposta parziale.
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area", return_value="LETTURA")
    @patch.object(ai_assistant_service, "MAX_TOOL_ITERATIONS", 2)
    def test_query_max_iterations(self, mock_perms, mock_disabled, mock_log, mock_provider):
        tool = _DummySearchTool(
            name="cerca_pratiche", description="d", input_schema={},
            endpoint=EndpointGemello(_PraticheView, "GET"),
        )
        tool_registry.register_tool(tool)

        # Provider che restituisce SEMPRE tool_call (non termina mai)
        provider = MockProvider(
            tool_response=ToolCall(id="tc_loop", name="cerca_pratiche", input={}),
        )
        # Override: restituisci sempre tool_call, anche dopo la prima

        def always_tool_call(**kwargs):
            from apps.ai_assistant.types import ProviderResponse, TokenUsage
            return ProviderResponse(
                content=None,
                tool_calls=[ToolCall(id=f"tc_{provider.call_count}", name="cerca_pratiche", input={})],
                usage=TokenUsage(input_tokens=10, output_tokens=5),
                stop_reason="tool_use",
            )

        provider.send_message = always_tool_call
        mock_provider.return_value = provider

        result = ai_assistant_service.query(
            user=self.user, request=self.request, message="loop infinito",
        )
        self.assertTrue(result["has_more"])
        self.assertIn("limite", result["response"].lower())

    # Scopo: regressione per data leak cross-user (fix 23-04-2026).
    #        Utente B che usa un conversation_id generato da utente A NON
    #        deve leggere i messaggi di A: il service tratta la riga come
    #        "non esistente" e crea una nuova conversation sotto lo stesso
    #        UUID, isolata per scope (owner_user_id).
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area", return_value="BLOCCATO")
    def test_conversation_scope_isolates_users(
        self, mock_perms, mock_disabled, mock_log, mock_provider
    ):
        # Utente A crea una conversazione
        user_a = MagicMock()
        user_a.id = 100
        user_a.first_name = "Alice"
        user_a.last_name = "A"
        user_a.username = "alice"
        request_a = MagicMock()
        request_a.user = user_a
        request_a.auth = None

        provider_a = MockProvider(default_response="Segreto di A")
        mock_provider.return_value = provider_a
        r_a = ai_assistant_service.query(
            user=user_a, request=request_a, message="domanda privata di A",
        )
        conv_id = r_a["conversation_id"]

        # Utente B tenta di continuare la conversation_id di A
        user_b = MagicMock()
        user_b.id = 200
        user_b.first_name = "Bob"
        user_b.last_name = "B"
        user_b.username = "bob"
        request_b = MagicMock()
        request_b.user = user_b
        request_b.auth = None

        provider_b = MockProvider(default_response="Risposta a B")
        mock_provider.return_value = provider_b
        ai_assistant_service.query(
            user=user_b, request=request_b, message="cosa ha chiesto A?",
            conversation_id=conv_id,
        )

        # Il provider per B non deve aver ricevuto i messaggi di A:
        # solo il suo ("cosa ha chiesto A?"), senza contesto storico.
        user_msgs_in_b = [
            m for m in provider_b.last_messages
            if m.get("role") == "user"
        ]
        self.assertEqual(len(user_msgs_in_b), 1)
        self.assertIn("cosa ha chiesto A?", user_msgs_in_b[0]["content"])
        # Sanity: provider B non ha visto il contenuto privato di A
        all_contents = " ".join(
            str(m.get("content", "")) for m in provider_b.last_messages
        )
        self.assertNotIn("Segreto di A", all_contents)
        self.assertNotIn("domanda privata di A", all_contents)

    # Scopo: stessa persona fisica con due vesti (identita_id diverse).
    #        Le conversazioni devono restare isolate: passare al claim
    #        identita diverso = nuova conversazione anche se user_id
    #        e conversation_id coincidono. Garantisce che un operatore
    #        che switcha veste non veda contesto della veste precedente.
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area", return_value="BLOCCATO")
    def test_conversation_scope_isolates_identita(
        self, mock_perms, mock_disabled, mock_log, mock_provider
    ):
        user = MagicMock()
        user.id = 300
        user.first_name = "Mario"
        user.last_name = "Rossi"
        user.username = "mariorossi"

        # Veste 1: identita_id = 10
        request_v1 = MagicMock()
        request_v1.user = user
        request_v1.auth = {"identita_id": 10}
        provider_v1 = MockProvider(default_response="Contesto veste 1")
        mock_provider.return_value = provider_v1
        r_v1 = ai_assistant_service.query(
            user=user, request=request_v1, message="ciao dalla veste 1",
        )
        conv_id = r_v1["conversation_id"]

        # Veste 2: identita_id = 20 (stessa persona, veste diversa)
        request_v2 = MagicMock()
        request_v2.user = user
        request_v2.auth = {"identita_id": 20}
        provider_v2 = MockProvider(default_response="Contesto veste 2")
        mock_provider.return_value = provider_v2
        ai_assistant_service.query(
            user=user, request=request_v2, message="ciao dalla veste 2",
            conversation_id=conv_id,
        )

        # Il provider della veste 2 non deve aver ricevuto il contesto
        # della veste 1.
        all_contents = " ".join(
            str(m.get("content", "")) for m in provider_v2.last_messages
        )
        self.assertNotIn("ciao dalla veste 1", all_contents)

    # Scopo: ri-check permessi a execution-time nel loop. Anche se il catalogo
    #        inviato e' filtrato, un tool_call per un tool NON permesso (prompt
    #        injection / errore modello) deve essere rifiutato, senza preview ne'
    #        execute.
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area", return_value="LETTURA")
    def test_query_tool_call_not_permitted_is_refused(
        self, mock_perms, mock_disabled, mock_log, mock_provider
    ):
        spy = _SpyWriteTool(
            name="cambia_stato_pratica", description="d", input_schema={},
            endpoint=EndpointGemello(_PraticheView, "POST"),
        )
        tool_registry.register_tool(spy)

        # L'LLM chiama comunque il tool in scrittura (l'utente ha solo LETTURA).
        provider = MockProvider(
            tool_response=ToolCall(id="tc1", name="cambia_stato_pratica", input={}),
            default_response="Non posso eseguire questa operazione.",
        )
        mock_provider.return_value = provider

        result = ai_assistant_service.query(
            user=self.user, request=self.request, message="cambia stato pratica 1",
        )

        # Rifiutato prima di preview/execute: nessuna conferma proposta.
        self.assertFalse(spy.executed)
        self.assertFalse(spy.previewed)
        self.assertFalse(any(a.get("type") == "confirm" for a in result["actions"]))

    # Scopo: ri-check permessi alla conferma (TOCTOU). Tool offerto+previewato con
    #        TUTTO, poi il livello scende a LETTURA prima del __confirm__: la
    #        conferma deve essere rifiutata e il tool NON eseguito.
    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    def test_execute_confirmation_refused_when_permission_lost(
        self, mock_disabled, mock_log, mock_provider
    ):
        spy = _SpyWriteTool(
            name="cambia_stato_pratica", description="d", input_schema={},
            endpoint=EndpointGemello(_PraticheView, "POST"),
        )
        tool_registry.register_tool(spy)

        provider = MockProvider(
            tool_response=ToolCall(
                id="tc1", name="cambia_stato_pratica",
                input={"pratica_id": 1, "nuovo_stato": "APERTA"},
            ),
            default_response="Vuoi confermare?",
        )
        mock_provider.return_value = provider

        # Fase 1: permesso pieno → preview + conferma pendente.
        with patch.object(PermissionResolver, "get_livello_area", return_value="TUTTO"):
            r1 = ai_assistant_service.query(
                user=self.user, request=self.request, message="cambia stato pratica 1",
            )
        conv_id = r1["conversation_id"]
        self.assertTrue(any(a.get("type") == "confirm" for a in r1["actions"]))
        self.assertTrue(spy.previewed)
        self.assertFalse(spy.executed)

        # Fase 2: permesso declassato → conferma rifiutata, tool non eseguito.
        with patch.object(PermissionResolver, "get_livello_area", return_value="LETTURA"):
            r2 = ai_assistant_service.query(
                user=self.user, request=self.request, message="__confirm__",
                conversation_id=conv_id,
            )
        self.assertFalse(spy.executed)
        self.assertIn("permessi", r2["response"].lower())


class _SpyWriteTool(AITool):
    """Tool in scrittura di test: traccia preview/execute senza effetti reali,
    e se ciascuno e' girato dentro la sola lettura (`spia`, se data)."""

    def __init__(self, *, spia: _SpiaSolaLettura | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.previewed = False
        self.executed = False
        self.spia = spia
        self.preview_in_sola_lettura: bool | None = None
        self.execute_in_sola_lettura: bool | None = None

    def preview(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        self.previewed = True
        if self.spia is not None:
            self.preview_in_sola_lettura = self.spia.dentro
        return {"summary": "preview operazione", "details": params}

    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        self.executed = True
        if self.spia is not None:
            self.execute_in_sola_lettura = self.spia.dentro
        return {"message": "operazione eseguita"}


class _SpyReadTool(AITool):
    """Tool in lettura di test: dice se execute e' girato in sola lettura."""

    def __init__(self, *, spia: _SpiaSolaLettura, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.spia = spia
        self.execute_in_sola_lettura: bool | None = None

    def execute(self, params: dict[str, Any], request: Any) -> dict[str, Any]:
        self.execute_in_sola_lettura = self.spia.dentro
        return {"count": 0, "results": []}


# Scopo: brief-db-area-funzionale-assistente-ai §5.3 punto 3 — DOVE il ciclo
#        apre la sola lettura. Lettura e anteprima dentro; l'esecuzione
#        confermata di una scrittura fuori (deve scrivere).
class TestSolaLetturaNelCiclo(unittest.TestCase):

    # Stesso ambiente della classe madre (cache, permessi, spia), senza
    # ereditarne i test.
    setUp = TestAIAssistantService.setUp
    tearDown = TestAIAssistantService.tearDown

    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area", return_value="TUTTO")
    def test_il_tool_che_legge_gira_in_sola_lettura(
        self, mock_perms, mock_disabled, mock_log, mock_provider,
    ):
        spy = _SpyReadTool(
            spia=self.spia_sola_lettura,
            name="cerca_pratiche", description="d", input_schema={},
            endpoint=EndpointGemello(_PraticheView, "GET"),
        )
        tool_registry.register_tool(spy)
        mock_provider.return_value = MockProvider(
            tool_response=ToolCall(id="tc1", name="cerca_pratiche", input={}),
            default_response="Nessuna pratica.",
        )

        ai_assistant_service.query(user=self.user, request=self.request, message="pratiche?")

        self.assertIs(spy.execute_in_sola_lettura, True)

    @patch("apps.ai_assistant.services.ai_assistant_service.get_ai_provider")
    @patch("apps.ai_assistant.services.ai_assistant_service._log_query")
    @patch.object(tool_registry, "_get_disabled_tools", return_value=set())
    @patch.object(PermissionResolver, "get_livello_area", return_value="TUTTO")
    def test_l_anteprima_si_e_l_esecuzione_confermata_no(
        self, mock_perms, mock_disabled, mock_log, mock_provider,
    ):
        spy = _SpyWriteTool(
            spia=self.spia_sola_lettura,
            name="crea_pratica", description="d", input_schema={},
            endpoint=EndpointGemello(_PraticheView, "POST"),
        )
        tool_registry.register_tool(spy)
        mock_provider.return_value = MockProvider(
            tool_response=ToolCall(id="tc1", name="crea_pratica", input={}),
            default_response="Vuoi confermare?",
        )

        r1 = ai_assistant_service.query(user=self.user, request=self.request, message="crea")
        self.assertIs(spy.preview_in_sola_lettura, True)
        self.assertFalse(spy.executed)

        ai_assistant_service.query(
            user=self.user, request=self.request, message="__confirm__",
            conversation_id=r1["conversation_id"],
        )
        self.assertIs(spy.execute_in_sola_lettura, False)


class TestAuditLogReliability(unittest.TestCase):
    """Test affidabilita' audit ai_query_log (P2): le scritture confermate
    devono alzare un alert ERROR se il logging fallisce; le letture restano
    best-effort (WARNING)."""

    def _save_with_failing_db(self, *, reliable: bool):
        from apps.ai_assistant.db import ai_query_log_repository as mod

        repo = mod.AIQueryLogRepository()
        with patch.object(mod, "connection") as mock_conn:
            mock_conn.cursor.side_effect = RuntimeError("db down")
            with self.assertLogs(mod.logger, level="WARNING") as cm:
                repo.save_query_log(
                    request_id="req-1", user_id=1, input_text="x",
                    tools_called=None, response_text=None,
                    provider="mock", model="m",
                    tokens_input=None, tokens_output=None,
                    duration_ms=1, error_code=None, reliable=reliable,
                )
        return cm

    # Scopo: scrittura confermata (reliable=True) → fallimento log = alert ERROR.
    def test_reliable_failure_logs_error(self):
        cm = self._save_with_failing_db(reliable=True)
        self.assertTrue(any(r.levelname == "ERROR" for r in cm.records))

    # Scopo: lettura (reliable=False) → fallimento log = solo WARNING.
    def test_best_effort_failure_logs_warning(self):
        cm = self._save_with_failing_db(reliable=False)
        self.assertTrue(any(r.levelname == "WARNING" for r in cm.records))
        self.assertFalse(any(r.levelname == "ERROR" for r in cm.records))
