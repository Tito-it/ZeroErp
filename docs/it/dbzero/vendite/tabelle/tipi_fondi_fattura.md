{% include-markdown "it/dbzero/vendite/manual/tipi_fondi_fattura.md" %}
# 📚 Tabella `tipi_fondi_fattura`

> 📝 **Descrizione**
>
> Tipologie di fondi fattura (addebiti/accrediti, canone RAI, ecc.).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying(50) | NO |  |
| codice_interno | character varying(50) | YES |  |
| descrizione | character varying(200) | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_fondi_fattura | id |
| UNIQUE | uq_tipi_fondi_fattura_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_fondi_fattura | `CREATE UNIQUE INDEX pk_tipi_fondi_fattura ON vendite.tipi_fondi_fattura USING btree (id)` |
| uq_tipi_fondi_fattura_codice | `CREATE UNIQUE INDEX uq_tipi_fondi_fattura_codice ON vendite.tipi_fondi_fattura USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_fondi_fattura_a10_fatture_fondi_fattura_block_d_5495a3 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_fondi_fattura', 'tipo_fondo_fattura_id', 'id', 'attivo')` |
| trg_tipi_fondi_fattura_a10_fatture_fondi_fattura_source_e5a0fb | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture_fondi_fattura_source', 'tipo_fondo_fattura_id', 'id', 'attivo')` |
| trg_tipi_fondi_fattura_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_tipi_fondi_fattura_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_fondi_fattura_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_fondi_fattura_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_fondi_fattura_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
