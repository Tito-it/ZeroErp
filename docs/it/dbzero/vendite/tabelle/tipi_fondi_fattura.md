{% include-markdown "it/dbzero/vendite/manual/tipi_fondi_fattura.md" %}
# 📚 Tabella `tipi_fondi_fattura`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | YES |  |
| descrizione | character varying | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| UNIQUE | uq_tipi_fondi_fattura_codice | codice |
| PRIMARY KEY | pk_tipi_fondi_fattura | id |

---
{% include-markdown "signature-core.md" %}
