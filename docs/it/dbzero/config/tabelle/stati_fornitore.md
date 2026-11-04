{% include-markdown "it/dbzero/config/manual/stati_fornitore.md" %}
# 📚 Tabella `stati_fornitore`

> 📝 **Descrizione**
>
> Stati operativi dei fornitori. blocca_ordini impedisce nuovi ordini/DDT.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(10) | NO |  |
| codice_interno | character varying(10) | NO |  |
| descrizione | character varying(100) | NO | ''::character varying |
| descrizione_breve | character varying(20) | NO |  |
| attivo | boolean | NO | true |
| blocca_ordini | boolean | NO | false |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_fornitore | id |
| UNIQUE | uq_stati_fornitore_codice | codice |
| UNIQUE | uq_stati_fornitore_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_stati_fornitore | `CREATE UNIQUE INDEX pk_stati_fornitore ON config.stati_fornitore USING btree (id)` |
| uq_stati_fornitore_codice | `CREATE UNIQUE INDEX uq_stati_fornitore_codice ON config.stati_fornitore USING btree (codice)` |
| uq_stati_fornitore_codice_interno | `CREATE UNIQUE INDEX uq_stati_fornitore_codice_interno ON config.stati_fornitore USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_fornitore_a10_fornitori_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'fornitori', 'stato_fornitore_id', 'id', 'attivo')` |
| trg_stati_fornitore_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_stati_fornitore_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_fornitore_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_stati_fornitore_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_fornitore_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
