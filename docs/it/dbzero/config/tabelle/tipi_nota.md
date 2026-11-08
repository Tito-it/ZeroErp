{% include-markdown "it/dbzero/config/manual/tipi_nota.md" %}
# 📚 Tabella `tipi_nota`

> 📝 **Descrizione**
>
> Tipologie di nota per pratiche e flussi.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(50) | NO |  |
| codice_interno | character varying(50) | NO |  |
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
| trg_tipi_nota_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_tipi_nota_a10_note_flussi_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'note_flussi', 'tipo_nota_id', 'id', 'attivo')` |
| trg_tipi_nota_a10_note_pratiche_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'note_pratiche', 'tipo_nota_id', 'id', 'attivo')` |
| trg_tipi_nota_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_nota_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_tipi_nota_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_nota_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
