{% include-markdown "it/dbzero/config/manual/utilities.md" %}
# 📚 Tabella `utilities`

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
| PRIMARY KEY | pk_utilities | id |
| UNIQUE | uq_utilities_codice | codice |
| UNIQUE | uq_utilities_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_utilities | `CREATE UNIQUE INDEX pk_utilities ON config.utilities USING btree (id)` |
| uq_utilities_codice | `CREATE UNIQUE INDEX uq_utilities_codice ON config.utilities USING btree (codice)` |
| uq_utilities_codice_interno | `CREATE UNIQUE INDEX uq_utilities_codice_interno ON config.utilities USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_utilities_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_utilities_audit_data_user_generic_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
