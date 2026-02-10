{% include-markdown "it/dbzero/vendite/manual/fatture_arrotondamenti_scope.md" %}
# 📚 Tabella `fatture_arrotondamenti_scope`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| billing_account_id | bigint | NO |  |
| utility_id | integer | NO |  |
| tipo_doc_fiscale_id | bigint | NO |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| valuta_id | bigint | NO |  |
| saldo_arrotondamento | numeric | NO | 0 |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_fatture_arrotondamenti_scope_ba | billing_account_id |
| FOREIGN KEY | fk_fatture_arrotondamenti_scope_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_fatture_arrotondamenti_scope_tipo_doc | tipo_doc_fiscale_id |
| FOREIGN KEY | fk_fatture_arrotondamenti_scope_utility | utility_id |
| FOREIGN KEY | fk_fatture_arrotondamenti_scope_valuta | valuta_id |
| PRIMARY KEY | pk_fatture_arrotondamenti_scope | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatture_arrotondamenti_scope | `CREATE UNIQUE INDEX pk_fatture_arrotondamenti_scope ON vendite.fatture_arrotondamenti_scope USING btree (id)` |
| uq_fatture_arrotondamenti_scope_key | `CREATE UNIQUE INDEX uq_fatture_arrotondamenti_scope_key ON vendite.fatture_arrotondamenti_scope USING btree (billing_account_id, utility_id, tipo_doc_fiscale_id, emittente_soggetto_ruolo_id, valuta_id)` |

---
{% include-markdown "signature-core.md" %}
