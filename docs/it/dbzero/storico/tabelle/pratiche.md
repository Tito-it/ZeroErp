{% include-markdown "it/dbzero/storico/manual/pratiche.md" %}
# 📚 Tabella `pratiche`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.pratiche_id_seq'::regclass) |
| pratiche_id | bigint | NO |  |
| change_type | character(1) | YES | 'A'::bpchar |
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
| PRIMARY KEY | pk_storico_pratiche | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_pratiche_pratiche_id_fk | `CREATE INDEX ix_pratiche_pratiche_id_fk ON storico.pratiche USING btree (pratiche_id)` |
| ix_pratiche_scope_ef | `CREATE INDEX ix_pratiche_scope_ef ON storico.pratiche USING btree (scope_emittente_fiscale_id)` |
| pk_storico_pratiche | `CREATE UNIQUE INDEX pk_storico_pratiche ON storico.pratiche USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_pratiche_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_pratiche_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
