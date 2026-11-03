## 📘 Documentazione Concettuale – Vista `maintenance.vw_job_run_da_superuser`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale, e il suo `ruolo_sessione`
>
> Approfondimento viste:
>
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — la sorella: com'è andata l'ultima corsa vera
>
> Approfondimento funzioni:
>
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — scrive il ruolo collegato sulle corse dei job del database
> * [script.fn_job_run_start](/dbzero/script/funzioni/fn_job_run_start) — lo scrive sulle corse dei lavori del backend
> * [maintenance.fn_job_run_log_failure](/dbzero/maintenance/funzioni/fn_job_run_log_failure) — lo scrive sul verbale di un fallimento
>
> Guide:
>
> * [Processi pgAgent funzionali](/guide/processi-pgagent-funzionali) — con che utente girano i lavori

---

### 🎯 Scopo Principale

Il presidio «nessun superuser al lavoro»: per ogni processo, l'ultima corsa registrata nel
giornale, se il ruolo che si è collegato per farla è un superuser. Deve restare vuota.

---

### ⭐ Basta guardare il superuser

Un lavoro del database gira come il **proprietario**, attraverso una procedura
`SECURITY DEFINER`; a collegarsi è pgAgent come `zeroerp_job`, il migratore nella convergenza del
rilascio, o una persona. Le procedure dei job non sono eseguibili da `PUBLIC` né
dall'applicazione: possono chiamarle solo il proprietario e i suoi membri, `zeroerp_job` e i suoi
membri, e un superuser. Il proprietario è un chiamante legittimo; quello che resta da vedere è il
superuser.

⚠️ La vista non può fare di più, e non serve: il giornale non distingue una corsa di pgAgent da
una della convergenza o lanciata a mano. `origine` vale `PGAGENT` per tutte, e pgAgent non
dichiara un nome di applicazione.

⛔ Si giudica dagli **attributi** del ruolo (`rolsuper` nel catalogo dei ruoli), **mai dal nome**:
chi installa può far girare pgAgent con un utente suo.

---

### Che cosa guarda

* **L'ultima corsa per processo**: le corse si raggruppano per codice del processo o, dove manca,
  per `jobname`. Un processo che ha avuto una corsa da superuser e poi una in regola non compare.
* **Anche le corse saltate.** A differenza di `vw_job_run_da_guardare`, che vuole l'ultima corsa
  *vera*, qui la domanda è chi si è collegato, e una corsa saltata lo dice quanto una corsa vera.
* **Solo le corse con il ruolo registrato.** Le corse con `ruolo_sessione` vuoto — scritte prima
  della colonna — non entrano: «non registrato» non è un guasto.
* **Solo i ruoli che esistono.** Un ruolo che non c'è più nel catalogo dei ruoli non è un
  superuser, e la corsa non entra.

Su un'installazione dove pgAgent si collega con un superuser la vista si accende: è proprio ciò
che deve dire.

---

### Chi la vede

L'applicazione la legge, come le altre viste di presidio: la leggono il pannello e il digest.
Nel catalogo dei presidi è un presidio che deve restare vuoto, guardato ogni giorno, e tocca a chi
gestisce il database: il testo per chi legge chiede che il programmatore dei lavori si colleghi con
`zeroerp_job`, o con un utente suo che ne sia membro.

---

### Test

`db/pgtap/maintenance/test-job-run-ruolo-sessione-v1.sql` — la vista prende l'ultima corsa di un
processo fatta da un superuser, non quella di un processo la cui ultima corsa è di un altro ruolo,
né una corsa senza ruolo o di un ruolo che non esiste più; il presidio è a catalogo, e
l'applicazione lo legge.

---

### Note di migrazione

* 2026-10-15 — nasce insieme a `job_run_log.ruolo_sessione` (`brief-db-ruoli-di-sistema`).

---

{% include-markdown "signature-core.md" %}
