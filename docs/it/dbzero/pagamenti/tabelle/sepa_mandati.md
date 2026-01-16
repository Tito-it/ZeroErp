# 📚 Tabella `sepa_mandati`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| soggetto_ruolo_conto_id | bigint | NO |  |
| billing_account_id | bigint | YES |  |
| istanza_utility_id | bigint | YES |  |
| umr | character varying | NO |  |
| schema | character varying | NO |  |
| creditor_id | character varying | YES |  |
| data_firma | date | YES |  |
| data_attivazione | date | YES |  |
| data_revoca | date | YES |  |
| stato | character varying | NO | 'IN_VALIDAZIONE'::character varying |
| iban_snapshot | character varying | YES |  |
| intestatario_snapshot | character varying | YES |  |
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
| CHECK | chk_sepa_mandati_date |  |
| CHECK | chk_sepa_mandati_iban_snap_fmt |  |
| CHECK | chk_sepa_mandati_perimetro |  |
| CHECK | chk_sepa_mandati_schema |  |
| CHECK | chk_sepa_mandati_stato |  |
| CHECK | chk_sepa_mandati_umr_fmt |  |
| FOREIGN KEY | fk_sepa_mandati_billing_account | billing_account_id |
| FOREIGN KEY | fk_sepa_mandati_istanza_utility | istanza_utility_id |
| FOREIGN KEY | fk_sepa_mandati_soggetto_ruolo_conto | soggetto_ruolo_conto_id |
| PRIMARY KEY | pk_sepa_mandati | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_pagamenti_sepa_mandati_billing_account_id | `CREATE INDEX ix_pagamenti_sepa_mandati_billing_account_id ON pagamenti.sepa_mandati USING btree (billing_account_id)` |
| ix_pagamenti_sepa_mandati_soggetto_ruolo_conto_id | `CREATE INDEX ix_pagamenti_sepa_mandati_soggetto_ruolo_conto_id ON pagamenti.sepa_mandati USING btree (soggetto_ruolo_conto_id)` |
| ix_sepa_mandati_ba_schema_attivo | `CREATE UNIQUE INDEX ix_sepa_mandati_ba_schema_attivo ON pagamenti.sepa_mandati USING btree (billing_account_id, schema) WHERE (((stato)::text = 'ATTIVO'::text) AND (billing_account_id IS NOT NULL))` |
| ix_sepa_mandati_istanza_schema_attivo | `CREATE UNIQUE INDEX ix_sepa_mandati_istanza_schema_attivo ON pagamenti.sepa_mandati USING btree (istanza_utility_id, schema) WHERE (((stato)::text = 'ATTIVO'::text) AND (istanza_utility_id IS NOT NULL))` |
| pk_sepa_mandati | `CREATE UNIQUE INDEX pk_sepa_mandati ON pagamenti.sepa_mandati USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_sepa_mandati_guard_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_sepa_mandati_guard()` |
| trg_sepa_mandati_guard_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_sepa_mandati_guard()` |

---
{% include-markdown "signature-core.md" %}
