# Tool Registry — Registro strumenti AI (Django)

## Scopo

Gestire il catalogo centralizzato degli strumenti AI disponibili per il function calling, con filtro per permessi utente e blacklist per installazione.

## Contesto

Ogni strumento AI (tool) wrappa un service/repository esistente di ZeroERP e lo rende disponibile all'LLM tramite function calling. Il registro viene popolato all'avvio dell'app (`AppConfig.ready()`) e filtrato ad ogni richiesta in base ai permessi dell'operatore autenticato.

Ogni tool dichiara il suo **endpoint gemello** (`EndpointGemello(view, metodo)`): la view della UI che chiama lo stesso service con lo stesso significato. Dal gemello si **derivano** il permesso del tool e se il tool scrive; il tool non dichiara area, livello, azione o conferma.

## Catalogo strumenti registrati

L'elenco dei tool con il loro gemello sta in una sede sola: [guida AI §6](../../../guide/integrazione-ai.md). La prova che ogni gemello regge (la view esiste, implementa il metodo, la regola lo sa valutare) e' `apps/ai_assistant/tests/tools/test_tool_endpoint_gemello.py`, che legge il registro e non un elenco scritto a mano.

## Input

### `get_tools_for_user(user)` / `is_tool_allowed_for_user(user, tool)`

Un predicato solo, chiamato quando il catalogo si offre al modello, quando un tool viene eseguito e quando si conferma una scrittura. Tre filtri, in ordine:

1. **Blacklist installazione**: `config.parameters` chiave `AI_DISABLED_TOOLS` (lista separata da virgola). Cache TTL 300s.
2. **Permesso del gemello**: `valuta_accesso_endpoint(user, gemello.view, method=gemello.metodo)`, la stessa regola di `ZeroERPPermission` per la UI: area dal model o da `area_funzionale`, tipo di accesso del metodo, `<metodo>_permission`, override per oggetto, `skip_area_check`, `SUPER_ADMIN`. Una veste spenta (`attivo = false`) non dà un'identità attiva, quindi niente `SUPER_ADMIN` e livello d'area negato.
3. **Livello sull'assistente**: `valuta_accesso_endpoint(user, AIQueryView, method="POST", accesso=<tipo del tool>)`. Il tipo e' `view` se il tool legge, quello del gemello se scrive. Quindi `LETTURA` su `ai_assistant` concede solo i tool di lettura, `TUTTO` anche quelli di scrittura, `BLOCCATO` niente. Vale sempre il piu' stretto fra questo livello e quello del dominio.

## Output

Lista di oggetti `AITool` con:

- `name`: identificativo univoco (es. `cerca_pratiche`)
- `description`: descrizione in italiano per l'LLM
- `input_schema`: JSON Schema dei parametri
- `endpoint`: il gemello (`EndpointGemello`)
- `scrive` / `requires_confirmation`: derivati dal gemello con `chiamata_in_scrittura` (tutto cio' che non chiede `view`)
- `route_template`: template rotta Vue per azioni di navigazione

## Regole

- Ogni tool deve corrispondere a un service/repository gia' esistente e stabile — mai SQL diretto nel tool handler.
- Un tool che scrive chiede sempre conferma; la sua anteprima e ogni tool che legge girano in `transazione_sola_lettura` (il DB ferma una scrittura con `25006`). Lo applica `ai_assistant_service`, non il registro.
- Il catalogo viene convertito in formato JSON Schema per l'API Anthropic tramite `tool.to_tool_schema()`.
- Le azioni di navigazione vengono estratte automaticamente dai risultati tramite `tool.extract_actions()` se il tool ha un `route_template` definito. Massimo 5 azioni per tool.
- La blacklist usa `config.parameters` (chiave `AI_DISABLED_TOOLS`), coerente con il pattern configurazione di ZeroERP. Se il parametro non esiste, nessun tool e' disabilitato.
- Un tool senza gemello e' un'eccezione da decidere e scrivere per nome, con il motivo, in `_SENZA_GEMELLO` (`test_tool_endpoint_gemello.py`).

## Dipendenze DB

- `script.fn_resolve_livello_area` / `fn_resolve_livello_oggetto` / `fn_check_azione_processo` (via `PermissionResolver`) — i livelli e le azioni dell'utente
- `script.fn_get_parameter_full('AI_DISABLED_TOOLS')` — blacklist tool (opzionale)

## Note di migrazione

- Il registro e' un dizionario Python in-memory, non una tabella DB.
- Per aggiungere un nuovo tool: creare il file in `tools/`, implementare la classe con `execute()` (e `preview()` se il gemello scrive), dichiarare il gemello, registrare in `populate_registry()`.
- La blacklist ha cache TTL 300s — modifiche a `config.parameters` sono visibili entro 5 minuti senza restart.
