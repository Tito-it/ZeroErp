# 📚 Tabella `conti_bancari`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.conti_bancari_id_seq'::regclass) |
| conti_bancari_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_conti_bancari | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_conti_bancari_conti_bancari_id_fk | `CREATE INDEX ix_conti_bancari_conti_bancari_id_fk ON storico.conti_bancari USING btree (conti_bancari_id)` |
| pk_storico_conti_bancari | `CREATE UNIQUE INDEX pk_storico_conti_bancari ON storico.conti_bancari USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_conti_bancari_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_conti_bancari_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
