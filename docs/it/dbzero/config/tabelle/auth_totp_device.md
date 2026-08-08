{% include-markdown "it/dbzero/config/manual/auth_totp_device.md" %}
# 📚 Tabella `auth_totp_device`

> 📝 **Descrizione**
>
> Device TOTP per autenticazione a due fattori. 1:1 con auth_user.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| secret_encrypted | character varying | NO |  |
| abilitato | boolean | NO | false |
| confermato | boolean | NO | false |
| recovery_codes_hash | jsonb | NO | '[]'::jsonb |
| ultimo_codice_usato | character varying | YES |  |
| ultimo_uso_at | timestamp with time zone | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | auth_totp_device_pkey | id |
| UNIQUE | uq_auth_totp_device_auth_user | auth_user_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| auth_totp_device_pkey | `CREATE UNIQUE INDEX auth_totp_device_pkey ON config.auth_totp_device USING btree (id)` |
| uq_auth_totp_device_auth_user | `CREATE UNIQUE INDEX uq_auth_totp_device_auth_user ON config.auth_totp_device USING btree (auth_user_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_auth_totp_device_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_auth_totp_device_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
