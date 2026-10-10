{% include-markdown "it/dbzero/config/manual/profili_accesso_bindings.md" %}
# 📚 Tabella `profili_accesso_bindings`

> 📝 **Descrizione**
>
> Associa un profilo di accesso a UNA entita di dominio (reparto / identita / ruolo applicativo). CHECK xor +3 indici parziali UNIQUE garantiscono esattamente un binding per entita. La coerenza tipo_profilo &lt;-&gt; tipo_binding e' delegata al guard trgfn_profili_accesso_bindings_guard_coerenza.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| profilo_accesso_id | integer | NO |  |
| unita_organizzativa_id | integer | YES |  |
| identita_digitale_id | bigint | YES |  |
| ruolo_applicativo | config.ruolo_applicativo | YES |  |
| attivo | boolean | NO | true |
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
| CHECK | chk_profili_accesso_bindings_xor |  |
| FOREIGN KEY | fk_profili_accesso_bindings_identita | identita_digitale_id |
| FOREIGN KEY | fk_profili_accesso_bindings_profilo | profilo_accesso_id |
| FOREIGN KEY | fk_profili_accesso_bindings_uo | unita_organizzativa_id |
| PRIMARY KEY | pk_profili_accesso_bindings | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_profili_accesso_bindings | `CREATE UNIQUE INDEX pk_profili_accesso_bindings ON config.profili_accesso_bindings USING btree (id)` |
| uq_profili_accesso_bindings_identita | `CREATE UNIQUE INDEX uq_profili_accesso_bindings_identita ON config.profili_accesso_bindings USING btree (identita_digitale_id) WHERE (identita_digitale_id IS NOT NULL)` |
| uq_profili_accesso_bindings_ruolo | `CREATE UNIQUE INDEX uq_profili_accesso_bindings_ruolo ON config.profili_accesso_bindings USING btree (ruolo_applicativo) WHERE (ruolo_applicativo IS NOT NULL)` |
| uq_profili_accesso_bindings_uo | `CREATE UNIQUE INDEX uq_profili_accesso_bindings_uo ON config.profili_accesso_bindings USING btree (unita_organizzativa_id) WHERE (unita_organizzativa_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_profili_accesso_bindings_a10_guard_coerenza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_profili_accesso_bindings_guard_coerenza()` |
| trg_profili_accesso_bindings_a10_guard_coerenza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_profili_accesso_bindings_guard_coerenza()` |
| trg_profili_accesso_bindings_a10_guard_ultimo_super_admin_upd_d | AFTER | UPDATE | `EXECUTE FUNCTION config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin()` |
| trg_profili_accesso_bindings_a10_guard_ultimo_super_admin_upd_d | AFTER | DELETE | `EXECUTE FUNCTION config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin()` |
| trg_profili_accesso_bindings_a10_profili_accesso_require_2ec6bd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'profili_accesso', 'attivo', 'profilo_accesso_id', 'id')` |
| trg_profili_accesso_bindings_a10_profili_accesso_require_2ec6bd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'profili_accesso', 'attivo', 'profilo_accesso_id', 'id')` |
| trg_profili_accesso_bindings_a10_unita_organizzative_req_b93e21 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_profili_accesso_bindings_a10_unita_organizzative_req_b93e21 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id', 'id')` |
| trg_profili_accesso_bindings_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_profili_accesso_bindings_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_profili_accesso_bindings_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_profili_accesso_bindings_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_profili_accesso_bindings_z90_notify_permessi_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |
| trg_profili_accesso_bindings_z90_notify_permessi_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |
| trg_profili_accesso_bindings_z90_notify_permessi_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION script.trgfn_notify_permessi_catalogo()` |
| trg_profili_accesso_bindings_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('profili_accesso_bindings_id')` |
| trg_profili_accesso_bindings_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('profili_accesso_bindings_id')` |

---
{% include-markdown "signature-core.md" %}
