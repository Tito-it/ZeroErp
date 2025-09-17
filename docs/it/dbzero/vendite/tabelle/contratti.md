# 📚 Tabella `contratti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| numero_contratto | character varying | NO |  |
| billing_account_id | integer | NO |  |
| istanza_utility_id | integer | NO |  |
| utility_id | integer | NO |  |
| ambito | character varying | YES | 'COMMODITY'::character varying |
| valid_from | date | NO | CURRENT_DATE |
| valid_to | date | YES |  |
| stato | character varying | YES | 'BOZZA'::character varying |
| parent_contratto_id | bigint | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_contratti_stato |  |
| FOREIGN KEY | fk_contratti_billing_account | billing_account_id |
| FOREIGN KEY | fk_contratti_istanza | istanza_utility_id |
| FOREIGN KEY | fk_contratti_parent | parent_contratto_id |
| FOREIGN KEY | fk_contratti_utility | utility_id |
| PRIMARY KEY | pk_contratti | id |
| UNIQUE | uq_contratti_numero | numero_contratto |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_contratti_no_overlap | `CREATE INDEX ex_contratti_no_overlap ON vendite.contratti USING gist (billing_account_id, istanza_utility_id, utility_id, ambito, daterange(valid_from, COALESCE(valid_to, 'infinity'::date), '[]'::text))` |
| ix_contratti_ambito | `CREATE INDEX ix_contratti_ambito ON vendite.contratti USING btree (ambito)` |
| ix_contratti_ba_istanza | `CREATE INDEX ix_contratti_ba_istanza ON vendite.contratti USING btree (billing_account_id, istanza_utility_id)` |
| pk_contratti | `CREATE UNIQUE INDEX pk_contratti ON vendite.contratti USING btree (id)` |
| uq_contratti_numero | `CREATE UNIQUE INDEX uq_contratti_numero ON vendite.contratti USING btree (numero_contratto)` |

---
{% include-markdown "signature-core.md" %}
