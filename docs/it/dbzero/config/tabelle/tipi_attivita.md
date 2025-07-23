# 📚 Tabella `tipi_attivita`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.tipi_attivita_id_seq'::regclass) |
| cod_tipo_attivita | character varying | NO |  |
| descrizione | character varying | NO |  |
| cd_int_tipo_attivita | character varying | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_attivita | id |
| UNIQUE | uq_tipi_attivita_cd_int_tipo_attivita | cd_int_tipo_attivita |
| UNIQUE | uq_tipi_attivita_cod_tipo_attivita | cod_tipo_attivita |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_attivita | `CREATE UNIQUE INDEX pk_tipi_attivita ON config.tipi_attivita USING btree (id)` |
| uq_tipi_attivita_cd_int_tipo_attivita | `CREATE UNIQUE INDEX uq_tipi_attivita_cd_int_tipo_attivita ON config.tipi_attivita USING btree (cd_int_tipo_attivita)` |
| uq_tipi_attivita_cod_tipo_attivita | `CREATE UNIQUE INDEX uq_tipi_attivita_cod_tipo_attivita ON config.tipi_attivita USING btree (cod_tipo_attivita)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_attivita_upd_lock_codiceinterno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('cd_int_tipo_attivita', 'CODICE_NON_MODIFICABILE')` |
| trg_upd_tipi_attivita_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |