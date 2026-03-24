# 📚 Tabella `stati_fornitore`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | character varying | NO | ''::character varying |
| descrizione_breve | character varying | NO |  |
| attivo | boolean | NO | true |
| blocca_ordini | boolean | NO | false |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_fornitore | id |
| UNIQUE | uq_stati_fornitore_codice | codice |
| UNIQUE | uq_stati_fornitore_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_stati_fornitore | `CREATE UNIQUE INDEX pk_stati_fornitore ON config.stati_fornitore USING btree (id)` |
| uq_stati_fornitore_codice | `CREATE UNIQUE INDEX uq_stati_fornitore_codice ON config.stati_fornitore USING btree (codice)` |
| uq_stati_fornitore_codice_interno | `CREATE UNIQUE INDEX uq_stati_fornitore_codice_interno ON config.stati_fornitore USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}
