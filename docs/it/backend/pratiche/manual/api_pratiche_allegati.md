# API allegati pratiche (Django)

## Scopo

Esporre via HTTP la gestione allegati associati a una pratica. V1: solo metadati (nome_file, tipo, dimensione) — upload file posticipato. Gli allegati sono immutabili: solo creazione e eliminazione, nessun aggiornamento.

## Contesto

La tabella `pratiche.allegati_pratiche` supporta gli allegati con versionamento via `allegato_padre_id` (self-reference per nuove versioni). Il trigger `trgfn_allegati_pratiche_giornale` registra automaticamente ogni inserimento nel giornale. La tabella non ha `data_update`/`user_update` — gli allegati sono immutabili by design.

## Input

### GET — Lista allegati pratica

- Metodo: `GET`
- Path: `/api/v1/pratiche/<pratica_id>/allegati/`
- Header: `Authorization: Bearer <access_token>`

### POST — Crea record allegato (metadati)

- Metodo: `POST`
- Path: `/api/v1/pratiche/<pratica_id>/allegati/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `tipo_allegato_codice` (string, **obbligatorio**) — codice_interno tipo allegato (es. `DOCUMENTO`, `IMMAGINE`)
  - `nome_file` (string, **obbligatorio**) — nome file originale
  - `percorso` (string, opzionale) — path storage o key (da usare con upload futuro)
  - `mime_type` (string, opzionale) — content-type (es. `application/pdf`)
  - `dimensione` (int, opzionale) — dimensione file in byte

### DELETE — Elimina allegato

- Metodo: `DELETE`
- Path: `/api/v1/pratiche/<pratica_id>/allegati/<allegato_id>/`

> **NOTA**: nessun endpoint PATCH — gli allegati sono immutabili. Per una nuova versione, creare un nuovo allegato con `allegato_padre_id` che punta al precedente.

## Output

### GET 200

```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "pratica_id": 10,
        "tipo_allegato_id": 1,
        "tipo_allegato_codice": "DOCUMENTO",
        "tipo_allegato_descrizione": "Documento",
        "nome_file": "contratto.pdf",
        "percorso": null,
        "mime_type": "application/pdf",
        "dimensione": 12345,
        "allegato_padre_id": null,
        "data_insert": "2026-03-29T10:00:00+00:00",
        "user_insert": "operatore1"
      }
    ]
  }
}
```

### POST 200

```json
{ "data": { "allegato_id": 5, "status": "ok" } }
```

### DELETE 200

```json
{ "data": { "deleted": true } }
```

### Errori

- `400`: validazione (`E_PRATICA_VALIDATION`, col campo: nome_file vuoto, `tipo_allegato_codice` assente o non trovato)
- `401`: JWT mancante
- `404`: allegato non trovato o non appartiene alla pratica

## Regole

- `tipo_allegato_codice` risolto a ID via lookup su `config.tipi_allegato` (codice_interno). Se non trovato o non attivo: `400 E_PRATICA_VALIDATION` sul campo `tipo_allegato_codice` (fino al 2026-10-20 era un `500 E_CONFIG_MANCANTE`).
- Ownership check: DELETE verifica che l'allegato appartenga alla pratica.
- Il trigger DB registra automaticamente `ALLEGATO_AGGIUNTO` nel giornale all'INSERT.
- Ordinamento GET: `data_insert DESC, id DESC`.
- Tipi allegato seed: DOCUMENTO, IMMAGINE, MODULO, CONTRATTO, FATTURA, VERBALE, CERTIFICATO, ALTRO.

## Dipendenze DB

- `pratiche.allegati_pratiche` (tabella dati)
- `config.tipi_allegato` (JOIN display, lookup codice_interno)
- `pratiche.giornale` (alimentato da trigger)

## Note di migrazione

- V1 (marzo 2026): solo metadati, upload file non implementato.
- Il campo `percorso` sara' usato per lo storage path quando l'upload sara' implementato.
- Il campo `allegato_padre_id` consente il versionamento: un nuovo allegato "sostituisce" il precedente mantenendo lo storico.
