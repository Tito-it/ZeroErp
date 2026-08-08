{% include-markdown "it/dbzero/vendite/manual/tipi_doc_fiscale_registri.md" %}
# 📚 Tabella `tipi_doc_fiscale_registri`

> 📝 **Descrizione**
>
> Associazione tipo documento fiscale -&gt; registro di fatturazione.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| tipo_doc_fiscale_id | bigint | NO |  |
| registro_id | bigint | NO |  |
| codice_interno | text | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_tipi_doc_fiscale_registri_registro | registro_id |
| FOREIGN KEY | fk_tipi_doc_fiscale_registri_tipo_doc | tipo_doc_fiscale_id |
| PRIMARY KEY | pk_tipi_doc_fiscale_registri | id |
| UNIQUE | uq_tipi_doc_fiscale_registri_tipo_doc_registro | tipo_doc_fiscale_id, registro_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_doc_fiscale_registri | `CREATE UNIQUE INDEX pk_tipi_doc_fiscale_registri ON vendite.tipi_doc_fiscale_registri USING btree (id)` |
| uq_tipi_doc_fiscale_registri_tipo_doc_registro | `CREATE UNIQUE INDEX uq_tipi_doc_fiscale_registri_tipo_doc_registro ON vendite.tipi_doc_fiscale_registri USING btree (tipo_doc_fiscale_id, registro_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_doc_fiscale_registri_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_tipi_doc_fiscale_registri_a10_registri_fatturazione__3f401f | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_tipi_doc_fiscale_registri_a10_registri_fatturazione__3f401f | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_tipi_doc_fiscale_registri_a10_tipi_doc_fiscale_requi_f3dd83 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_tipi_doc_fiscale_registri_a10_tipi_doc_fiscale_requi_f3dd83 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_tipi_doc_fiscale_registri_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_doc_fiscale_registri_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
