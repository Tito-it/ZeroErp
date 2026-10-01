{% include-markdown "it/dbzero/config/manual/auth_totp_device.md" %}
# 📚 Tabella `auth_totp_device`

> 📝 **Descrizione**
>
> Device del secondo fattore (TOTP) di una CREDENZIALE: 1:1 con django.auth_user. Due stati: registrato e non confermato (setup in corso) e confermato (in uso); disabilitare cancella la riga (D-T3). Il segreto lo cifra il backend (DJANGO_FIELD_ENCRYPTION_KEYS) e il DB non lo vede mai in chiaro: la verifica del codice e' del backend, il DB custodisce lo stato e fa rispettare le regole (monouso dei codici di recupero, anti-replay sul passo, chi puo' cosa). Scrivono solo i verbi script.fn_totp_* (SECURITY DEFINER), all'app solo SELECT; si legge con script.fn_get_totp_device. Niente storico, niente RLS (letta prima del login). Brief: brief-db-secondo-fattore-totp.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| secret_encrypted | character varying | NO |  |
| confermato | boolean | NO | false |
| recovery_codes_hash | jsonb | NO | '[]'::jsonb |
| ultimo_uso_at | timestamp with time zone | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| ultimo_passo_usato | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_auth_totp_device_confermato_passo |  |
| CHECK | chk_auth_totp_device_passo |  |
| CHECK | chk_auth_totp_device_recovery_array |  |
| CHECK | chk_auth_totp_device_segreto |  |
| FOREIGN KEY | fk_config_auth_totp_device_auth_user | auth_user_id |
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
