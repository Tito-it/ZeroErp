# API flusso_assegnazione (Django)

## Scopo

Esporre via HTTP l'assegnazione di un **singolo flusso** (step) a un operatore e/o a
un reparto. Simmetrico ad [api_pratica_assegnazione](api_pratica_assegnazione.md), ma a
livello di step invece che di testata pratica.

## Contesto

Endpoint di scrittura che, dopo la verifica ownership flusso↔pratica
(`_get_flusso_verificato` → `E_FLUSSO_OWNERSHIP`), delega a
`pratiche_service.assegna_flusso`. Aggiorna `risorsa_umana_id` (operatore) e/o
`unita_organizzativa_id` (reparto) su `pratiche.flussi`. L'UPDATE di questi campi attiva
il trigger giornale `trg_flussi_z90_giornale_assegnazione_upd`
(evento `FLUSSO_ASSEGNAZIONE_CAMBIATA`, origine `UTENTE`).

Routing/assegnazione (policy reparto-first): un flusso può essere **instradato a un
reparto** (coda del reparto) e/o assegnato a un **operatore specifico di quel reparto**. La
selezione dell'operatore lato FE è filtrata sul reparto via
[api_operatori_reparto](api_operatori_reparto.md).

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/<pratica_id>/flussi/<flusso_id>/assegnazione/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body:
  - `risorsa_umana_id` (int|null, opzionale) — ID operatore; `null` = de-assegna
  - `unita_organizzativa_id` (int|null, opzionale) — ID reparto; `null` = de-assegna

### Semantica chiave-assente vs null

La **presenza della chiave** nel payload governa l'aggiornamento (flag `set_*` lato
service):

- chiave **assente** → il campo **non** viene toccato;
- chiave presente con valore int → imposta l'assegnazione;
- chiave presente con valore **`null`** → **de-assegna** (azzera il campo).

## Output

### 200:
```json
{ "data": { "status": "ok" } }
```

### Errori

- `400`: `flusso_id` non valido (`E_INVALID_ID`)
- `400`: il flusso non appartiene alla pratica dell'URL (`E_FLUSSO_OWNERSHIP`)
- `401`: JWT mancante o non valido
- `404`: flusso non trovato (`E_FLUSSO_NOT_FOUND`)

## Regole

- Ownership: il flusso dell'URL deve appartenere alla pratica dell'URL.
- Se nessuna chiave di assegnazione è presente nel payload → noop (nessun update).
- Aggiorna solo i campi le cui chiavi sono presenti (update parziale, de-assegna con `null`).
- La coerenza "operatore appartiene al reparto" è un vincolo **UX** (picker filtrato), non
  un guard DB: la validazione FK (operatore/reparto esistenti) resta a carico del DB.
- Permission: `assegna_pratica` (area `pratiche`) — riusa la stessa azione di processo
  dell'assegnazione di testata.
- Endpoint v1 richiede JWT.

## Dipendenze DB

- `pratiche.flussi` (UPDATE `risorsa_umana_id`/`unita_organizzativa_id`)
- `pratiche.trgfn_flussi_giornale_assegnazione` + trigger
  `trg_flussi_z90_giornale_assegnazione_upd` (giornale `FLUSSO_ASSEGNAZIONE_CAMBIATA`)

## Note di migrazione

- Service `assegna_flusso` + `PraticheRepository.update_flusso` (whitelist
  `risorsa_umana_id`/`unita_organizzativa_id` + guard not-found `E_FLUSSO_NOT_FOUND`).
- Trigger giornale: migration `20260618-08`; azione `FLUSSO_ASSEGNAZIONE_CAMBIATA`
  aggiunta al CHECK `chk_giornale_azione` in `20260618-07`.
- L'eligibilità di **presa in carico** (chi può prendere un flusso instradato) segue la
  policy reparto-first: vedi [api_prendi_in_carico](api_prendi_in_carico.md).
