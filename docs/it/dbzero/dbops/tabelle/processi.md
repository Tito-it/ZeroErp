{% include-markdown "it/dbzero/dbops/manual/processi.md" %}
# 📚 Tabella `processi`

> 📝 **Descrizione**
>
> Registro di CATALOGO dei processi automatici: quali esistono, di che classe e su quale canale. Il codice e' l'attore di un run (maintenance.job_run_log.processo_codice, hard FK). La classe e' una dichiarazione di chi progetta il processo, verificata dal DB in una direzione sola (DOMINIO senza percorso verso un emittente -&gt; dbops.vw_processi_dominio_senza_emittente). Il legame processo -&gt; utente tecnico e' dati di macchina e sta in dbops.processi_identita. Brief: brief-db-processi-automatici-identita-e-perimetro §2.2.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | text | NO |  |
| descrizione | text | NO |  |
| classe | text | NO |  |
| canale | text | NO |  |
| attivo | boolean | NO | true |
| obsoleto_dal | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| jobname_pgagent | text | YES |  |
| tolleranza_minuti | integer | YES |  |
| segno_di_vita | text | NO | 'GIORNALE'::text |
| ci_ordine | integer | YES |  |
| ci_procedura | text | YES |  |
| ci_esclusione | text | YES |  |
| acceso_in_sviluppo | boolean | YES |  |
| acceso_in_produzione | boolean | YES |  |
| spegnibile | boolean | YES |  |
| causa_fallimento | text | NO |  |
| corsa_verdetto_completo | boolean | NO | false |
| accendibile_in_produzione | boolean | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_processi_accensione |  |
| CHECK | chk_processi_canale |  |
| CHECK | chk_processi_classe |  |
| CHECK | chk_processi_contratto_solo_command |  |
| CHECK | chk_processi_convergenza_ci |  |
| CHECK | chk_processi_jobname_pgagent_non_vuoto |  |
| CHECK | chk_processi_ritiro_con_data |  |
| CHECK | chk_processi_segno_di_vita |  |
| CHECK | chk_processi_sessione_senza_tolleranza |  |
| CHECK | chk_processi_tolleranza_positiva |  |
| FOREIGN KEY | fk_processi_cause_fallimento | causa_fallimento |
| PRIMARY KEY | pk_processi | id |
| UNIQUE | uq_processi_ci_ordine | ci_ordine |
| UNIQUE | uq_processi_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_processi | `CREATE UNIQUE INDEX pk_processi ON dbops.processi USING btree (id)` |
| uq_processi_ci_ordine | `CREATE UNIQUE INDEX uq_processi_ci_ordine ON dbops.processi USING btree (ci_ordine)` |
| uq_processi_codice | `CREATE UNIQUE INDEX uq_processi_codice ON dbops.processi USING btree (codice)` |
| uq_processi_jobname_pgagent | `CREATE UNIQUE INDEX uq_processi_jobname_pgagent ON dbops.processi USING btree (jobname_pgagent) WHERE (jobname_pgagent IS NOT NULL)` |

---
{% include-markdown "signature-core.md" %}
