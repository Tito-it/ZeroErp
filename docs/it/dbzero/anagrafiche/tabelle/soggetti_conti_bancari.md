{% include-markdown "it/dbzero/anagrafiche/manual/soggetti_conti_bancari.md" %}
# 📚 Tabella `soggetti_conti_bancari`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_id | uuid | NO |  |
| conto_bancario_id | bigint | NO |  |
| uso | character varying | NO | 'GENERICO'::character varying |
| predefinito | boolean | NO | false |
| valido_dal | date | YES |  |
| valido_al | date | YES |  |
| intestazione_dichiarata | character varying | YES |  |
| verificato | boolean | NO | false |
| bloccato | boolean | NO | false |
| meta | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_soggetti_conti_bancari_uso |  |
| CHECK | chk_soggetti_conti_bancari_validita |  |
| FOREIGN KEY | fk_soggetti_conti_bancari_conti_bancari | conto_bancario_id |
| FOREIGN KEY | fk_soggetti_conti_bancari_soggetti | soggetto_id |
| PRIMARY KEY | pk_soggetti_conti_bancari | id |
| UNIQUE | uq_soggetti_conti_bancari_soggetto_id_conto_id_uso | soggetto_id, conto_bancario_id, uso |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_anagrafiche_soggetti_conti_bancari_conto_bancario_id | `CREATE INDEX ix_anagrafiche_soggetti_conti_bancari_conto_bancario_id ON anagrafiche.soggetti_conti_bancari USING btree (conto_bancario_id)` |
| ix_anagrafiche_soggetti_conti_bancari_soggetto_id | `CREATE INDEX ix_anagrafiche_soggetti_conti_bancari_soggetto_id ON anagrafiche.soggetti_conti_bancari USING btree (soggetto_id)` |
| ix_soggetti_conti_bancari_predef_per_uso | `CREATE UNIQUE INDEX ix_soggetti_conti_bancari_predef_per_uso ON anagrafiche.soggetti_conti_bancari USING btree (soggetto_id, uso) WHERE (predefinito = true)` |
| pk_soggetti_conti_bancari | `CREATE UNIQUE INDEX pk_soggetti_conti_bancari ON anagrafiche.soggetti_conti_bancari USING btree (id)` |
| uq_soggetti_conti_bancari_soggetto_id_conto_id_uso | `CREATE UNIQUE INDEX uq_soggetti_conti_bancari_soggetto_id_conto_id_uso ON anagrafiche.soggetti_conti_bancari USING btree (soggetto_id, conto_bancario_id, uso)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soggetti_conti_bancari_a10_conti_bancari_require_att_e85d18 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'conti_bancari', 'attivo', 'conto_bancario_id')` |
| trg_soggetti_conti_bancari_a10_conti_bancari_require_att_e85d18 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'conti_bancari', 'attivo', 'conto_bancario_id')` |
| trg_soggetti_conti_bancari_a10_soggetti_require_attivo_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id')` |
| trg_soggetti_conti_bancari_a10_soggetti_require_attivo_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('anagrafiche', 'soggetti', 'attivo', 'soggetto_id')` |
| trg_soggetti_conti_bancari_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_soggetti_conti_bancari_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_soggetti_conti_bancari_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_conti_bancari_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_conti_bancari_guard_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_conti_bancari_guard()` |
| trg_soggetti_conti_bancari_guard_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_conti_bancari_guard()` |
| trg_soggetti_conti_bancari_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('soggetti_conti_bancari_id')` |
| trg_soggetti_conti_bancari_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('soggetti_conti_bancari_id')` |

---
{% include-markdown "signature-core.md" %}
