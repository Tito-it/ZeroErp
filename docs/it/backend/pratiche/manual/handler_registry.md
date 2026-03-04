# handler_registry (Django)

## Scopo

Registry degli handler flusso: mapping statico da `handler_key` (definita in DB nella tabella `pratiche.handler_flussi`) a classi Python che implementano la logica di automazione.

## Contesto

Il modulo vive in `apps/pratiche/services/handler_registry.py`. Il pattern e' esplicito e sicuro: nessun dynamic import, nessun magic. Il DB contiene le chiavi (`handler_key`), Django contiene il mapping a classi concrete.

Un handler viene invocato da `pratiche_service.dispatch_handler` quando un flusso ha un `template_flusso_id` il cui template ha un `handler_id` configurato in `pratiche.handler_flussi`.

## Componenti

### BaseFlussoHandler (Protocol)

Contratto per handler flusso. Ogni handler deve implementare:

```python
def execute(self, flusso_id: int, pratica_id: int, meta: dict[str, Any]) -> dict[str, Any]: ...
```

### HANDLER_MAP

Dizionario statico `dict[str, type[BaseFlussoHandler]]`. Vuoto per default — da popolare man mano che si implementano handler specifici.

Esempio di registrazione:
```python
HANDLER_MAP: dict[str, type[BaseFlussoHandler]] = {
    "APPUNTAMENTO": AppuntamentoHandler,
    "SOPRALLUOGO": SopralluogoHandler,
}
```

### get_handler(handler_key)

Restituisce la classe handler per la chiave indicata, o `None` se non registrata.

## Regole

- No dynamic import: il mapping e' statico e esplicito.
- Se la chiave non e' registrata in `HANDLER_MAP`, `dispatch_handler` ritorna `None` senza errore.
- Ogni handler riceve `flusso_id`, `pratica_id` e `meta` (dal campo jsonb del flusso).
- L'handler viene istanziato ad ogni invocazione (`handler_class()`).

## Dipendenze DB

- `pratiche.handler_flussi` (tabella config con handler_key)
- `pratiche.template_flussi` (FK handler_id → handler_flussi)

## Note di migrazione

- Il registry e' attualmente vuoto. Gli handler specifici verranno implementati come estensioni future (appuntamento, sopralluogo, preventivo, comunicazione, spedizione).
- L'architettura e' pronta: basta aggiungere la classe e registrarla in `HANDLER_MAP`.
