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
2. POST /password-reset-request/ { identificativo }
   → Cerca la credenziale per email (se c'e' una «@»), poi per nome utente
   → Se trovato e ha email: genera token + invia email con link
   → Risposta SEMPRE 200 (non rivela se utente esiste)
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
{ "identificativo": "mario.rossi" }
```

`identificativo` è il **nome utente o l'email** (dal 2026-10-06, L-4 del piano
accessi, D-9: chi entra dal portale o dallo shop conosce la sua email). Con una
«@» si cerca prima l'email, senza maiuscole (`credenziale_per_email`, la regola
del login per email); se non trova niente, il nome utente esatto
(`credenziale_per_nome_utente`), perché il modello non vieta una «@» nel nome
utente. Vale per ogni credenziale: la prova
è il possesso dell'email a cui arriva il link. Il campo `username` di prima non
è più letto (risposta 200, nessuna ricerca).

#### Output (sempre 200)

```json
{
  "data": {
    "message": "Se l'utente esiste e ha un'email configurata, ricevera' un link per reimpostare la password."
  }
}
```

> **Sicurezza**: la risposta e' identica sia che l'utente esista o no.
> Non rivela quali username sono registrati nel sistema.

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

**Non autenticato**. Rate limiting: `ConfermaTokenRateThrottle`, 10 richieste / 15 minuti per IP
(fino al 2026-10-02 era il 3/15m della richiesta).

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
2. Token valido (non scaduto, non gia' usato) — **validato senza consumare**
3. utente del token esistente
4. `new_password` non vuota
5. `new_password == new_password_confirm`
6. `new_password` passa i 5 validators di `AUTH_PASSWORD_VALIDATORS` (i 4 di Django
   + `ComplexityValidator`)
7. **Solo dopo la validazione password**: il token viene consumato

#### Azioni

In un'unica transazione:

1. Consumo del token (registra l'IP)
2. `user.set_password(new_password)` + save
3. Spegne l'obbligo di cambio password della **credenziale**
   (`fn_imposta_deve_cambiare_password`: e' uno solo, vale per tutte le vesti)
4. Blacklist di tutti i refresh token precedenti
5. **Azzera i tentativi falliti** della credenziale su tutte le provenienze
   (`AuthRepository.azzera_tentativi_credenziale`): chi possiede l'email ha
   superato la prova che il freno protegge. ⛔ Il **blocco dell'amministratore
   resta**: il reset dimostra il possesso dell'email, non annulla una decisione

Dopo il commit, fuori transazione:

6. Invio email conferma con template `CAMBIO_PASSWORD_CONFERMA` (un errore di invio
   viene solo loggato, la risposta resta 200)
7. Log audit: `password_reset_confirmed`

`token` viene ripulito dagli spazi iniziali e finali; `new_password` e
`new_password_confirm` **no**: si salva la password digitata, e il login non la
ripulisce (S-5, 2026-09-27).

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
| `E_RESET_PASSWORD` | 400 | Token vuoto, non valido, scaduto o gia' usato; password vuota, mismatch, troppo semplice |
| `E_TOKEN` | 400 | Token consumato da un'altra richiesta fra la validazione e il consumo (concorrenza) |

---

## Rate Limiting

- `PasswordResetRateThrottle`: 3 richieste / 15 minuti per IP, sulla **richiesta**.
- `ConfermaTokenRateThrottle`: 10 richieste / 15 minuti per IP, sulla **conferma**
  (contatore proprio dal 2026-10-02: una password rifiutata dai validators non
  esaurisce i tentativi di chi ha gia' il link).
- Nessun throttle dedicato sulla validate (GET sola lettura).

Base class condivisa `_CustomRateAnonThrottle` con `LoginRateThrottle`
per parsing rate custom (`"3/15m"`).

## Sicurezza

- **Risposta opaca**: la request ritorna sempre 200 (non rivela username registrati)
- **Token SHA-256**: solo l'hash e' in DB, il token in chiaro viaggia solo nell'email
- **Scadenza 1 ora**: token reset ha vita breve
- **Invalidazione**: alla creazione di un nuovo token, i precedenti vengono invalidati
- **IP tracking**: il consumo del token registra l'IP di chi lo usa
- **Validate-before-consume**: la password viene validata PRIMA di consumare il token — se la password e' troppo debole, il token resta valido e l'operatore puo' riprovare
- **Blacklist JWT**: al reset, tutti i refresh token dell'utente vanno in blacklist; gli access token gia' emessi restano validi fino alla loro scadenza
- **Rate limiting**: 3/15min per IP sulla request, 10/15min sulla confirm
- **Email conferma**: l'operatore riceve notifica del cambio avvenuto

## Settings

| Setting | Default | Scopo |
| --- | --- | --- |
| `FRONTEND_URL` | obbligatoria, nessun default (l'ingresso Nginx, es. `https://backend-dev.tailXXXX.ts.net`) | Base URL per link nelle email |

## Dipendenze

| Componente | Ruolo |
| --- | --- |
| `TokenService` | Genera/valida/consuma token monouso |
| `EmailDispatchService` | Invia email reset e conferma |
| `AuthRepository.set_deve_cambiare_password` | Spegne l'obbligo di cambio password della credenziale |
| `AuthRepository.azzera_tentativi_credenziale` | Azzera i tentativi falliti (tutte le provenienze) |
| Template `RESET_PASSWORD` | Corpo email con link |
| Template `CAMBIO_PASSWORD_CONFERMA` | Notifica cambio avvenuto |

## File Python

| File | Scopo |
| --- | --- |
| `apps/core/api/password_reset_views.py` | 3 view (request, validate, confirm) |
| `apps/core/api/throttling.py` | `PasswordResetRateThrottle`, `ConfermaTokenRateThrottle` + base class condivisa |
