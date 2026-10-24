# API pratica_giornale (Django)

## Scopo

Esporre via HTTP il giornale di bordo (audit trail) di una pratica con paginazione.

## Contesto

Endpoint di sola lettura su `pratiche.giornale`. Il giornale e' popolato automaticamente dai trigger DB ad ogni evento significativo (creazione pratica, cambio stato, creazione/completamento flusso). Ogni riga include `tx_id` per correlazione con la transazione DB di origine.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/giornale/`
- Header sicurezza: `Authorization: Bearer <access_token>`
- Query param:
  - `limit` (int, opzionale) — righe per pagina, default `100`, max `200`
  - `offset` (int, opzionale) — offset paginazione, default `0`

## Output

### 200:
```json
{
  "data": {
    "count": 3,
    "results": [
      {
        "id": 10,
        "pratica_id": 1,
        "flusso_id": 5,
        "azione": "FLUSSO_COMPLETATO",
        "origine": "SISTEMA",
        "dettaglio": { "esito": "POSITIVO" },
        "tx_id": "abc-123-def",
        "data_insert": "2026-03-04T10:30:00+00:00",
        "user_insert": "zeroerp"
      }
    ]
  }
}
```

- `401`: JWT mancante o non valido

## Regole

- Ordinamento: `data_insert DESC, id DESC` (piu' recente in cima).
- Finestra letta da `pagina_da_query`: `limit` fuori da 1..200 (`limit_fuori_limiti_1_200`),
  `offset` negativo (`offset_negativo`) o valori non interi → 400 `E_VALIDATION_INPUT`
  (dal 2026-10-21; prima si riportavano nei limiti in silenzio). `page`/`page_size` → 400.
- Il giornale e' append-only: nessuna operazione di modifica/cancellazione.
- `flusso_id` e' nullable: eventi a livello di pratica hanno `flusso_id = null`.
- `tx_id` correla l'evento alla transazione DB che lo ha generato.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.giornale` (tabella principale, append-only)

## Note di migrazione

- Due query per request: `COUNT(*)` + dati con `LIMIT/OFFSET`.
- Il giornale e' popolato esclusivamente dai trigger DB; nessun INSERT applicativo.
