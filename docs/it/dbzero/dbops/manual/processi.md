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
(latest review 14-09-2026)

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

### I quattro canali

| canale | Chi lo fa partire |
| --- | --- |
| `PGAGENT` | lo scheduler del database, di notte, da solo |
| `COMMAND` | una persona o un cron che lancia un comando |
| `CODA` | **una persona** che accoda un lavoro dall'applicazione |
| `CODA_AUTOMATICA` | **una macchina** (un job pgAgent che sveglia e non lavora) che accoda un lavoro eseguito dal drenatore — dal 2026-09-05, correzione R-E |

⭐ **Il canale `CODA` è quello che cambia le regole**, e va capito bene: un
lavoro accodato porta con sé **l'identità di chi l'ha chiesto**. Non gli serve
un utente tecnico, e dargliene uno cancellerebbe il nome della persona che ha
premuto il pulsante. Per questo i presidi che cercano gli utenti tecnici
**escludono** i processi di coda.

⚠️ **`CODA_AUTOMATICA` non è un terzo caso: è la correzione del modello.** Un
lavoro che passa dalla coda ma lo accoda una **sveglia** non ha un nome da
prestare — vuole l'identità tecnica come i `PGAGENT` e i `COMMAND`, e i presidi
lo contano fra quelli. Fino al 05-09 questa tabella ne elencava tre e
`chiusura_scadenze_daily` sarebbe apparso «non ne vuole» mentre ne usava una
(brief `brief-db-processi-automatici-residui-be` §1-quater).

⭐ **Un `CODA` può essere anche di `MANUTENZIONE`**, e non è una contraddizione:
`avvio_manuale` (dal 2026-09-14) è il gesto «Esegui ora» su una sveglia di
deploy — lo accoda una persona, quindi `CODA`; non tocca i dati di nessuna
azienda, quindi `MANUTENZIONE`. Nel panorama è `SU_RICHIESTA` come gli altri
`CODA`, e sotto di lui **non si scrive nessun run**: l'audit del gesto è la riga
di [coda_lavori](/dbzero/dbops/manual/coda_lavori), l'audit dell'esecuzione è
il run che il comando lanciato scrive sotto il **proprio** processo (origine
`COMMAND`, `auth_user_id` di chi ha premuto). Il tipo che ospita è
`ESEGUI_PROCESSO` — brief `brief-db-avvio-manuale-di-un-processo` §8.

---

### Campi chiave

* `codice`: nome stabile del processo (UNIQUE). ⭐ Per i job di pgAgent è
  **identico al nome del job** — non è un vezzo: è ciò che permette al giornale
  dei run di riconoscere chi sta girando senza che si debba toccare la
  configurazione dello scheduler.
* `classe`: `MANUTENZIONE` | `AMMINISTRAZIONE` | `DOMINIO` (CHECK).
* `canale`: `PGAGENT` | `COMMAND` | `CODA` | `CODA_AUTOMATICA` (CHECK).
* `attivo` / `obsoleto_dal`: un processo ritirato **non si cancella**, si
  spegne. La sua storia nel giornale dei run resta leggibile.
* `meta`: estensioni JSONB.
* `tolleranza_minuti` / `segno_di_vita` (dal 2026-09-11): il **contratto di
  liveness** — sezione sotto. Solo sui `COMMAND`.

---

### ⭐ Il contratto di liveness — il catalogo dichiara l'attesa, non la sveglia

Per i `PGAGENT` la programmazione si legge da `pgagent.*`; per i `CODA` una
cadenza non esiste. Per i **`COMMAND`** — quelli che sveglia systemd — il
database non vedeva niente, e li chiamava `FUORI_PORTATA`.
[maintenance.vw_job_run_da_guardare](/dbzero/maintenance/manual/vw_job_run_da_guardare)
lo aveva scritto: *«non vede il job che non parte affatto: per quello servirebbe
che ogni processo dichiarasse ogni quanto deve girare, e `dbops.processi` non ce
l'ha»*. Ora ce l'ha.

| Colonna | Che cosa dice | Valori |
| --- | --- | --- |
| `tolleranza_minuti` | *«se sto bene, lascio un segno di vita almeno ogni N minuti»* | intero > 0, oppure `NULL` = non si presidia da qui |
| `segno_di_vita` | **dove** il database cerca quel segno | `GIORNALE` (default): l'ultima corsa su `job_run_log` · `SESSIONE`: una connessione viva in `pg_stat_activity` con `application_name = codice` |

**Perché a catalogo e non nel deploy.** Non perché «la tolleranza è modello» in
astratto: perché **il lettore che serve vive nel database**. Il guardiano del
digest ([fn_guardiano_digest](/dbzero/dbops/manual/fn_guardiano_digest)) è un job
pgAgent, e legge solo qui. Una sede sola resta una sede sola: `tolleranza_minuti`
**esce** da `backend/deploy/sveglie.json` (lavoro del backend).

⚠️ **Cadenza e tolleranza non sono indipendenti** — il deploy stesso scriveva
*«1560 = un giro più due ore»*. La lettura che regge: la tolleranza è il
**contratto** del processo, uguale su ogni installazione; la cadenza
(`oncalendar`, nel deploy) è **come l'host lo onora**. Un timer più lento della
tolleranza lo viola: quella verifica è del backend, sul JSON.

⭐ **`SESSIONE` è un fatto, non una dichiarazione.** Un listener `LISTEN/NOTIFY`
tiene una connessione aperta: se muore, la sessione sparisce. `application_name`
si legge da qualunque ruolo, senza `pg_read_all_stats`. Niente battito sul
giornale (che è il giornale delle *corse*), niente tabella nuova; la decisione
del 2026-09-05 — un solo run all'avvio — resta. Per `SESSIONE` la tolleranza è
`NULL`: la domanda è «c'è **adesso**?».

⛔ **Il limite, dichiarato ora.** Il catalogo non sa quali processi sono
**accesi su questo host** (`abilita` sta nel deploy). Oggi non morde: ogni
sveglia accesa è universale, e `run_fatturazione_batch` è spento per decisione
di **prodotto** — tolleranza `NULL`, e il giorno in cui si accende è una
release. Un processo acceso su un host e spento su un altro vorrà un **registro
di silenziamento** a database, non una colonna nel JSON.

Vincoli: `chk_processi_tolleranza_positiva`, `chk_processi_segno_di_vita`,
`chk_processi_contratto_solo_command`, `chk_processi_sessione_senza_tolleranza`.
Lo legge [vw_processi_programmazione](/dbzero/dbops/manual/vw_processi_programmazione):
`OK` / `MUTO` / `MAI_PARTITO`.

Valori al 2026-09-11 (dal seed): `draina_coda_lavori` 10, `draina_coda_stampa`
10, `send_pending_emails` 30, `digest_presidi` 11520 (la più larga delle due
corsie), `listen_cambio_reparto` `SESSIONE`, `run_fatturazione_batch` `NULL`.

---

### Come si registra un processo nuovo

1. Una riga nel **seed** `80_data/sql/dbops/processi.csv` — è catalogo, non
   dato di macchina: si cambia dal CSV, mai con una `UPDATE` diretta.
2. Se è di **dominio**, una riga in
   [processi_bersagli](/dbzero/dbops/manual/processi_bersagli) per ogni tabella
   che tocca, con il percorso che porta all'emittente.
3. Se è di dominio **e non ha un operatore che lo lancia** (canali `PGAGENT`,
   `COMMAND` e `CODA_AUTOMATICA`), un utente tecnico per ogni emittente che deve
   servire —
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

Origine: `docs/it/dev/work-done/brief-db-processi-automatici-identita-e-perimetro.md` §2.

---

{% include-markdown "signature-core.md" %}
