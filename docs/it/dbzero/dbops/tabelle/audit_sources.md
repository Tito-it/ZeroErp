{% include-markdown "it/dbzero/dbops/manual/audit_sources.md" %}
# 📚 Tabella `audit_sources`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO |  |
| code | text | NO |  |
| storico_table | text | NO |  |
| storico_pk_col | text | NO |  |
| label_key | text | NO |  |
| area_funzionale | text | NO |  |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_audit_sources | id |
| UNIQUE | uq_audit_sources_code | code |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_audit_sources | `CREATE UNIQUE INDEX pk_audit_sources ON dbops.audit_sources USING btree (id)` |
| uq_audit_sources_code | `CREATE UNIQUE INDEX uq_audit_sources_code ON dbops.audit_sources USING btree (code)` |

---
{% include-markdown "signature-core.md" %}
