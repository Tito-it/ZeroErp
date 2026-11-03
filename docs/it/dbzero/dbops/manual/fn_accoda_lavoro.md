## 📘 Documentazione Concettuale – Funzione `dbops.fn_accoda_lavoro`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — la coda in cui la funzione scrive
> * [dbops.coda_lavori_tipi](/dbzero/dbops/tabelle/coda_lavori_tipi) — il registro dei tipi, con i default
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — da dove si legge la classe del lavoro
>
> Approfondimento funzioni:
>
> * [dbops.fn_accoda_chiusura_scadenze](/dbzero/dbops/funzioni/fn_accoda_chiusura_scadenze) — un chiamante dal database: la sveglia della chiusura per scadenza
> * [dbops.fn_guardiano_digest](/dbzero/dbops/funzioni/fn_guardiano_digest) — un chiamante dal database: l'avviso del digest muto
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — da dove passano i rifiuti
>
> Guide:
>
> * [Gestione delle code di lavoro](/guide/gestione-code-di-lavoro) — il ciclo intero, dall'accodamento al drenatore

---

### 🎯 Scopo Principale

L'unica porta d'ingresso della coda lavori generica: valida il tipo, risolve i default del tipo,
controlla che un lavoro di dominio abbia un operatore, e scrive il lavoro con una sola `INSERT`
idempotente sui lavori vivi. Restituisce l'id del lavoro, nuovo o già esistente.

Si chiama dal backend (un endpoint che accoda) e dal database (le sveglie della chiusura per
scadenza e del guardiano del digest); è scritta per poterla chiamare anche un trigger, nella stessa
transazione del dato che chiede il lavoro (`origine = TRIGGER`). La presa in carico, l'esito, i tentativi e il reaper non sono qui: li fa il drenatore del
backend.

---

### I default vengono dal tipo, e si possono sovrascrivere

`run_as` e `max_tentativi` non passati si prendono dal tipo (`run_as_default`,
`max_tentativi_default`); la priorità vale 100 e l'origine `API` se non dette. Un default è un
suggerimento: chi accoda può passare un altro valore.

Il tipo deve esistere in `dbops.coda_lavori_tipi` ed essere acceso. Un tipo spento è un tipo il cui
handler non è (ancora) dichiarato in servizio dal backend: accodarlo vorrebbe dire mandare il lavoro
in `ERRORE` al primo tentativo.

---

### ⛔ Un lavoro di dominio si accoda solo come operatore

Proprio perché `run_as` si sovrascrive, un tipo di dominio accodato come `SISTEMA` girerebbe senza
perimetro, cioè senza sapere per conto di quale azienda lavora. La funzione lo rifiuta: se il
processo del tipo è di classe `DOMINIO`, il lavoro passa solo come `OPERATORE`.

La classe non è copiata sul tipo: si legge da `dbops.processi` passando per
`coda_lavori_tipi.processo_codice`. Una sede sola, e se un processo cambia classe la coda lo sa
subito.

Il vincolo di tabella `chk_coda_lavori_run_as_scope` non prende questo caso: guarda la coerenza fra
`run_as` e `scope`, non la natura del lavoro.

---

### Un operatore porta sempre il suo scope

Un lavoro `OPERATORE` senza scope girerebbe senza filtro di row level security: la funzione lo
rifiuta con un messaggio parlante prima che arrivi al vincolo di tabella. Il caso simmetrico — un
lavoro `SISTEMA` con uno scope — lo respinge il vincolo stesso (23514), senza un messaggio di
dominio. Lo scope è quello **catturato all'accodamento**: il drenatore lo applica tale e quale anche
se nel frattempo i permessi dell'operatore sono cambiati.

---

### ⭐ Idempotente sui lavori vivi

Con una chiave di idempotenza, due accodamenti dello stesso tipo e della stessa chiave mentre il
primo è ancora vivo (`PENDING` o `IN_CORSO`) danno **un** lavoro: il secondo riceve l'id del primo.
Lo garantisce l'indice unico parziale `uq_coda_lavori_vivo_idem`, non un controllo letto prima.

A lavoro finito (`FATTO`, `ERRORE`, `ANNULLATO`) la stessa chiave accoda di nuovo: rieseguire è
un'intenzione, e decidere se un lavoro già fatto chiude la questione spetta a chi accoda (la sveglia
della chiusura per scadenza lo fa da sé). Senza chiave, ogni chiamata accoda.

⚠️ Se il lavoro vivo che ha fatto scattare il conflitto si chiude fra la scrittura e la rilettura,
la rilettura non trova più un lavoro vivo e la funzione restituisce un id vuoto.

La chiave della coda è una chiave **di business** (per esempio competenza e perimetro): non è
l'Idempotency-Key HTTP, che vive in `dbops.idempotency_keys` e rimanda la risposta già data.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — tipo vuoto, oppure un lavoro `OPERATORE` senza scope.
* `E_JOB_TYPE_NON_TROVATO` — il tipo non è in `dbops.coda_lavori_tipi`.
* `E_JOB_TYPE_NON_ATTIVO` — il tipo c'è ma è spento.
* `E_JOB_DOMINIO_SENZA_OPERATORE` — il processo del tipo è di classe `DOMINIO` e il lavoro non è
  `OPERATORE`.

I valori fuori vocabolario di `run_as` e `origine`, e un `SISTEMA` con scope, arrivano dai vincoli
della tabella (23514).

---

### Test

* `db/pgtap/dbops/test-coda-lavori.sql` — l'accodamento coi default del tipo, l'idempotenza sui
  lavori vivi (stesso id, un solo vivo per chiave), i rifiuti per tipo inesistente, spento, vuoto e
  per operatore senza scope, il lavoro `SISTEMA` senza scope, i vincoli di tabella.
* `db/pgtap/dbops/test-coda-accoda-classe.sql` — il guard di classe: un lavoro di dominio come
  `SISTEMA` è rifiutato anche quando il default del tipo dice `OPERATORE`; come operatore con scope
  passa; un lavoro di manutenzione come `SISTEMA` passa.
* `db/pgtap/dbops/test-fn-accoda-chiusura-scadenze.sql` e
  `db/pgtap/dbops/test-fn-guardiano-digest.sql` — i chiamanti dal database.

---

### Note di migrazione

* 2026-07-20 — nasce con la coda lavori generica (`brief-db-coda-lavori-generica`).
* 2026-09-04 — il guard di classe (`brief-db-processi-automatici-identita-e-perimetro`).

---

{% include-markdown "signature-core.md" %}
