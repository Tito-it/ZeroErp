## 📘 Documentazione Concettuale – Funzione `dbops.fn_guardiano_digest`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il contratto di liveness del digest
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — dove finisce l'avviso
> * [dbops.coda_lavori_tipi](/dbzero/dbops/tabelle/coda_lavori_tipi) — il tipo `NOTIFICA_DIGEST_MUTO` e il suo handler
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — dove si decide che il digest è `MUTO`
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — dove si vede una corsa rossa del guardiano
>
> Approfondimento funzioni:
>
> * [dbops.fn_accoda_lavoro](/dbzero/dbops/funzioni/fn_accoda_lavoro) — la porta della coda
> * [maintenance.proc_guardiano_digest_job](/dbzero/maintenance/funzioni/proc_guardiano_digest_job) — il job che la chiama passando dal giornale
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — il giornale della corsa

---

### 🎯 Scopo Principale

Il corpo del job pgAgent `guardiano_digest`: chi guarda il guardiano. Ogni ora legge lo stato del
digest dei presidi dal panorama dei processi e, se è `MUTO`, accoda **un lavoro al giorno** che lo
dica a una persona.

Il digest dei presidi segnala tutti gli altri; se muore lui, l'unica cosa che lo direbbe è il
digest stesso. Un digest morto non manda il messaggio che dice che è morto, e l'assenza di una
mail non si nota.

---

### ⭐ La guardia reciproca

pgAgent vive dentro il database e non muore insieme ai servizi del backend: è un posto da cui la
morte del digest si vede senza dipendere dal digest. E il guardiano è a sua volta un processo
`PGAGENT` a catalogo che passa dal giornale: il panorama guarda anche lui. Il digest riporta il
guardiano, il guardiano accoda per il digest, e ognuno dei due vede la morte dell'altro.

---

### ⛔ Non manda una mail

pgAgent non spedisce e non conosce il destinatario, che è un fatto di deploy e resta nel backend.
Il guardiano **accoda un lavoro** `NOTIFICA_DIGEST_MUTO`; lo esegue il drenatore della coda — il
processo più vivo del backend, con il suo badge — che spedisce al destinatario suo. Nessun
indirizzo entra nel database.

---

### Che cosa fa, in ordine

1. Legge stato, tolleranza e ultimo segno di vita del digest da
   [vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione). ⭐ Il criterio di
   `MUTO` non è qui: sta accanto al `CASE` che lo produce, e se cambia lì questa funzione lo segue.
2. Se il digest non è nel panorama — perché non è a catalogo, è spento o è ritirato — solleva
   `E_CONFIG_MANCANTE`: un guardiano che non ha niente da guardare lo dice, non dorme.
3. Se lo stato non è `MUTO` torna `DIGEST_<stato>` e non fa altro. ⚠️ Solo `MUTO`, «era vivo ed è
   taciuto»: un digest mai partito lo dice già il panorama nel pannello, e un avviso ogni ora su
   un'installazione nuova insegnerebbe a ignorare il guardiano. Anche un digest con la sveglia
   spenta su questa installazione torna qui, come `DIGEST_SPENTO`.
4. Se esiste già un lavoro con la chiave del giorno, in **qualunque** stato, torna
   `GIA_NOTIFICATO_OGGI`. La coda deduplica solo fra i lavori ancora vivi: un lavoro già eseguito
   non fermerebbe il successivo un'ora dopo. Una mail al giorno è il ritmo del digest stesso.
5. Altrimenti accoda, come `SISTEMA` e senza scope (un avviso di manutenzione non appartiene a
   un'azienda), con origine `CRON` e nel payload ciò che serve all'handler per comporre la mail
   senza rileggere niente: il processo, lo stato, la tolleranza, l'ultimo segno di vita e da quanto
   tace. Torna `ACCODATO:<id>`.

Il testo restituito finisce nel giornale della corsa, nell'esito: è ciò che dice, a chi guarda la
corsa, che cosa ha deciso il guardiano.

---

### ⚠️ Se il tipo di lavoro fosse spento, la corsa sarebbe rossa

Il tipo `NOTIFICA_DIGEST_MUTO` è acceso e il backend ha il suo handler, quindi l'avviso parte
davvero. La funzione non aggira il binding: se il tipo venisse spento, il giorno in cui il digest
tace la coda solleverebbe `E_JOB_TYPE_NON_ATTIVO` e la corsa sarebbe **rossa** nel presidio dei
lavori del database — «ho visto e non ho potuto dirlo». Un ritorno silenzioso sarebbe un presidio
che tace proprio quando serve.

---

### Codici errore

* `E_CONFIG_MANCANTE` — il processo `digest_presidi` non è nel panorama: non a catalogo, non attivo
  o ritirato.
* `E_JOB_TYPE_NON_ATTIVO` — lo solleva la coda quando il tipo `NOTIFICA_DIGEST_MUTO` è spento, e
  passa di qui.

---

### Test

* `db/pgtap/dbops/test-fn-guardiano-digest.sql` — il guardiano è a catalogo; digest vivo →
  `DIGEST_OK`; digest `MUTO` col tipo spento → solleva; col tipo acceso → accoda con la forma giusta;
  un'ora dopo → `GIA_NOTIFICATO_OGGI` anche se il lavoro è già eseguito; digest tornato vivo →
  `DIGEST_OK`; digest tolto dal catalogo → solleva.

---

### Note di migrazione

* 2026-09-11 — nasce con `brief-db-quattro-processi-senza-presidio` §10.2, per decisione di Tid; il
  tipo `NOTIFICA_DIGEST_MUTO` nasce spento e si accende la sera stessa, quando il backend dichiara
  pronto l'handler.
* 2026-11-03 — l'esito testuale arriva nel giornale della corsa (`brief-db-revisione-maintenance`
  D5): prima il giornale scriveva solo che la corsa era finita.

---

{% include-markdown "signature-core.md" %}
