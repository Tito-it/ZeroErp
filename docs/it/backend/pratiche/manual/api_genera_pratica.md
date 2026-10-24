# API genera_pratica (Django)

## Scopo

Esporre via HTTP la generazione manuale di una nuova pratica da un flusso applicando una regola di generazione.

## Contesto

Endpoint di scrittura con ownership check. Delega a `generazione_service.genera_pratica_manuale` che verifica il flusso e invoca la funzione DB `pratiche.fn_genera_pratica_da_flusso`. La funzione DB crea la nuova pratica con `flusso_origine_id` impostato, applicando la configurazione della regola (tipo prestazione, template flusso destinazione).

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/<flusso_id>/genera/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `regola_id` (int, **obbligatorio**) — ID della regola di generazione da applicare (> 0)

## Output

### 200:
```json
{
  "data": {
    "pratica_id": 200,
    "status": "ok"
  }
}
```

- `400`: ownership mismatch (`E_FLUSSO_OWNERSHIP`), `flusso_id` non valido o `regola_id` assente dal corpo o <= 0 (`E_INVALID_ID`, campo `regola_id`)
- `401`: JWT mancante o non valido
- `404`: flusso non trovato (`E_FLUSSO_NOT_FOUND`)

## Regole

- Ownership check prima della generazione.
- `flusso_id` e `regola_id` devono essere > 0.
- Verifica esistenza flusso prima di generare.
- Wrappato in `@transaction.atomic()`.
- La funzione DB gestisce: creazione pratica, impostazione `flusso_origine_id`, applicazione configurazione regola, registrazione nel giornale.
- Permission: `genera_pratica_manuale` (area `pratiche`).

## Dipendenze DB

- `pratiche.flussi` (verifica esistenza)
- `pratiche.fn_genera_pratica_da_flusso(flusso_id, regola_id)` (generazione effettiva)
- `pratiche.regole_generazione` (configurazione regola usata dalla funzione DB)

## Note di migrazione

- La generazione e' interamente in DB; il backend fa validazione e dispatch.
- Le regole `auto = true` non passano da questo endpoint: vengono eseguite dal trigger DB al completamento flusso.
