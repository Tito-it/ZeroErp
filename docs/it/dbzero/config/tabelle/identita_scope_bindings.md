{% include-markdown "it/dbzero/config/manual/identita_scope_bindings.md" %}
# 📚 Tabella `identita_scope_bindings`

> 📝 **Descrizione**
>
> Binding identita_digitale &lt;-&gt; scope_policy (§4.4 WIP multi-face-auth). Un'identita puo avere piu policy concorrenti. UNIQUE garantisce una sola riga per coppia (identita, policy). La logica di risoluzione e' nelle funzioni script.fn_scope_* puntate da scope_policy.funzione_db.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| identita_digitale_id | bigint | NO |  |
| scope_policy_id | integer | NO |  |
| parametri | jsonb | NO | '{}'::jsonb |
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
| FOREIGN KEY | fk_identita_scope_bindings_identita | identita_digitale_id |
| FOREIGN KEY | fk_identita_scope_bindings_policy | scope_policy_id |
| PRIMARY KEY | pk_identita_scope_bindings | id |
| UNIQUE | uq_identita_scope_bindings_identita_policy | identita_digitale_id, scope_policy_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_identita_scope_bindings | `CREATE UNIQUE INDEX pk_identita_scope_bindings ON config.identita_scope_bindings USING btree (id)` |
| uq_identita_scope_bindings_identita_policy | `CREATE UNIQUE INDEX uq_identita_scope_bindings_identita_policy ON config.identita_scope_bindings USING btree (identita_digitale_id, scope_policy_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_identita_scope_bindings_a10_identita_digitali_requir_23cc8c | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'identita_digitali', 'attivo', 'identita_digitale_id', 'id')` |
| trg_identita_scope_bindings_a10_identita_digitali_requir_23cc8c | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'identita_digitali', 'attivo', 'identita_digitale_id', 'id')` |
| trg_identita_scope_bindings_a10_scope_policy_require_att_bf4c7c | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'scope_policy', 'attivo', 'scope_policy_id', 'id')` |
| trg_identita_scope_bindings_a10_scope_policy_require_att_bf4c7c | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'scope_policy', 'attivo', 'scope_policy_id', 'id')` |
| trg_identita_scope_bindings_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_identita_scope_bindings_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_identita_scope_bindings_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_identita_scope_bindings_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_identita_scope_bindings_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('identita_scope_bindings_id')` |
| trg_identita_scope_bindings_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('identita_scope_bindings_id')` |

---
{% include-markdown "signature-core.md" %}
