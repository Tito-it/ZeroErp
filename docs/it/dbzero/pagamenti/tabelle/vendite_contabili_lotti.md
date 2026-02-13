{% include-markdown "it/dbzero/pagamenti/manual/vendite_contabili_lotti.md" %}
# 📚 Tabella `vendite_contabili_lotti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lotto_id | bigint | NO |  |
| contabile_id | bigint | NO |  |
| meta | jsonb | NO | '{}'::jsonb |
| attivo | boolean | NO | true |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_vendite_contabili_lotti_contabile | contabile_id |
| FOREIGN KEY | fk_vendite_contabili_lotti_lotto | lotto_id |
| PRIMARY KEY | pk_vendite_contabili_lotti | id |
| UNIQUE | uq_vendite_contabili_lotti_lotto_contabile | lotto_id, contabile_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_vendite_contabili_lotti | `CREATE UNIQUE INDEX pk_vendite_contabili_lotti ON pagamenti.vendite_contabili_lotti USING btree (id)` |
| uq_vendite_contabili_lotti_lotto_contabile | `CREATE UNIQUE INDEX uq_vendite_contabili_lotti_lotto_contabile ON pagamenti.vendite_contabili_lotti USING btree (lotto_id, contabile_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_vendite_contabili_lotti_a10_guard_compensazione_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_lotti_guard_compensazione()` |
| trg_vendite_contabili_lotti_a10_guard_compensazione_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION pagamenti.trgfn_vendite_contabili_lotti_guard_compensazione()` |

---
{% include-markdown "signature-core.md" %}
