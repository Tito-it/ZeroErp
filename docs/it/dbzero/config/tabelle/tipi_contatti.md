{% include-markdown "it/dbzero/config/manual/tipi_contatti.md" %}
# 📚 Tabella `tipi_contatti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.tipi_contatti_id_seq'::regclass) |
| descrizione | text | NO |  |
| cod_int_tipo_contatto | character varying | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tipi_contatti_descr_non_vuota |  |
| PRIMARY KEY | pk_tipi_contatti | id |
| UNIQUE | uq_tipi_contatti_cod_int_contatto | cod_int_tipo_contatto |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_contatti | `CREATE UNIQUE INDEX pk_tipi_contatti ON config.tipi_contatti USING btree (id)` |
| uq_tipi_contatti_cod_int_contatto | `CREATE UNIQUE INDEX uq_tipi_contatti_cod_int_contatto ON config.tipi_contatti USING btree (cod_int_tipo_contatto)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_contatti_upd_lock_cod_interno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('cd_int_tipo_attivita', 'CODICE_NON_MODIFICABILE')` |
| trg_upd_tipi_contatti_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
---
{% include-markdown "signature-core.md" %}
