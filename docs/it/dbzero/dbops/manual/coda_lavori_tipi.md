## 📘 Documentazione Concettuale – Tabella `dbops.coda_lavori_tipi`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — la coda: il suo `job_type` punta qui
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo di ogni tipo, da cui si legge la classe
> * [dbops.pipeline_task_registry_impl](/dbzero/dbops/tabelle/pipeline_task_registry_impl) — lo stesso schema di registro per i task di pipeline
>
> Approfondimento viste:
>
> * [dbops.vw_coda_lavori_da_guardare](/dbzero/dbops/views/vw_coda_lavori_da_guardare) — dove finisce un lavoro di un tipo senza handler
>
> Approfondimento funzioni:
>
> * [dbops.fn_accoda_lavoro](/dbzero/dbops/funzioni/fn_accoda_lavoro) — valida il tipo e ne legge i default
>
> Guide:
>
> * [Gestione delle code di lavoro](/guide/gestione-code-di-lavoro) — il ciclo intero, dall'accodamento al drenatore
> * [Processi automatici: classe e identità](/guide/processi-automatici-classe-e-identita) — classe e canale dei processi

---

### 🎯 Scopo Principale

Il registro dei tipi di lavoro della coda generica: una riga per `job_type`. Il database valida il
tipo all'accodamento e porta i default del tipo (`run_as`, `max_tentativi`); il legame fra
`handler_code` e la funzione Python che esegue resta nel backend, registrato all'avvio, senza
import dinamici.

---

### Le colonne che contano

* `codice`: il `job_type`, chiave naturale a cui la coda punta. Non si rinomina: è un contratto fra
  ambienti.
* `handler_code`: la chiave con cui il drenatore trova l'handler. Il database conosce la stringa, non
  la funzione.
* `run_as_default`, `max_tentativi_default`: i default che `fn_accoda_lavoro` usa quando il
  chiamante non li dice. Sono suggerimenti: il chiamante li può sovrascrivere.
* `attivo`: un tipo spento non si accoda (`E_JOB_TYPE_NON_ATTIVO`).
* `processo_codice`: il processo a cui il tipo appartiene, obbligatorio (vedi sotto).
* `meta`: estensioni per tipo.

---

### ⭐ Ogni tipo dichiara il suo processo

`processo_codice` serve a una cosa: far sapere alla coda se il lavoro appartiene a un'azienda.
Poiché `run_as_default` si sovrascrive, un tipo di dominio accodato come `SISTEMA` girerebbe senza
perimetro; `fn_accoda_lavoro` lo rifiuta leggendo la classe del processo.

La classe **non** è copiata qui: due scritture dello stesso fatto prima o poi dissentono. Si tiene
il puntatore al processo e la classe si legge da `dbops.processi`. Registrare un tipo nuovo vuol
dire quindi registrare prima il processo, poi il tipo.

---

### ⛔ Un tipo nasce spento, e si accende a handler in servizio

Il drenatore **prende** ogni lavoro `PENDING` del suo turno: un tipo acceso senza handler non
resta in attesa, fallisce a ogni presa (`E_CODA_HANDLER_NON_REGISTRATO`, sollevato dal backend),
finisce in `ERRORE` a tentativi esauriti e compare in `dbops.vw_coda_lavori_da_guardare`. Per questo l'ordine è fisso: il tipo entra nel seed spento,
il backend registra l'handler e va in servizio, poi il seed lo accende.

L'accensione è una cella del CSV (`80_data/sql/dbops/coda_lavori_tipi.csv`, che il migrate ricarica
quando cambia), non un changeSet. Due guardrail del backend tengono l'ordine: un handler registrato senza
tipo a catalogo è rosso, un tipo acceso senza handler è rosso.

---

### ⭐ Il canale del processo e il `run_as` del tipo si accordano

* sotto un processo di canale `CODA` e di classe `DOMINIO` il tipo è `OPERATORE`: lo accoda una
  persona, tocca i dati di un'azienda, e l'identità è la sua. Sotto un `CODA` di `MANUTENZIONE` può
  essere `SISTEMA`: allora chi preme è l'**attore** del lavoro, nei suoi dati, non la sua identità;
* sotto un processo `PGAGENT` il tipo è `SISTEMA`: una macchina non ha un nome da prestare, e un
  lavoro che vuole un'identità sta sotto un processo `CODA_AUTOMATICA`;
* nessun tipo sta sotto un processo `COMMAND`: quello lo esegue systemd, non il drenatore.

Non c'è un guard a database per questo: lo presidia un pgTAP sul seed.

---

### I tipi a catalogo

| Tipo | Processo (canale, classe) | `run_as` | Che cosa fa |
| --- | --- | --- | --- |
| `FATTURAZIONE_GIRO` | `FATTURAZIONE_GIRO` (`CODA`, `DOMINIO`) | `OPERATORE` | Il giro di fatturazione su richiesta |
| `FATTURAZIONE_NUMERA` | `FATTURAZIONE_NUMERA` (`CODA`, `DOMINIO`) | `OPERATORE` | La numerazione dei lotti emessi di un mese |
| `CHIUSURA_SCADENZE` | `chiusura_scadenze_daily` (`CODA_AUTOMATICA`, `DOMINIO`) | `OPERATORE` | La chiusura per scadenza di un'azienda, accodata dalla sveglia pgAgent con l'identità tecnica dell'azienda |
| `NOTIFICA_DIGEST_MUTO` | `guardiano_digest` (`PGAGENT`, `MANUTENZIONE`) | `SISTEMA` | Avvisa una persona che il digest dei presidi ha smesso di girare, uno al giorno |
| `ESEGUI_PROCESSO` | `avvio_manuale` (`CODA`, `MANUTENZIONE`) | `SISTEMA` | «Esegui ora» su una sveglia di deploy: il comando serve da sé tutte le aziende del suo processo, chi preme viaggia nei dati del lavoro (`richiesto_da`); un tentativo solo, perché un processo caduto a metà non è idempotente |

---

### Codici errore

La tabella non solleva errori propri. Quelli che nascono dalle sue righe li solleva
`dbops.fn_accoda_lavoro`: `E_JOB_TYPE_NON_TROVATO`, `E_JOB_TYPE_NON_ATTIVO`,
`E_JOB_DOMINIO_SENZA_OPERATORE`.

---

### Test

* `db/pgtap/dbops/test-coda-lavori.sql` — la struttura del registro e il tipo
  `FATTURAZIONE_GIRO` a catalogo e acceso.
* `db/pgtap/dbops/test-coda-accoda-classe.sql` — `processo_codice` e la sua chiave esterna; i tipi
  del seed dichiarano tutti il processo.
* `db/pgtap/dbops/test-coda-tipi-canale-e-run-as.sql` — il canale del processo e il `run_as` del
  tipo si accordano; il tipo `ESEGUI_PROCESSO` e il suo processo.

---

### Note di migrazione

* 2026-07-20 — nasce con la coda generica (`brief-db-coda-lavori-generica`).
* 2026-09-04 — nasce `processo_codice`, obbligatorio dalla stessa data
  (`brief-db-processi-automatici-identita-e-perimetro`).
* 2026-09-11 — `NOTIFICA_DIGEST_MUTO` nasce spento e si accende la sera stessa, a handler in
  servizio.
* 2026-09-14 — la regola del binding (tipo spento fino all'handler) sostituisce la frase «senza
  handler i lavori restano in attesa», vera prima del drenatore; il pgTAP su canale e `run_as`.
* 2026-09-15 — `ESEGUI_PROCESSO` si accende, nato spento il giorno prima
  (`brief-db-avvio-manuale-di-un-processo`).
* 2026-11-07 — `ESEGUI_PROCESSO` passa a `SISTEMA`, e la regola fra canale e `run_as` si restringe
  ai `CODA` di `DOMINIO` (`brief-db-revisione-dbops`, giro 5): revoca in parte la decisione del
  2026-09-14.

---

{% include-markdown "signature-core.md" %}
