# fn_check_blocco_login

### Scopo

Verifica se un utente e' temporaneamente bloccato per tentativi di login falliti.
Da chiamare **PRIMA** della verifica credenziali nel flusso di autenticazione.

- Se `bloccato_fino_a` e' scaduto: resetta automaticamente (`tentativi_falliti = 0`, `bloccato_fino_a = NULL`)
- Se blocco ancora attivo: lancia errore `E_UTENTE_BLOCCATO` con minuti rimanenti
- Se nessun blocco: ritorna senza errore

## Schema

`script` (funzione cross-dominio)

## Firma

```sql
script.fn_check_blocco_login(
    p_auth_user_id  anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE
) RETURNS void
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:------------:|-------------|
| `p_auth_user_id` | `risorse_umane_auth_user.auth_user_id%TYPE` | Si | ID utente Django (`auth_user.id`) |

## Caratteristiche

- **VOLATILE**: modifica dati (reset blocco scaduto)
- Guard: `p_auth_user_id NULL` o `<= 0` → ritorna senza errore
- Se nessun record ponte `risorse_umane_auth_user` → ritorna senza errore

## Errori

| Codice | Quando | Messaggio |
|--------|--------|-----------|
| `E_UTENTE_BLOCCATO` | Blocco attivo (`bloccato_fino_a > NOW()`) | `Utente temporaneamente bloccato. Riprovare tra N minuti.` |

## Flusso backend

```text
1. POST /api/v1/auth/login/
2. Backend chiama fn_check_blocco_login(auth_user_id)
   → Se bloccato: errore 403 con minuti rimanenti
   → Se OK: procede con verifica credenziali
3. Dopo verifica credenziali: fn_registra_tentativo_login(auth_user_id, successo)
```

## Esempio

```sql
-- Prima della verifica credenziali
SELECT script.fn_check_blocco_login(42);
-- Se bloccato: lancia errore
-- Se OK: void (nessun errore)
```
