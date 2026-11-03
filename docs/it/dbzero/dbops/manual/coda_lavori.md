## 📘 Documentazione Concettuale – Tabella `dbops.coda_lavori`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.coda_lavori_tipi](/dbzero/dbops/tabelle/coda_lavori_tipi) — il registro dei tipi: il `job_type` di ogni riga
> * [dbops.idempotency_keys](/dbzero/dbops/tabelle/idempotency_keys) — l'altra idempotenza, quella delle richieste HTTP
> * [vendite.fatture_stampa_coda](/dbzero/vendite/tabelle/fatture_stampa_coda) — la coda gemella delle stampe, con la stessa archiviazione
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale delle corse, a cui una riga può legarsi
>
> Approfondimento viste:
>
> * [dbops.vw_coda_lavori_da_guardare](/dbzero/dbops/views/vw_coda_lavori_da_guardare) — i lavori falliti, rimasti a metà o mai presi
>
> Approfondimento funzioni:
>
> * [dbops.fn_accoda_lavoro](/dbzero/dbops/funzioni/fn_accoda_lavoro) — l'unica porta d'ingresso
> * [dbops.trgfn_coda_archiviazione](/dbzero/dbops/funzioni/trgfn_coda_archiviazione) — governa la bandiera `archiviato`
>
> Guide:
>
> * [Gestione delle code di lavoro](/guide/gestione-code-di-lavoro) — il ciclo intero, dall'accodamento al drenatore

---

### 🎯 Scopo Principale

La coda di lavori generica dell'ERP, sul database e senza broker: una riga è un lavoro asincrono
(un tipo e i suoi argomenti). Si accoda con `dbops.fn_accoda_lavoro`, anche nella stessa
transazione del dato che chiede il lavoro; un drenatore del backend la svuota e passa ogni lavoro
all'handler del suo tipo.

Un lavoro asincrono nuovo è un tipo a catalogo più un handler, non una tabella e un worker nuovi.

---

### Chi esegue: `run_as` e `scope`

* `SISTEMA`: il drenatore apre il contesto di processo di sistema; lo scope è vuoto.
* `OPERATORE`: il drenatore applica lo **scope catturato all'accodamento** (la terna dell'utente e
  gli emittenti), senza bypass della row level security.

Il vincolo `chk_coda_lavori_run_as_scope` tiene insieme le due cose: un operatore senza scope
girerebbe senza filtro, un lavoro di sistema con uno scope direbbe un perimetro che nessuno
applica. Che un lavoro di **dominio** sia sempre `OPERATORE` lo controlla `fn_accoda_lavoro`, perché
il vincolo non conosce la natura del lavoro.

Un lavoro `OPERATORE` che parte completa con lo scope con cui è nato: una revoca dei permessi vale
per i lavori futuri, non interrompe quello in corso.

---

### Le colonne che si leggono male

* `origine`: chi ha **accodato** (`API`, `CRON`, `COMMAND`, `TRIGGER`). È un vocabolario della coda,
  distinto da `maintenance.job_run_log.origine`, che dice chi esegue una corsa.
* `priorita`: più bassa è più urgente; il drenatore prende a lotti misti per priorità e id, così un
  tipo non affama gli altri.
* `run_after`: un lavoro è eleggibile solo da quell'istante; serve ai lavori differiti e al
  backoff fra un tentativo e l'altro.
* `claimed_at`: l'istante della presa in carico, scritto dal drenatore; è il riferimento del
  reaper.
* `idempotency_key`: la chiave **di business** che impedisce due lavori vivi uguali (vedi sotto).
* `job_run_id`: il legame con la corsa del giornale, quando c'è. `result`: il riepilogo che
  l'handler restituisce. `ultimo_errore`: l'ultimo fallimento.

---

### Il ciclo di vita

```text
PENDING ──presa──▶ IN_CORSO ──▶ FATTO
   ▲                  │
   └── riprova ───────┤ (con backoff, finché restano tentativi)
                      └──▶ ERRORE (tentativi esauriti)
PENDING ──annulla──▶ ANNULLATO
```

Le transizioni le scrive il drenatore del backend, non il database: il database dà l'accodamento,
i vincoli e l'archiviazione.

* **Presa in carico**: solo righe `PENDING` eleggibili, a lotti, con `SKIP LOCKED`; più drenatori
  in parallelo non si pestano.
* **Esito**: `FATTO` col risultato, oppure di nuovo `PENDING` con backoff fino a `max_tentativi`,
  poi `ERRORE`.
* **Annullamento**: solo da `PENDING`; un lavoro già preso non si annulla.
* **Reaper**: un `IN_CORSO` preso da troppo tempo torna `PENDING` (il drenatore è morto a metà).
* **Sblocco a mano**: un lavoro fermo torna `PENDING` conservando i tentativi fatti, con qualche
  tentativo in più concesso.

---

### ⭐ Due idempotenze, per due domande diverse

* **Questa coda** non ammette due lavori **vivi** (`PENDING`, `IN_CORSO`) con lo stesso tipo e la
  stessa chiave: lo garantisce l'indice unico parziale `uq_coda_lavori_vivo_idem`. A lavoro finito
  la stessa chiave si riaccoda: rieseguire è un'intenzione.
* **Le richieste HTTP** (`dbops.idempotency_keys`) non eseguono due volte lo stesso invio e
  rimandano la risposta già data. La chiave della coda non è l'Idempotency-Key della richiesta.

---

### Perché la coda delle stampe resta a parte

`vendite.fatture_stampa_coda` non è assorbita qui: è un outbox di documenti, con una sorgente reale
e un documento come destino, un asse diverso da quello dei lavori. Le due tabelle condividono il
motore di drenaggio del backend e la regola di archiviazione, non la riga.

---

### Archiviare una riga senza toccarne lo stato

`archiviato`, `archiviato_il` e `archiviato_da` tolgono una riga **dall'elenco**, non dal lavoro.
Cancellare o annullare non andava bene: i conteggi che l'operatore legge sono raggruppati per stato
senza filtro di visibilità, e una cancellazione li fa calare, un annullamento sposta la
ripartizione.

* ⛔ **Un solo lettore: la lista.** Né la presa in carico, né il reaper, né i conteggi la leggono:
  un lettore in più farebbe dell'archiviazione un annullamento silenzioso.
* **Si archivia solo una riga non viva.** Lo impongono il vincolo
  `chk_coda_lavori_archiviato_non_vivo` (la sede dell'invariante) e la trigger function
  `dbops.trgfn_coda_archiviazione` (la sede del messaggio). Una riga viva archiviata resterebbe nel
  conteggio del badge e fuori dall'elenco, senza modo di arrivarci.
* ⭐ **Una riga che torna viva riabbassa la bandiera da sola**: un lavoro archiviato e poi rimesso in
  coda sarebbe altrimenti vivo e invisibile.
* **Data e autore dell'archiviazione li scrive il database**, e restano fermi finché la riga resta
  archiviata; `chk_coda_lavori_archiviato_coerente` impedisce una bandiera senza data o una data
  senza bandiera.
* La regola è identica su `vendite.fatture_stampa_coda`, con la stessa funzione: un pgTAP confronta
  colonne, vincoli e trigger delle due code.

---

### Più scrittori, quindi audit e tx_id

Accodano i domini, scrive il drenatore, annulla e sblocca un amministratore, archivia l'operatore.
Per questo la tabella ha i trigger di audit (`data_update`, `user_update`) e del `tx_id`, generati
dalle automazioni.

---

### Codici errore

* `E_CODA_ARCHIVIAZIONE_NON_AMMESSA` — si archivia una riga ancora viva (dalla trigger function
  dell'archiviazione).

---

### Test

* `db/pgtap/dbops/test-coda-lavori.sql` — la struttura di coda e registro, i vincoli di stato,
  `run_as` e origine, l'indice unico dei vivi, l'accodamento e i suoi rifiuti.
* `db/pgtap/dbops/test-coda-archiviazione.sql` — l'archiviazione: le due code simmetriche, una
  riga viva rifiutata, i timbri derivati e immutabili, il reset al requeue, i vincoli all'inserimento.
* `db/pgtap/dbops/test-vw-coda-lavori-da-guardare.sql` — il presidio sulla coda.
* `db/pgtap/dbops/test-stati-check-scrittori-v1.sql` — ogni stato del vincolo ha uno scrittore
  dichiarato.

---

### Note di migrazione

* 2026-07-20 — nasce, con il registro dei tipi e la porta d'ingresso
  (`brief-db-coda-lavori-generica`).
* 2026-09-04 — nasce l'archiviazione, insieme sulle due code (`brief-db-archiviazione-righe-code`).

---

{% include-markdown "signature-core.md" %}
