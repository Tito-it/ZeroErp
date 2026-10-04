{% include-markdown "it/dbzero/storico/manual/template_documenti_versioni.md" %}
# 📚 Tabella `template_documenti_versioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.template_documenti_versioni_id_seq'::regclass) |
| template_documenti_versioni_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_template_documenti_versioni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_template_documenti_versioni_scope_ef | `CREATE INDEX ix_template_documenti_versioni_scope_ef ON storico.template_documenti_versioni USING btree (scope_emittente_fiscale_id)` |
| ix_template_documenti_versioni_template_documenti_versioni_id_f | `CREATE INDEX ix_template_documenti_versioni_template_documenti_versioni_id_f ON storico.template_documenti_versioni USING btree (template_documenti_versioni_id)` |
| pk_storico_template_documenti_versioni | `CREATE UNIQUE INDEX pk_storico_template_documenti_versioni ON storico.template_documenti_versioni USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_template_documenti_versioni_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_template_documenti_versioni_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
