# 📚 Tabella `eventi_assets`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.eventi_assets_id_seq'::regclass) |
| eventi_assets_id | bigint | NO |  |
| change_type | character | YES | 'A'::bpchar |
| tipo_operazione | smallint | YES |  |
| snapshot | jsonb | YES |  |
| user_insert | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | YES | now() |
| tx_id | uuid | YES |  |
| valid_from | timestamp with time zone | YES | now() |
| valid_to | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_eventi_assets | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_eventi_assets_eventi_assets_id_fk | `CREATE INDEX ix_eventi_assets_eventi_assets_id_fk ON storico.eventi_assets USING btree (eventi_assets_id)` |
| pk_storico_eventi_assets | `CREATE UNIQUE INDEX pk_storico_eventi_assets ON storico.eventi_assets USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_eventi_assets_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_eventi_assets_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
