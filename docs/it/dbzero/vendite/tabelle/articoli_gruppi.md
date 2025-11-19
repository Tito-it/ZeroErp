{% include-markdown "it/dbzero/vendite/manual/articoli_gruppi.md" %}
# 📚 Tabella `articoli_gruppi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| attivo | boolean | NO | true |
| user_insert | character varying | NO | CURRENT_USER |
| user_update | character varying | YES | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_articoli_gruppi | id |
| UNIQUE | uq_articoli_gruppi_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_articoli_gruppi_codice_upper | `CREATE INDEX ix_articoli_gruppi_codice_upper ON vendite.articoli_gruppi USING btree (upper((codice)::text))` |
| pk_articoli_gruppi | `CREATE UNIQUE INDEX pk_articoli_gruppi ON vendite.articoli_gruppi USING btree (id)` |
| uq_articoli_gruppi_codice | `CREATE UNIQUE INDEX uq_articoli_gruppi_codice ON vendite.articoli_gruppi USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_gruppi_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
