{% include-markdown "it/dbzero/storico/manual/risorse_umane.md" %}
# 📚 Tabella `risorse_umane`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.risorse_umane_id_seq'::regclass) |
| risorse_umane_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_risorse_umane | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_risorse_umane_risorse_umane_id_fk | `CREATE INDEX ix_risorse_umane_risorse_umane_id_fk ON storico.risorse_umane USING btree (risorse_umane_id)` |
| ix_risorse_umane_scope_ef | `CREATE INDEX ix_risorse_umane_scope_ef ON storico.risorse_umane USING btree (scope_emittente_fiscale_id)` |
| pk_storico_risorse_umane | `CREATE UNIQUE INDEX pk_storico_risorse_umane ON storico.risorse_umane USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_risorse_umane_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_risorse_umane_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
