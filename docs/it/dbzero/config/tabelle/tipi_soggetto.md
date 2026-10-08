{% include-markdown "it/dbzero/config/manual/tipi_soggetto.md" %}
# 📚 Tabella `tipi_soggetto`

> 📝 **Descrizione**
>
> Macro-tipologia soggetto: Persona fisica, Persona giuridica, Ente, ecc.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | character varying(10) | NO |  |
| descrizione | character varying(100) | NO |  |
| user_insert | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | YES |  |
| natura_soggetto | config.natura_soggetto_enum | NO |  |

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
| trg_tipi_soggetto_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_soggetto_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
