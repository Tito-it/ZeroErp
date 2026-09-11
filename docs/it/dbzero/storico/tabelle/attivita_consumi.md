{% include-markdown "it/dbzero/storico/manual/attivita_consumi.md" %}
# 📚 Tabella `attivita_consumi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.attivita_consumi_id_seq'::regclass) |
| attivita_consumi_id | bigint | NO |  |
| change_type | character | YES | 'A'::bpchar |
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
| PRIMARY KEY | pk_storico_attivita_consumi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_attivita_consumi_attivita_consumi_id_fk | `CREATE INDEX ix_attivita_consumi_attivita_consumi_id_fk ON storico.attivita_consumi USING btree (attivita_consumi_id)` |
| ix_attivita_consumi_scope_ef | `CREATE INDEX ix_attivita_consumi_scope_ef ON storico.attivita_consumi USING btree (scope_emittente_fiscale_id)` |
| pk_storico_attivita_consumi | `CREATE UNIQUE INDEX pk_storico_attivita_consumi ON storico.attivita_consumi USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_attivita_consumi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_attivita_consumi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
