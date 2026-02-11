{% include-markdown "it/dbzero/vendite/manual/fatture_fondi_fattura_source.md" %}
# 📚 Tabella `fatture_fondi_fattura_source`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_sorgente_id | bigint | NO |  |
| tipo_fondo_fattura_id | bigint | NO |  |
| importo | numeric | NO |  |
| stato | character varying | NO |  |
| fattura_figlia_id | bigint | YES |  |
| data_assegnazione | timestamp with time zone | YES |  |
| user_assegnazione | text | YES |  |
| billing_account_id | bigint | NO |  |
| utility_id | integer | NO |  |
| tipo_doc_fiscale_id | bigint | NO |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| valuta_id | bigint | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_fondi_source_ba | billing_account_id |
| FOREIGN KEY | fk_fondi_source_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_fondi_source_fattura_figlia | fattura_figlia_id |
| FOREIGN KEY | fk_fondi_source_fattura_sorgente | fattura_sorgente_id |
| FOREIGN KEY | fk_fondi_source_tipo | tipo_fondo_fattura_id |
| FOREIGN KEY | fk_fondi_source_tipo_doc | tipo_doc_fiscale_id |
| FOREIGN KEY | fk_fondi_source_utility | utility_id |
| FOREIGN KEY | fk_fondi_source_valuta | valuta_id |
| PRIMARY KEY | pk_fatture_fondi_fattura_source | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatture_fondi_fattura_source | `CREATE UNIQUE INDEX pk_fatture_fondi_fattura_source ON vendite.fatture_fondi_fattura_source USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
