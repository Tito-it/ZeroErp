{% include-markdown "it/dbzero/documenti/manual/documenti_generati_eventi.md" %}
# 📚 Tabella `documenti_generati_eventi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| documento_generato_id | bigint | NO |  |
| evento_tipo | character varying | NO |  |
| evento_at | timestamp with time zone | NO | now() |
| user_id | integer | YES |  |
| esito | character varying | NO | 'OK'::character varying |
| messaggio | text | YES |  |
| detail | jsonb | NO | '{}'::jsonb |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_documenti_generati_eventi_detail_obj |  |
| CHECK | chk_documenti_generati_eventi_esito |  |
| CHECK | chk_documenti_generati_eventi_evento_tipo |  |
| CHECK | chk_documenti_generati_eventi_messaggio_non_vuoto |  |
| CHECK | chk_documenti_generati_eventi_meta_obj |  |
| FOREIGN KEY | documenti_generati_eventi_documento_generato_id_fkey | documento_generato_id |
| FOREIGN KEY | fk_documenti_generati_eventi_django_auth_user | user_id |
| PRIMARY KEY | documenti_generati_eventi_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| documenti_generati_eventi_pkey | `CREATE UNIQUE INDEX documenti_generati_eventi_pkey ON documenti.documenti_generati_eventi USING btree (id)` |
| ix_documenti_generati_eventi_documento_evento_at | `CREATE INDEX ix_documenti_generati_eventi_documento_evento_at ON documenti.documenti_generati_eventi USING btree (documento_generato_id, evento_at DESC)` |
| ix_documenti_generati_eventi_evento_tipo | `CREATE INDEX ix_documenti_generati_eventi_evento_tipo ON documenti.documenti_generati_eventi USING btree (evento_tipo)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_documenti_generati_eventi_a10_block_delete_dlt | BEFORE | DELETE | `EXECUTE FUNCTION documenti.trgfn_documenti_generati_eventi_block_delete()` |
| trg_documenti_generati_eventi_a10_block_update_upd | BEFORE | UPDATE | `EXECUTE FUNCTION documenti.trgfn_documenti_generati_eventi_block_update()` |
| trg_documenti_generati_eventi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_documenti_generati_eventi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_documenti_generati_eventi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_documenti_generati_eventi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
