{% include-markdown "it/dbzero/anagrafiche/manual/soggetti_ruoli.md" %}
# 📚 Tabella `soggetti_ruoli`

> 📝 **Descrizione**
>
> Relazione tra soggetti e ruoli assegnati

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_id | uuid | NO |  |
| tipo_ruolo_id | integer | NO |  |
| meta | jsonb | YES | '{}'::jsonb |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_soggetti_anagrafiche | soggetto_id |
| FOREIGN KEY | fk_tipi_ruoli_config | tipo_ruolo_id |
| PRIMARY KEY | pk_soggetti_ruoli | id |
| UNIQUE | uq_soggetto_ruolo | soggetto_id, tipo_ruolo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_soggetti_ruoli_tipo_ruolo_id | `CREATE INDEX ix_anagrafiche_soggetti_ruoli_tipo_ruolo_id ON anagrafiche.soggetti_ruoli USING btree (tipo_ruolo_id)` |
| pk_soggetti_ruoli | `CREATE UNIQUE INDEX pk_soggetti_ruoli ON anagrafiche.soggetti_ruoli USING btree (id)` |
| uq_soggetto_ruolo | `CREATE UNIQUE INDEX uq_soggetto_ruolo ON anagrafiche.soggetti_ruoli USING btree (soggetto_id, tipo_ruolo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soggetti_ruoli_a10_guard_natura_ammessa_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa()` |
| trg_soggetti_ruoli_a10_guard_natura_ammessa_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa()` |
| trg_soggetti_ruoli_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('soggetto_id', 'E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE')` |
| trg_soggetti_ruoli_a10_soggetti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_soggetti_ruoli_a10_soggetti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id', 'id')` |
| trg_soggetti_ruoli_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_soggetti_ruoli_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_soggetti_ruoli_def_guard_indirizzi_required_aft_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required()` |
| trg_soggetti_ruoli_def_guard_indirizzi_required_aft_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required()` |
| trg_soggetti_ruoli_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_ruoli_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
