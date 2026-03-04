# API pratiche_generate (Django)

## Scopo

Esporre via HTTP le pratiche generate da un flusso.

## Contesto

Endpoint di sola lettura con ownership check. Delega a `generazione_service.get_pratiche_generate` che interroga `pratiche.pratiche` filtrando per `flusso_origine_id`. Utile per la UI per visualizzare l'albero di pratiche generate da un flusso completato.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/<flusso_id>/pratiche-generate/`
- Header sicurezza: `Authorization: Bearer <access_token>`

## Output

### 200:
```json
{
  "data": {
    "results": [
      {
        "id": 200,
        "emittente_fiscale_id": 10,
        "tipo_prestazione_id": 7,
        "stato_id": 1,
        "flusso_origine_id": 5,
        "codice": "P-200",
        "descrizione": "Pratica generata",
        "meta": {},
        "data_insert": "2026-03-04T11:00:00+00:00",
        "user_insert": "zeroerp"
      }
    ]
  }
}
```

- `400`: ownership mismatch (`E_FLUSSO_OWNERSHIP`)
- `401`: JWT mancante o non valido
- `404`: flusso non trovato (`E_FLUSSO_NOT_FOUND`)

## Regole

- Ownership check prima della lettura.
- `flusso_id` deve essere > 0.
- Ordinamento per `id ASC`.
- Include sia pratiche generate automaticamente (trigger) che manualmente (endpoint genera).

## Dipendenze DB

- `pratiche.flussi` (ownership check)
- `pratiche.pratiche` (filtro `flusso_origine_id = flusso_id`)

## Note di migrazione

- Query raw nel repository (`GenerazioneRepository.get_pratiche_generate_da_flusso`).
- Riusa `PraticheRepository._map_pratica_row` per coerenza di mapping.
