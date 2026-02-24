{% include-markdown "it/dbzero/vendite/manual/listini.md" %}
# 📚 Tabella `listini`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| dominio | character varying | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_listini_dominio |  |
| PRIMARY KEY | pk_listini | id |
| UNIQUE | uq_listini_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_listini | `CREATE UNIQUE INDEX pk_listini ON vendite.listini USING btree (id)` |
| uq_listini_codice | `CREATE UNIQUE INDEX uq_listini_codice ON vendite.listini USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
