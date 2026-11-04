## 📘 Documentazione Concettuale – Vista `dbops.vw_processi_dominio_su_pgagent`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — classe e canale del processo
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo in cui la vista è un presidio
>
> Approfondimento funzioni:
>
> * [dbops.fn_accoda_chiusura_scadenze](/dbzero/dbops/funzioni/fn_accoda_chiusura_scadenze) — un job pgAgent che sveglia un processo di dominio accodandolo
> * [dbops.fn_accoda_lavoro](/dbzero/dbops/funzioni/fn_accoda_lavoro) — la porta della coda, dove il lavoro vero resta tracciato
>
> Guide:
>
> * [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita) — chi suona la sveglia non è chi fa il lavoro

---

### 🎯 Scopo Principale

Presidio: i processi di classe `DOMINIO`, attivi e non ritirati, che **eseguono** dentro pgAgent.
Deve restare vuota; ogni riga dice il rimedio.

---

### ⛔ Perché un processo di dominio non esegue dentro pgAgent

Dentro pgAgent un processo:

* **non ha un'identità**, quindi nessun perimetro emittente: tocca i dati di tutte le aziende
  insieme;
* **non ha dove raccontare un fallimento**: la traccia finisce nel giornale di pgAgent, che
  l'applicazione non vede e che nessuno guarda.

⭐ L'argomento è sperimentale, non teorico: un lavoro settimanale è morto ogni settimana per sei mesi
senza che nessuno lo sapesse.

---

### ⭐ Svegliare da pgAgent resta lecito

| | |
| --- | --- |
| ⛔ **eseguire** dentro pgAgent | tocca i documenti senza identità e senza perimetro |
| ✅ **svegliare** da pgAgent | mette in coda un lavoro e non tocca nessun documento |

Un job che si limita ad accodare, se muore, non ha fatto danni, e il lavoro vero resta tracciato
nella coda, che sa dire se è fallito. Il registro descrive **il processo**, non chi suona la
sveglia: per un processo così il canale è `CODA_AUTOMATICA`, ed è il rimedio che il `motivo` di ogni
riga indica.

⚠️ Il presidio non è una tassa su pgAgent: la manutenzione del database su pgAgent è al suo posto, e
non compare.

---

### ⛔ Perché una vista e non un vincolo

Il registro dei processi è **catalogo**, e si cambia dal seed. Un vincolo trasformerebbe un errore
di configurazione in un aggiornamento del database rotto, cioè in un problema di tutti invece che
di quella riga. E quando la regola è nata, il processo da spostare c'era ancora: un vincolo avrebbe
fermato la migrazione prima di poterlo spostare.

---

### Chi la guarda

Nel catalogo dei presidi è un presidio che deve restare vuoto, guardato ogni settimana, che tocca
allo sviluppo: da quando è vuota, una riga è una regressione. La vista gira coi privilegi del
proprietario.

---

### Test

* `db/pgtap/dbops/test-vw-processi-dominio-su-pgagent.sql` — è vuota, e per il motivo giusto (la
  chiusura per scadenze è passata a `CODA_AUTOMATICA`, non è stata spenta); un processo di dominio
  su `PGAGENT`, costruito, compare col rimedio nel motivo; un processo di manutenzione su `PGAGENT`
  non compare.

---

### Note di migrazione

* 2026-09-05 — nasce con la regola «nessun processo di dominio esegue dentro pgAgent»
  (`brief-db-processi-automatici-identita-e-perimetro`, §12.12); lo stesso giorno
  `chiusura_scadenze_daily` passa a `CODA_AUTOMATICA` e la vista diventa vuota.

---

{% include-markdown "signature-core.md" %}
