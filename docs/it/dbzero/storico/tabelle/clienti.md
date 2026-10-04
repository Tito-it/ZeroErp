{% include-markdown "it/dbzero/storico/manual/clienti.md" %}
# 📚 Tabella `clienti`

> 📝 **Descrizione**
>
> Tabella storica per i clienti con snapshot JSONB e campi di audit

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| valid_from | timestamp with time zone | NO | now() |
| valid_to | timestamp with time zone | YES |  |
| change_type | character(1) | YES | 'A'::bpchar |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| cliente_id | bigint | NO |  |
| snapshot | jsonb | NO |  |
| tipo_operazione | smallint | YES |  |
| tx_id | uuid | YES |  |
| origine_schema | text | NO |  |
| scope_emittente_fiscale_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_clienti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_clienti_scope_ef | `CREATE INDEX ix_clienti_scope_ef ON storico.clienti USING btree (scope_emittente_fiscale_id)` |
| pk_storico_clienti | `CREATE UNIQUE INDEX pk_storico_clienti ON storico.clienti USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_clienti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_clienti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
