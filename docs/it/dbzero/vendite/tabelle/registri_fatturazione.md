{% include-markdown "it/dbzero/vendite/manual/registri_fatturazione.md" %}
# 📚 Tabella `registri_fatturazione`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| uid | uuid | NO | uuidv7() |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| emittente_soggetto_ruolo_id | bigint | YES |  |
| serie_default | character varying | YES |  |
| reset_policy | character varying | NO | 'ANNUALE'::character varying |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |
| utility_id | integer | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_registri_fatturazione_reset |  |
| FOREIGN KEY | fk_registri_fatturazione_emitt | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_registri_fatturazione_utility | utility_id |
| PRIMARY KEY | pk_regfatt | id |
| UNIQUE | uq_registri_fatturazione_codice | codice |
| UNIQUE | uq_registri_fatturazione_uid | uid |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_regfatt | `CREATE UNIQUE INDEX pk_regfatt ON vendite.registri_fatturazione USING btree (id)` |
| uq_registri_fatturazione_codice | `CREATE UNIQUE INDEX uq_registri_fatturazione_codice ON vendite.registri_fatturazione USING btree (codice)` |
| uq_registri_fatturazione_uid | `CREATE UNIQUE INDEX uq_registri_fatturazione_uid ON vendite.registri_fatturazione USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_registri_fatturazione_a10_fatture_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'fatture', 'registro_id', 'id', 'attivo')` |
| trg_registri_fatturazione_a10_registri_fatturazione_prog_17cdc5 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'registri_fatturazione_progressivi', 'registro_id', 'id', 'attivo')` |
| trg_registri_fatturazione_a10_tipi_doc_fiscale_registri__d1c865 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('vendite', 'tipi_doc_fiscale_registri', 'registro_id', 'id', 'attivo')` |
| trg_registri_fatturazione_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_registri_fatturazione_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_registri_fatturazione_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_registri_fatturazione_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_registri_fatturazione_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('registri_fatturazione_id')` |
| trg_registri_fatturazione_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('registri_fatturazione_id')` |

---
{% include-markdown "signature-core.md" %}
