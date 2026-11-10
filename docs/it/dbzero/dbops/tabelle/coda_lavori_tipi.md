{% include-markdown "it/dbzero/dbops/manual/coda_lavori_tipi.md" %}
# 📚 Tabella `coda_lavori_tipi`

> 📝 **Descrizione**
>
> Il catalogo dei tipi di lavoro della coda dei lavori (dbops.coda_lavori). codice e' il job_type; handler_code la chiave di dispatch verso il registro degli handler del backend (nessun import dinamico); processo_codice il processo di dbops.processi a cui il tipo appartiene; run_as_default e max_tentativi_default i valori che un lavoro prende se chi accoda non li passa. Un tipo spento (attivo = false) non si accoda.

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

---
{% include-markdown "signature-core.md" %}
