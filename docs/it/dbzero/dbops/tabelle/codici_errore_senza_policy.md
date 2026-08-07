# 📚 Tabella `codici_errore_senza_policy`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | text | NO |  |
| da_trigger | boolean | NO |  |
| data_registrazione | date | NO | CURRENT_DATE |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_codici_errore_senza_policy_conforme |  |
| PRIMARY KEY | pk_codici_errore_senza_policy | id |
| UNIQUE | uq_codici_errore_senza_policy_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_codici_errore_senza_policy | `CREATE UNIQUE INDEX pk_codici_errore_senza_policy ON dbops.codici_errore_senza_policy USING btree (id)` |
| uq_codici_errore_senza_policy_codice | `CREATE UNIQUE INDEX uq_codici_errore_senza_policy_codice ON dbops.codici_errore_senza_policy USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
