{% include-markdown "it/dbzero/storico/manual/assets.md" %}
# 📚 Tabella `assets`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.assets_id_seq'::regclass) |
| assets_id | bigint | NO |  |
| change_type | character(1) | YES | 'A'::bpchar |
| tipo_operazione | smallint | YES |  |
| snapshot | jsonb | YES |  |
| user_insert | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | YES | now() |
| tx_id | uuid | YES |  |
| valid_from | timestamp with time zone | YES | now() |
| valid_to | timestamp with time zone | YES |  |
| origine_schema | text | NO |  |
| scope_emittente_fiscale_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_assets | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_assets_assets_id_fk | `CREATE INDEX ix_assets_assets_id_fk ON storico.assets USING btree (assets_id)` |
| ix_assets_scope_ef | `CREATE INDEX ix_assets_scope_ef ON storico.assets USING btree (scope_emittente_fiscale_id)` |
| pk_storico_assets | `CREATE UNIQUE INDEX pk_storico_assets ON storico.assets USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_assets_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_assets_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
