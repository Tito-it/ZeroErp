{% include-markdown "it/dbzero/config/manual/tipi_soggetto.md" %}
# 📚 Tabella `tipi_soggetto`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id_tipo_soggetto | character varying | NO |  |
| descrizione | character varying | NO |  |
| user_insert | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| user_update | text | YES |  |
| data_update | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | tipi_soggetto_pkey | id_tipo_soggetto |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| tipi_soggetto_pkey | `CREATE UNIQUE INDEX tipi_soggetto_pkey ON config.tipi_soggetto USING btree (id_tipo_soggetto)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_overrides_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |