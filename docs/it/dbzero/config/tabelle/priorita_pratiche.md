{% include-markdown "it/dbzero/config/manual/priorita_pratiche.md" %}
# 📚 Tabella `priorita_pratiche`

> 📝 **Descrizione**
>
> Livelli di priorita' delle pratiche con ordinamento.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(50) | NO |  |
| codice_interno | character varying(50) | NO |  |
| descrizione | text | NO |  |
| sequenza | integer | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_priorita_pratiche | id |
| UNIQUE | uq_priorita_pratiche_codice | codice |
| UNIQUE | uq_priorita_pratiche_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_priorita_pratiche | `CREATE UNIQUE INDEX pk_priorita_pratiche ON config.priorita_pratiche USING btree (id)` |
| uq_priorita_pratiche_codice | `CREATE UNIQUE INDEX uq_priorita_pratiche_codice ON config.priorita_pratiche USING btree (codice)` |
| uq_priorita_pratiche_codice_interno | `CREATE UNIQUE INDEX uq_priorita_pratiche_codice_interno ON config.priorita_pratiche USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_priorita_pratiche_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_priorita_pratiche_a10_pratiche_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('pratiche', 'pratiche', 'priorita_id', 'id', 'attivo')` |
| trg_priorita_pratiche_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_priorita_pratiche_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_priorita_pratiche_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_priorita_pratiche_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
