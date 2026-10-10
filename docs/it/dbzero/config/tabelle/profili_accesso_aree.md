{% include-markdown "it/dbzero/config/manual/profili_accesso_aree.md" %}
# 📚 Tabella `profili_accesso_aree`

> 📝 **Descrizione**
>
> Dettaglio delle aree funzionali coperte da un profilo di accesso con il rispettivo livello. Rimpiazza concettualmente profili_reparto_aree generalizzando il padre da reparto a profilo.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| profilo_accesso_id | integer | NO |  |
| area_id | integer | NO |  |
| livello | config.livello_accesso | NO | 'BLOCCATO'::config.livello_accesso |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_profili_accesso_aree_area | area_id |
| FOREIGN KEY | fk_profili_accesso_aree_profilo | profilo_accesso_id |
| PRIMARY KEY | pk_profili_accesso_aree | id |
| UNIQUE | uq_profili_accesso_aree_profilo_area | profilo_accesso_id, area_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_profili_accesso_aree | `CREATE UNIQUE INDEX pk_profili_accesso_aree ON config.profili_accesso_aree USING btree (id)` |
| uq_profili_accesso_aree_profilo_area | `CREATE UNIQUE INDEX uq_profili_accesso_aree_profilo_area ON config.profili_accesso_aree USING btree (profilo_accesso_id, area_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_profili_accesso_aree_a10_aree_funzionali_require_att_e70a78 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id', 'id')` |
| trg_profili_accesso_aree_a10_aree_funzionali_require_att_e70a78 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id', 'id')` |
| trg_profili_accesso_aree_a10_profili_accesso_require_att_eae6ec | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'profili_accesso', 'attivo', 'profilo_accesso_id', 'id')` |
| trg_profili_accesso_aree_a10_profili_accesso_require_att_eae6ec | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'profili_accesso', 'attivo', 'profilo_accesso_id', 'id')` |
| trg_profili_accesso_aree_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_profili_accesso_aree_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_profili_accesso_aree_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_profili_accesso_aree_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_profili_accesso_aree_z90_notify_permessi_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |
| trg_profili_accesso_aree_z90_notify_permessi_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |
| trg_profili_accesso_aree_z90_notify_permessi_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |
| trg_profili_accesso_aree_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('profili_accesso_aree_id')` |
| trg_profili_accesso_aree_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('profili_accesso_aree_id')` |

---
{% include-markdown "signature-core.md" %}
