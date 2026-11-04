{% include-markdown "it/dbzero/config/manual/scope_policy.md" %}
# 📚 Tabella `scope_policy`

> 📝 **Descrizione**
>
> Registro delle policy di scope usate dal modello multi-face auth. funzione_db = schema.nome della funzione (firma fissa: p_identita_id BIGINT, p_target_id BIGINT) RETURNS BOOLEAN. L'associazione identita &lt;-&gt; policy e' in config.identita_scope_bindings.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(60) | NO |  |
| descrizione | text | NO |  |
| funzione_db | character varying(150) | NO |  |
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
| PRIMARY KEY | pk_scope_policy | id |
| UNIQUE | uq_scope_policy_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_scope_policy | `CREATE UNIQUE INDEX pk_scope_policy ON config.scope_policy USING btree (id)` |
| uq_scope_policy_codice | `CREATE UNIQUE INDEX uq_scope_policy_codice ON config.scope_policy USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_scope_policy_a10_identita_scope_bindings_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'identita_scope_bindings', 'scope_policy_id', 'id', 'attivo')` |
| trg_scope_policy_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_scope_policy_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_scope_policy_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_scope_policy_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_scope_policy_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_scope_policy_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_scope_policy_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('scope_policy_id')` |
| trg_scope_policy_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('scope_policy_id')` |

---
{% include-markdown "signature-core.md" %}
