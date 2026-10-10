{% include-markdown "it/dbzero/storico/manual/comuni.md" %}
# 📚 Tabella `comuni`

> 📝 **Descrizione**
>
> Storico dei comuni con dati anagrafici e JSONB

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| valid_from | timestamp with time zone | NO | now() |
| valid_to | timestamp with time zone | YES |  |
| data_insert | timestamp with time zone | YES | now() |
| user_insert | text | YES | CURRENT_USER |
| comuni_id | integer | YES |  |
| provincia_id | integer | YES |  |
| tx_id | uuid | YES |  |
| snapshot | jsonb | YES |  |
| tipo_operazione | smallint | YES |  |
| change_type | character(1) | NO | 'A'::bpchar |
| origine_schema | text | NO |  |
| scope_emittente_fiscale_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_comuni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_comuni_scope_ef | `CREATE INDEX ix_comuni_scope_ef ON storico.comuni USING btree (scope_emittente_fiscale_id)` |
| ix_storico_comuni_provincia_id | `CREATE INDEX ix_storico_comuni_provincia_id ON storico.comuni USING btree (provincia_id)` |
| ix_storico_comuni_valid | `CREATE INDEX ix_storico_comuni_valid ON storico.comuni USING btree (valid_from, valid_to)` |
| pk_comuni | `CREATE UNIQUE INDEX pk_comuni ON storico.comuni USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_comuni_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_comuni_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
