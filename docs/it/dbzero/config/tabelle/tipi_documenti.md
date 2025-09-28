# 📚 Tabella `tipi_documenti`

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
| PRIMARY KEY | pk_tipi_documenti | id |
| UNIQUE | uq_tipi_documenti_codice | codice |
| UNIQUE | uq_tipi_documenti_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_documenti | `CREATE UNIQUE INDEX pk_tipi_documenti ON config.tipi_documenti USING btree (id)` |
| uq_tipi_documenti_codice | `CREATE UNIQUE INDEX uq_tipi_documenti_codice ON config.tipi_documenti USING btree (codice)` |
| uq_tipi_documenti_codice_interno | `CREATE UNIQUE INDEX uq_tipi_documenti_codice_interno ON config.tipi_documenti USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_documenti_a10_upd_lock_columns | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_tipi_documenti_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
