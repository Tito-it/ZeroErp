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
4. Frontend apre pagina attivazione
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
2. `risorse_umane_auth_user` esiste e `attivo = true`
3. `ruolo_sistema <> 'DISABILITATO'`
4. L'utente ha un indirizzo email configurato
5. `last_login IS NULL` (non ha mai effettuato login)

#### Output (successo)

```json
{ "data": { "inviato": true, "email": "m***@azienda.it" } }
```

L'email e' mascherata per sicurezza (solo primo carattere + `***@dominio`).

#### Errori

| Codice | HTTP | Causa |
| --- | --- | --- |
| `E_INVITO_OPERATORE` | 400 | Operatore non invitabile (motivo specifico nel messaggio) |

### Reinvia invito

```http
POST /api/v1/amm-software/operatori/{auth_user_id}/reinvia-invito/
```

Invalida il token invito precedente, ne genera uno nuovo e rinvia l'email.
Utile se l'invito e' scaduto o non e' stato ricevuto.

---

## Endpoint Pubblico — Attivazione

```http
POST /api/v1/auth/attivazione/
```

**Non autenticato** (`AllowAny`).

### Input

```json
{
  "token": "a1b2c3d4...",
  "new_password": "password-scelta",
  "new_password_confirm": "password-scelta"
}
```

### Validazioni

1. `token` non vuoto
2. `new_password` non vuota
3. `new_password == new_password_confirm`
4. Token valido tipo `INVITO_OPERATORE` (non scaduto, non usato)
5. Password passa i 4 validators Django

### Azioni (atomiche)

1. Consuma token (registra IP e timestamp)
2. `user.set_password(new_password)` + save
3. Reset flag `deve_cambiare_password = false`

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
| `E_TOKEN` | 400 | Token non valido, scaduto o gia' usato |
| `E_ATTIVAZIONE` | 400 | Password vuota, mismatch, troppo semplice |

---

## Sicurezza

- **Password temporanea** casuale, non comunicata (solo il token viaggia nell'email)
- **Token SHA-256**: solo hash in DB, token in chiaro solo nell'email
- **Scadenza 72 ore**: l'operatore ha 3 giorni per attivare
- **Invalidazione**: il reinvio invalida automaticamente il token precedente
- **IP tracking**: l'attivazione registra l'IP di chi consuma il token
- **Email mascherata**: la response all'admin mostra solo `m***@dominio`

## Dipendenze DB

| Oggetto | Scopo |
| --- | --- |
| `script.fn_check_operatore_invitabile(auth_user_id)` | Verifica 5 condizioni invitabilita' |
| `config.token_monouso` | Token invito con scadenza 72h |
| `anagrafiche.risorse_umane_auth_user.invito_inviato_at` | Timestamp ultimo invito |
| `anagrafiche.risorse_umane_auth_user.deve_cambiare_password` | Flag cambio password |

## File Python

| File | Scopo |
| --- | --- |
| `apps/anagrafiche/services/invito_operatore_service.py` | Service: verifica, genera, invia, reinvia |
| `apps/amm_software/api/invito_views.py` | 2 endpoint admin (invita, reinvia) |
| `apps/core/api/attivazione_view.py` | 1 endpoint pubblico (attivazione) |
| `apps/core/db/auth_repository.py` | +get_unita_organizzativa_id, +set_invito_inviato_at |
