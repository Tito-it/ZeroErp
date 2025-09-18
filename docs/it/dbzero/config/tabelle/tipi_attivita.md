# 📚 Tabella `tipi_attivita`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| codice_interno | character varying | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | 'CURRENT_USER'::character varying |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | NO | 'CURRENT_USER'::character varying |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_attivita | id |
| UNIQUE | uq_tipi_attivita_codice | codice |
| UNIQUE | uq_tipi_attivita_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_attivita | `CREATE UNIQUE INDEX pk_tipi_attivita ON config.tipi_attivita USING btree (id)` |
| uq_tipi_attivita_codice | `CREATE UNIQUE INDEX uq_tipi_attivita_codice ON config.tipi_attivita USING btree (codice)` |
| uq_tipi_attivita_codice_interno | `CREATE UNIQUE INDEX uq_tipi_attivita_codice_interno ON config.tipi_attivita USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_attivita_upd_lock_codiceinterno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_upd_tipi_attivita_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
