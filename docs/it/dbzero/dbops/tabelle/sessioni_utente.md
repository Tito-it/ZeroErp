{% include-markdown "it/dbzero/dbops/manual/sessioni_utente.md" %}
# 📚 Tabella `sessioni_utente`

> 📝 **Descrizione**
>
> Audit delle sessioni JWT e del secondo fattore: traccia login, refresh, logout e revoca dei token, e la disattivazione del secondo fattore. La scadenza di un token non e' un evento: si legge dalla scadenza del token.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| evento | text | NO |  |
| jti | text | YES |  |
| ip_address | inet | YES |  |
| user_agent | text | YES |  |
| request_id | uuid | YES |  |
| dettaglio | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| cleanup_at | timestamp with time zone | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_sessioni_utente_evento |  |
| PRIMARY KEY | pk_sessioni_utente | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_sessioni_utente_auth_user_id | `CREATE INDEX ix_sessioni_utente_auth_user_id ON dbops.sessioni_utente USING btree (auth_user_id)` |
| ix_sessioni_utente_cleanup_at | `CREATE INDEX ix_sessioni_utente_cleanup_at ON dbops.sessioni_utente USING btree (cleanup_at)` |
| ix_sessioni_utente_data_insert | `CREATE INDEX ix_sessioni_utente_data_insert ON dbops.sessioni_utente USING btree (data_insert DESC)` |
| ix_sessioni_utente_jti | `CREATE INDEX ix_sessioni_utente_jti ON dbops.sessioni_utente USING btree (jti)` |
| pk_sessioni_utente | `CREATE UNIQUE INDEX pk_sessioni_utente ON dbops.sessioni_utente USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_sessioni_utente_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_sessioni_utente_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_sessioni_utente_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_sessioni_utente_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
