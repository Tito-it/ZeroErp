{% include-markdown "it/dbzero/config/manual/tipi_ruoli.md" %}
# 📚 Tabella `tipi_ruoli`

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
| ricerca_visibile | boolean | NO | false |
| entita_tabella | text | YES |  |
| entita_colonna_codice | text | YES |  |
| entita_esistenza | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tipi_ruoli_entita_esistenza_forma |  |
| PRIMARY KEY | pk_tipi_ruoli | id |
| UNIQUE | uq_tipi_ruoli_codice | codice |
| UNIQUE | uq_tipi_ruoli_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_ruoli | `CREATE UNIQUE INDEX pk_tipi_ruoli ON config.tipi_ruoli USING btree (id)` |
| uq_tipi_ruoli_codice | `CREATE UNIQUE INDEX uq_tipi_ruoli_codice ON config.tipi_ruoli USING btree (codice)` |
| uq_tipi_ruoli_codice_interno | `CREATE UNIQUE INDEX uq_tipi_ruoli_codice_interno ON config.tipi_ruoli USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_ruoli_a10_guard_entita_ref_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_tipi_ruoli_guard_entita_ref()` |
| trg_tipi_ruoli_a10_guard_entita_ref_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_tipi_ruoli_guard_entita_ref()` |
| trg_tipi_ruoli_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_tipi_ruoli_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_ruoli_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_ruoli_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_ruoli_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
