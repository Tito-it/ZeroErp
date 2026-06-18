# 📚 Tabella `competenze_flussi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.competenze_flussi_id_seq'::regclass) |
| competenze_flussi_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_competenze_flussi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_competenze_flussi_competenze_flussi_id_fk | `CREATE INDEX ix_competenze_flussi_competenze_flussi_id_fk ON storico.competenze_flussi USING btree (competenze_flussi_id)` |
| pk_storico_competenze_flussi | `CREATE UNIQUE INDEX pk_storico_competenze_flussi ON storico.competenze_flussi USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_competenze_flussi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_competenze_flussi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
