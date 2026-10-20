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
    "risorsa_umana_display": "Rossi Mario",
    "unita_organizzativa_descrizione": null,
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
> Dal 2026-06-18 espone anche `risorsa_umana_display` (ragione sociale dell'operatore
> assegnato) e `unita_organizzativa_descrizione` (reparto), via JOIN — vedi
> [api_flusso_assegnazione](api_flusso_assegnazione.md).

- `400`: flusso non appartiene alla pratica (`E_FLUSSO_OWNERSHIP`)
- `401`: JWT mancante o non valido
- `404`: flusso non trovato (`E_FLUSSO_NOT_FOUND`)

## Regole

- **Ownership check**: il flusso deve appartenere alla pratica indicata nell'URL; in caso contrario → `E_FLUSSO_OWNERSHIP` (400).
- Tutti gli endpoint nested su flussi usano la stessa verifica ownership tramite `_get_flusso_verificato`.
- Endpoint v1 richiede JWT.

## `GET /api/v1/pratiche/flussi/<flusso_id>/pratica/` — la pratica di un flusso

L'unica rotta dei flussi **non annidata** sotto la pratica: serve a chi conosce solo
l'id del flusso (per esempio il bersaglio di un errore `E_FLUSSI_*`) per sapere dove
aprirlo. Risponde l'id, non il flusso: il dettaglio resta la rotta sopra, con la sua
verifica di appartenenza.

- Risposta 200: `{"data": {"pratica_id": 1}}`
- `400`: `flusso_id` <= 0 (`E_INVALID_ID`)
- `404`: flusso inesistente o non visibile (`E_FLUSSO_NOT_FOUND`)
- Permesso: area `pratiche` + `view` su `pratiche.pratica`.

## Dipendenze DB

- `pratiche.flussi` (tabella principale)

## Note di migrazione

- L'ownership check e' applicativo (Python), non DB. Il DB non ha vincoli che impediscano la lettura di flussi di altre pratiche.
