## 📘 Documentazione Concettuale – Vista `maintenance.vw_job_run_corsie`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale da cui legge
>
> Approfondimento viste:
>
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — il presidio, una riga per corsia
>
> Approfondimento funzioni:
>
> * [maintenance.fn_pota_giornale_corse](/dbzero/maintenance/funzioni/fn_pota_giornale_corse) — la potatura, che tiene l'ultima di ogni corsia

---

### 🎯 Scopo Principale

L'elenco delle corsie del giornale delle corse: una riga per ogni coppia `processo_codice` e
`jobname` che ha almeno una corsa. È il punto di partenza di chi vuole «l'ultima corsa di ogni
corsia».

---

### ⛔ La corsia è la coppia, non il nome

Il modello non lega un `jobname` a un processo solo: due processi possono avere una corsia con lo
stesso nome. Chi cerca per il solo nome unisce due lavori diversi senza accorgersene, e l'ultima
corsa dell'uno copre quella dell'altro. La chiave è quindi la coppia, in ogni lettore.

---

### Come lavora

Le corsie non hanno una tabella loro, e raggruppare il giornale costerebbe quanto tutta la sua
storia. La vista salta nell'indice delle corsie (`ix_job_run_log_processo_codice_jobname_started_at`)
da una coppia alla successiva: una ricerca per corsia, quindi il costo segue il numero delle
corsie, non la storia.

---

### Chi la legge

* `maintenance.vw_job_run_da_guardare` — per ogni corsia, l'ultima corsa vera e i rossi.
* `maintenance.fn_pota_giornale_corse` — per ogni corsia, le righe che la potatura tiene.

È la sede unica di questa discesa: chi deve elencare le corsie la legge, non la riscrive. Non ha
`GRANT` all'applicazione: la leggono una vista e una funzione del proprietario.

---

### Test

* `db/pgtap/maintenance/test-job-run-log-per-chiave-v1.sql`, test 16 — un nome usato da due
  processi sono due corsie. I test 13-15 provano la vista da guardare sulla stessa fixture.
* `db/pgtap/maintenance/test-pota-giornale-corse-v1.sql` — la potatura, che parte da qui.

---

### Note di migrazione

* 2026-11-23 — nasce, dalla discesa sulle coppie che stava nella potatura, quando anche la vista da
  guardare è passata alla corsia (`brief-db-giornale-corse-indici` §11.5, la corsia in ogni lettore).

---

{% include-markdown "signature-core.md" %}
