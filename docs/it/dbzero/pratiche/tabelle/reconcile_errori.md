{% include-markdown "it/dbzero/pratiche/manual/reconcile_errori.md" %}
# 📚 Tabella `reconcile_errori`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| sorgente_tipo_id | bigint | YES |  |
| sorgente_uid | text | YES |  |
| pratica_id | bigint | YES |  |
| flusso_id | bigint | YES |  |
| errcode | text | YES |  |
| messaggio | text | YES |  |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_reconcile_errori | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_reconcile_errori_data_insert | `CREATE INDEX ix_reconcile_errori_data_insert ON pratiche.reconcile_errori USING btree (data_insert DESC)` |
| ix_reconcile_errori_sorgente | `CREATE INDEX ix_reconcile_errori_sorgente ON pratiche.reconcile_errori USING btree (sorgente_tipo_id, sorgente_uid)` |
| pk_reconcile_errori | `CREATE UNIQUE INDEX pk_reconcile_errori ON pratiche.reconcile_errori USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
