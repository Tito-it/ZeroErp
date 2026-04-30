# fn_check_operatore_invitabile

### Scopo

Verifica se un operatore puo' ricevere un invito email per il primo accesso al sistema. Controlla tutte le precondizioni necessarie e ritorna un JSONB con esito, motivo e indirizzo email.

Da chiamare **PRIMA** dell'invio dell'invito nel flusso di onboarding operatore.

## Schema

`script` (funzione cross-dominio)

## Firma

```sql
script.fn_check_operatore_invitabile(
    p_auth_user_id  anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:------------:|-------------|
| `p_auth_user_id` | `risorse_umane_auth_user.auth_user_id%TYPE` | Si | ID utente Django (`auth_user.id`) |

## Condizioni di invitabilita'

Tutte devono essere soddisfatte:

Condizioni post §4.6.B + Fase 7 (2026-04-29): la fn legge da
`anagrafiche.identita_digitali` (ruolo_applicativo='OPERATORE'), non
piu' dal bridge legacy. Tutte devono essere soddisfatte:

| # | Condizione | Motivo se non soddisfatta |
|---|-----------|---------------------------|
| 1 | `auth_user` esiste | `Utente non trovato` |
| 2 | `auth_user.is_active = true` | `Utente disattivato (is_active=false)` |
| 3 | Identita OPERATORE esiste | `Nessuna identita OPERATORE` |
| 4 | `identita_digitali.attivo = true` | `Identita OPERATORE non attiva` |
| 5 | `identita.ruolo_applicativo <> 'DISABILITATO'` | `Ruolo applicativo DISABILITATO` |
| 6 | identita in finestra temporale (`valido_dal/al`) | `Identita fuori finestra temporale` |
| 7 | `auth_user.email` valorizzata | `Nessun indirizzo email configurato` |
| 8 | `auth_user.last_login IS NULL` | `Utente ha gia' effettuato login` |

## Caratteristiche

- **STABLE**: non modifica dati, solo lettura
- **Non lancia eccezioni**: ritorna sempre un JSONB con il risultato
- Guard: `p_auth_user_id` NULL o <= 0 → ritorna `{invitabile: false}`

## Risultato

JSONB con le chiavi:

| Chiave | Tipo | Descrizione |
|--------|------|-------------|
| `invitabile` | boolean | `true` se tutte le condizioni soddisfatte |
| `motivo` | text | Motivo del rifiuto (NULL se invitabile) |
| `email` | text | Indirizzo email dell'operatore (NULL se non trovato) |

## Dipendenze

- `django.auth_user` — dati utente Django
- `anagrafiche.risorse_umane_auth_user` — bridge HR-auth

## Flusso backend

```text
1. Admin clicca "Invia invito" su un operatore
2. Backend chiama fn_check_operatore_invitabile(auth_user_id)
   → Se invitabile=false: mostra motivo all'admin
   → Se invitabile=true: procede con preparazione bozza email
3. Prepara bozza outbox → dialog anteprima → conferma invio
```

## Esempio

```sql
-- Operatore invitabile
SELECT script.fn_check_operatore_invitabile(42);
-- {"invitabile": true, "motivo": null, "email": "mario.rossi@azienda.it"}

-- Operatore gia' loggato
SELECT script.fn_check_operatore_invitabile(10);
-- {"invitabile": false, "motivo": "Utente ha gia' effettuato login", "email": "luca@azienda.it"}
```
