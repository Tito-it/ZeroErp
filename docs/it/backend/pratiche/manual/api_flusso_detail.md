# API flusso_detail (Django)

## Scopo

Esporre via HTTP il dettaglio di un flusso con verifica ownership pratica.

## Contesto

Endpoint di sola lettura su `pratiche.flussi`. Utilizza il pattern `_get_flusso_verificato` che recupera il flusso dal repository e verifica che `flusso.pratica_id == pratica_id` dall'URL. Questo impedisce accesso a flussi di altre pratiche tramite manipolazione URL.

## Input

- Metodo: `GET`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/<flusso_id>/`
- Header sicurezza: `Authorization: Bearer <access_token>`

## Output

### 200:
```json
{
  "data": {
    "id": 5,
    "pratica_id": 1,
    "template_flusso_id": 10,
    "stato_id": 2,
    "flusso_padre_id": null,
    "risorsa_umana_id": 3,
    "unita_organizzativa_id": null,
    "sequenza": 1,
    "esito": "POSITIVO",
    "note_esito": "Tutto ok",
    "data_scadenza": null,
    "meta": {},
    "template_modalita_esito": "CONTESTUALE",
    "template_esito_default": "POSITIVO",
    "data_insert": "2026-03-04T10:00:00+00:00",
    "user_insert": "zeroerp"
  }
}
```

> Oltre ai campi tabella, la proiezione include display fields dal template e dalla
> pratica (`template_flusso_codice`/`_descrizione`, `stato_codice_interno`,
> `template_azione_ui_key`, `pratica_*`). Dal 2026-06-17 espone anche
> `template_modalita_esito` e `template_esito_default` (config esito dello step,
> consumati dal `FlussoDrawer` FE — vedi [api_flusso_stato](api_flusso_stato.md)).

- `400`: flusso non appartiene alla pratica (`E_FLUSSO_OWNERSHIP`)
- `401`: JWT mancante o non valido
- `404`: flusso non trovato (`E_FLUSSO_NOT_FOUND`)

## Regole

- **Ownership check**: il flusso deve appartenere alla pratica indicata nell'URL; in caso contrario → `E_FLUSSO_OWNERSHIP` (400).
- Tutti gli endpoint nested su flussi usano la stessa verifica ownership tramite `_get_flusso_verificato`.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.flussi` (tabella principale)

## Note di migrazione

- L'ownership check e' applicativo (Python), non DB. Il DB non ha vincoli che impediscano la lettura di flussi di altre pratiche.
