{% include-markdown "it/dbzero/config/manual/tipi_ruoli.md" %}
# 📚 Tabella `tipi_ruoli`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| codice_interno | character varying | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_ruoli | id |
| UNIQUE | uq_tipi_ruoli_codice | codice |
| UNIQUE | uq_tipi_ruoli_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_ruoli | `CREATE UNIQUE INDEX pk_tipi_ruoli ON config.tipi_ruoli USING btree (id)` |
| uq_tipi_ruoli_codice | `CREATE UNIQUE INDEX uq_tipi_ruoli_codice ON config.tipi_ruoli USING btree (codice)` |
| uq_tipi_ruoli_codice_interno | `CREATE UNIQUE INDEX uq_tipi_ruoli_codice_interno ON config.tipi_ruoli USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_ruoli_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_tipi_ruoli_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
