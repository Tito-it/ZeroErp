{% include-markdown "it/dbzero/config/manual/email_outbox.md" %}
# 📚 Tabella `email_outbox`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| email_account_id | integer | YES |  |
| email_template_id | integer | YES |  |
| ambito | character varying | NO | 'SISTEMA'::character varying |
| unita_organizzativa_id | integer | YES |  |
| pratica_id | bigint | YES |  |
| destinatario | character varying | NO |  |
| destinatari_cc | ARRAY | YES |  |
| oggetto | text | NO |  |
| corpo_html | text | NO |  |
| corpo_testo | text | YES |  |
| stato | character varying | NO | 'DRAFT'::character varying |
| contesto_json | jsonb | NO | '{}'::jsonb |
| auth_user_id | integer | YES |  |
| creato_da_user_id | integer | YES |  |
| inviato_at | timestamp with time zone | YES |  |
| email_log_id | bigint | YES |  |
| tx_id | uuid | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_email_outbox_ambito |  |
| CHECK | chk_email_outbox_reparto_uo |  |
| CHECK | chk_email_outbox_stato |  |
| FOREIGN KEY | email_outbox_email_account_id_fkey | email_account_id |
| FOREIGN KEY | email_outbox_email_template_id_fkey | email_template_id |
| FOREIGN KEY | email_outbox_pratica_id_fkey | pratica_id |
| FOREIGN KEY | email_outbox_unita_organizzativa_id_fkey | unita_organizzativa_id |
| FOREIGN KEY | fk_email_outbox_email_log | email_log_id |
| PRIMARY KEY | email_outbox_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| email_outbox_pkey | `CREATE UNIQUE INDEX email_outbox_pkey ON config.email_outbox USING btree (id)` |
| ix_email_outbox_ambito_uo | `CREATE INDEX ix_email_outbox_ambito_uo ON config.email_outbox USING btree (ambito, unita_organizzativa_id)` |
| ix_email_outbox_pratica_id | `CREATE INDEX ix_email_outbox_pratica_id ON config.email_outbox USING btree (pratica_id)` |
| ix_email_outbox_stato_creato_da | `CREATE INDEX ix_email_outbox_stato_creato_da ON config.email_outbox USING btree (stato, creato_da_user_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_email_outbox_a10_email_account_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'email_account', 'attivo', 'email_account_id')` |
| trg_email_outbox_a10_email_account_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'email_account', 'attivo', 'email_account_id')` |
| trg_email_outbox_a10_email_template_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'email_template', 'attivo', 'email_template_id')` |
| trg_email_outbox_a10_email_template_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'email_template', 'attivo', 'email_template_id')` |
| trg_email_outbox_a10_unita_organizzative_require_attivo__7d7a72 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id')` |
| trg_email_outbox_a10_unita_organizzative_require_attivo__7d7a72 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id')` |
| trg_email_outbox_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_email_outbox_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_email_outbox_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_email_outbox_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
