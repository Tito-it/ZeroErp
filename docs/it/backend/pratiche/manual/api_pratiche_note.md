# API note pratiche (Django)

## Scopo

Esporre via HTTP il CRUD note associate a una pratica. Le note sono annotazioni testuali con tipo (GENERALE, INTERNA, CLIENTE, TECNICA, LEGALE) registrate nel giornale automaticamente dal trigger DB.

## Contesto

Le tabelle `pratiche.note_pratiche` e `config.tipi_nota` supportano le note. Il trigger `trgfn_note_pratiche_giornale` registra automaticamente ogni inserimento nel giornale. Le note sono mutabili (update consentito), diversamente dagli allegati.

## Input

### GET — Lista note pratica

- Metodo: `GET`
- Path: `/api/v1/pratiche/<pratica_id>/note/`
- Header: `Authorization: Bearer <access_token>`

### POST — Crea nota

- Metodo: `POST`
- Path: `/api/v1/pratiche/<pratica_id>/note/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `tipo_nota_codice` (string, **obbligatorio**) — codice_interno tipo nota (es. `GENERALE`, `INTERNA`)
  - `contenuto` (string, **obbligatorio**) — testo della nota

### PATCH — Aggiorna nota

- Metodo: `PATCH`
- Path: `/api/v1/pratiche/<pratica_id>/note/<nota_id>/`
- Body:
  - `contenuto` (string, **obbligatorio**) — nuovo testo

### DELETE — Elimina nota

- Metodo: `DELETE`
- Path: `/api/v1/pratiche/<pratica_id>/note/<nota_id>/`

## Output

### GET 200

```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "pratica_id": 10,
        "tipo_nota_id": 1,
        "tipo_nota_codice": "GENERALE",
        "tipo_nota_descrizione": "Generale",
        "contenuto": "Nota di esempio",
        "data_insert": "2026-03-29T10:00:00+00:00",
        "user_insert": "operatore1",
        "data_update": "2026-03-29T10:00:00+00:00",
        "user_update": "operatore1"
      }
    ]
  }
}
```

### POST 200

```json
{ "data": { "nota_id": 5, "status": "ok" } }
```

### PATCH 200

```json
{ "data": { "updated": true } }
```

### DELETE 200

```json
{ "data": { "deleted": true } }
```

### Errori

- `400`: validazione (`E_PRATICA_VALIDATION`, col campo: contenuto vuoto, `tipo_nota_codice` assente o non trovato)
- `401`: JWT mancante
- `404`: nota non trovata o non appartiene alla pratica

## Regole

- `tipo_nota_codice` risolto a ID via lookup su `config.tipi_nota` (codice_interno). Se non trovato o non attivo: `400 E_PRATICA_VALIDATION` sul campo `tipo_nota_codice` (fino al 2026-10-20 era un `500 E_CONFIG_MANCANTE`).
- Ownership check: PATCH e DELETE verificano che la nota appartenga alla pratica.
- Il trigger DB registra automaticamente `NOTA_AGGIUNTA` nel giornale all'INSERT.
- Ordinamento GET: `data_insert DESC, id DESC`.

## Dipendenze DB

- `pratiche.note_pratiche` (tabella dati)
- `config.tipi_nota` (JOIN display, lookup codice_interno)
- `pratiche.giornale` (alimentato da trigger)
