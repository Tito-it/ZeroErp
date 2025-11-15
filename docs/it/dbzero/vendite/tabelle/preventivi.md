# 📚 Tabella `preventivi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| numero | character varying | NO |  |
| rev | integer | NO | 0 |
| is_revision_attiva | boolean | NO | false |
| billing_account_id | integer | YES |  |
| istanza_utility_id | integer | YES |  |
| utility_id | integer | NO |  |
| validita_dal | date | YES |  |
| validita_al | date | YES |  |
| totale_imponibile | numeric | YES | 0 |
| totale_iva | numeric | YES | 0 |
| totale_documento | numeric | YES | 0 |
| valuta_id | integer | YES |  |
| meta | jsonb | YES | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |
| competenza_mese | date | YES |  |
| fatturazione_immediata | boolean | YES | false |
| stato_doc_preventivo_id | bigint | NO |  |
| data | date | NO | CURRENT_DATE |
| termine_pagamento_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_preventivi_competenza_mese_primo |  |
| CHECK | chk_preventivi_validita |  |
| FOREIGN KEY | fk_preventivi_billing_account | billing_account_id |
| FOREIGN KEY | fk_preventivi_istanza | istanza_utility_id |
| FOREIGN KEY | fk_preventivi_termini_pagamento | termine_pagamento_id |
| FOREIGN KEY | fk_preventivi_utility | utility_id |
| FOREIGN KEY | fk_preventivi_valuta | valuta_id |
| FOREIGN KEY | fk_v_preventivi_stato_ddt | stato_doc_preventivo_id |
| PRIMARY KEY | pk_preventivi | id |
| UNIQUE | uq_preventivi_numero_rev | rev, numero |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_preventivi | `CREATE UNIQUE INDEX pk_preventivi ON vendite.preventivi USING btree (id)` |
| uq_preventivi_numero_rev | `CREATE UNIQUE INDEX uq_preventivi_numero_rev ON vendite.preventivi USING btree (numero, rev)` |
| ux_preventivi_numero_attiva | `CREATE UNIQUE INDEX ux_preventivi_numero_attiva ON vendite.preventivi USING btree (numero) WHERE (is_revision_attiva = true)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_preventivi_a10_upd_v_protect_num | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_a10_v_preventivi_protect_num()` |
| trg_preventivi_ins_upd_norm | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_preventivi_norm()` |
| trg_preventivi_ins_upd_norm | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_preventivi_norm()` |

---
{% include-markdown "signature-core.md" %}
