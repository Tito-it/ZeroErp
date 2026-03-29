# API prendi_in_carico (Django)

## Scopo

Esporre via HTTP la presa in carico di un flusso DA_ESEGUIRE da parte dell'operatore autenticato.

## Contesto

Endpoint di scrittura che delega alla funzione DB `pratiche.fn_prendi_in_carico_flusso`. La funzione DB gestisce atomicamente: lock della riga (FOR UPDATE), verifica stato, verifica competenza, assegnazione. Protegge da race condition (due operatori che tentano la presa in carico contemporanea).

L'operatore e' determinato automaticamente dal JWT autenticato.

## Input

- Metodo: `POST`
- Path canonico: `/api/v1/pratiche/flussi/<flusso_id>/prendi-in-carico/`
- Header: `Content-Type: application/json`, `Authorization: Bearer <access_token>`
- Body: `{}` (vuoto — l'operatore e' derivato dal JWT)

## Output

### 200 (assegnato):
```json
{ "data": { "assegnato": true, "status": "ok" } }
```

### 200 (gia' assegnato allo stesso operatore — noop):
```json
{ "data": { "assegnato": false, "status": "ok" } }
```

### Errori

- `400`: Operatore non associato a una risorsa umana (`E_PRATICA_VALIDATION`)
- `400`: Flusso non in stato DA_ESEGUIRE (`FLUSSI_PRESA_CARICO_STATO_ERRATO`)
- `400`: Flusso gia' assegnato ad altro operatore (`FLUSSI_GIA_ASSEGNATO`)
- `400`: Operatore non abilitato per il tipo di flusso (`FLUSSI_COMPETENZA_MANCANTE`)
- `400`: Flusso non trovato (`E_VALORE_MANCANTE`)
- `401`: JWT mancante o non valido

## Regole

- Il flusso deve essere in stato DA_ESEGUIRE.
- Il flusso non deve essere gia' assegnato ad altro operatore.
- L'operatore deve avere competenza attiva per il `template_flusso_id` del flusso (tabella `pratiche.competenze_flussi`).
- Se il flusso non ha `template_flusso_id` (flusso manuale), la verifica competenza e' saltata.
- Se il flusso e' gia' assegnato allo stesso operatore, ritorna `assegnato: false` (noop).
- La funzione DB usa `SELECT ... FOR UPDATE` per evitare race condition.

## Dipendenze DB

- `pratiche.fn_prendi_in_carico_flusso(flusso_id, risorsa_umana_id)` — funzione PL/pgSQL con FOR UPDATE
- `pratiche.competenze_flussi` — verifica competenza operatore
- `pratiche.flussi` — UPDATE risorsa_umana_id
- `config.stati_flussi_pratiche` — risoluzione stato DA_ESEGUIRE
- `anagrafiche.risorse_umane_auth_user` — bridge utente → risorsa umana

## Note di migrazione

- Funzione DB creata in migration `20260329-15` e fix race condition in `20260329-16`.
- Messaggi errore in `config.messaggi_errore.csv` (id 320-322).
