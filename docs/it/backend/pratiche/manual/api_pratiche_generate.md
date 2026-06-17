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
        "soggetto_id": null,
        "soggetto_ruolo_id": null,
        "istanza_utility_id": null,
        "stato_id": 1,
        "priorita_id": 2,
        "flusso_origine_id": 5,
        "codice": "PRA-0000200",
        "descrizione": "Pratica generata",
        "meta": {},
        "data_insert": "2026-03-04T11:00:00+00:00",
        "user_insert": "zeroerp",
        "tipo_prestazione_codice": "VERIFICA",
        "tipo_prestazione_descrizione": "Verifica impianto",
        "stato_codice_interno": "APERTA",
        "stato_descrizione": "Aperta",
        "priorita_codice_interno": "NORMALE",
        "priorita_descrizione": "Normale",
        "soggetto_display": null,
        "risorsa_umana_display": null,
        "unita_organizzativa_descrizione": null
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
- `pratiche.pratiche` + JOIN display (tipi_prestazione, stati, priorita', soggetti, risorse_umane, UO)

## Note di migrazione

- v2 (28 marzo 2026): risposta include display fields completi via JOIN.
- Riusa `PraticheRepository._PRATICA_SELECT` + `_dicts_from_cursor` per coerenza di mapping.
