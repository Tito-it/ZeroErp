{% include-markdown "it/dbzero/storico/manual/parameter_overrides.md" %}
# 📚 Tabella `parameter_overrides`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| valid_from | timestamp with time zone | NO | now() |
| valid_to | timestamp with time zone | YES |  |
| change_type | character | YES | 'A'::bpchar |
| data_insert | timestamp without time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| parameter_override_id | bigint | NO |  |
| snapshot | jsonb | NO |  |
| tipo_operazione | smallint | YES |  |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_parameter_overrides | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_storico_parameter_overrides_parameter_override_id | `CREATE INDEX ix_storico_parameter_overrides_parameter_override_id ON storico.parameter_overrides USING btree (parameter_override_id)` |
| pk_storico_parameter_overrides | `CREATE UNIQUE INDEX pk_storico_parameter_overrides ON storico.parameter_overrides USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_parameter_overrides_tx_id_managed_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_parameter_overrides_tx_id_managed_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
