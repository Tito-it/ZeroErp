{% include-markdown "it/dbzero/anagrafiche/manual/soggetti_ruoli_conti_bancari.md" %}
# 📚 Tabella `soggetti_ruoli_conti_bancari`

> 📝 **Descrizione**
>
> Associazione conti bancari a livello RUOLO (override).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
| conto_bancario_id | bigint | NO |  |
| uso | character varying(16) | NO | 'GENERICO'::character varying |
| predefinito | boolean | NO | false |
| valido_dal | date | YES |  |
| valido_al | date | YES |  |
| intestazione_dichiarata | character varying(140) | YES |  |
| verificato | boolean | NO | false |
| bloccato | boolean | NO | false |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| istanza_utility_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_soggetti_ruoli_conti_bancari_uso |  |
| CHECK | chk_soggetti_ruoli_conti_bancari_validita |  |
| FOREIGN KEY | fk_soggetti_ruoli_conti_bancari_conti_bancari | conto_bancario_id |
| FOREIGN KEY | fk_soggetti_ruoli_conti_bancari_soggetti_ruoli | soggetto_ruolo_id |
| FOREIGN KEY | fk_src_bancari_istanze_utilities | istanza_utility_id |
| PRIMARY KEY | pk_soggetti_ruoli_conti_bancari | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_src_bancari_conto_incasso_un_solo_soggetto | `CREATE INDEX ex_src_bancari_conto_incasso_un_solo_soggetto ON anagrafiche.soggetti_ruoli_conti_bancari USING gist (conto_bancario_id, soggetto_ruolo_id) WHERE ((uso)::text = 'INCASSO'::text)` |
| ix_anagrafiche_soggetti_ruoli_conti_bancari_conto_bancario_id | `CREATE INDEX ix_anagrafiche_soggetti_ruoli_conti_bancari_conto_bancario_id ON anagrafiche.soggetti_ruoli_conti_bancari USING btree (conto_bancario_id)` |
| ix_anagrafiche_soggetti_ruoli_conti_bancari_soggetto_ruolo_id | `CREATE INDEX ix_anagrafiche_soggetti_ruoli_conti_bancari_soggetto_ruolo_id ON anagrafiche.soggetti_ruoli_conti_bancari USING btree (soggetto_ruolo_id)` |
| ix_src_bancari_istanza_utility_id | `CREATE INDEX ix_src_bancari_istanza_utility_id ON anagrafiche.soggetti_ruoli_conti_bancari USING btree (istanza_utility_id)` |
| pk_soggetti_ruoli_conti_bancari | `CREATE UNIQUE INDEX pk_soggetti_ruoli_conti_bancari ON anagrafiche.soggetti_ruoli_conti_bancari USING btree (id)` |
| uq_src_bancari_predefinito_istanza | `CREATE UNIQUE INDEX uq_src_bancari_predefinito_istanza ON anagrafiche.soggetti_ruoli_conti_bancari USING btree (soggetto_ruolo_id, istanza_utility_id, uso) WHERE ((predefinito = true) AND (istanza_utility_id IS NOT NULL))` |
| uq_src_bancari_predefinito_no_istanza | `CREATE UNIQUE INDEX uq_src_bancari_predefinito_no_istanza ON anagrafiche.soggetti_ruoli_conti_bancari USING btree (soggetto_ruolo_id, uso) WHERE ((predefinito = true) AND (istanza_utility_id IS NULL))` |
| uq_src_bancari_ruolo_conto_uso_no_istanza | `CREATE UNIQUE INDEX uq_src_bancari_ruolo_conto_uso_no_istanza ON anagrafiche.soggetti_ruoli_conti_bancari USING btree (soggetto_ruolo_id, conto_bancario_id, uso) WHERE (istanza_utility_id IS NULL)` |
| uq_src_bancari_ruolo_istanza_conto_uso | `CREATE UNIQUE INDEX uq_src_bancari_ruolo_istanza_conto_uso ON anagrafiche.soggetti_ruoli_conti_bancari USING btree (soggetto_ruolo_id, istanza_utility_id, conto_bancario_id, uso) WHERE (istanza_utility_id IS NOT NULL)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soggetti_ruoli_conti_bancari_a10_conti_bancari_requi_713c18 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'conti_bancari', 'attivo', 'conto_bancario_id', 'id')` |
| trg_soggetti_ruoli_conti_bancari_a10_conti_bancari_requi_713c18 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'conti_bancari', 'attivo', 'conto_bancario_id', 'id')` |
| trg_soggetti_ruoli_conti_bancari_a10_date_validita_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_soggetti_ruoli_conti_bancari_a10_date_validita_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_guard_date_validita()` |
| trg_soggetti_ruoli_conti_bancari_a10_guard_istanza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_guard_istanza_del_ruolo()` |
| trg_soggetti_ruoli_conti_bancari_a10_guard_istanza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_guard_istanza_del_ruolo()` |
| trg_soggetti_ruoli_conti_bancari_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_soggetti_ruoli_conti_bancari_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_soggetti_ruoli_conti_bancari_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_ruoli_conti_bancari_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_ruoli_conti_bancari_guard_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard()` |
| trg_soggetti_ruoli_conti_bancari_guard_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard()` |
| trg_soggetti_ruoli_conti_bancari_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('soggetti_ruoli_conti_bancari_id')` |
| trg_soggetti_ruoli_conti_bancari_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('soggetti_ruoli_conti_bancari_id')` |

---
{% include-markdown "signature-core.md" %}
