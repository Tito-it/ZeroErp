# 📚 Tabella `iva_natura`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.iva_natura_id_seq'::regclass) |
| iva_natura_id | integer | NO |  |
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
| PRIMARY KEY | pk_storico_iva_natura | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_iva_natura_iva_natura_id_fk | `CREATE INDEX ix_iva_natura_iva_natura_id_fk ON storico.iva_natura USING btree (iva_natura_id)` |
| ix_iva_natura_scope_ef | `CREATE INDEX ix_iva_natura_scope_ef ON storico.iva_natura USING btree (scope_emittente_fiscale_id)` |
| pk_storico_iva_natura | `CREATE UNIQUE INDEX pk_storico_iva_natura ON storico.iva_natura USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_iva_natura_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_iva_natura_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
