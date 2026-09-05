{% include-markdown "it/dbzero/config/manual/email_log.md" %}
# 📚 Tabella `email_log`

> 📝 **Descrizione**
>
> Log invio email con retry, corpo inviato e ambito visibilita'.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| email_account_id | integer | YES |  |
| email_template_id | integer | YES |  |
| destinatario | character varying | NO |  |
| destinatari_cc | ARRAY | YES |  |
| oggetto | text | NO |  |
| corpo_inviato_html | text | YES |  |
| corpo_inviato_testo | text | YES |  |
| stato | character varying | NO | 'PENDING'::character varying |
| errore | text | YES |  |
| tentativi | integer | NO | 0 |
| max_tentativi | integer | NO | 3 |
| prossimo_tentativo | timestamp with time zone | YES |  |
| inviato_at | timestamp with time zone | YES |  |
| contesto_json | jsonb | NO | '{}'::jsonb |
| ambito | character varying | NO | 'SISTEMA'::character varying |
| unita_organizzativa_id | integer | YES |  |
| pratica_id | bigint | YES |  |
| auth_user_id | integer | YES |  |
| email_outbox_id | bigint | YES |  |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| emittente_fiscale_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_email_log_ambito |  |
| CHECK | chk_email_log_ambito_emittente |  |
| CHECK | chk_email_log_stato |  |
| FOREIGN KEY | fk_email_log_email_account | email_account_id |
| FOREIGN KEY | fk_email_log_email_template | email_template_id |
| FOREIGN KEY | fk_email_log_emittente_fiscale | emittente_fiscale_id |
| FOREIGN KEY | fk_email_log_outbox | email_outbox_id |
| FOREIGN KEY | fk_email_log_pratica | pratica_id |
| FOREIGN KEY | fk_email_log_unita_organizzativa | unita_organizzativa_id |
| PRIMARY KEY | email_log_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| email_log_pkey | `CREATE UNIQUE INDEX email_log_pkey ON config.email_log USING btree (id)` |
| ix_email_log_ambito_uo | `CREATE INDEX ix_email_log_ambito_uo ON config.email_log USING btree (ambito, unita_organizzativa_id)` |
| ix_email_log_auth_user_id | `CREATE INDEX ix_email_log_auth_user_id ON config.email_log USING btree (auth_user_id)` |
| ix_email_log_pratica_id | `CREATE INDEX ix_email_log_pratica_id ON config.email_log USING btree (pratica_id)` |
| ix_email_log_stato_prossimo | `CREATE INDEX ix_email_log_stato_prossimo ON config.email_log USING btree (stato, prossimo_tentativo)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_email_log_a10_email_account_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'email_account', 'attivo', 'email_account_id', 'id')` |
| trg_email_log_a10_email_account_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'email_account', 'attivo', 'email_account_id', 'id')` |
| trg_email_log_a10_email_template_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'email_template', 'attivo', 'email_template_id', 'id')` |
| trg_email_log_a10_email_template_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'email_template', 'attivo', 'email_template_id', 'id')` |
| trg_email_log_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_email_log_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')` |
| trg_email_log_a10_unita_organizzative_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_email_log_a10_unita_organizzative_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_email_log_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_email_log_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
