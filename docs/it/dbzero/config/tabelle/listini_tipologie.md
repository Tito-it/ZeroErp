{% include-markdown "it/dbzero/config/manual/listini_tipologie.md" %}
# 📚 Tabella `listini_tipologie`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| e_consumo | boolean | NO | false |
| e_quota_fissa | boolean | NO | false |
| e_imposta | boolean | NO | false |
| e_onere | boolean | NO | false |
| e_prodotto | boolean | NO | false |
| e_servizio | boolean | NO | false |
| ordinamento | smallint | NO | 100 |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_listini_tipologie_flag_esclusivi |  |
| PRIMARY KEY | pk_listini_tipologie | id |
| UNIQUE | uq_listini_tipologie_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_listini_tipologie | `CREATE UNIQUE INDEX pk_listini_tipologie ON config.listini_tipologie USING btree (id)` |
| uq_listini_tipologie_codice | `CREATE UNIQUE INDEX uq_listini_tipologie_codice ON config.listini_tipologie USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
