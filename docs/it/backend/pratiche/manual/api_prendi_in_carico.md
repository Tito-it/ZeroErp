# API prendi_in_carico (Django)

## Scopo

Esporre via HTTP la presa in carico di un flusso DA_ESEGUIRE da parte dell'operatore autenticato.

## Contesto

Endpoint di scrittura che delega alla funzione DB `pratiche.fn_prendi_in_carico_flusso`. La funzione DB gestisce atomicamente: lock della riga (FOR UPDATE), verifica stato, verifica **eligibilità** (policy reparto-first), assegnazione. Protegge da race condition (due operatori che tentano la presa in carico contemporanea).

L'operatore e' determinato automaticamente dal JWT autenticato.

### Policy di eligibilità (reparto-first, dal 2026-06-18)

La competenza **non è più sempre obbligatoria**. Per un flusso `DA_ESEGUIRE` non assegnato,
l'operatore `O` è eligibile secondo 4 casi (sia **skill-lock** = esiste almeno una competenza
**attiva** in `pratiche.competenze_flussi` per il `template_flusso_id`):

| Caso | Flusso | Eligibile se |
|---|---|---|
| A — reparto + skill | reparto valorizzato, skill-lock presente | competenza attiva (altrimenti `FLUSSI_COMPETENZA_MANCANTE`) |
| B — reparto, no skill | reparto valorizzato, skill-lock assente | appartiene al reparto **anagrafico** (`risorse_umane.unita_organizzativa_id`); altrimenti `FLUSSI_PRESA_NON_ELIGIBILE` |
| C — niente configurato | reparto NULL, skill-lock assente | **presa libera** (chiunque) |
| D — skill senza reparto | reparto NULL, skill-lock presente | competenza attiva (altrimenti `FLUSSI_COMPETENZA_MANCANTE`) |

La competenza è quindi un **lucchetto-skill opzionale**: vale solo quando configurata per
quel template; altrimenti decide l'appartenenza al reparto (o la presa libera).

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
- `409`: Operatore non abilitato per il tipo di flusso — casi A/D (`FLUSSI_COMPETENZA_MANCANTE`)
- `409`: Presa non consentita, operatore fuori dal reparto instradato — caso B (`FLUSSI_PRESA_NON_ELIGIBILE`)
- `400`: Flusso non trovato (`E_VALORE_MANCANTE`)
- `401`: JWT mancante o non valido

> Nota: gli errori del DB (`fn_log_and_raise_error`) sono tradotti in `ServiceError` dal
> service `pratiche_service.prendi_in_carico` via marker substring sul messaggio
> (`"non abilitato per il flusso"` → competenza, `"non consentita del flusso"` → eligibilità).

## Regole

- Il flusso deve essere in stato DA_ESEGUIRE.
- Il flusso non deve essere gia' assegnato ad altro operatore.
- Eligibilità **reparto-first** (4 casi A/B/C/D, vedi sopra): la competenza è un
  lucchetto-skill opzionale, non più sempre obbligatoria.
- Se il flusso non ha `template_flusso_id` (flusso manuale), non c'è skill-lock → vale il
  reparto (caso B) o la presa libera (caso C).
- Se il flusso e' gia' assegnato allo stesso operatore, ritorna `assegnato: false` (noop).
- La funzione DB usa `SELECT ... FOR UPDATE` per evitare race condition.

## Dipendenze DB

- `pratiche.fn_prendi_in_carico_flusso(flusso_id, risorsa_umana_id)` — funzione PL/pgSQL con FOR UPDATE
- `pratiche.competenze_flussi` — lucchetto-skill (eligibilità casi A/D)
- `anagrafiche.risorse_umane` — reparto anagrafico dell'operatore (eligibilità caso B)
- `pratiche.flussi` — `unita_organizzativa_id` (instradamento) + UPDATE `risorsa_umana_id`
- `config.stati_flussi_pratiche` — risoluzione stato DA_ESEGUIRE
- `anagrafiche.risorse_umane_auth_user` — bridge utente → risorsa umana

## Note di migrazione

- Funzione DB creata in migration `20260329-15` e fix race condition in `20260329-16`.
- (18 giugno 2026) `20260618-05`: policy eligibilità reparto-first (competenza condizionale,
  reparto anagrafico per il caso B, presa libera per il caso C).
- Messaggi errore in `config.messaggi_errore.csv` (id 320-322; `FLUSSI_PRESA_NON_ELIGIBILE`
  id 496). Codici registrati in `apps/core/services/error_policies.py` (409).
