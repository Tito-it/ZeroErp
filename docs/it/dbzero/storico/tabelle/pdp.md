{% include-markdown "it/dbzero/storico/manual/pdp.md" %}
# 📚 Tabella `pdp`

> 📝 **Descrizione**
>
> Storico dei PDP: snapshot JSONB, tipo operazione (I/U/D), tx_id, periodo di validità (valid_from/valid_to).

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
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pdp_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| idx_storico_pdp_pdp_id | `CREATE INDEX idx_storico_pdp_pdp_id ON storico.pdp USING btree (pdp_id)` |
| pdp_pkey | `CREATE UNIQUE INDEX pdp_pkey ON storico.pdp USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_pdp_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_pdp_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
