# 📚 Tabella `fatture_scadenze`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.fatture_scadenze_id_seq'::regclass) |
| fatture_scadenze_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_fatture_scadenze | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_scadenze_fatture_scadenze_id_fk | `CREATE INDEX ix_fatture_scadenze_fatture_scadenze_id_fk ON storico.fatture_scadenze USING btree (fatture_scadenze_id)` |
| pk_storico_fatture_scadenze | `CREATE UNIQUE INDEX pk_storico_fatture_scadenze ON storico.fatture_scadenze USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_scadenze_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatture_scadenze_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
