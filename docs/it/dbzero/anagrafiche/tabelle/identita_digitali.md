{% include-markdown "it/dbzero/anagrafiche/manual/identita_digitali.md" %}
# 📚 Tabella `identita_digitali`

> 📝 **Descrizione**
>
> Bridge generico soggetto_ruolo &lt;-&gt; auth_user per il modello multi-face auth. Un soggetto_ruolo puo avere piu identita nel tempo (una sola attiva); ogni auth_user e legato a una sola identita. Il ruolo_applicativo determina namespace API, scope dati e profilo capability.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| ruolo_applicativo | config.ruolo_applicativo | NO |  |
| attivo | boolean | NO | true |
| valido_dal | date | NO | script.fn_data_operativa() |
| valido_al | date | YES |  |
| invito_inviato_at | timestamp with time zone | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tecnica | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_identita_digitali_date |  |
| CHECK | chk_identita_digitali_ruolo_non_ritirato |  |
| FOREIGN KEY | fk_identita_digitali_auth_user | auth_user_id |
| FOREIGN KEY | fk_identita_digitali_soggetti_ruoli | soggetto_ruolo_id |
| PRIMARY KEY | pk_identita_digitali | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_identita_digitali | `CREATE UNIQUE INDEX pk_identita_digitali ON anagrafiche.identita_digitali USING btree (id)` |
| uq_identita_digitali_auth_user_ruolo_attivo | `CREATE UNIQUE INDEX uq_identita_digitali_auth_user_ruolo_attivo ON anagrafiche.identita_digitali USING btree (auth_user_id, ruolo_applicativo) WHERE (attivo = true)` |
| uq_identita_digitali_sr_ruolo_attivo | `CREATE UNIQUE INDEX uq_identita_digitali_sr_ruolo_attivo ON anagrafiche.identita_digitali USING btree (soggetto_ruolo_id, ruolo_applicativo) WHERE (attivo = true)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_identita_digitali_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_identita_digitali_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_identita_digitali_a10_guard_coerenza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_identita_digitali_guard_coerenza()` |
| trg_identita_digitali_a10_guard_coerenza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_identita_digitali_guard_coerenza()` |
| trg_identita_digitali_a10_guard_natura_credenziale_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_identita_digitali_guard_natura_credenziale()` |
| trg_identita_digitali_a10_guard_natura_credenziale_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_identita_digitali_guard_natura_credenziale()` |
| trg_identita_digitali_a10_guard_ultimo_super_admin_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin()` |
| trg_identita_digitali_a10_identita_scope_bindings_block_ef3f5e | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'identita_scope_bindings', 'identita_digitale_id', 'id', 'attivo')` |
| trg_identita_digitali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_identita_digitali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_identita_digitali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_identita_digitali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_identita_digitali_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('identita_digitali_id')` |
| trg_identita_digitali_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('identita_digitali_id')` |
| trg_identita_digitali_z90_sync_auth_user_active_ins | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_identita_digitali_sync_auth_user_active()` |
| trg_identita_digitali_z90_sync_auth_user_active_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_identita_digitali_sync_auth_user_active()` |

---
{% include-markdown "signature-core.md" %}
