{% include-markdown "it/dbzero/config/manual/motivi_fermo.md" %}
# 📚 Tabella `motivi_fermo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | text | NO |  |
| classe | character varying | NO |  |
| azione | character varying | YES |  |
| ordine | smallint | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_motivi_fermo_classe |  |
| PRIMARY KEY | pk_motivi_fermo | id |
| UNIQUE | uq_motivi_fermo_codice | codice |
| UNIQUE | uq_motivi_fermo_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_motivi_fermo | `CREATE UNIQUE INDEX pk_motivi_fermo ON config.motivi_fermo USING btree (id)` |
| uq_motivi_fermo_codice | `CREATE UNIQUE INDEX uq_motivi_fermo_codice ON config.motivi_fermo USING btree (codice)` |
| uq_motivi_fermo_codice_interno | `CREATE UNIQUE INDEX uq_motivi_fermo_codice_interno ON config.motivi_fermo USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}
