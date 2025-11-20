# 📚 Tabella `dati_catastali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| valid_from | timestamp with time zone | NO | now() |
| valid_to | timestamp with time zone | YES |  |
| change_type | character | YES | 'A'::bpchar |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| dato_catastale_id | bigint | NO |  |
| snapshot | jsonb | NO |  |
| tipo_operazione | smallint | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_dati_catastali | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_storico_dati_catastali | `CREATE UNIQUE INDEX pk_storico_dati_catastali ON storico.dati_catastali USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_dati_catastali_tx_id_managed_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_dati_catastali_tx_id_managed_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
