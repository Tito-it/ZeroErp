# API flusso_canali (Django)

## Scopo

Esporre via HTTP i canali abilitati per il template del flusso.

## Contesto

Endpoint di sola lettura con ownership check. Restituisce i canali configurati in `pratiche.template_flussi_canali` con JOIN su `config.canali_pratiche`. Se il flusso non ha template, restituisce lista vuota.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/<flusso_id>/canali/`
- Header sicurezza: `Authorization: Bearer <access_token>`

## Output

### 200:
```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "codice": "WEB_CLIENTI",
        "descrizione": "Portale web clienti",
        "codice_interno": "WEB_CLIENTI"
      },
      {
        "id": 2,
        "codice": "APP_TECNICA",
        "descrizione": "App tecnici",
        "codice_interno": "APP_TECNICA"
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
- Se `template_flusso_id` e' `null` → risultato `[]`.
- Solo canali con `attivo = true` su entrambe le tabelle (template_flussi_canali e canali_pratiche).
- Ordinamento per `codice`.

## Dipendenze DB

- `pratiche.flussi` (lettura template_flusso_id)
- `pratiche.template_flussi_canali` (mapping template → canali)
- `config.canali_pratiche` (tabella canali, JOIN per decodifica)

## Note di migrazione

- Query raw con JOIN nel repository (`PraticheRepository.get_canali_flusso`).
