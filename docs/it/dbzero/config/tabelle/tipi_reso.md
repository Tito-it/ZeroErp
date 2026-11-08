{% include-markdown "it/dbzero/config/manual/tipi_reso.md" %}
# 📚 Tabella `tipi_reso`

> 📝 **Descrizione**
>
> Dominio tipo reso per riga (brief-db-resi-vendita §1). Il flag riapre_residuo pilota il motore (RESO_A_CREDITO=false, RESO_PER_RICONSEGNA=true), nessun IF hardcoded. rev 2026-07-13.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying(32) | NO |  |
| codice | character varying(32) | NO |  |
| descrizione | character varying(120) | YES |  |
| riapre_residuo | boolean | NO |  |
| attivo | boolean | NO | true |
| ordine | smallint | NO | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_reso | id |
| UNIQUE | uq_tipi_reso_codice | codice |
| UNIQUE | uq_tipi_reso_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_reso_attivo | `CREATE INDEX ix_tipi_reso_attivo ON config.tipi_reso USING btree (attivo)` |
| ix_tipi_reso_ordine | `CREATE INDEX ix_tipi_reso_ordine ON config.tipi_reso USING btree (ordine)` |
| pk_tipi_reso | `CREATE UNIQUE INDEX pk_tipi_reso ON config.tipi_reso USING btree (id)` |
| uq_tipi_reso_codice | `CREATE UNIQUE INDEX uq_tipi_reso_codice ON config.tipi_reso USING btree (codice)` |
| uq_tipi_reso_codice_interno | `CREATE UNIQUE INDEX uq_tipi_reso_codice_interno ON config.tipi_reso USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_reso_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_tipi_reso_a10_resi_righe_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'resi_righe', 'tipo_reso_id', 'id', 'attivo')` |
| trg_tipi_reso_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_reso_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_reso_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_reso_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
