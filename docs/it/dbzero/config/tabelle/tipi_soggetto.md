{% include-markdown "it/dbzero/config/manual/tipi_soggetto.md" %}
# 📚 Tabella `tipi_soggetto`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | character varying | NO |  |
| descrizione | character varying | NO |  |
| user_insert | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| user_update | text | YES |  |
| data_update | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_soggetto | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_soggetto | `CREATE UNIQUE INDEX pk_tipi_soggetto ON config.tipi_soggetto USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_soggetto_audit_data_user_generic_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
