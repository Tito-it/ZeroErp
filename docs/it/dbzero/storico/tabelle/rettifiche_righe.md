{% include-markdown "it/dbzero/storico/manual/rettifiche_righe.md" %}
# 📚 Tabella `rettifiche_righe`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.rettifiche_righe_id_seq'::regclass) |
| rettifiche_righe_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_rettifiche_righe | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_rettifiche_righe_rettifiche_righe_id_fk | `CREATE INDEX ix_rettifiche_righe_rettifiche_righe_id_fk ON storico.rettifiche_righe USING btree (rettifiche_righe_id)` |
| ix_rettifiche_righe_scope_ef | `CREATE INDEX ix_rettifiche_righe_scope_ef ON storico.rettifiche_righe USING btree (scope_emittente_fiscale_id)` |
| pk_storico_rettifiche_righe | `CREATE UNIQUE INDEX pk_storico_rettifiche_righe ON storico.rettifiche_righe USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_rettifiche_righe_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_rettifiche_righe_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
