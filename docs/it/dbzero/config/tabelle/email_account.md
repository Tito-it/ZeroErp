{% include-markdown "it/dbzero/config/manual/email_account.md" %}
# 📚 Tabella `email_account`

> 📝 **Descrizione**
>
> Account SMTP per invio email. Ogni reparto puo' avere il proprio. NULL su unita_organizzativa_id = account di sistema/fallback.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(50) | NO |  |
| descrizione | text | NO |  |
| unita_organizzativa_id | integer | YES |  |
| smtp_host | character varying(255) | NO |  |
| smtp_port | integer | NO | 587 |
| smtp_use_tls | boolean | NO | true |
| smtp_use_ssl | boolean | NO | false |
| smtp_username | character varying(255) | NO |  |
| smtp_password_encrypted | character varying(512) | NO |  |
| email_from | character varying(255) | NO |  |
| email_reply_to | character varying(255) | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| codice_interno | character varying | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_email_account_codice_interno_nonvuoto |  |
| CHECK | chk_email_account_email_reply_to_non_vuoto |  |
| CHECK | chk_email_account_smtp_port |  |
| CHECK | chk_email_account_tls_ssl_exclusive |  |
| FOREIGN KEY | email_account_unita_organizzativa_id_fkey | unita_organizzativa_id |
| PRIMARY KEY | email_account_pkey | id |
| UNIQUE | uq_email_account_codice | codice |
| UNIQUE | uq_email_account_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| email_account_pkey | `CREATE UNIQUE INDEX email_account_pkey ON config.email_account USING btree (id)` |
| uq_email_account_codice | `CREATE UNIQUE INDEX uq_email_account_codice ON config.email_account USING btree (codice)` |
| uq_email_account_codice_interno | `CREATE UNIQUE INDEX uq_email_account_codice_interno ON config.email_account USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_email_account_a10_email_log_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'email_log', 'email_account_id', 'id', 'attivo')` |
| trg_email_account_a10_email_outbox_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'email_outbox', 'email_account_id', 'id', 'attivo')` |
| trg_email_account_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_email_account_a10_unita_organizzative_require_attivo_bdcebd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_email_account_a10_unita_organizzative_require_attivo_bdcebd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_email_account_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_email_account_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_email_account_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_email_account_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
