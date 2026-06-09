# handler_registry (Django)

## Scopo

Registry degli handler flusso: mapping statico da `handler_key` (definita in DB nella tabella `pratiche.handler_flussi`) a classi Python che implementano la logica di automazione.

## Contesto

Il modulo vive in `apps/pratiche/services/handler_registry.py`. Il pattern e' esplicito e sicuro: nessun dynamic import, nessun magic. Il DB contiene le chiavi (`handler_key`), Django contiene il mapping a classi concrete.

Un handler viene invocato da `pratiche_service.dispatch_handler` quando un flusso ha un `template_flusso_id` il cui template ha un `handler_id` configurato in `pratiche.handler_flussi`.

## Input

- `handler_key` (stringa) da `pratiche.handler_flussi.handler_key`.
- Dati runtime per execute handler:
  - `flusso_id` (int)
  - `pratica_id` (int)
  - `meta` (dict)

## Output

- `get_handler(handler_key)` restituisce:
  - classe handler registrata (`type[BaseFlussoHandler]`) se presente
  - `None` se non registrata
- `execute(...)` dell'handler restituisce payload `dict[str, Any]` dominio-specifico.

## Componenti

### BaseFlussoHandler (Protocol)

Contratto per handler flusso. Ogni handler deve implementare:

```python
def execute(self, flusso_id: int, pratica_id: int,
            meta: dict[str, Any], handler_params: dict[str, Any],
            user: str | None = None) -> dict[str, Any]: ...
```

- `meta`: jsonb del flusso (dati d'istanza, es. `preventivo_id`).
- `handler_params`: jsonb del template (configurazione statica, es.
  `modalita_fatturazione`).
- `user`: utente acting (per `p_user` delle fn DB; `None` = `CURRENT_USER`).

### HANDLER_MAP

Dizionario `dict[str, type[BaseFlussoHandler]]`. **Popolato a runtime** via
`register_handler()` chiamato da `AppConfig.ready()` del dominio consumatore
(es. `apps/vendite/apps.py`), per evitare la dipendenza di import
`pratiche→vendite` (l'handler vive nel dominio chiamante).

Handler registrati:

| handler_key | Classe | Dominio |
| --- | --- | --- |
| `vendita.push_preventivo` | `PushPreventivoHandler` | vendite |

### register_handler(handler_key, handler_class)

Registra (o sovrascrive) un handler. Idempotente. Chiamato in `ready()`.

### get_handler(handler_key)

Restituisce la classe handler per la chiave indicata, o `None` se non registrata.

## Regole

- No dynamic import: il mapping e' esplicito; la registrazione avviene in `ready()`.
- Se la chiave non e' registrata in `HANDLER_MAP`, `dispatch_handler` ritorna `None` senza errore.
- Ogni handler riceve `flusso_id`, `pratica_id`, `meta`, `handler_params`, `user`.
- L'handler viene istanziato ad ogni invocazione (`handler_class()`).
- `dispatch_handler` è invocato da `avvia_flusso` quando un flusso con
  `handler_id` passa a `IN_CORSO`; su successo `avvia_flusso` completa il flusso
  con esito `POSITIVO`, tutto in una transazione.

## Dipendenze DB

- `pratiche.handler_flussi` (tabella config con handler_key)
- `pratiche.template_flussi` (FK handler_id → handler_flussi)

## Note di migrazione

- Primo handler reale: `vendita.push_preventivo` (vedi
  `vendite/manual/push_preventivo_handler.md`).
- Per aggiungere un handler: implementare la classe nel dominio chiamante e
  registrarla in `AppConfig.ready()` con `register_handler(...)`.
