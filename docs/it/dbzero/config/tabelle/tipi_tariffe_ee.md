# 📚 Tabella `tipi_tariffe_ee`

> 📝 **Descrizione**
>
> Tipologia Tariffa mercato elettrico

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| gruppo_tariffa_ee | character varying | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_tariffe_ee | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_tariffe_ee | `CREATE UNIQUE INDEX pk_tipi_tariffe_ee ON config.tipi_tariffe_ee USING btree (id)` |

---
{% include-markdown "signature-core.md" %}
