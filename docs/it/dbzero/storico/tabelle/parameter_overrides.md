{% include-markdown "it/dbzero/storico/manual/parameter_overrides.md" %}
# 📚 Tabella `parameter_overrides`

> 📝 **Descrizione**
>
> Tabella storica per i parameter_overrides con snapshot JSONB e campi di audit

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| valid_from | timestamp with time zone | NO | now() |
| valid_to | timestamp with time zone | YES |  |
| change_type | character(1) | YES | 'A'::bpchar |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| parameter_override_id | bigint | NO |  |
| snapshot | jsonb | NO |  |
| tipo_operazione | smallint | YES |  |
| tx_id | uuid | YES |  |
| origine_schema | text | NO |  |
| scope_emittente_fiscale_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_parameter_overrides | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_parameter_overrides_scope_ef | `CREATE INDEX ix_parameter_overrides_scope_ef ON storico.parameter_overrides USING btree (scope_emittente_fiscale_id)` |
| ix_storico_parameter_overrides_parameter_override_id | `CREATE INDEX ix_storico_parameter_overrides_parameter_override_id ON storico.parameter_overrides USING btree (parameter_override_id)` |
| pk_storico_parameter_overrides | `CREATE UNIQUE INDEX pk_storico_parameter_overrides ON storico.parameter_overrides USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_parameter_overrides_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_parameter_overrides_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
