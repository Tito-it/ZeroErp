{% include-markdown "it/dbzero/config/manual/tipi_indirizzi.md" %}
# 📚 Tabella `tipi_indirizzi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | 'CURRENT_USER'::text |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | 'CURRENT_USER'::text |
| codice | character varying | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_indirizzi | id |
| UNIQUE | uq_tipi_indirizzi_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_indirizzi | `CREATE UNIQUE INDEX pk_tipi_indirizzi ON config.tipi_indirizzi USING btree (id)` |
| uq_tipi_indirizzi_codice_interno | `CREATE UNIQUE INDEX uq_tipi_indirizzi_codice_interno ON config.tipi_indirizzi USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_indirizzi_a10_upd_lock_columns | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_tipi_indirizzi_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
