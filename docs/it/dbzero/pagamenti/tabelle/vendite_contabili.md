{% include-markdown "it/dbzero/pagamenti/manual/vendite_contabili.md" %}
# 📚 Tabella `vendite_contabili`

> 📝 **Descrizione**
>
> Testata contabile per movimenti vendite

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| centro_riscossione_id | bigint | NO |  |
| data_contabile | date | NO |  |
| data_registrazione | date | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| ente_incasso_id | bigint | YES |  |
| stato_id | smallint | NO | 1 |
| data_conferma | timestamp with time zone | YES |  |
| user_conferma | text | YES |  |
| origine | character varying | NO | 'GENERATA'::character varying |
| importo_dichiarato | numeric | YES |  |
| contabile_corretta_id | bigint | YES |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| registro_id | bigint | YES |  |
| anno | smallint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_vendite_contabili_automatica_dichiara |  |
| CHECK | chk_vendite_contabili_corretta_non_se_stessa |  |
| CHECK | chk_vendite_contabili_generata_non_dichiara |  |
| CHECK | chk_vendite_contabili_importo_dichiarato_finito |  |
| CHECK | chk_vendite_contabili_origine |  |
| FOREIGN KEY | fk_vendite_contabili_centro_riscossione | centro_riscossione_id |
| FOREIGN KEY | fk_vendite_contabili_corretta | contabile_corretta_id |
| FOREIGN KEY | fk_vendite_contabili_emittente_sr | emittente_soggetto_ruolo_id |
| FOREIGN KEY | fk_vendite_contabili_ente_incasso | ente_incasso_id |
| FOREIGN KEY | fk_vendite_contabili_registro | registro_id |
| FOREIGN KEY | fk_vendite_contabili_stato | stato_id |
| PRIMARY KEY | pk_vendite_contabili | id |
| UNIQUE | uq_vendite_contabili_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vendite_contabili_registro_anno | `CREATE INDEX ix_vendite_contabili_registro_anno ON pagamenti.vendite_contabili USING btree (registro_id, anno)` |
| pk_vendite_contabili | `CREATE UNIQUE INDEX pk_vendite_contabili ON pagamenti.vendite_contabili USING btree (id)` |
| uq_vendite_contabili_codice | `CREATE UNIQUE INDEX uq_vendite_contabili_codice ON pagamenti.vendite_contabili USING btree (codice)` |
| uq_vendite_contabili_correzione | `CREATE UNIQUE INDEX uq_vendite_contabili_correzione ON pagamenti.vendite_contabili USING btree (contabile_corretta_id) WHERE (contabile_corretta_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_vendite_contabili_a10_centri_riscossione_require_att_2ae3a9 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'centri_riscossione', 'attivo', 'centro_riscossione_id', 'id')` |
| trg_vendite_contabili_a10_centri_riscossione_require_att_2ae3a9 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'centri_riscossione', 'attivo', 'centro_riscossione_id', 'id')` |
| trg_vendite_contabili_a10_emittente_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_emittente()` |
| trg_vendite_contabili_a10_emittente_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_emittente()` |
| trg_vendite_contabili_a10_enti_incasso_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'enti_incasso', 'attivo', 'ente_incasso_id', 'id')` |
| trg_vendite_contabili_a10_enti_incasso_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'enti_incasso', 'attivo', 'ente_incasso_id', 'id')` |
| trg_vendite_contabili_a10_gen_codice_ins | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_gen_codice()` |
| trg_vendite_contabili_a10_guard_emittente_scope_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('soggetto_ruolo', 'emittente_soggetto_ruolo_id')` |
| trg_vendite_contabili_a10_guard_emittente_scope_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_emittente_scope('soggetto_ruolo', 'emittente_soggetto_ruolo_id')` |
| trg_vendite_contabili_a10_guard_ente_centro_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_guard_ente_centro()` |
| trg_vendite_contabili_a10_guard_ente_centro_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_guard_ente_centro()` |
| trg_vendite_contabili_a10_guard_transizione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_guard_transizione()` |
| trg_vendite_contabili_a10_guard_validazione_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_guard_validazione()` |
| trg_vendite_contabili_a10_guard_verifica_chiusura_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_guard_chiusura()` |
| trg_vendite_contabili_a10_registri_fatturazione_require_eb4fe3 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_vendite_contabili_a10_registri_fatturazione_require_eb4fe3 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('vendite', 'registri_fatturazione', 'attivo', 'registro_id', 'id')` |
| trg_vendite_contabili_a10_sorgente_in_uscita_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_sorgente_in_uscita()` |
| trg_vendite_contabili_a10_vendite_contabili_stati_requir_c1cc51 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'vendite_contabili_stati', 'attivo', 'stato_id', 'id')` |
| trg_vendite_contabili_a10_vendite_contabili_stati_requir_c1cc51 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('pagamenti', 'vendite_contabili_stati', 'attivo', 'stato_id', 'id')` |
| trg_vendite_contabili_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_vendite_contabili_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_vendite_contabili_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_vendite_contabili_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_vendite_contabili_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_vendite_contabili_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
