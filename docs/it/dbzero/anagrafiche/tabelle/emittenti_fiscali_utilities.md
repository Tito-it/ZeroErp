{% include-markdown "it/dbzero/anagrafiche/manual/emittenti_fiscali_utilities.md" %}
# 📚 Tabella `emittenti_fiscali_utilities`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| utility_id | bigint | NO |  |
| minimo_soglia_min | numeric | YES |  |
| minimo_soglia_max | numeric | YES |  |
| arrotondamento_importi_dec | smallint | NO |  |
| metodo_arrotondamento_importi | character varying | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_emittenti_fiscali_utilities_arrotondamento_dec |  |
| CHECK | chk_emittenti_fiscali_utilities_metodo_arrotondamento |  |
| CHECK | chk_emittenti_fiscali_utilities_soglie |  |
| FOREIGN KEY | fk_emittenti_fiscali_utilities_emittente | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_emittenti_fiscali_utilities_utility | utility_id |
| PRIMARY KEY | pk_emittenti_fiscali_utilities | id |
| UNIQUE | uq_emittenti_fiscali_utilities_emittente_utility | emittente_soggetto_ruolo_id, utility_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_emittenti_fiscali_utilities | `CREATE UNIQUE INDEX pk_emittenti_fiscali_utilities ON anagrafiche.emittenti_fiscali_utilities USING btree (id)` |
| uq_emittenti_fiscali_utilities_emittente_utility | `CREATE UNIQUE INDEX uq_emittenti_fiscali_utilities_emittente_utility ON anagrafiche.emittenti_fiscali_utilities USING btree (emittente_soggetto_ruolo_id, utility_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_emittenti_fiscali_utilities_a10_emittenti_fiscali_re_62dfda | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_soggetto_ruolo_id')` |
| trg_emittenti_fiscali_utilities_a10_emittenti_fiscali_re_62dfda | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'emittenti_fiscali', 'attivo', 'emittente_soggetto_ruolo_id')` |
| trg_emittenti_fiscali_utilities_a10_guard_utility_tipo_r_cd07ac | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_utility_tipo_ruolo_by_cols('utility_id', 'emittente_soggetto_ruolo_id')` |
| trg_emittenti_fiscali_utilities_a10_guard_utility_tipo_r_cd07ac | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_utility_tipo_ruolo_by_cols('utility_id', 'emittente_soggetto_ruolo_id')` |
| trg_emittenti_fiscali_utilities_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_emittenti_fiscali_utilities_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_emittenti_fiscali_utilities_def_guard_required_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_utilities_required()` |
| trg_emittenti_fiscali_utilities_def_guard_required_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_utilities_required()` |
| trg_emittenti_fiscali_utilities_def_guard_required_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_guard_utilities_required()` |

---
{% include-markdown "signature-core.md" %}
