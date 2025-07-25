# 📚 Tabella `tipi_documenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('tipi_documenti_id_seq'::regclass) |
| cod_tipo_documento | character varying | NO |  |
| descrizione | character varying | NO |  |
| cd_int_tipo_documento | character varying | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_documenti | id |
| UNIQUE | uq_tipi_documenti_cd_int_tipo_documento | cd_int_tipo_documento |
| UNIQUE | uq_tipi_documenti_cod_tipo_documento | cod_tipo_documento |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_documenti | `CREATE UNIQUE INDEX pk_tipi_documenti ON config.tipi_documenti USING btree (id)` |
| uq_tipi_documenti_cd_int_tipo_documento | `CREATE UNIQUE INDEX uq_tipi_documenti_cd_int_tipo_documento ON config.tipi_documenti USING btree (cd_int_tipo_documento)` |
| uq_tipi_documenti_cod_tipo_documento | `CREATE UNIQUE INDEX uq_tipi_documenti_cod_tipo_documento ON config.tipi_documenti USING btree (cod_tipo_documento)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_contatti_upd_lock_cod_interno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('cd_int_tipo_documento', 'CODICE_NON_MODIFICABILE')` |
| trg_upd_tipi_documenti_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
---
{% include-markdown "signature-core.md" %}
