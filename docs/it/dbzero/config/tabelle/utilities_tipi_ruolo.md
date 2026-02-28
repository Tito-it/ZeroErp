{% include-markdown "it/dbzero/config/manual/utilities_tipi_ruolo.md" %}
# 📚 Tabella `utilities_tipi_ruolo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| utility_id | integer | NO |  |
| tipo_ruolo_id | integer | NO |  |
| attivo | boolean | NO | true |
| valido_dal | date | YES |  |
| valido_al | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| storicizza | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_utilities_tipi_ruolo_validita |  |
| FOREIGN KEY | fk_utilities_tipi_ruolo_tipo_ruolo | tipo_ruolo_id |
| FOREIGN KEY | fk_utilities_tipi_ruolo_utility | utility_id |
| PRIMARY KEY | pk_utilities_tipi_ruolo | id |
| UNIQUE | uq_utilities_tipi_ruolo_utility_tipo_ruolo | utility_id, tipo_ruolo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_utilities_tipi_ruolo_tipo_ruolo_id | `CREATE INDEX ix_utilities_tipi_ruolo_tipo_ruolo_id ON config.utilities_tipi_ruolo USING btree (tipo_ruolo_id)` |
| ix_utilities_tipi_ruolo_utility_id | `CREATE INDEX ix_utilities_tipi_ruolo_utility_id ON config.utilities_tipi_ruolo USING btree (utility_id)` |
| pk_utilities_tipi_ruolo | `CREATE UNIQUE INDEX pk_utilities_tipi_ruolo ON config.utilities_tipi_ruolo USING btree (id)` |
| uq_utilities_tipi_ruolo_utility_tipo_ruolo | `CREATE UNIQUE INDEX uq_utilities_tipi_ruolo_utility_tipo_ruolo ON config.utilities_tipi_ruolo USING btree (utility_id, tipo_ruolo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_utilities_tipi_ruolo_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_utilities_tipi_ruolo_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_utilities_tipi_ruolo_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('utilities_tipi_ruolo_id')` |
| trg_utilities_tipi_ruolo_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('utilities_tipi_ruolo_id')` |

---
{% include-markdown "signature-core.md" %}
