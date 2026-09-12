{% include-markdown "it/dbzero/storico/manual/documenti_fatturazione_canali.md" %}
# 📚 Tabella `documenti_fatturazione_canali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.documenti_fatturazione_canali_id_seq'::regclass) |
| documenti_fatturazione_canali_id | bigint | NO |  |
| change_type | character | YES | 'A'::bpchar |
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
| PRIMARY KEY | pk_storico_documenti_fatturazione_canali | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_documenti_fatturazione_canali_documenti_fatturazione_canali_ | `CREATE INDEX ix_documenti_fatturazione_canali_documenti_fatturazione_canali_ ON storico.documenti_fatturazione_canali USING btree (documenti_fatturazione_canali_id)` |
| ix_documenti_fatturazione_canali_scope_ef | `CREATE INDEX ix_documenti_fatturazione_canali_scope_ef ON storico.documenti_fatturazione_canali USING btree (scope_emittente_fiscale_id)` |
| pk_storico_documenti_fatturazione_canali | `CREATE UNIQUE INDEX pk_storico_documenti_fatturazione_canali ON storico.documenti_fatturazione_canali USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_documenti_fatturazione_canali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_documenti_fatturazione_canali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
