# Autenticazione a Due Fattori (2FA TOTP) — WIP

> Documento di pianificazione per 2FA TOTP opzionale.
> Data creazione: 2026-04-01
> Stato: **PIANIFICATO — non ancora in sviluppo**
> Estratto da: gestione-autenticazioni.md (Fase 4, ora in work-done)
>
> Dipende da:
>
> * Fasi 1-3 completate (email, token, cambio password, reset, invito)
> * Nuove dipendenze Python: `pyotp`, `qrcode`, `Pillow`

---

## Obiettivo

Aggiungere autenticazione TOTP opzionale (Google Authenticator, Authy).
L'admin puo' rendere il 2FA obbligatorio per singoli operatori.

---

## DB (gia' creato)

- [x] 4.1 — Creare tabella `config.auth_totp_device` ✅ `20260328-20`

```
config.auth_totp_device
├── id                  BIGSERIAL PK
├── auth_user_id        INTEGER UNIQUE NOT NULL FK → auth_user(id)
│                       (1:1 — un solo device TOTP per utente)
├── secret_encrypted    VARCHAR(512) NOT NULL
│                       (secret TOTP crittografato con Fernet/SECRET_KEY)
├── abilitato           BOOLEAN NOT NULL DEFAULT false
├── confermato          BOOLEAN NOT NULL DEFAULT false
│                       (true solo dopo prima verifica riuscita)
├── recovery_codes_hash JSONB NOT NULL DEFAULT '[]'
│                       (array di hash SHA-256 dei codici recovery)
├── ultimo_codice_usato VARCHAR(10) NULL
│                       (anti-replay: ultimo codice TOTP verificato)
├── ultimo_uso_at       TIMESTAMPTZ NULL
├── meta                JSONB NOT NULL DEFAULT '{}'
├── data_insert         TIMESTAMPTZ NOT NULL DEFAULT now()
├── user_insert         TEXT NOT NULL DEFAULT CURRENT_USER
├── data_update         TIMESTAMPTZ NOT NULL DEFAULT now()
├── user_update         TEXT NOT NULL DEFAULT CURRENT_USER
```

- [x] 4.2 — Aggiungere colonna a `anagrafiche.risorse_umane_auth_user`: ✅ `20260328-21`

```sql
ALTER TABLE anagrafiche.risorse_umane_auth_user
  ADD COLUMN totp_obbligatorio BOOLEAN NOT NULL DEFAULT false;
```

- [ ] 4.3 — Aggiornare `script.fn_get_user_profile()`:
  - Includere `totp_abilitato` e `totp_obbligatorio` nel JSONB di risposta

---

## Backend

- [ ] 4.4 — Creare `apps/core/services/totp_service.py` — `TotpService`

Responsabilita':
  - `setup_device(auth_user_id)`:
    1. Genera secret TOTP (`pyotp.random_base32()`)
    2. Salva crittografato in `auth_totp_device`
    3. Genera 10 recovery codes (monouso)
    4. Salva hash dei recovery codes
    5. Ritorna: `{ secret, provisioning_uri, qr_code_base64, recovery_codes }`
  - `confirm_setup(auth_user_id, codice)`:
    1. Verifica codice TOTP con `pyotp.TOTP(secret).verify(codice, valid_window=1)`
    2. Se valido → `confermato = true`, `abilitato = true`
  - `verify(auth_user_id, codice)`:
    1. Anti-replay: rifiuta se `codice == ultimo_codice_usato`
    2. Verifica TOTP
    3. Se fallisce → prova recovery codes
    4. Aggiorna `ultimo_codice_usato` e `ultimo_uso_at`
    5. Ritorna `{valido: bool, tipo: 'totp'|'recovery', recovery_rimanenti: N}`
  - `disable(auth_user_id)`:
    1. Imposta `abilitato = false`
    2. Cancella secret e recovery codes
  - `regenerate_recovery_codes(auth_user_id, codice_totp)`:
    1. Verifica codice TOTP corrente (conferma identita')
    2. Genera nuovi 10 recovery codes
    3. Ritorna in chiaro (unica volta)

- [ ] 4.5 — Modificare flusso login (login a due step):

Step 1 — `POST /api/v1/admin/token/` (esistente, modificato):
  - Login username+password come ora
  - Se 2FA abilitato → NON rilascia token JWT definitivo
  - Risposta: `{ two_factor_required: true, two_factor_token: "<token_temporaneo>" }`
  - Il `two_factor_token` e' un token firmato (Django signing) con scadenza 5 minuti
    contenente `auth_user_id` — NON e' un JWT

Step 2 — `POST /api/v1/admin/token/2fa-verify/` (nuovo):
  - Input: `{ two_factor_token, code }`
  - Verifica firma e scadenza del token temporaneo
  - Verifica codice TOTP via `TotpService.verify()`
  - Se valido → rilascia coppia JWT (access + refresh) come login normale
  - Se fallisce → errore + log tentativo

- [ ] 4.6 — Creare endpoint profilo 2FA:
  - `POST /api/v1/auth/2fa/setup/` — avvia setup, ritorna QR code
  - `POST /api/v1/auth/2fa/confirm/` — conferma setup con primo codice
  - `POST /api/v1/auth/2fa/disable/` — disabilita (richiede password corrente)
  - `POST /api/v1/auth/2fa/recovery-codes/` — rigenera codici (richiede codice TOTP)

- [ ] 4.7 — Endpoint admin per gestione 2FA operatori:
  - `DELETE /api/v1/amm-software/operatori/<id>/2fa/` — disabilita 2FA (emergenza admin)
  - `PUT /api/v1/amm-software/operatori/<id>/2fa-obbligatorio/` — imposta obbligo
  - Log audit per ogni operazione admin su 2FA

- [ ] 4.8 — Middleware 2FA obbligatorio:
  - Se `totp_obbligatorio = true` e `totp_abilitato = false`:
    - Consenti solo: setup 2FA, logout, me
    - Tutti gli altri → HTTP 403 con codice `E_2FA_SETUP_RICHIESTO`

---

## Frontend

- [ ] 4.9 — Modificare `LoginView.vue` per flusso a due step:
  - Step 1: username + password (come ora)
  - Se `two_factor_required: true` → mostra campo codice TOTP
  - Step 2: input codice 6 cifre + bottone verifica
  - Link "Usa codice di recupero" → campo testo per recovery code

- [ ] 4.10 — Creare sezione "Sicurezza" nel profilo utente:
  - Stato 2FA: Abilitato/Disabilitato
  - Bottone "Configura 2FA" → wizard setup:
    1. Mostra QR code + secret testuale (per input manuale)
    2. Campo verifica: inserisci codice dall'app
    3. Mostra recovery codes (scaricabili/stampabili)
    4. Conferma: "Ho salvato i codici di recupero"
  - Bottone "Disabilita 2FA" (richiede password)
  - Bottone "Rigenera codici di recupero" (richiede codice TOTP)

- [ ] 4.11 — Aggiungere nel drawer operatore (admin):
  - Badge "2FA Attivo" / "2FA Non configurato" / "2FA Obbligatorio"
  - Bottone "Disabilita 2FA" (emergenza)
  - Toggle "2FA Obbligatorio"

- [ ] 4.12 — Pagina forzata setup 2FA:
  - Se `totp_obbligatorio = true` e non configurato → redirect a setup
  - Simile al blocco cambio password (Fase 1)

---

## Test

- [ ] 4.T1 — Test Django: setup device → secret + QR + recovery codes
- [ ] 4.T2 — Test Django: conferma setup con codice valido
- [ ] 4.T3 — Test Django: login 2 step completo
- [ ] 4.T4 — Test Django: anti-replay (stesso codice rifiutato)
- [ ] 4.T5 — Test Django: recovery code valido + decremento contatore
- [ ] 4.T6 — Test Django: admin disabilita 2FA operatore
- [ ] 4.T7 — Test Django: middleware 2FA obbligatorio

---

## Dipendenze Python (da aggiungere a requirements.in)

| Pacchetto | Versione | Scopo |
|-----------|----------|-------|
| `pyotp` | >=2.9 | Generazione/verifica codici TOTP |
| `qrcode` | >=8.0 | Generazione QR code per setup authenticator |
| `Pillow` | >=11.0 | Dipendenza qrcode per output immagine |
