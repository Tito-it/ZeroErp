{% include-markdown "it/dbzero/storico/manual/pratiche_sorgenti.md" %}
# 📚 Tabella `pratiche_sorgenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.pratiche_sorgenti_id_seq'::regclass) |
| pratiche_sorgenti_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_pratiche_sorgenti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_pratiche_sorgenti_pratiche_sorgenti_id_fk | `CREATE INDEX ix_pratiche_sorgenti_pratiche_sorgenti_id_fk ON storico.pratiche_sorgenti USING btree (pratiche_sorgenti_id)` |
| pk_storico_pratiche_sorgenti | `CREATE UNIQUE INDEX pk_storico_pratiche_sorgenti ON storico.pratiche_sorgenti USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_pratiche_sorgenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_pratiche_sorgenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
