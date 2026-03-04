# API flusso_prerequisiti (Django)

## Scopo

Esporre via HTTP i prerequisiti di un template flusso con flag `soddisfatto` per preview/UI.

## Contesto

Endpoint di sola lettura con ownership check. Se il flusso ha un `template_flusso_id`, delega a `pratiche_service.verifica_prerequisiti` che invoca la funzione DB `pratiche.fn_check_prerequisiti_flusso`. Se il flusso non ha template, restituisce lista vuota.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/<flusso_id>/prerequisiti/`
- Header sicurezza: `Authorization: Bearer <access_token>`

## Output

### 200:
```json
{
  "data": {
    "results": [
      {
        "prerequisito_id": 1,
        "codice": "DOC_IDENTITA",
        "descrizione": "Documento di identita' valido",
        "soddisfatto": true
      },
      {
        "prerequisito_id": 2,
        "codice": "FLUSSO_PREV_COMPLETATO",
        "descrizione": "Flusso precedente completato",
        "soddisfatto": false
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
- Se `template_flusso_id` e' `null` → risultato `[]` (nessun prerequisito).
- La verifica e' pura lettura (funzione DB `STABLE`): non modifica stato.
- Destinato alla UI per mostrare lo stato dei prerequisiti prima dell'avvio del flusso.

## Dipendenze DB

- `pratiche.flussi` (lettura template_flusso_id)
- `pratiche.fn_check_prerequisiti_flusso(pratica_id, template_flusso_id)` (funzione STABLE)
- `pratiche.template_flussi_prerequisiti` (configurazione prerequisiti)

## Note di migrazione

- La logica di verifica e' interamente in DB (`fn_check_prerequisiti_flusso`); il backend fa solo dispatch.
