{% include-markdown "it/dbzero/dbops/manual/cause_fallimento.md" %}
# 📚 Tabella `cause_fallimento`

> 📝 **Descrizione**
>
> Il vocabolario delle cause per cui un lavoro automatico fallisce: AMBIENTE (server, connessione, risorse, ruoli del database), PROGRAMMA (serve una modifica al codice o al database), CONFIGURAZIONE (si sistema dalle impostazioni dell'applicazione). Lo dichiarano dbops.processi.causa_fallimento (la natura dei fallimenti del processo quando l'ambiente e' sano) e config.codici_errore.causa_fallimento (la natura di un errore preciso, quando lo sa), con FK verso questa tabella. maintenance.vw_job_run_da_guardare ne ricava la causa di ogni riga, e dbops.presidi_cause dice a chi tocca: le cause di quel presidio coincidono con questo vocabolario (pgTAP maintenance/test-vw-job-run-da-guardare-causa-v1). Seed: 80_data/sql/dbops/cause_fallimento.csv.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | text | NO |  |
| descrizione | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_cause_fallimento_codice_non_vuoto |  |
| CHECK | chk_cause_fallimento_descrizione_non_vuota |  |
| PRIMARY KEY | pk_cause_fallimento | id |
| UNIQUE | uq_cause_fallimento_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_cause_fallimento | `CREATE UNIQUE INDEX pk_cause_fallimento ON dbops.cause_fallimento USING btree (id)` |
| uq_cause_fallimento_codice | `CREATE UNIQUE INDEX uq_cause_fallimento_codice ON dbops.cause_fallimento USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}
