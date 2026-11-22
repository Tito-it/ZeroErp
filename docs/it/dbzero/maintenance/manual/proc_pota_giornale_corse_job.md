## 📘 Documentazione Concettuale – Procedura `maintenance.proc_pota_giornale_corse_job`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `pota_giornale_corse`
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale che la potatura cancella, e in cui la sua corsa lascia la riga
>
> Approfondimento funzioni:
>
> * [maintenance.fn_pota_giornale_corse](/dbzero/maintenance/funzioni/fn_pota_giornale_corse) — il lavoro vero: che cosa si cancella e che cosa resta
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — il giornale da cui passa la chiamata
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello dello step pgAgent
> * [script.fn_mesi_dopo](/dbzero/script/funzioni/fn_mesi_dopo) — come si contano i 12 mesi

---

### 🎯 Scopo Principale

Il wrapper del job `pota_giornale_corse`: la ritenzione del giornale delle corse, **12 mesi**.
Chiama `maintenance.fn_pota_giornale_corse` passando dal giornale, sotto il codice del processo,
con il lock della corsia.

⭐ **La ritenzione sta qui, e solo qui.** La soglia è l'inizio del giorno aziendale di 12 mesi fa:
il giorno di oggi nel fuso dell'azienda, 12 mesi indietro di calendario, e l'istante in cui quel
giorno comincia. Non è `now()` meno un intervallo, che conterebbe nel fuso della sessione di
pgAgent.

---

### Dove gira

| Dove | Chi la chiama | Quando |
| --- | --- | --- |
| dbdev e installazioni | il job pgAgent `pota_giornale_corse` | ogni notte alle 03:30 |
| CI e scratch | nessuno | il processo è fuori dalla convergenza di CI: cancella le corse vecchie, non cambia la struttura del database |

Lo step pgAgent chiama la procedura solo se `maintenance.fn_sveglia_accesa('pota_giornale_corse')`
è vero: a sveglia spenta il lavoro non parte, e il giornale non scrive niente.

---

### Gira come il proprietario

La procedura è `SECURITY DEFINER`, con `search_path` fissato, e appartiene a `zeroerp_owner`,
come tutte le `maintenance.proc_*_job`. L'`EXECUTE` lo ha solo `zeroerp_job`, dal provisioning
(fase `post`); `PUBLIC` e l'applicazione no. È l'unica strada da cui si cancella dal giornale.

L'esito (`soglia`, `cancellate`) il giornale lo conserva in `meta.esito` della corsa della
potatura.

---

### Test

* `db/pgtap/maintenance/test-pota-giornale-corse-v1.sql` — fra l'altro, la soglia di 12 mesi
  scritta nella procedura, la postura, il processo a catalogo e il job pgAgent dietro il cancello.
* `db/pgtap/maintenance/test-proc-job-definer-v1.sql` — per ogni `maintenance.proc_*_job`:
  `SECURITY DEFINER`, `search_path` fissato, proprietario dello schema, nessun `EXECUTE` a
  `PUBLIC` né a `zeroerp_app`.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il nome passato dal wrapper esiste in
  `dbops.processi`.

---

### Note di migrazione

* 2026-11-22 — nasce col job notturno (`brief-db-giornale-corse-indici` §7, §8).

---

{% include-markdown "signature-core.md" %}
