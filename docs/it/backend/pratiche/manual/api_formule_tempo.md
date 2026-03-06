# API formule_tempo (Django)

## Scopo

Esporre via HTTP le formule tempo attive per un tipo prestazione.

## Contesto

Endpoint di sola lettura che delega a `pratiche_service.get_formule_tempo`. Restituisce le formule configurate nella tabella `pratiche.formule_tempo` filtrate per tipo prestazione. Ogni formula definisce il tempo massimo atteso tra il completamento di due flussi (da/a) con soglie warning e critico per i semafori UI.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/formule-tempo/?tipo_prestazione_id=<id>`
- Header: `Authorization: Bearer <access_token>`
- Parametri query:
  - `tipo_prestazione_id` (integer, **obbligatorio**) — ID del tipo prestazione

## Output

### 200:
```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "tipo_prestazione_id": 26,
        "template_flusso_da_id": 5,
        "template_flusso_a_id": 10,
        "giorni_esecuzione": 15,
        "giorni_warning": 12,
        "giorni_critico": 14,
        "attivo": true,
        "descrizione": "Tempo presa carico - sopralluogo",
        "meta": {}
      }
    ]
  }
}
```

- `400`: `tipo_prestazione_id` mancante o non valido (`E_INVALID_ID`)
- `401`: JWT mancante o non valido

## Regole

- Sola lettura, nessun side-effect.
- Restituisce solo formule con `attivo = true`.
- `tipo_prestazione_id` deve essere > 0.
- `giorni_warning > giorni_critico` (warning scatta prima del critico).
- `giorni_warning < giorni_esecuzione` (warning dentro il tempo massimo).
- Permission: area `pratiche` (lettura implicita).
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.formule_tempo` (SELECT con filtro tipo_prestazione_id e attivo = true)

## Note di migrazione

- Le formule tempo sono configurazione statica: inserite via seed SQL o admin.
- La UI usa queste formule per mostrare i semafori temporali sulle pratiche.
