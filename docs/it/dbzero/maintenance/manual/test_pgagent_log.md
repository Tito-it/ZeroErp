## 📘 Documentazione Concettuale – Tabella `maintenance.test_pgagent_log`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale vero delle corse dei lavori
>
> Guide:
>
> * [Processi pgAgent funzionali](/guide/processi-pgagent-funzionali) — i lavori a orario di oggi

---

### 🎯 Scopo Principale

Una tabella di collaudo di pgAgent, nata con il primo impianto del database: serviva a vedere
che lo scheduler si svegliasse e scrivesse. Oggi non la scrive e non la legge nessuno.

---

### ⛔ Non è il giornale dei job

Le corse dei lavori automatici si registrano in `maintenance.job_run_log`, con processo, esito,
ruolo e causa del fallimento. Questa tabella non c'entra: nessun job pgAgent la scrive, nessuna
funzione, vista, pgTAP o script la nomina, e nessun presidio la legge. Chi cerca com'è andato un
lavoro guarda il giornale, non qui.

---

### Perché c'è ancora

Nasce nell'albero delle migrazioni della prima versione, che il changelog di oggi include ancora:
per questo **rinasce a ogni ricostruzione da zero**, e un `DROP` a mano non la toglie. Per ritirarla
serve un changeSet in avanti nell'albero attuale, che giri dopo quello della prima versione.

---

### ⚠️ L'applicazione non la legge

Il provisioning non concede niente su questa tabella, e nessun changeSet lo fa: senza un lettore, un
privilegio non avrebbe una sede da cui essere dichiarato. Un permesso di lettura trovato su un
database è un ricordo dato a mano, non una configurazione.

---

### Note di migrazione

* 2025-08-08 — nasce al bootstrap, per collaudare pgAgent.

---

{% include-markdown "signature-core.md" %}
