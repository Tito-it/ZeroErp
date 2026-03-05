{% include-markdown "it/dbzero/config/manual/tipi_nota.md" %}
# 📚 Tabella `tipi_nota`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | text | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_nota | id |
| UNIQUE | uq_tipi_nota_codice | codice |
| UNIQUE | uq_tipi_nota_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_nota | `CREATE UNIQUE INDEX pk_tipi_nota ON config.tipi_nota USING btree (id)` |
| uq_tipi_nota_codice | `CREATE UNIQUE INDEX uq_tipi_nota_codice ON config.tipi_nota USING btree (codice)` |
| uq_tipi_nota_codice_interno | `CREATE UNIQUE INDEX uq_tipi_nota_codice_interno ON config.tipi_nota USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_nota_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_nota_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
