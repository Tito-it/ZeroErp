# API flusso_stato (Django)

## Scopo

Esporre via HTTP le transizioni di stato di un flusso: avvio (IN_CORSO), completamento (COMPLETATO con esito) e transizioni generiche (SOSPESO, ANNULLATO, ecc.).

## Contesto

Endpoint di scrittura con ownership check. Smista la richiesta in base al valore di `nuovo_stato`:

- `IN_CORSO` → `pratiche_service.avvia_flusso`
- `COMPLETATO` → `pratiche_service.completa_flusso` (con esito obbligatorio)
- Altro → `pratiche_service.cambia_stato_flusso` (transizione generica)

La generazione automatica cross-pratica al completamento e' gestita dal trigger DB `trgfn_flussi_generazione`.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/<flusso_id>/stato/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `nuovo_stato` (string, **obbligatorio**) — codice_interno dello stato (es. `IN_CORSO`, `COMPLETATO`, `SOSPESO`, `ANNULLATO`)
  - `esito` (string, obbligatorio se `nuovo_stato = COMPLETATO`) — esito del flusso: `POSITIVO`, `NEGATIVO`, `PARZIALE`, `NON_APPLICABILE`
  - `note_esito` (string, opzionale) — note sull'esito

## Output

### 200:
```json
{ "data": { "status": "ok" } }
```

- `400`: ownership mismatch (`E_FLUSSO_OWNERSHIP`), esito non valido (`E_FLUSSO_VALIDATION`), stato vuoto (`E_FLUSSO_VALIDATION`)
- `401`: JWT mancante o non valido
- `404`: flusso non trovato (`E_FLUSSO_NOT_FOUND`)
- `500`: stato non trovato in config (`E_CONFIG_MANCANTE`)

## Regole

- Ownership check prima di qualsiasi operazione.
- Se `nuovo_stato = COMPLETATO`, `esito` e' obbligatorio e deve essere uno tra: `POSITIVO`, `NEGATIVO`, `PARZIALE`, `NON_APPLICABILE`.
- Se `nuovo_stato = IN_CORSO`, il servizio transiziona direttamente senza parametri aggiuntivi.
- Per qualsiasi altro stato, il servizio delega a `cambia_stato_flusso` con validazione stato non vuoto.
- Tutte le transizioni sono wrappate in `@transaction.atomic()`.
- Al completamento con esito, il trigger DB `trgfn_flussi_generazione` verifica le regole di generazione automatica (`auto = true`) e crea nuove pratiche se applicabile.
- Permission: `cambia_stato_flusso` (area `pratiche`).

## Dipendenze DB

- `pratiche.flussi` (UPDATE stato_id, esito, note_esito)
- `config.stati_flussi_pratiche` (risoluzione codice_interno → id)
- `pratiche.trgfn_flussi_generazione` (trigger su UPDATE per generazione automatica)

## Note di migrazione

- La risoluzione stato avviene esplicitamente prima dell'UPDATE per evitare SET NULL su colonna NOT NULL.
- La generazione automatica cross-pratica e' completamente lato DB; il backend non ha logica di generazione automatica.
