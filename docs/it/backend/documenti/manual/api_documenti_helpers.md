# Building block — helper API motore documentale

## Scopo

Helper condivisi `apps/documenti/api/` riusabili dalle view documentali
"per sorgente" (offerta, preventivo, contratto, ...) per:

1. risolvere il **contesto comune** richiesto da ogni endpoint
   `documenti/...` (entità sorgente esistente, emittente fiscale
   risolto, sorgente_tipo configurato e attivo);
2. estrarre gli **allegati multipart** in forma neutra consumabile da
   `DocumentGenerationService.genera_documento(allegati=...)`.

Centralizzano logica che prima era duplicata in ogni
`<sorgente>_documenti_views.py` (offerte, preventivi, contratti), con
disallineamenti su codici errore, formato file e check sequenziali.

## Contesto

Introdotti il 2026-05-28 contestualmente all'introduzione del pattern
unificato cross-dominio per emissione + allegati su offerta / preventivo
/ contratto. La differenza per dominio è ridotta al repository che
fetcha l'entità e ai messaggi i18n-aware: l'helper accetta l'entità già
fetchata + i messaggi già formulati.

Caller noti:

- `apps.vendite.api.offerte_documenti_views._resolve_contesto_offerta`
- `apps.vendite.api.preventivi_documenti_views._resolve_contesto_preventivo`
- `apps.vendite.api.contratti_documenti_views._resolve_contesto_contratto`

Estendibili a futuri domini documentali (es. ordini, DDT, fatture
PRO-FORMA) senza altra duplicazione.

## Input

### `resolve_contesto_documentale`

```python
from apps.documenti.api.contesto_helpers import resolve_contesto_documentale

def _resolve_contesto_<x>(x_id: int) -> tuple[dict[str, Any], int]:
    entity = XRepository().get_for_documento_generation(x_id)
    return resolve_contesto_documentale(
        entity=entity,
        entity_id=x_id,
        not_found_message="<X> non trovato/a.",
        emittente_message="Emittente fiscale non risolto per <l'x>.",
        sorgente_codice="<CODICE>",
    )
```

Parametri (tutti keyword-only):

| Parametro            | Tipo                | Descrizione                                                                                |
| -------------------- | ------------------- | ------------------------------------------------------------------------------------------ |
| `entity`             | `dict \| None`      | Riga DB già fetchata dal repository dominio. Deve contenere almeno la chiave `emittente_fiscale_id` |
| `entity_id`          | `int`               | ID dell'entità (usato per `detail` degli errori) |
| `not_found_message`  | `str`               | Messaggio business-safe quando l'entità non esiste                                          |
| `emittente_message`  | `str`               | Messaggio business-safe quando l'entità esiste ma non ha emittente risolto                  |
| `sorgente_codice`    | `str`               | Codice in `documenti.sorgenti_tipi` (es. `"OFFERTA_COMMERCIALE"`, `"PREVENTIVO"`, `"CONTRATTO"`) |

### `extract_allegati`

```python
from apps.documenti.api.multipart_helpers import extract_allegati

def post(self, request: Request, ...) -> JsonResponse:
    allegati = extract_allegati(request)
    DocumentGenerationService().genera_documento(..., allegati=allegati)
```

Parametri:

| Parametro | Tipo                          | Descrizione                                                                |
| --------- | ----------------------------- | -------------------------------------------------------------------------- |
| `request` | `rest_framework.request.Request` | Request DRF. Il campo file ripetuto atteso è `allegati` (multipart) |

## Output

### `resolve_contesto_documentale`

Ritorna `tuple[dict[str, Any], int]`:

- entity validata (stessa dict passata in input, garantita non-None);
- `sorgente_tipo_id` risolto (int).

Il tuple è pensato per essere unpackato direttamente nella view:

```python
entity, sorgente_tipo_id = _resolve_contesto_<x>(x_id)
```

### `extract_allegati`

Ritorna `list[dict[str, Any]]` con elementi:

```python
{
    "file_bytes": bytes,        # contenuto file
    "mime_type": str,           # content_type (vuoto se assente)
    "file_name": str,           # nome originale (vuoto se assente)
}
```

Lista vuota se la request non contiene allegati: il flusso a valle
persiste solo il PDF principale.

## Regole

1. **Fail-fast con messaggi parlanti** su ogni ramo: la view chiamante
   non gestisce esplicitamente gli errori, propaga al middleware standard.
2. **Codici errore unificati** (allineati alla convenzione delle view
   documentali):
   - `E_DOCUMENTI_NOT_FOUND` (404) — entità non trovata
   - `E_DOCUMENTI_VALIDATION` (400/422) — emittente non risolto o
     sorgente non configurata/non attiva
3. **Neutro vs UploadedFile**: `extract_allegati` materializza i bytes
   eagerly (chiamata `read()`) e ritorna un dict semplice — il
   `DocumentGenerationService` non dipende dall'oggetto DRF/Django, è
   testabile con fixture in-memory.
4. **Idempotente sul resolver sorgente**: la lookup
   `DocumentiRepository.get_sorgente_tipo_id_by_codice` è cached lato DB
   (config statica); il check `attivo` blocca sorgenti
   disabilitate/deprecate.
5. **Niente i18n nei messaggi**: le stringhe arrivano dalla view caller
   già formulate per il dominio (es. articolo determinativo italiano —
   "l'offerta" vs "il preventivo"). L'helper resta neutrale.

## Dipendenze DB

- `documenti.sorgenti_tipi` — lookup `get_sorgente_tipo_id_by_codice`
- `documenti.documenti_generati` (a valle, via service) — persistenza
  documento + allegati

## Codici errore

| Codice                    | HTTP    | Quando                                                                       |
| ------------------------- | ------- | ---------------------------------------------------------------------------- |
| `E_DOCUMENTI_NOT_FOUND`   | 404     | `entity is None` (record dominio inesistente)                                |
| `E_DOCUMENTI_VALIDATION`  | 400/422 | `emittente_fiscale_id is None` su entity, oppure `sorgente_codice` non trovato/non `attivo` |

## Riferimenti

- File helper:
  - `backend/apps/documenti/api/contesto_helpers.py`
  - `backend/apps/documenti/api/multipart_helpers.py`
- Endpoint che li usano:
  - [api_offerte](../../vendite/manual/api_offerte.md) — sezione "Cambio stato BOZZA -> EMESSA"
  - [api_preventivi](../../vendite/manual/api_preventivi.md) — §5b "Emissione" + §18 "Documenti preventivo"
  - [api_contratti](../../vendite/manual/api_contratti.md) — "Attivazione DRAFT→ATTIVO" + "Documenti contratto"
- Service consumer: `apps.documenti.services.document_generation_service.DocumentGenerationService.genera_documento`
- Pattern documentale parametrico: [api_documenti_templates](api_documenti_templates.md)
