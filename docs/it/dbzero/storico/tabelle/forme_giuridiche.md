{% include-markdown "it/dbzero/storico/manual/forme_giuridiche.md" %}
# 📚 Tabella `forme_giuridiche`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.forme_giuridiche_id_seq'::regclass) |
| forme_giuridiche_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_forme_giuridiche | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_forme_giuridiche_forme_giuridiche_id_fk | `CREATE INDEX ix_forme_giuridiche_forme_giuridiche_id_fk ON storico.forme_giuridiche USING btree (forme_giuridiche_id)` |
| ix_forme_giuridiche_scope_ef | `CREATE INDEX ix_forme_giuridiche_scope_ef ON storico.forme_giuridiche USING btree (scope_emittente_fiscale_id)` |
| pk_storico_forme_giuridiche | `CREATE UNIQUE INDEX pk_storico_forme_giuridiche ON storico.forme_giuridiche USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_forme_giuridiche_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_forme_giuridiche_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
