{% include-markdown "it/dbzero/vendite/manual/contratti.md" %}
# 📚 Tabella `contratti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| numero | character varying | NO |  |
| billing_account_id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| utility_id | integer | NO |  |
| ambito | character varying | YES | 'COMMODITY'::character varying |
| valido_dal | date | NO | CURRENT_DATE |
| valido_al | date | YES |  |
| parent_contratto_id | bigint | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| stato_doc_contratto_id | bigint | NO |  |
| data | date | NO | CURRENT_DATE |
| uid | uuid | NO | uuidv7() |
| validita | daterange | NO |  |
| listino_id | bigint | YES |  |
| tipo_variazione_globale | character varying | YES |  |
| valore_variazione_globale | numeric | YES |  |
| categoria_cliente_id_snapshot | smallint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_contratti_modalita_pricing |  |
| CHECK | chk_contratti_tipo_variazione_globale |  |
| CHECK | chk_contratti_validita |  |
| CHECK | chk_contratti_variazione_globale_coerente |  |
| FOREIGN KEY | fk_contratti_billing_account | billing_account_id |
| FOREIGN KEY | fk_contratti_categoria_cliente_snapshot | categoria_cliente_id_snapshot |
| FOREIGN KEY | fk_contratti_istanza | istanza_utility_id |
| FOREIGN KEY | fk_contratti_listino | listino_id |
| FOREIGN KEY | fk_contratti_parent | parent_contratto_id |
| FOREIGN KEY | fk_contratti_utility | utility_id |
| FOREIGN KEY | fk_v_contratti_stato_ddt | stato_doc_contratto_id |
| PRIMARY KEY | pk_contratti | id |
| UNIQUE | uq_contratti_numero | numero |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_contratti_no_overlap | `CREATE INDEX ex_contratti_no_overlap ON vendite.contratti USING gist (billing_account_id, istanza_utility_id, utility_id, ambito, validita)` |
| ix_contratti_ambito | `CREATE INDEX ix_contratti_ambito ON vendite.contratti USING btree (ambito)` |
| ix_contratti_ba_istanza | `CREATE INDEX ix_contratti_ba_istanza ON vendite.contratti USING btree (billing_account_id, istanza_utility_id)` |
| ix_contratti_categoria_cliente_snapshot | `CREATE INDEX ix_contratti_categoria_cliente_snapshot ON vendite.contratti USING btree (categoria_cliente_id_snapshot)` |
| pk_contratti | `CREATE UNIQUE INDEX pk_contratti ON vendite.contratti USING btree (id)` |
| uq_contratti_numero | `CREATE UNIQUE INDEX uq_contratti_numero ON vendite.contratti USING btree (numero)` |
| uq_contratti_uid | `CREATE UNIQUE INDEX uq_contratti_uid ON vendite.contratti USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_contratti_a10_gen_codice_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_contratti_gen_codice()` |
| trg_contratti_a10_gen_codice_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_contratti_gen_codice()` |
| trg_contratti_a10_guard_modalita_c_activation_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_contratti_guard_modalita_c_activation()` |
| trg_contratti_a10_guard_modalita_c_activation_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_contratti_guard_modalita_c_activation()` |
| trg_contratti_a10_listini_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id', 'id')` |
| trg_contratti_a10_listini_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'listini', 'attivo', 'listino_id', 'id')` |
| trg_contratti_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('numero', 'CODICE_NON_MODIFICABILE')` |
| trg_contratti_a10_set_categoria_cliente_snapshot_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_contratti_set_categoria_cliente_snapshot()` |
| trg_contratti_a10_set_categoria_cliente_snapshot_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_contratti_set_categoria_cliente_snapshot()` |
| trg_contratti_a10_stati_doc_contratti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_contratti', 'attivo', 'stato_doc_contratto_id', 'id')` |
| trg_contratti_a10_stati_doc_contratti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'stati_doc_contratti', 'attivo', 'stato_doc_contratto_id', 'id')` |
| trg_contratti_a20_set_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_set_validita()` |
| trg_contratti_a20_set_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_set_validita()` |
| trg_contratti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_contratti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_contratti_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_contratti_normalize()` |
| trg_contratti_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_contratti_normalize()` |
| trg_contratti_z90_snapshot_precontrattuali_ins | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_contratti_snapshot_precontrattuali()` |
| trg_contratti_z90_sync_canali_ins | AFTER | INSERT | `EXECUTE FUNCTION vendite.trgfn_documenti_sync_canali()` |

---
{% include-markdown "signature-core.md" %}
