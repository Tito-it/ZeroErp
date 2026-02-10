{% include-markdown "it/dbzero/vendite/manual/fatture_fondi_fattura.md" %}
# 📚 Tabella `fatture_fondi_fattura`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| riferimento_fattura_id | bigint | YES |  |
| tipo_fondo_fattura_id | bigint | NO |  |
| importo | numeric | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_fatture_fondi_fattura_fattura | fattura_id |
| FOREIGN KEY | fk_fatture_fondi_fattura_rif_fattura | riferimento_fattura_id |
| FOREIGN KEY | fk_fatture_fondi_fattura_tipo | tipo_fondo_fattura_id |
| PRIMARY KEY | pk_fatture_fondi_fattura | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_fondi_fattura_fattura | `CREATE INDEX ix_fatture_fondi_fattura_fattura ON vendite.fatture_fondi_fattura USING btree (fattura_id)` |
| ix_fatture_fondi_fattura_tipo | `CREATE INDEX ix_fatture_fondi_fattura_tipo ON vendite.fatture_fondi_fattura USING btree (tipo_fondo_fattura_id)` |

---
{% include-markdown "signature-core.md" %}
