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
| valid_from | date | NO | CURRENT_DATE |
| valid_to | date | YES |  |
| parent_contratto_id | bigint | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| stato_doc_contratto_id | bigint | NO |  |
| data | date | NO | CURRENT_DATE |
| uid | uuid | NO | uuidv7() |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_contratti_billing_account | billing_account_id |
| FOREIGN KEY | fk_contratti_istanza | istanza_utility_id |
| FOREIGN KEY | fk_contratti_parent | parent_contratto_id |
| FOREIGN KEY | fk_contratti_utility | utility_id |
| FOREIGN KEY | fk_v_contratti_stato_ddt | stato_doc_contratto_id |
| PRIMARY KEY | pk_contratti | id |
| UNIQUE | uq_contratti_numero | numero |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ex_contratti_no_overlap | `CREATE INDEX ex_contratti_no_overlap ON vendite.contratti USING gist (billing_account_id, istanza_utility_id, utility_id, ambito, daterange(valid_from, COALESCE(valid_to, 'infinity'::date), '[]'::text))` |
| ix_contratti_ambito | `CREATE INDEX ix_contratti_ambito ON vendite.contratti USING btree (ambito)` |
| ix_contratti_ba_istanza | `CREATE INDEX ix_contratti_ba_istanza ON vendite.contratti USING btree (billing_account_id, istanza_utility_id)` |
| pk_contratti | `CREATE UNIQUE INDEX pk_contratti ON vendite.contratti USING btree (id)` |
| uq_contratti_numero | `CREATE UNIQUE INDEX uq_contratti_numero ON vendite.contratti USING btree (numero)` |
| uq_contratti_uid | `CREATE UNIQUE INDEX uq_contratti_uid ON vendite.contratti USING btree (uid)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_contratti_a10_v_protect_num_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_v_contratti_protect_num()` |
| trg_contratti_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_contratti_normalize()` |
| trg_contratti_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_contratti_normalize()` |

---
{% include-markdown "signature-core.md" %}
