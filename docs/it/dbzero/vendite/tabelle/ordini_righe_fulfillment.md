{% include-markdown "it/dbzero/vendite/manual/ordini_righe_fulfillment.md" %}
# 📚 Tabella `ordini_righe_fulfillment`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| ordine_riga_id | bigint | NO |  |
| ddt_riga_id | bigint | NO |  |
| qta_evasa | numeric | NO |  |
| note | character varying | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ordini_r_ful_v_qta_pos |  |
| FOREIGN KEY | fk_ordini_r_ful_v_ddt_riga | ddt_riga_id |
| FOREIGN KEY | fk_ordini_r_ful_v_ordine_riga | ordine_riga_id |
| PRIMARY KEY | pk_fulv | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ordini_r_ful_v_ddt_riga | `CREATE INDEX ix_ordini_r_ful_v_ddt_riga ON vendite.ordini_righe_fulfillment USING btree (ddt_riga_id)` |
| pk_fulv | `CREATE UNIQUE INDEX pk_fulv ON vendite.ordini_righe_fulfillment USING btree (id)` |
| uq_ordini_r_ful_v_pair | `CREATE UNIQUE INDEX uq_ordini_r_ful_v_pair ON vendite.ordini_righe_fulfillment USING btree (ordine_riga_id, ddt_riga_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ordini_righe_fulfillment_a10_guard_consistenza_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION vendite.trgfn_ordini_ful_guard_consistenza()` |
| trg_ordini_righe_fulfillment_a10_guard_consistenza_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION vendite.trgfn_ordini_ful_guard_consistenza()` |

---
{% include-markdown "signature-core.md" %}
