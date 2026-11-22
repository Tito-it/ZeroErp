{% include-markdown "it/dbzero/config/manual/azioni_processo.md" %}
# 📚 Tabella `azioni_processo`

> 📝 **Descrizione**
>
> Registro azioni di processo gestibili nell'interfaccia permessi.
>  permission_codename e' la chiave tecnica immutabile (riferimento
>  al codename in django.auth_permission).
>  Il flag pericolosa segnala azioni che richiedono conferma aggiuntiva.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| area_id | integer | NO |  |
| permission_codename | character varying(100) | NO |  |
| descrizione | character varying(200) | NO |  |
| pericolosa | boolean | NO | false |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| livello_minimo_area | config.livello_accesso | NO | 'TUTTO'::config.livello_accesso |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_azioni_processo_livello_minimo_area |  |
| FOREIGN KEY | fk_azioni_processo_aree_funzionali | area_id |
| PRIMARY KEY | pk_azioni_processo | id |
| UNIQUE | uq_azioni_processo_id_area | id, area_id |
| UNIQUE | uq_azioni_processo_permission_codename | permission_codename |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_azioni_processo_area_id | `CREATE INDEX ix_azioni_processo_area_id ON config.azioni_processo USING btree (area_id)` |
| pk_azioni_processo | `CREATE UNIQUE INDEX pk_azioni_processo ON config.azioni_processo USING btree (id)` |
| uq_azioni_processo_id_area | `CREATE UNIQUE INDEX uq_azioni_processo_id_area ON config.azioni_processo USING btree (id, area_id)` |
| uq_azioni_processo_permission_codename | `CREATE UNIQUE INDEX uq_azioni_processo_permission_codename ON config.azioni_processo USING btree (permission_codename)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_azioni_processo_a10_aree_funzionali_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id', 'id')` |
| trg_azioni_processo_a10_aree_funzionali_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id', 'id')` |
| trg_azioni_processo_a10_profili_accesso_azioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'profili_accesso_azioni', 'azione_id', 'id', 'attivo')` |
| trg_azioni_processo_a10_stati_doc_fiscale_transizioni_bl_8bc4e2 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'stati_doc_fiscale_transizioni', 'azione_processo_codename', 'permission_codename', 'attivo')` |
| trg_azioni_processo_a10_stati_doc_offerte_transizioni_bl_848c75 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'stati_doc_offerte_transizioni', 'azione_processo_codename', 'permission_codename', 'attivo')` |
| trg_azioni_processo_a10_transizioni_stati_commessa_block_711b6c | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'transizioni_stati_commessa', 'azione_processo_codename', 'permission_codename', 'attivo')` |
| trg_azioni_processo_a10_transizioni_stati_contratti_bloc_5e7d14 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_contratti', 'azione_processo_codename', 'permission_codename', 'attivo')` |
| trg_azioni_processo_a10_transizioni_stati_ddt_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_ddt', 'azione_processo_codename', 'permission_codename', 'attivo')` |
| trg_azioni_processo_a10_transizioni_stati_listino_versio_b0ef73 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_listino_versioni', 'azione_processo_codename', 'permission_codename', 'attivo')` |
| trg_azioni_processo_a10_transizioni_stati_ordini_block_d_5bfc98 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_ordini', 'azione_processo_codename', 'permission_codename', 'attivo')` |
| trg_azioni_processo_a10_transizioni_stati_preventivi_blo_69cb17 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_preventivi', 'azione_processo_codename', 'permission_codename', 'attivo')` |
| trg_azioni_processo_a10_transizioni_stati_reso_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'transizioni_stati_reso', 'azione_processo_codename', 'permission_codename', 'attivo')` |
| trg_azioni_processo_a10_user_override_azioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'user_override_azioni', 'azione_id', 'id', 'attivo')` |
| trg_azioni_processo_a10_widget_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('ui', 'widget', 'azione_id', 'id', 'attivo')` |
| trg_azioni_processo_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_azioni_processo_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_azioni_processo_z90_notify_permessi_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |
| trg_azioni_processo_z90_notify_permessi_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |
| trg_azioni_processo_z90_notify_permessi_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |

---
{% include-markdown "signature-core.md" %}
