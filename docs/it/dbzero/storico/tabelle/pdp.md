{% include-markdown "it/dbzero/storico/manual/pdp.md" %}
# 📚 Tabella `pdp`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| pdp_id | bigint | NO |  |
| tipo_operazione | character | NO |  |
| snapshot | jsonb | NO |  |
| tx_id | uuid | NO |  |
| valid_from | timestamp with time zone | NO | now() |
| valid_to | timestamp with time zone | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | pdp_tipo_operazione_check |  |
| PRIMARY KEY | pdp_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| idx_storico_pdp_open | `CREATE INDEX idx_storico_pdp_open ON storico.pdp USING btree (pdp_id) WHERE (valid_to IS NULL)` |
| idx_storico_pdp_pdp_id | `CREATE INDEX idx_storico_pdp_pdp_id ON storico.pdp USING btree (pdp_id)` |
| pdp_pkey | `CREATE UNIQUE INDEX pdp_pkey ON storico.pdp USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_pdp_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_pdp_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
