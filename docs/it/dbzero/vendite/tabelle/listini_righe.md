{% include-markdown "it/dbzero/vendite/manual/listini_righe.md" %}
# 📚 Tabella `listini_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| listino_versione_id | bigint | NO |  |
| articolo_id | uuid | NO |  |
| uom_id | bigint | NO |  |
| billing_account_id | bigint | YES |  |
| utility_id | integer | YES |  |
| emittente_soggetto_ruolo_id | bigint | YES |  |
| prezzo | numeric | NO |  |
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
| CHECK | chk_listini_righe_prezzo |  |
| FOREIGN KEY | fk_listini_righe_articolo | articolo_id |
| FOREIGN KEY | fk_listini_righe_ba | billing_account_id |
| FOREIGN KEY | fk_listini_righe_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_listini_righe_uom | uom_id |
| FOREIGN KEY | fk_listini_righe_utility | utility_id |
| FOREIGN KEY | fk_listini_righe_versione | listino_versione_id |
| PRIMARY KEY | pk_listini_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_listini_righe_lookup | `CREATE INDEX ix_listini_righe_lookup ON vendite.listini_righe USING btree (listino_versione_id, articolo_id, uom_id, billing_account_id, utility_id, emittente_soggetto_ruolo_id) WHERE (attivo IS TRUE)` |
| pk_listini_righe | `CREATE UNIQUE INDEX pk_listini_righe ON vendite.listini_righe USING btree (id)` |
| uq_listini_righe_key_attiva | `CREATE UNIQUE INDEX uq_listini_righe_key_attiva ON vendite.listini_righe USING btree (listino_versione_id, articolo_id, uom_id, COALESCE(billing_account_id, ('-1'::integer)::bigint), COALESCE(utility_id, '-1'::integer), COALESCE(emittente_soggetto_ruolo_id, ('-1'::integer)::bigint)) WHERE (attivo IS TRUE)` |

---
{% include-markdown "signature-core.md" %}
