# fn_resolve_email_account

### 🎯 Scopo Principale

Risolve l'account SMTP da utilizzare per l'invio di una email, dato il reparto (unita' organizzativa) del contesto. Implementa una catena di fallback a 2 livelli per garantire che ci sia sempre un account disponibile.

## Schema

`config`

## Firma

```sql
config.fn_resolve_email_account(
    p_unita_organizzativa_id  config.email_account.unita_organizzativa_id%TYPE
                              DEFAULT NULL
) RETURNS jsonb
```

## Parametri

| Parametro                  | Tipo                                        | Obbligatorio | Descrizione                                              |
| -------------------------- | ------------------------------------------- | :----------: | -------------------------------------------------------- |
| `p_unita_organizzativa_id` | `email_account.unita_organizzativa_id%TYPE` |      No      | ID reparto. NULL = usa direttamente l'account di sistema |

## Catena di fallback

1. **Account del reparto**: cerca un account attivo con `unita_organizzativa_id` corrispondente
2. **Account SISTEMA**: cerca l'account con `codice = 'SISTEMA'` e `attivo = true`

Se nessun account trovato in nessun livello, ritorna `NULL`.

## Caratteristiche

- **STABLE**: non modifica dati, solo lettura
- Se il reparto ha piu' account attivi, usa il primo per `id` (ORDER BY id LIMIT 1)

## Risultato

JSONB con le chiavi:

| Chiave                    | Tipo    | Descrizione                              |
| ------------------------- | ------- | ---------------------------------------- |
| `id`                      | integer | ID dell'account                          |
| `codice`                  | text    | Codice account (es. `SISTEMA`, `ACQ_01`) |
| `smtp_host`               | text    | Hostname SMTP                            |
| `smtp_port`               | integer | Porta SMTP                               |
| `smtp_use_tls`            | boolean | Flag STARTTLS                            |
| `smtp_use_ssl`            | boolean | Flag SSL diretto                         |
| `smtp_username`           | text    | Username SMTP                            |
| `smtp_password_encrypted` | text    | Password crittografata (Fernet)          |
| `email_from`              | text    | Indirizzo mittente                       |
| `email_reply_to`          | text    | Indirizzo reply-to (puo' essere null)    |

## Dipendenze

- `config.email_account` — tabella account SMTP

## Esempio

```sql
-- Account per il reparto Acquisti (id=3)
SELECT config.fn_resolve_email_account(3);

-- Account di sistema (fallback diretto)
SELECT config.fn_resolve_email_account(NULL);
SELECT config.fn_resolve_email_account();
```
