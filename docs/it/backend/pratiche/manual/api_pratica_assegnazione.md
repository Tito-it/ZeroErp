# API pratica_assegnazione (Django)

## Scopo

Esporre via HTTP l'assegnazione di una pratica a risorsa umana e/o unita' organizzativa.

## Contesto

Endpoint di scrittura che delega a `pratiche_service.assegna_pratica`. Aggiorna i campi `risorsa_umana_id` e/o `unita_organizzativa_id` sulla pratica. Se nessun campo viene fornito, non viene eseguito alcun update.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/assegnazione/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `risorsa_umana_id` (int, opzionale) — ID risorsa umana
  - `unita_organizzativa_id` (int, opzionale) — ID unita' organizzativa

## Output

### 200:
```json
{ "data": { "status": "ok" } }
```

- `400`: `pratica_id` non valido (`E_INVALID_ID`)
- `401`: JWT mancante o non valido

## Regole

- `pratica_id` deve essere > 0.
- Se nessun campo di assegnazione viene fornito, il servizio non esegue update (noop).
- Aggiorna solo i campi presenti nel payload **e non `null`** (update parziale): un
  `null` esplicito è ignorato, non azzera l'assegnazione.
- Permission: `assegna_pratica` (area `pratiche`).
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.pratiche` (UPDATE campi assegnazione)

## Note di migrazione

- Usa `PraticheRepository.update_pratica` con dict dinamico dei soli campi forniti.
