# 📚 Tabella `dashboard_definizione`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| note | text | YES |  |
| attivo | boolean | NO | true |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | character varying | NO |  |
| data_update | timestamp without time zone | YES |  |
| user_update | character varying | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | dashboard_definizione_pkey | id |
| UNIQUE | uq_ui_dashboard_definizione_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| dashboard_definizione_pkey | `CREATE UNIQUE INDEX dashboard_definizione_pkey ON ui.dashboard_definizione USING btree (id)` |
| uq_ui_dashboard_definizione_codice | `CREATE UNIQUE INDEX uq_ui_dashboard_definizione_codice ON ui.dashboard_definizione USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
