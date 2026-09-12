{% include-markdown "it/dbzero/dbops/manual/coda_lavori_tipi.md" %}
# 📚 Tabella `coda_lavori_tipi`

> 📝 **Descrizione**
>
> Registry dei tipi di job della coda lavori generica (dbops.coda_lavori). codice = job_type; handler_code = chiave di dispatch verso il handler_registry Python (no dynamic import); default per-tipo run_as/max_tentativi. Brief: brief-db-coda-lavori-generica §2.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | text | NO |  |
| handler_code | text | NO |  |
| descrizione | text | YES |  |
| run_as_default | text | NO |  |
| max_tentativi_default | integer | NO | 5 |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| processo_codice | text | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_coda_lavori_tipi_max_tentativi |  |
| CHECK | chk_coda_lavori_tipi_run_as_default |  |
| FOREIGN KEY | fk_coda_lavori_tipi_processi | processo_codice |
| PRIMARY KEY | pk_coda_lavori_tipi | id |
| UNIQUE | uq_coda_lavori_tipi_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_coda_lavori_tipi | `CREATE UNIQUE INDEX pk_coda_lavori_tipi ON dbops.coda_lavori_tipi USING btree (id)` |
| uq_coda_lavori_tipi_codice | `CREATE UNIQUE INDEX uq_coda_lavori_tipi_codice ON dbops.coda_lavori_tipi USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_coda_lavori_tipi_audit_data_user_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_coda_lavori_tipi_audit_data_user_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_coda_lavori_tipi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_coda_lavori_tipi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}
