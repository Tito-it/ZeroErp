# API pratica_sospensioni (Django)

## Scopo

Esporre via HTTP la lista delle sospensioni (attive e chiuse) di una pratica.

## Contesto

Endpoint di sola lettura che delega a `pratiche_service.get_sospensioni`. Restituisce tutte le sospensioni della pratica ordinate per data_inizio decrescente. Include sia sospensioni a livello pratica (flusso_id IS NULL) sia a livello flusso.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/sospensioni/`
- Header: `Authorization: Bearer <access_token>`
- Nessun parametro query.

## Output

### 200:
```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "pratica_id": 1,
        "flusso_id": null,
        "data_inizio": "2026-03-06T10:00:00+00:00",
        "data_fine": null,
        "data_riattivazione_prevista": null,
        "motivo": "Attesa documenti",
        "data_insert": "2026-03-06T10:00:00+00:00",
        "user_insert": "tid",
        "data_update": null,
        "user_update": null
      }
    ]
  }
}
```

- `401`: JWT mancante o non valido

## Regole

- Sola lettura, nessun side-effect.
- Restituisce tutte le sospensioni (attive e chiuse) ordinate per `data_inizio DESC, id DESC`.
- Le sospensioni con `flusso_id != null` sono relative a un singolo flusso.
- Le sospensioni con `data_fine IS NULL` sono ancora attive.
- Permission: area `pratiche` (lettura implicita).
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.sospensioni` (SELECT con filtro pratica_id)

## Note di migrazione

- Nessuna paginazione al momento; la cardinalita' e' bassa per design (poche sospensioni per pratica).
