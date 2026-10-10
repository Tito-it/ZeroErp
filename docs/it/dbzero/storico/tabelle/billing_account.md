{% include-markdown "it/dbzero/storico/manual/billing_account.md" %}
# 📚 Tabella `billing_account`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.billing_account_id_seq'::regclass) |
| billing_account_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_billing_account | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_billing_account_billing_account_id_fk | `CREATE INDEX ix_billing_account_billing_account_id_fk ON storico.billing_account USING btree (billing_account_id)` |
| ix_billing_account_scope_ef | `CREATE INDEX ix_billing_account_scope_ef ON storico.billing_account USING btree (scope_emittente_fiscale_id)` |
| pk_storico_billing_account | `CREATE UNIQUE INDEX pk_storico_billing_account ON storico.billing_account USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_billing_account_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_billing_account_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
