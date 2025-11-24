# 📚 Tabella `bank_branches`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| bank_code | character varying | NO |  |
| branch_code | character varying | NO |  |
| bic_swift | character varying | YES |  |
| name | character varying | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | check_bank_branches_bic_swift_fmt |  |
| FOREIGN KEY | fk_bank_branches_soggetti_ruoli | soggetto_ruolo_id |
| PRIMARY KEY | pk_bank_branches | id |
| UNIQUE | uq_bank_branches_soggetto_ruolo_bank_branch_code | soggetto_ruolo_id, bank_code, branch_code |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_bank_branches_attivo | `CREATE INDEX ix_bank_branches_attivo ON anagrafiche.bank_branches USING btree (attivo)` |
| ix_bank_branches_soggetto_ruolo_id | `CREATE INDEX ix_bank_branches_soggetto_ruolo_id ON anagrafiche.bank_branches USING btree (soggetto_ruolo_id)` |
| pk_bank_branches | `CREATE UNIQUE INDEX pk_bank_branches ON anagrafiche.bank_branches USING btree (id)` |
| uq_bank_branches_soggetto_ruolo_bank_branch_code | `CREATE UNIQUE INDEX uq_bank_branches_soggetto_ruolo_bank_branch_code ON anagrafiche.bank_branches USING btree (soggetto_ruolo_id, bank_code, branch_code)` |

---
{% include-markdown "signature-core.md" %}
