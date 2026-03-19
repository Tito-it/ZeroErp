# fn_registra_tentativo_login

### Scopo

Registra l'esito di un tentativo di login e gestisce il blocco temporaneo.
Da chiamare **DOPO** la verifica credenziali nel flusso di autenticazione.

- Login riuscito: reset contatore a 0, rimuove blocco
- Login fallito: incrementa contatore
  - Se contatore >= max (da `config.parameters`): imposta blocco temporaneo

## Schema

`script` (funzione cross-dominio)

## Firma

```sql
script.fn_registra_tentativo_login(
    p_auth_user_id  anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE,
    p_successo      boolean
) RETURNS jsonb
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:------------:|-------------|
| `p_auth_user_id` | `risorse_umane_auth_user.auth_user_id%TYPE` | Si | ID utente Django (`auth_user.id`) |
| `p_successo` | boolean | Si | `true` = login riuscito, `false` = fallito |

## Valore di ritorno

JSONB con la seguente struttura:

```json
{
    "bloccato": false,
    "minuti_rimanenti": 0,
    "tentativi": 0
}
```

| Chiave | Tipo | Descrizione |
|--------|------|-------------|
| `bloccato` | boolean | `true` se l'utente e' stato bloccato con questo tentativo |
| `minuti_rimanenti` | integer | Minuti di blocco (0 se non bloccato) |
| `tentativi` | integer | Numero tentativi falliti consecutivi (0 dopo reset) |

## Caratteristiche

- **VOLATILE**: modifica dati
- Guard: `p_auth_user_id NULL` o `<= 0` → ritorna `{bloccato: false, ...}`
- Se nessun record ponte → ritorna senza modifiche

## Parametri config.parameters

| Code | Default | Descrizione |
|------|---------|-------------|
| `login_max_tentativi_falliti` | 5 | Tentativi prima del blocco |
| `login_blocco_minuti` | 15 | Durata blocco in minuti |

Modificabili dall'admin senza deploy — il DB li legge a ogni chiamata.

## Flusso completo

```text
1. POST /api/v1/auth/login/ { username, password }
2. fn_check_blocco_login(auth_user_id)        → blocco attivo? errore 403
3. Verifica credenziali Django (authenticate)
4. fn_registra_tentativo_login(auth_user_id, successo_o_fallimento)
   → Se successo: reset, rilascia JWT
   → Se fallimento: ritorna { bloccato, tentativi, minuti }
     → Frontend mostra messaggio appropriato
```

## Esempi

```sql
-- Login riuscito: reset
SELECT script.fn_registra_tentativo_login(42, true);
-- {"bloccato": false, "minuti_rimanenti": 0, "tentativi": 0}

-- Login fallito (primo tentativo)
SELECT script.fn_registra_tentativo_login(42, false);
-- {"bloccato": false, "minuti_rimanenti": 0, "tentativi": 1}

-- Login fallito (quinto tentativo, blocco attivato)
SELECT script.fn_registra_tentativo_login(42, false);
-- {"bloccato": true, "minuti_rimanenti": 15, "tentativi": 5}
```
