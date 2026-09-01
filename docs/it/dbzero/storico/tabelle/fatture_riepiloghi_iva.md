# 📚 Tabella `fatture_riepiloghi_iva`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.fatture_riepiloghi_iva_id_seq'::regclass) |
| fatture_riepiloghi_iva_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_fatture_riepiloghi_iva | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_riepiloghi_iva_fatture_riepiloghi_iva_id_fk | `CREATE INDEX ix_fatture_riepiloghi_iva_fatture_riepiloghi_iva_id_fk ON storico.fatture_riepiloghi_iva USING btree (fatture_riepiloghi_iva_id)` |
| pk_storico_fatture_riepiloghi_iva | `CREATE UNIQUE INDEX pk_storico_fatture_riepiloghi_iva ON storico.fatture_riepiloghi_iva USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_riepiloghi_iva_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_riepiloghi_iva_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
