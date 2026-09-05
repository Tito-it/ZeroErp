## 📘 Documentazione Concettuale – Procedura `maintenance.proc_apply_storicizza_defaults()`

> **Collegamenti utili**
>
Approfondimenti tabelle:
>
[`config.storico_set_storicizza`](/dbzero/config/tabelle/storico_set_storicizza)
>
Approfondimenti funzioni:
>
[`maintenance.proc_sync_storico_set_storicizza`](/dbzero/maintenance/manual/proc_sync_storico_set_storicizza) ·
[`maintenance.fn_run_and_log`](/dbzero/maintenance/manual/fn_run_and_log)

---
### 🎯 Scopo Principale
(latest review 05-09-2026)

Rimette `DEFAULT true` sulla colonna `storicizza` di ogni tabella elencata in
`config.storico_set_storicizza`, così che le righe nuove nascano storicizzate.

È il **consumatore** di un insieme derivato: chi lo popola e lo pota è
[`proc_sync_storico_set_storicizza`](/dbzero/maintenance/manual/proc_sync_storico_set_storicizza).

---

### ⛔ Il guasto che questa procedura ha causato per sei mesi

Fino al 5 settembre 2026 il giro era tutto-o-niente: un `ALTER TABLE` per riga,
in un ciclo unico. **Una sola riga che puntava a una tabella ritirata sollevava
`undefined_table` e fermava il lavoro per tutte le altre cento.**

⭐ Ed è successo: il job settimanale è morto ogni settimana **dal 21 febbraio al
5 settembre 2026**. Nessuno se n'è accorto, e non per distrazione — il giornale
delle esecuzioni continuava a dire *«done»*, perché il verbale del fallimento
veniva scritto e poi buttato via insieme alla transazione.

---

### ⭐ Che cosa fa adesso

1. una riga che **non risolve** a nessun oggetto viene **saltata**, e lo dice;
2. un `ALTER` che fallisce per un altro motivo isola **quella riga sola**;
3. il giro finisce sempre con un riepilogo: *quante applicate, saltate, fallite*.

> ⚠️ **Non è «ingoiare gli errori»**: cambia il **posto** dove il guasto si
> racconta. Un'eccezione dentro un job pgAgent non la legge nessuno — è
> esattamente ciò che questi sei mesi dimostrano. Un `WARNING` nel log del
> server, sì.

---

### ⭐ Perché l'isolamento serve anche dopo la potatura

Non è una toppa sulle tre righe morte di quel giorno.

Chi popola e chi consuma sono **due job pgAgent distinti, su due schedulazioni
diverse**. Se l'apply gira prima del sync — e prima o poi capita, è l'ordine di
due sveglie indipendenti — la riga stantia **c'è**.

⇒ È una possibilità **strutturale**: chi consuma un insieme derivato non può
morire perché una riga non è ancora stata potata.

---

### ⚠️ Il messaggio distingue due casi, perché hanno rimedi opposti

| Riga saltata | Che cosa succederà |
| --- | --- |
| **derivata** | la poterà il prossimo sync, da sola |
| **manuale** | ⛔ il sync non la tocca mai: è una decisione che ha perso il suo bersaglio, e va guardata da una persona |

Promettere una potatura che non arriverà sarebbe peggio che non dire niente.

---

### 🕒 Esecuzione programmata

Job pgAgent **`apply_storicizza_weekly`**, step `run_apply_storicizza`, che
chiama il wrapper
[`proc_apply_storicizza_defaults_job`](/dbzero/maintenance/manual/proc_apply_storicizza_defaults_job)
— il wrapper passa da `maintenance.fn_run_and_log`, che registra la corsa nel
giornale.

> ⚠️ Il job vive in `85_pgagent`, che in CI è `MARK_RAN`: su un ambiente
> ricostruito da zero **non viene creato**, e nessun test lo direbbe.

---

### Verifica

`db/pgtap/maintenance/test-storicizza-set-potatura.sql` — in particolare il test
che chiama la procedura con una riga stantia **davvero presente**, non simulata.

---

{% include-markdown "signature-core.md" %}
