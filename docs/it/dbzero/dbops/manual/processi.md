## 📘 Documentazione Concettuale – Tabella `dbops.processi`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.processi_bersagli](/dbzero/dbops/manual/processi_bersagli)
> • [dbops.processi_identita](/dbzero/dbops/manual/processi_identita)
> • [dbops.coda_lavori_tipi](/dbzero/dbops/manual/coda_lavori_tipi)
> • [maintenance.job_run_log](/dbzero/maintenance/manual/job_run_log)
>
**Approfondimento funzioni:**
>
• [script.fn_crea_utente_tecnico](/dbzero/script/manual/fn_crea_utente_tecnico)
> • [dbops.fn_accoda_lavoro](/dbzero/dbops/manual/fn_accoda_lavoro)
>

### 🎯 Scopo Principale
(latest review 04-09-2026)

`dbops.processi` è l'**anagrafica di tutto ciò che il sistema fa da solo**: i
lavori notturni, i comandi lanciati a mano, i job messi in coda. Una riga per
processo.

Serve a rispondere a una domanda che prima non aveva risposta scritta da
nessuna parte:

> **Questo lavoro automatico sta manutenendo il database, o sta lavorando i
> documenti di un'azienda?**

Sono due mestieri diversi e vogliono regole diverse. Un lavoro che ricostruisce
gli indici non appartiene a nessuno; un lavoro che emette fatture appartiene
**sempre** a un emittente, e chi lo fa girare deve avere il permesso di toccare
i documenti di quell'emittente.

---

### ⭐ La classe è una DICHIARAZIONE, non una deduzione

È il punto che regge tutto il resto.

Si sarebbe potuto **dedurre** la natura di un processo guardando che cosa
tocca: *«scrive su una tabella protetta, quindi è di dominio»*. ⛔ È la strada
sbagliata, e per una ragione precisa: una tabella nuova nasce **senza**
protezioni, quindi il processo che la tocca risulterebbe innocuo — proprio nel
momento in cui è più pericoloso.

⇒ La classe la scrive una persona quando registra il processo. Poi il DB
**verifica in un verso solo**: che ciò che è dichiarato di dominio abbia
davvero un perimetro e una difesa. Una dichiarazione sbagliata si vede; una
deduzione sbagliata no.

---

### Le tre classi

| classe | Che cosa fa | Ha un emittente? |
| --- | --- | --- |
| `MANUTENZIONE` | tiene in ordine il database: indici, storicizzazione, pulizie, automazioni | **no** — non appartiene a nessuno |
| `AMMINISTRAZIONE` | governa la macchina: utenze, scadenze tecniche, sincronizzazioni | **no** |
| `DOMINIO` | lavora i documenti di un'azienda: fatture, DDT, listini, incassi | ⛔ **sì, sempre** |

⚠️ **Il confine non è «tocca dati» / «non tocca dati»**, ed è l'errore che si
fa leggendo in fretta. Un processo di manutenzione tocca eccome i dati: li
storicizza, li archivia. La differenza è **di chi sono** quei dati. Se una riga
ha un padrone, il processo è di dominio.

---

### I tre canali

| canale | Chi lo fa partire |
| --- | --- |
| `PGAGENT` | lo scheduler del database, di notte, da solo |
| `COMMAND` | una persona o un cron che lancia un comando |
| `CODA` | un operatore che accoda un lavoro dall'applicazione |

⭐ **Il canale `CODA` è quello che cambia le regole**, e va capito bene: un
lavoro accodato porta con sé **l'identità di chi l'ha chiesto**. Non gli serve
un utente tecnico, e dargliene uno cancellerebbe il nome della persona che ha
premuto il pulsante. Per questo i presidi che cercano gli utenti tecnici
**escludono** i processi di coda.

---

### Campi chiave

* `codice`: nome stabile del processo (UNIQUE). ⭐ Per i job di pgAgent è
  **identico al nome del job** — non è un vezzo: è ciò che permette al giornale
  dei run di riconoscere chi sta girando senza che si debba toccare la
  configurazione dello scheduler.
* `classe`: `MANUTENZIONE` | `AMMINISTRAZIONE` | `DOMINIO` (CHECK).
* `canale`: `PGAGENT` | `COMMAND` | `CODA` (CHECK).
* `attivo` / `obsoleto_dal`: un processo ritirato **non si cancella**, si
  spegne. La sua storia nel giornale dei run resta leggibile.
* `meta`: estensioni JSONB.

---

### Come si registra un processo nuovo

1. Una riga nel **seed** `80_data/sql/dbops/processi.csv` — è catalogo, non
   dato di macchina: si cambia dal CSV, mai con una `UPDATE` diretta.
2. Se è di **dominio**, una riga in
   [processi_bersagli](/dbzero/dbops/manual/processi_bersagli) per ogni tabella
   che tocca, con il percorso che porta all'emittente.
3. Se è di dominio **e non ha un operatore che lo lancia** (canali `PGAGENT` e
   `COMMAND`), un utente tecnico per ogni emittente che deve servire —
   [fn_crea_utente_tecnico](/dbzero/script/manual/fn_crea_utente_tecnico).

⇒ I presidi lo dicono da soli se un passo è stato saltato: le viste
`vw_processi_dominio_senza_emittente`, `vw_processi_dominio_senza_difesa`,
`vw_processi_dominio_senza_identita` e `vw_emittenti_non_serviti` **devono
restare vuote**.

---

### Note operative

* Il ruolo applicativo ha **sola lettura** su questa tabella: la scrive il
  seed, non l'applicazione.
* ⚠️ Il codice è referenziato in **hard FK** da
  [coda_lavori_tipi](/dbzero/dbops/manual/coda_lavori_tipi) e da
  [job_run_log](/dbzero/maintenance/manual/job_run_log): rinominare un processo
  è un'operazione di migrazione, non una modifica di catalogo.

Origine: `docs/it/dev/work-in-progress/brief-db-processi-automatici-identita-e-perimetro.md` §2.

---

{% include-markdown "signature-core.md" %}
