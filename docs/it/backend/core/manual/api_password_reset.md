# API Reset Password Dimenticata

## Scopo

Permette all'operatore di reimpostare la propria password via email, senza intervento admin.
Tre endpoint pubblici (non autenticati) con rate limiting.

## Contesto

Usa i building block gia' pronti:

- **BB-1** (Email): invio email con template `RESET_PASSWORD` e `CAMBIO_PASSWORD_CONFERMA`
- **BB-2** (Token): token monouso tipo `RESET_PASSWORD` con scadenza 1 ora

Il flusso e' completamente self-service. L'admin non interviene.

---

## Flusso completo

```text
1. Operatore clicca "Password dimenticata?" nel frontend
   |
2. POST /password-reset-request/ { email }
   → Cerca utente con email attiva
   → Se trovato: genera token + invia email con link
   → Risposta SEMPRE 200 (non rivela se email esiste)
   |
3. Operatore riceve email con link: {FRONTEND_URL}/reset-password/{token}
   |
4. Frontend apre la pagina e chiama:
   GET /password-reset-validate/{token}/
   → { valid: true } o { valid: false, message: "..." }
   |
5. Se valido, operatore inserisce nuova password e conferma:
   POST /password-reset-confirm/ { token, new_password, new_password_confirm }
   → Consuma token, cambia password, blacklista JWT precedenti
   → Invia email conferma
   → { message: "Password reimpostata. Effettua il login." }
   |
6. Operatore fa login con la nuova password
```

---

## Endpoint

### 1. Richiesta reset

```http
POST /api/v1/auth/password-reset-request/
```

**Non autenticato** (`AllowAny`). Rate limiting: 3 richieste / 15 minuti per IP.

#### Input

```json
{ "email": "mario@azienda.it" }
```

#### Output (sempre 200)

```json
{
  "data": {
    "message": "Se l'email e' registrata, riceverai un link per reimpostare la password."
  }
}
```

> **Sicurezza**: la risposta e' identica sia che l'email esista o no.
> Non rivela quali email sono registrate nel sistema.

#### Logica interna (se utente trovato)

1. Genera token tipo `RESET_PASSWORD` (scadenza 1 ora)
2. Invalida eventuali token reset precedenti per lo stesso utente
3. Risolve account email mittente per reparto dell'operatore
4. Invia email con template `RESET_PASSWORD`:
   - Variabili: `nome`, `azienda`, `link`, `scadenza_ore`
   - Link: `{FRONTEND_URL}/reset-password/{token}`

---

### 2. Validazione token

```http
GET /api/v1/auth/password-reset-validate/{token}/
```

**Non autenticato**. Nessun rate limiting (solo lettura, non consuma).

#### Output

```json
{ "data": { "valid": true } }
```

oppure:

```json
{ "data": { "valid": false, "message": "Token non valido, scaduto o gia' utilizzato." } }
```

Usato dal frontend per mostrare il form o un messaggio di errore prima
che l'operatore compili la nuova password.

---

### 3. Conferma reset

```http
POST /api/v1/auth/password-reset-confirm/
```

**Non autenticato**. Rate limiting: 3 richieste / 15 minuti per IP.

#### Input

```json
{
  "token": "a1b2c3d4...",
  "new_password": "nuova-password-sicura",
  "new_password_confirm": "nuova-password-sicura"
}
```

#### Validazioni (ordine critico)

1. `token` non vuoto
2. `new_password` non vuota
3. `new_password == new_password_confirm`
4. Token valido (non scaduto, non gia' usato) — **validato senza consumare**
5. `new_password` passa i 4 validators Django
6. **Solo dopo la validazione password**: il token viene consumato

#### Azioni (atomiche)

1. `user.set_password(new_password)` + save
2. Reset flag `deve_cambiare_password = false`
3. Blacklist tutti i refresh token precedenti
4. Invia email conferma con template `CAMBIO_PASSWORD_CONFERMA`
5. Log audit: `password_reset_confirmed`

#### Output

```json
{
  "data": {
    "message": "Password reimpostata con successo. Effettua il login con la nuova password."
  }
}
```

> **Nota**: non vengono rilasciati nuovi token JWT. L'operatore deve
> fare login manualmente con la nuova password.

#### Errori

| Codice | HTTP | Causa |
| --- | --- | --- |
| `E_TOKEN` | 400 | Token non valido, scaduto o gia' usato |
| `E_RESET_PASSWORD` | 400 | Password vuota, mismatch, troppo semplice |

---

## Rate Limiting

`PasswordResetRateThrottle`: 3 richieste / 15 minuti per IP.
Applicato su request e confirm (non su validate che e' GET sola lettura).

Base class condivisa `_CustomRateAnonThrottle` con `LoginRateThrottle`
per parsing rate custom (`"3/15m"`).

## Sicurezza

- **Risposta opaca**: la request ritorna sempre 200 (non rivela email registrate)
- **Token SHA-256**: solo l'hash e' in DB, il token in chiaro viaggia solo nell'email
- **Scadenza 1 ora**: token reset ha vita breve
- **Invalidazione**: alla creazione di un nuovo token, i precedenti vengono invalidati
- **IP tracking**: il consumo del token registra l'IP di chi lo usa
- **Validate-before-consume**: la password viene validata PRIMA di consumare il token — se la password e' troppo debole, il token resta valido e l'operatore puo' riprovare
- **Blacklist JWT**: al reset, tutti i token JWT dell'utente vengono invalidati
- **Rate limiting**: 3/15min per IP su request e confirm
- **Email conferma**: l'operatore riceve notifica del cambio avvenuto

## Settings

| Setting | Default | Scopo |
| --- | --- | --- |
| `FRONTEND_URL` | `http://localhost:5173` | Base URL per link nelle email |

## Dipendenze

| Componente | Ruolo |
| --- | --- |
| `TokenService` | Genera/valida/consuma token monouso |
| `EmailDispatchService` | Invia email reset e conferma |
| `AuthRepository.set_deve_cambiare_password` | Reset flag dopo cambio |
| Template `RESET_PASSWORD` | Corpo email con link |
| Template `CAMBIO_PASSWORD_CONFERMA` | Notifica cambio avvenuto |

## File Python

| File | Scopo |
| --- | --- |
| `apps/core/api/password_reset_views.py` | 3 view (request, validate, confirm) |
| `apps/core/api/throttling.py` | `PasswordResetRateThrottle` + base class condivisa |
