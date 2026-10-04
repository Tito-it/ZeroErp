{% include-markdown "it/dbzero/storico/manual/template_documenti.md" %}
# 📚 Tabella `template_documenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.template_documenti_id_seq'::regclass) |
| template_documenti_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_template_documenti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_template_documenti_scope_ef | `CREATE INDEX ix_template_documenti_scope_ef ON storico.template_documenti USING btree (scope_emittente_fiscale_id)` |
| ix_template_documenti_template_documenti_id_fk | `CREATE INDEX ix_template_documenti_template_documenti_id_fk ON storico.template_documenti USING btree (template_documenti_id)` |
| pk_storico_template_documenti | `CREATE UNIQUE INDEX pk_storico_template_documenti ON storico.template_documenti USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_template_documenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_template_documenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
