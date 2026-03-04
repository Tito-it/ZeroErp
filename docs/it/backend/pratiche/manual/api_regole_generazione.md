# API regole_generazione (Django)

## Scopo

Esporre via HTTP le regole di generazione cross-pratica applicabili a un flusso.

## Contesto

Endpoint di sola lettura con ownership check. Delega a `generazione_service.get_regole_applicabili` che recupera il template del flusso e interroga `pratiche.regole_generazione` per le regole attive. Destinato alla UI per mostrare le possibili generazioni manuali (`auto = false`).

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/<flusso_id>/regole-generazione/`
- Header sicurezza: `Authorization: Bearer <access_token>`

## Output

### 200:
```json
{
  "data": {
    "results": [
      {
        "id": 1,
        "template_flusso_origine_id": 10,
        "tipo_prestazione_dest_id": 5,
        "template_flusso_dest_id": null,
        "esito_richiesto": "POSITIVO",
        "auto": false,
        "attivo": true,
        "descrizione": "Genera pratica assistenza tecnica",
        "meta": {}
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
- Solo regole con `attivo = true`.
- Se il flusso non ha `template_flusso_id` → lista vuota.
- Le regole `auto = true` vengono eseguite automaticamente dal trigger DB; qui sono visibili per informazione.
- Le regole `auto = false` sono generabili manualmente dall'endpoint `genera/`.

## Dipendenze DB

- `pratiche.flussi` (lettura template_flusso_id)
- `pratiche.regole_generazione` (regole configurate per template)

## Note di migrazione

- Query raw nel repository (`GenerazioneRepository.list_regole_generazione`).
