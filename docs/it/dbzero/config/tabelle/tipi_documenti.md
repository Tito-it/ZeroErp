{% include-markdown "it/dbzero/config/manual/tipi_documenti.md" %}
# 📚 Tabella `tipi_documenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(10) | NO |  |
| descrizione | character varying(100) | NO |  |
| codice_interno | character varying(10) | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

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
| trg_tipi_documenti_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_tipi_documenti_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_documenti_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_documenti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_documenti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
