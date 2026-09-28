# API Token Monouso e Cambio Password

## Scopo

Building block per token monouso (inviti, reset password, conferme) e meccanismo
di cambio password obbligatorio al primo accesso. I due componenti lavorano insieme:
il flag `deve_cambiare_password` forza il cambio, il `TokenService` genera token
sicuri per i flussi che lo richiedono.

## Contesto

Il `TokenService` e' un BB generico (Anello 0) riutilizzato da:

- Invito operatore (Fase 3): token tipo `INVITO_OPERATORE`
- Reset password (Fase 2): token tipo `RESET_PASSWORD`
- Conferme generiche: qualsiasi tipo custom

Il cambio password obbligatorio intercetta tutte le richieste API tramite
middleware e blocca la navigazione finche' l'operatore non cambia password.

---

## Token Monouso — Architettura

```text
TokenService (apps/core/services/token_service.py)
  |
TokenRepository (apps/core/db/token_repository.py)
  |
config.token_monouso (tabella DB)
```

### Sicurezza

- Il token in chiaro viene generato (32 bytes = 64 hex) e ritornato una sola volta
- In DB si salva solo l'hash SHA-256 — il token in chiaro **non e' recuperabile**
- Alla creazione, tutti i token precedenti dello stesso tipo/utente vengono invalidati
- Il consumo registra IP e timestamp
- Token scaduti vengono puliti periodicamente da `config.fn_cleanup_token_scaduti()`

### API interna (Python, non esposta come REST)

Il `TokenService` non ha endpoint REST propri — e' usato internamente dai service
di invito e reset password.

```python
from apps.core.services.token_service import TokenService

token_service = TokenService()

# Genera token (ritorna in chiaro, unica volta)
token_plain = token_service.create(
    tipo="RESET_PASSWORD",
    auth_user_id=42,
    scadenza_ore=1,
    meta={"richiesto_da": "self-service"},
)

# Valida senza consumare
result = token_service.validate(token_plain, "RESET_PASSWORD")
# result = (42, {"richiesto_da": "self-service"}) oppure None

# Consuma (segna come utilizzato)
auth_user_id = token_service.consume(token_plain, "RESET_PASSWORD", ip="192.168.1.1")
# Lancia ServiceError se token invalido/scaduto/gia' usato

# Invalida tutti i token di un tipo per un utente
count = token_service.invalidate_all("RESET_PASSWORD", 42)
```

---

## Cambio Password — Endpoint

### POST /api/v1/auth/change-password/

Autenticazione: JWT (operatore autenticato).

```http
POST /api/v1/auth/change-password/
Content-Type: application/json
Authorization: Bearer {access_token}
```

#### Input

```json
{
  "old_password": "password-attuale",
  "new_password": "nuova-password-sicura",
  "new_password_confirm": "nuova-password-sicura"
}
```

| Campo | Tipo | Obbligatorio | Note |
| --- | --- | :---: | --- |
| `old_password` | string | Si | Password corrente |
| `new_password` | string | Si | Deve superare i 5 validators configurati |
| `new_password_confirm` | string | Si | Deve coincidere con `new_password` |

#### Validazioni

1. `old_password` non vuota
2. `new_password` non vuota
3. `new_password == new_password_confirm`
4. `new_password != old_password` (deve essere diversa)
5. `old_password` corretta (check hash Django)
6. `new_password` passa i 5 validators di `AUTH_PASSWORD_VALIDATORS`:
   - `UserAttributeSimilarityValidator` — non simile a username/email
   - `MinimumLengthValidator` — lunghezza minima
   - `CommonPasswordValidator` — non nella lista password comuni
   - `NumericPasswordValidator` — non solo numeri
   - `apps.core.password_validators.ComplexityValidator` — complessita' minima

I tre campi **non** vengono ripuliti dagli spazi: si verifica e si salva la password digitata, come fa il login (S-5, 2026-09-27).

#### Azioni

1. Rilegge l'identita' della veste del JWT corrente (`identita_id` del claim): se nel
   frattempo e' stata revocata, 401 `E_IDENTITA_NON_ATTIVA` **prima** di toccare la
   password
2. `user.set_password(new_password)` + `user.save()`, spegnimento dell'obbligo
   di cambio password della **credenziale** (uno solo per tutte le vesti),
   blacklist di tutti i refresh
   token precedenti dell'utente (atomiche, `apply_new_password`)
3. Riapre la sessione **nella stessa veste** con la catena del login,
   `emetti_refresh_veste` (`multi_veste_token_serializer.py`): `sid` nuovo,
   `identita_id`, `ruolo_applicativo` e, per un operatore, l'emittente attivo risolto
   come al login. La sessione e' nuova perche' la blacklist ha appena chiuso le altre
4. Audit: evento LOGIN con il `sid` della sessione nuova

> ⚠️ Fino al 2026-09-24 la coppia si emetteva con `RefreshToken.for_user(user)`, senza i
> claim della veste: il frontend la installava e la richiesta successiva usciva 401
> `E_JWT_SENZA_IDENTITA` — proprio nel cambio obbligatorio al primo accesso — e l'audit
> registrava il `jti` al posto del `sid` (M-2 della [analisi difetti](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md)).

#### Output (successo)

```json
{
  "data": {
    "access": "eyJ...",
    "refresh": "eyJ..."
  },
  "meta": { "request_id": "..." }
}
```

Il frontend deve aggiornare i token nello store con quelli nuovi.

#### Errori

| Codice | HTTP | Causa |
| --- | --- | --- |
| `E_CHANGE_PASSWORD` | 400 | Validazione fallita (password vuota, mismatch, troppo semplice, ecc.) |
| `E_CHANGE_PASSWORD` | 400 | Password attuale non corretta |
| `E_IDENTITA_NON_ATTIVA` | 401 | La veste della sessione non e' piu' attiva: la password non cambia |

---

## Flag `deve_cambiare_password` — Flusso completo

⭐ **Il flag e' della credenziale, non della veste** (dal 2026-09-25): la
password e' una sola, quindi l'obbligo di cambiarla vale su ogni porta. Sede:
`config.credenziali`, letta e scritta **solo** da
`fn_get_deve_cambiare_password` / `fn_imposta_deve_cambiare_password` (riga
assente = `false`). Lo accende l'invito operatore; lo spegne qualunque nuova
password (cambio, reset, attivazione).

### 1. Login

Il flag viene controllato dopo login riuscito in `AuditTokenObtainPairView`.
Se attivo, la response include:

```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "password_change_required": true
}
```

Il token JWT viene comunque rilasciato (serve per chiamare `/change-password/`).

### 2. Middleware blocco

`PasswordChangeRequiredMiddleware` intercetta TUTTE le richieste `/api/v1/*` e blocca
con 403 se il flag e' attivo. Endpoint consentiti:

- `POST /api/v1/auth/change-password/`
- `POST /api/v1/auth/logout/`
- `GET /api/v1/core/me/`

Qualsiasi altro endpoint ritorna 403:

```json
{
  "error": {
    "code": "E_CAMBIO_PASSWORD_RICHIESTO",
    "message": "Devi cambiare la password prima di procedere."
  }
}
```

### 3. Cambio password

L'operatore chiama `/change-password/` con vecchia e nuova password.
Al successo, il flag viene resettato e i token precedenti invalidati.

### 4. Navigazione libera

Con i nuovi token, tutte le API sono di nuovo accessibili.

---

## Middleware — Comportamento in caso di errore DB

Se la query per il flag fallisce (DB irraggiungibile), il middleware **blocca per sicurezza**
(fail-closed) ritornando 503:

```json
{
  "error": {
    "code": "E_CAMBIO_PASSWORD_CHECK_FALLITO",
    "message": "Impossibile verificare lo stato delle credenziali. Riprova."
  }
}
```

Superuser bypassa completamente il middleware.

> ⚠️ Difetto noto ([E-1](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md)): `E_CAMBIO_PASSWORD_RICHIESTO` ed
> `E_CAMBIO_PASSWORD_CHECK_FALLITO` sono scritti a mano dal middleware e non sono a
> catalogo codici: niente classe, `ui_action` ne' ripiego. La risposta 503 esce anche
> senza `meta`.
>
> ⛔ Difetto noto ([S-2](../../../dev/work-in-progress/analisi-be-difetti-emersi-verifica-doc-api-core.md), verificato il 2026-09-28): il blocco gira in `process_view`,
> dove per le richieste con JWT Bearer `request.user` e' ancora anonimo
> (l'autenticazione DRF avviene dopo, nel dispatch della view): per i client Bearer
> **non scatta**, e nessun'altra sede fa rispettare `deve_cambiare_password`. Si
> sposta dopo l'autenticazione col lotto L-6 del piano accessi.

---

## Dipendenze DB

| Oggetto | Scopo |
| --- | --- |
| `config.token_monouso` | Tabella token con hash SHA-256, scadenza, consumo |
| `config.fn_cleanup_token_scaduti(giorni)` | Job pulizia periodica |
| `config.credenziali.deve_cambiare_password` | Flag cambio password della credenziale (fino al 2026-09-25 stava su ogni riga di `identita_digitali`) |
| `script.fn_get_deve_cambiare_password` / `fn_imposta_deve_cambiare_password` | Unica lettura e scrittura del flag |
| `script.fn_get_user_profile()` | Include `deve_cambiare_password` nel JSONB profilo (letto dalla credenziale) |

## File Python

| File | Scopo |
| --- | --- |
| `apps/core/db/token_repository.py` | Repository: create, find_valid, consume, invalidate_all |
| `apps/core/services/token_service.py` | Service: hash, generate, validate, consume |
| `apps/core/api/change_password_view.py` | Endpoint POST /auth/change-password/ |
| `apps/core/middleware/password_change_middleware.py` | Blocco navigazione se flag attivo |
| `apps/core/db/auth_repository.py` | `get/set_deve_cambiare_password(auth_user_id)` — della credenziale, senza veste |
| `apps/core/api/auth_views.py` | +flag password_change_required nella response login |

## Ordine middleware

```text
SecurityMiddleware
SessionMiddleware
CommonMiddleware
RequestContextMiddleware
ApiExceptionMiddleware
UserLanguageMiddleware
CsrfViewMiddleware
AuthenticationMiddleware
JwtAuditMiddleware              ← reset GUC, guard BYPASSRLS (non autentica)
PasswordChangeRequiredMiddleware ← blocca se deve cambiare password
RequestLogMiddleware
MessageMiddleware
XFrameOptionsMiddleware
```
