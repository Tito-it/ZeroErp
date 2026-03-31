# Tool Registry — Registro strumenti AI (Django)

## Scopo

Gestire il catalogo centralizzato degli strumenti AI disponibili per il function calling, con filtro per permessi utente e blacklist per installazione.

## Contesto

Ogni strumento AI (tool) wrappa un service/repository esistente di ZeroERP e lo rende disponibile all'LLM tramite function calling. Il registro viene popolato all'avvio dell'app (`AppConfig.ready()`) e filtrato ad ogni richiesta in base ai permessi dell'operatore autenticato.

## Catalogo strumenti registrati

### Fase 1

| Tool | Dominio | Area | Livello | Service wrappato |
|---|---|---|---|---|
| `cerca_pratiche` | pratiche | `pratiche` | LETTURA | `pratiche_service.cerca_pratiche()` |

### Fase 3

| Tool | Dominio | Area | Livello | Service wrappato |
|---|---|---|---|---|
| `dettaglio_pratica` | pratiche | `pratiche` | LETTURA | `PraticheRepository.get_pratica()` |
| `cerca_flussi_pratica` | pratiche | `pratiche` | LETTURA | `PraticheRepository.list_flussi()` |
| `cerca_soggetti` | anagrafiche | `anagrafiche` | LETTURA | `SoggettiService.list_soggetti()` |
| `dettaglio_soggetto` | anagrafiche | `anagrafiche` | LETTURA | `SoggettiService.get_soggetto()` |
| `cerca_operatori` | amm_software | `amm_software` | LETTURA | `AmmSoftwareService.list_operatori()` |

## Input

### `get_tools_for_user(user)` — Tool disponibili per un utente

Applica tre livelli di filtro:

1. **Blacklist installazione**: `config.parameters` chiave `AI_DISABLED_TOOLS` (lista separata da virgola). Cache TTL 300s.
2. **Permessi area**: confronto `tool.required_area` con `script.fn_get_user_permissions_map(user_id)`. Se l'area e' `BLOCCATO` o non presente, il tool viene escluso. Se `required_area` e' `None`, il tool e' disponibile a tutti.
3. **Livello accesso**: se `tool.required_level = TUTTO` e l'utente ha solo `LETTURA`, il tool viene escluso.

## Output

Lista di oggetti `AITool` con:
- `name`: identificativo univoco (es. `cerca_pratiche`)
- `description`: descrizione in italiano per l'LLM
- `input_schema`: JSON Schema dei parametri
- `required_area`: area funzionale richiesta
- `required_level`: livello minimo accesso
- `route_template`: template rotta Vue per azioni di navigazione

## Regole

- Ogni tool deve corrispondere a un service/repository gia' esistente e stabile — mai SQL diretto nel tool handler.
- Il catalogo viene convertito in formato JSON Schema per l'API Anthropic tramite `tool.to_tool_schema()`.
- Le azioni di navigazione vengono estratte automaticamente dai risultati tramite `tool.extract_actions()` se il tool ha un `route_template` definito. Massimo 5 azioni per tool.
- La blacklist usa `config.parameters` (chiave `AI_DISABLED_TOOLS`), coerente con il pattern configurazione di ZeroERP. Se il parametro non esiste, nessun tool e' disabilitato.

## Dipendenze DB

- `script.fn_get_user_permissions_map(user_id)` — mappa permessi area dell'utente
- `script.fn_get_parameter_full('AI_DISABLED_TOOLS')` — blacklist tool (opzionale)

## Note di migrazione

- Il registro e' un dizionario Python in-memory, non una tabella DB.
- Per aggiungere un nuovo tool: creare il file in `tools/`, implementare la classe con `execute()`, registrare in `populate_registry()`.
- La blacklist ha cache TTL 300s — modifiche a `config.parameters` sono visibili entro 5 minuti senza restart.
