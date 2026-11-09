{% include-markdown "it/dbzero/vendite/manual/tipi_doc_fiscale_registri.md" %}
# 📚 Tabella `tipi_doc_fiscale_registri`

> 📝 **Descrizione**
>
> Mapping (tipo documento fiscale, natura del documento) -&gt; (registro di numerazione, serie). Risolto da vendite.fn_get_registro_id, che applica un fallback a quattro livelli su utility ed emittente. rev 2026-08-18 (brief-design-note-credito-resi N2): la natura e' entrata nella chiave, e la UNIQUE con lei — senza, mappare fattura e nota di credito sullo STESSO registro con due serie diverse sarebbe stato vietato da un vincolo che non sapeva della natura.

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
| natura_doc_id | bigint | NO | config.fn_get_natura_doc_fiscale_id('FATTURA'::character varying) |
| serie | character varying(8) | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_tipi_doc_fiscale_registri_natura_doc | natura_doc_id |
| FOREIGN KEY | fk_tipi_doc_fiscale_registri_registro | registro_id |
| FOREIGN KEY | fk_tipi_doc_fiscale_registri_tipo_doc | tipo_doc_fiscale_id |
| PRIMARY KEY | pk_tipi_doc_fiscale_registri | id |
| UNIQUE | uq_tipi_doc_fiscale_registri_tipo_doc_natura_registro | tipo_doc_fiscale_id, natura_doc_id, registro_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_tipi_doc_fiscale_registri | `CREATE UNIQUE INDEX pk_tipi_doc_fiscale_registri ON vendite.tipi_doc_fiscale_registri USING btree (id)` |
| uq_tipi_doc_fiscale_registri_tipo_doc_natura_registro | `CREATE UNIQUE INDEX uq_tipi_doc_fiscale_registri_tipo_doc_natura_registro ON vendite.tipi_doc_fiscale_registri USING btree (tipo_doc_fiscale_id, natura_doc_id, registro_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_doc_fiscale_registri_a10_guard_coppia_unica_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_tipi_doc_fiscale_registri_guard_coppia_unica()` |
| trg_tipi_doc_fiscale_registri_a10_guard_coppia_unica_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_tipi_doc_fiscale_registri_guard_coppia_unica()` |
| trg_tipi_doc_fiscale_registri_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_tipi_doc_fiscale_registri_a10_nature_doc_fiscale_req_e1197d | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_doc_fiscale', 'attivo', 'natura_doc_id', 'id')` |
| trg_tipi_doc_fiscale_registri_a10_nature_doc_fiscale_req_e1197d | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'nature_doc_fiscale', 'attivo', 'natura_doc_id', 'id')` |
| trg_tipi_doc_fiscale_registri_a10_registri_fatturazione_3f401f | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_tipi_doc_fiscale_registri_a10_registri_fatturazione_3f401f | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_tipi_doc_fiscale_registri_a10_tipi_doc_fiscale_requi_f3dd83 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_tipi_doc_fiscale_registri_a10_tipi_doc_fiscale_requi_f3dd83 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_doc_fiscale', 'attivo', 'tipo_doc_fiscale_id', 'id')` |
| trg_tipi_doc_fiscale_registri_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_doc_fiscale_registri_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}
