# API Invito Operatore al Primo Accesso

## Scopo

Permette all'admin di invitare un operatore via email. L'operatore riceve un link,
imposta la propria password e attiva l'account. Nessuna password viene comunicata
manualmente.

## Contesto

Usa i building block:

- **BB-1** (Email): template `INVITO_OPERATORE`, risoluzione account per reparto
- **BB-2** (Token): token monouso tipo `INVITO_OPERATORE` con scadenza 72 ore
- **BB-3** (Cambio password): flag `deve_cambiare_password` impostato a true

Il flusso e' guidato dall'admin ma l'attivazione e' self-service.

---

## Flusso completo

```text
1. Admin apre drawer operatore → clicca "Invia invito"
   |
2. POST /amm-software/operatori/{id}/invita/
   → Verifica invitabilita' (fn_check_operatore_invitabile)
   → Imposta password temporanea casuale (non comunicata)
   → Imposta deve_cambiare_password = true
   → Genera token invito (72 ore)
   → Invia email con link: {FRONTEND_URL}/attivazione/{token}
   → Aggiorna invito_inviato_at
   → Response: { inviato: true, email: "m***@azienda.it" }
   |
3. Operatore riceve email → clicca link
   |
4. GET /auth/attivazione-validate/{token}/
   → Se valido: frontend mostra form password
   → Se invalido/scaduto: messaggio errore
   |
5. POST /auth/attivazione/ { token, new_password, new_password_confirm }
   → Consuma token
   → Imposta password scelta dall'operatore
   → Resetta deve_cambiare_password = false
   → Response: { message: "Account attivato." }
   |
6. Operatore fa login con la nuova password
```

---

## Endpoint Admin

Base path: `/api/v1/amm-software/`
Autenticazione: JWT + ruolo ADMIN

### Invia invito

```http
POST /api/v1/amm-software/operatori/{auth_user_id}/invita/
```

Body vuoto. L'endpoint verifica automaticamente se l'operatore e' invitabile.

**Condizioni per essere invitabile** (verificate da `script.fn_check_operatore_invitabile`):

1. `auth_user` esiste e `is_active = true`
2. `identita_digitali` con veste OPERATORE esiste e `attivo = true`
3. `ruolo_applicativo <> 'DISABILITATO'`
4. L'identita' e' nella sua finestra di validita' (`valido_dal`/`valido_al` rispetto a oggi)
5. L'utente ha un indirizzo email configurato
6. `last_login IS NULL` (non ha mai effettuato login)

#### Output (successo)

```json
{ "data": { "inviato": true, "email": "m***@azienda.it" } }
```

L'email e' mascherata per sicurezza (solo primo carattere + `***@dominio`).

La risposta e' `inviato: true` anche se l'invio dell'email fallisce: l'errore viene
solo loggato, il token resta valido e l'invito e' recuperabile col reinvio.
⚠️ Difetto noto (F-3): `inviato: true` non dice se l'email e' partita, e `invita`
(a differenza di `reinvia-invito`) non invalida i token di un invito precedente —
possono restarne validi piu' d'uno. Vedi [analisi difetti](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md).

#### Errori

| Codice | HTTP | Causa |
| --- | --- | --- |
| `E_INVITO_OPERATORE` | 400 | Operatore non invitabile (motivo specifico nel messaggio), anche quando l'utente non esiste |

⚠️ Difetto noto (E-4): anche un `auth_user_id` inesistente esce 400 e non 404 — vedi
[analisi difetti](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md).

### Reinvia invito

```http
POST /api/v1/amm-software/operatori/{auth_user_id}/reinvia-invito/
```

Invalida il token invito precedente, ne genera uno nuovo e rinvia l'email.
Utile se l'invito e' scaduto o non e' stato ricevuto.

---

## Endpoint Pubblico — Validazione Token Invito

```http
GET /api/v1/auth/attivazione-validate/{token}/
```

**Non autenticato** (`AllowAny`). Verifica se un token invito e' ancora valido senza consumarlo.
Usato dal frontend per mostrare il form di attivazione o un messaggio di errore/scadenza.

### Output

```json
{ "data": { "valid": true } }
```

oppure:

```json
{ "data": { "valid": false, "message": "Token non valido, scaduto o gia' utilizzato." } }
```

---

## Endpoint Pubblico — Attivazione

```http
POST /api/v1/auth/attivazione/
```

**Non autenticato** (`AllowAny`). Rate limiting: 3 richieste / 15 minuti per IP.

### Input

```json
{
  "token": "a1b2c3d4...",
  "new_password": "password-scelta",
  "new_password_confirm": "password-scelta"
}
```

### Validazioni (ordine critico)

1. `token` non vuoto
2. `new_password` non vuota (dopo aver tolto gli spazi iniziali e finali)
3. `new_password == new_password_confirm`
4. Token valido tipo `INVITO_OPERATORE` — **validato senza consumare**
5. Password passa i validators configurati in `AUTH_PASSWORD_VALIDATORS` (i 4 di Django piu' `ComplexityValidator`)
6. **Solo dopo validazione password**: il token viene consumato

> Se la password e' troppo debole (es. "12345678"), il token resta valido
> e l'operatore puo' riprovare con una password piu' forte.

⚠️ Difetto noto (S-5): `new_password` e `new_password_confirm` vengono ripulite
dagli spazi iniziali e finali (`.strip()`) prima di essere salvate — la password
registrata puo' differire da quella digitata. Vedi [analisi difetti](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md).

### Azioni (atomiche)

1. `user.set_password(new_password)` + save
2. Reset flag `deve_cambiare_password = false`

### Output

```json
{
  "data": {
    "message": "Account attivato con successo. Effettua il login con la nuova password."
  }
}
```

> L'operatore deve fare login manualmente dopo l'attivazione.

### Errori

| Codice | HTTP | Causa |
| --- | --- | --- |
| `E_ATTIVAZIONE` | 400 | Token assente, non valido, scaduto o gia' usato; utente inesistente; password vuota, mismatch, troppo semplice |
| `E_TOKEN` | 400 | Il token era valido alla verifica ma il consumo non riesce (es. consumato in parallelo) |

---

## Sicurezza

- **Password temporanea** casuale, non comunicata (solo il token viaggia nell'email)
- **Token SHA-256**: solo hash in DB, token in chiaro solo nell'email
- **Scadenza 72 ore**: l'operatore ha 3 giorni per attivare
- **Invalidazione**: il reinvio invalida automaticamente il token precedente
- **Validate-before-consume**: la password viene validata PRIMA di consumare il token — password debole non brucia il token
- **Rate limiting**: 3/15min per IP sull'endpoint attivazione
- **IP tracking**: l'attivazione registra l'IP di chi consuma il token
- **Operazioni atomiche**: password + flag in `transaction.atomic()`, email invito in try/except (non blocca il flusso)
- **Email mascherata**: la response all'admin mostra solo `m***@dominio`

## Dipendenze DB

| Oggetto | Scopo |
| --- | --- |
| `script.fn_check_operatore_invitabile(auth_user_id)` | Verifica 6 condizioni invitabilita' |
| `config.token_monouso` | Token invito con scadenza 72h |
| `anagrafiche.identita_digitali.invito_inviato_at` | Timestamp ultimo invito |
| `anagrafiche.identita_digitali.deve_cambiare_password` | Flag cambio password (⚠️ fino al 2026-09-12 questa riga nominava la vista `risorse_umane_auth_user`, nome vecchio del ponte in ritiro (analisi-software-per-dati-morti §2.1)) |

## File Python

| File | Scopo |
| --- | --- |
| `apps/anagrafiche/services/invito_operatore_service.py` | Service: verifica, genera, invia, reinvia |
| `apps/amm_software/api/invito_views.py` | 2 endpoint admin (invita, reinvia) |
| `apps/core/api/attivazione_view.py` | 2 endpoint pubblici (validate + attivazione) |
| `apps/core/db/auth_repository.py` | +get_unita_organizzativa_id, +set_invito_inviato_at |
