{% include-markdown "it/dbzero/anagrafiche/manual/categorie_clienti.md" %}
# 📚 Tabella `categorie_clienti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | smallint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| partecipa_promo | boolean | NO | true |
| ordinamento | smallint | NO | 100 |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_categorie_clienti | id |
| UNIQUE | uq_categorie_clienti_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_categorie_clienti_attivo | `CREATE INDEX ix_categorie_clienti_attivo ON anagrafiche.categorie_clienti USING btree (attivo)` |
| pk_categorie_clienti | `CREATE UNIQUE INDEX pk_categorie_clienti ON anagrafiche.categorie_clienti USING btree (id)` |
| uq_categorie_clienti_codice | `CREATE UNIQUE INDEX uq_categorie_clienti_codice ON anagrafiche.categorie_clienti USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
