{% include-markdown "it/dbzero/storico/manual/template_flussi.md" %}
# 📚 Tabella `template_flussi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.template_flussi_id_seq'::regclass) |
| template_flussi_id | integer | NO |  |
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
| PRIMARY KEY | pk_storico_template_flussi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_template_flussi_scope_ef | `CREATE INDEX ix_template_flussi_scope_ef ON storico.template_flussi USING btree (scope_emittente_fiscale_id)` |
| ix_template_flussi_template_flussi_id_fk | `CREATE INDEX ix_template_flussi_template_flussi_id_fk ON storico.template_flussi USING btree (template_flussi_id)` |
| pk_storico_template_flussi | `CREATE UNIQUE INDEX pk_storico_template_flussi ON storico.template_flussi USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_template_flussi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_template_flussi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
