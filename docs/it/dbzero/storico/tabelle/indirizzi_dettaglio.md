{% include-markdown "it/dbzero/storico/manual/indirizzi_dettaglio.md" %}
# 📚 Tabella `indirizzi_dettaglio`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.indirizzi_dettaglio_id_seq'::regclass) |
| valid_from | date | NO | CURRENT_DATE |
| valid_to | date | YES |  |
| change_type | character | YES | 'A'::bpchar |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| indirizzo_dettaglio_id | integer | NO |  |
| snapshot | jsonb | NO |  |
| tipo_operazione | smallint | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_indirizzi_dettaglio | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_indirizzi_dettaglio_indirizzo_dettaglio_id | `CREATE INDEX ix_indirizzi_dettaglio_indirizzo_dettaglio_id ON storico.indirizzi_dettaglio USING btree (indirizzo_dettaglio_id)` |
| pk_indirizzi_dettaglio | `CREATE UNIQUE INDEX pk_indirizzi_dettaglio ON storico.indirizzi_dettaglio USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_indirizzi_dettaglio_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_indirizzi_dettaglio_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
