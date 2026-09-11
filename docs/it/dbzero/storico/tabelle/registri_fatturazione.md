{% include-markdown "it/dbzero/storico/manual/registri_fatturazione.md" %}
# 📚 Tabella `registri_fatturazione`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.registri_fatturazione_id_seq'::regclass) |
| registri_fatturazione_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_registri_fatturazione | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_registri_fatturazione_registri_fatturazione_id_fk | `CREATE INDEX ix_registri_fatturazione_registri_fatturazione_id_fk ON storico.registri_fatturazione USING btree (registri_fatturazione_id)` |
| ix_registri_fatturazione_scope_ef | `CREATE INDEX ix_registri_fatturazione_scope_ef ON storico.registri_fatturazione USING btree (scope_emittente_fiscale_id)` |
| pk_storico_registri_fatturazione | `CREATE UNIQUE INDEX pk_storico_registri_fatturazione ON storico.registri_fatturazione USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_registri_fatturazione_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_registri_fatturazione_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
