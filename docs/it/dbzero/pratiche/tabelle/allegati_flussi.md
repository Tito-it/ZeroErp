{% include-markdown "it/dbzero/pratiche/manual/allegati_flussi.md" %}
# 📚 Tabella `allegati_flussi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| flusso_id | bigint | NO |  |
| tipo_allegato_id | integer | NO |  |
| nome_file | text | NO |  |
| percorso | text | NO |  |
| mime_type | character varying | YES |  |
| dimensione | bigint | YES |  |
| allegato_padre_id | bigint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_allegati_flussi_allegato_padre | allegato_padre_id |
| FOREIGN KEY | fk_allegati_flussi_flusso | flusso_id |
| FOREIGN KEY | fk_allegati_flussi_tipo_allegato | tipo_allegato_id |
| PRIMARY KEY | pk_pratiche_allegati_flussi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_allegati_flussi | `CREATE UNIQUE INDEX pk_pratiche_allegati_flussi ON pratiche.allegati_flussi USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_allegati_flussi_a10_tipi_allegato_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_allegato', 'attivo', 'tipo_allegato_id', 'id')` |
| trg_allegati_flussi_a10_tipi_allegato_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'tipi_allegato', 'attivo', 'tipo_allegato_id', 'id')` |
| trg_allegati_flussi_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_allegati_flussi_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_allegati_flussi_z90_giornale_ins | AFTER | INSERT | `EXECUTE FUNCTION pratiche.trgfn_allegati_flussi_giornale()` |

---
{% include-markdown "signature-core.md" %}
