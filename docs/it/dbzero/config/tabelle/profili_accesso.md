{% include-markdown "it/dbzero/config/manual/profili_accesso.md" %}
# 📚 Tabella `profili_accesso`

> 📝 **Descrizione**
>
> Header di un profilo di accesso (§4.3 WIP multi-face-auth). Raggruppa le capability per area (profili_accesso_aree) e per azione (profili_accesso_azioni). Assegnato a reparti, ruoli applicativi o identita tramite profili_accesso_bindings.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| tipo | config.tipo_profilo_accesso | NO |  |
| codice | character varying(100) | NO |  |
| descrizione | text | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| richiede_secondo_fattore | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_profili_accesso_super_admin_secondo_fattore |  |
| PRIMARY KEY | pk_profili_accesso | id |
| UNIQUE | uq_profili_accesso_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_profili_accesso | `CREATE UNIQUE INDEX pk_profili_accesso ON config.profili_accesso USING btree (id)` |
| uq_profili_accesso_codice | `CREATE UNIQUE INDEX uq_profili_accesso_codice ON config.profili_accesso USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_profili_accesso_a10_profili_accesso_aree_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'profili_accesso_aree', 'profilo_accesso_id', 'id', 'attivo')` |
| trg_profili_accesso_a10_profili_accesso_azioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'profili_accesso_azioni', 'profilo_accesso_id', 'id', 'attivo')` |
| trg_profili_accesso_a10_profili_accesso_bindings_block_d_3be0cf | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'profili_accesso_bindings', 'profilo_accesso_id', 'id', 'attivo')` |
| trg_profili_accesso_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_profili_accesso_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_profili_accesso_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_profili_accesso_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_profili_accesso_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_profili_accesso_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_profili_accesso_z90_notify_permessi_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |
| trg_profili_accesso_z90_notify_permessi_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |
| trg_profili_accesso_z90_notify_permessi_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |
| trg_profili_accesso_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('profili_accesso_id')` |
| trg_profili_accesso_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('profili_accesso_id')` |

---
{% include-markdown "signature-core.md" %}
