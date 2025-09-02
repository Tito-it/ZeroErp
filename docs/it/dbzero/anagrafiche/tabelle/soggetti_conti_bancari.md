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
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_soggetti_conti_bancari_uso |  |
| CHECK | chk_soggetti_conti_bancari_validita |  |
| FOREIGN KEY | fk_soggetti_conti_bancari_conti_bancari | conto_bancario_id |
| FOREIGN KEY | fk_soggetti_conti_bancari_soggetti | soggetto_id |
| PRIMARY KEY | pk_soggetti_conti_bancari | id |
| UNIQUE | uq_soggetti_conti_bancari_soggetto_id_conto_id_uso | uso, conto_bancario_id, soggetto_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_soggetti_conti_bancari_conto_bancario_id | `CREATE INDEX ix_soggetti_conti_bancari_conto_bancario_id ON anagrafiche.soggetti_conti_bancari USING btree (conto_bancario_id)` |
| ix_soggetti_conti_bancari_predef_per_uso | `CREATE UNIQUE INDEX ix_soggetti_conti_bancari_predef_per_uso ON anagrafiche.soggetti_conti_bancari USING btree (soggetto_id, uso) WHERE (predefinito = true)` |
| ix_soggetti_conti_bancari_soggetto_id | `CREATE INDEX ix_soggetti_conti_bancari_soggetto_id ON anagrafiche.soggetti_conti_bancari USING btree (soggetto_id)` |
| pk_soggetti_conti_bancari | `CREATE UNIQUE INDEX pk_soggetti_conti_bancari ON anagrafiche.soggetti_conti_bancari USING btree (id)` |
| uq_soggetti_conti_bancari_soggetto_id_conto_id_uso | `CREATE UNIQUE INDEX uq_soggetti_conti_bancari_soggetto_id_conto_id_uso ON anagrafiche.soggetti_conti_bancari USING btree (soggetto_id, conto_bancario_id, uso)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soggetti_conti_bancari_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_conti_bancari_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_soggetti_conti_bancari_ins_upd_guard | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_conti_bancari_guard()` |
| trg_soggetti_conti_bancari_ins_upd_guard | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_conti_bancari_guard()` |
| trg_upd_soggetti_conti_bancari_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_z90_soggetti_conti_bancari_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('soggetti_conti_bancari_id')` |
| trg_z90_soggetti_conti_bancari_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('soggetti_conti_bancari_id')` |

---
{% include-markdown "signature-core.md" %}
