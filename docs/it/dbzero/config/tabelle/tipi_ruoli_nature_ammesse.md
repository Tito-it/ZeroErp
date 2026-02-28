{% include-markdown "it/dbzero/config/manual/tipi_ruoli_nature_ammesse.md" %}
# 📚 Tabella `tipi_ruoli_nature_ammesse`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| tipo_ruolo_id | integer | NO |  |
| tipo_soggetto_id | character varying | NO |  |
| attivo | boolean | NO | true |
| valido_dal | date | YES |  |
| valido_al | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tipi_ruoli_nature_ammesse_validita |  |
| FOREIGN KEY | fk_tipi_ruoli_nature_ammesse_tipo_ruolo | tipo_ruolo_id |
| FOREIGN KEY | fk_tipi_ruoli_nature_ammesse_tipo_soggetto | tipo_soggetto_id |
| PRIMARY KEY | pk_tipi_ruoli_nature_ammesse | id |
| UNIQUE | uq_tipi_ruoli_nature_ammesse_ruolo_soggetto | tipo_ruolo_id, tipo_soggetto_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_ruoli_nature_ammesse_tipo_ruolo_id | `CREATE INDEX ix_tipi_ruoli_nature_ammesse_tipo_ruolo_id ON config.tipi_ruoli_nature_ammesse USING btree (tipo_ruolo_id)` |
| ix_tipi_ruoli_nature_ammesse_tipo_soggetto_id | `CREATE INDEX ix_tipi_ruoli_nature_ammesse_tipo_soggetto_id ON config.tipi_ruoli_nature_ammesse USING btree (tipo_soggetto_id)` |
| pk_tipi_ruoli_nature_ammesse | `CREATE UNIQUE INDEX pk_tipi_ruoli_nature_ammesse ON config.tipi_ruoli_nature_ammesse USING btree (id)` |
| uq_tipi_ruoli_nature_ammesse_ruolo_soggetto | `CREATE UNIQUE INDEX uq_tipi_ruoli_nature_ammesse_ruolo_soggetto ON config.tipi_ruoli_nature_ammesse USING btree (tipo_ruolo_id, tipo_soggetto_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_ruoli_nature_ammesse_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_ruoli_nature_ammesse_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
