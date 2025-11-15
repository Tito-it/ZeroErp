{% include-markdown "it/dbzero/anagrafiche/manual/soggetti_ruoli_conti_bancari.md" %}
# 📚 Tabella `soggetti_ruoli_conti_bancari`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_id | bigint | NO |  |
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
| CHECK | chk_soggetti_ruoli_conti_bancari_uso |  |
| CHECK | chk_soggetti_ruoli_conti_bancari_validita |  |
| FOREIGN KEY | fk_soggetti_ruoli_conti_bancari_conti_bancari | conto_bancario_id |
| FOREIGN KEY | fk_soggetti_ruoli_conti_bancari_soggetti_ruoli | soggetto_ruolo_id |
| PRIMARY KEY | pk_soggetti_ruoli_conti_bancari | id |
| UNIQUE | uq_soggetti_ruoli_conti_bancari_soggetto_ruolo_id_conto_bancari | soggetto_ruolo_id, uso, conto_bancario_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_soggetti_ruoli_conti_bancari_conto_bancario_id | `CREATE INDEX ix_soggetti_ruoli_conti_bancari_conto_bancario_id ON anagrafiche.soggetti_ruoli_conti_bancari USING btree (conto_bancario_id)` |
| ix_soggetti_ruoli_conti_bancari_predef_per_uso | `CREATE UNIQUE INDEX ix_soggetti_ruoli_conti_bancari_predef_per_uso ON anagrafiche.soggetti_ruoli_conti_bancari USING btree (soggetto_ruolo_id, uso) WHERE (predefinito = true)` |
| ix_soggetti_ruoli_conti_bancari_soggetto_ruolo_id | `CREATE INDEX ix_soggetti_ruoli_conti_bancari_soggetto_ruolo_id ON anagrafiche.soggetti_ruoli_conti_bancari USING btree (soggetto_ruolo_id)` |
| pk_soggetti_ruoli_conti_bancari | `CREATE UNIQUE INDEX pk_soggetti_ruoli_conti_bancari ON anagrafiche.soggetti_ruoli_conti_bancari USING btree (id)` |
| uq_soggetti_ruoli_conti_bancari_soggetto_ruolo_id_conto_bancari | `CREATE UNIQUE INDEX uq_soggetti_ruoli_conti_bancari_soggetto_ruolo_id_conto_bancari ON anagrafiche.soggetti_ruoli_conti_bancari USING btree (soggetto_ruolo_id, conto_bancario_id, uso)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_soggetti_ruoli_conti_bancari_ins_upd_guard | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard()` |
| trg_soggetti_ruoli_conti_bancari_ins_upd_guard | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_soggetti_ruoli_conti_bancari_guard()` |

---
{% include-markdown "signature-core.md" %}
