## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_pgagent_job_stato`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — `jobname_pgagent`, il nome che la funzione cerca
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il panorama dei processi, che la chiama per ogni processo
>
> Approfondimento funzioni:
>
> * [dbops.fn_check_funzioni_riferimenti_morti](/dbzero/dbops/funzioni/fn_check_funzioni_riferimenti_morti) — il presidio che ha trovato il suo difetto di permessi
>
> Guide:
>
> * [Processi pgAgent funzionali](/guide/processi-pgagent-funzionali) — i job pgAgent del progetto
> * [Analisi e tracciamento di processi e job](/guide/analisi-tracciamento-processi-e-job) — come si confrontano programmazione e giornale

---

### 🎯 Scopo Principale

Dice che cosa sa pgAgent di un job nominato: se è abilitato, quando ha girato l'ultima volta,
quando girerà la prossima. Sono le due date che il giornale dei job non ha, e servono al panorama
dei processi per rispondere a «ogni lavoro ha una programmazione, e sta partendo?».

---

### ⭐ Una funzione, non un join in una vista

Lo schema `pgagent` non c'è dappertutto: in CI la configurazione di pgAgent non gira. Una vista si
risolve quando si crea, e un join diretto su `pgagent.pga_job` fermerebbe il migrate dove
l'estensione manca. Una funzione si risolve quando si chiama, e qui controlla prima che la tabella
esista.

⛔ **Zero righe vuol dire «non so niente di questo job»**: l'estensione manca, il nome è vuoto
(il processo non dichiara un job), o il job non c'è. Chi chiama la usa in un join laterale esterno
e vede colonne vuote, che è la risposta giusta, non un errore.

---

### ⭐ Una porta stretta, `SECURITY DEFINER`

L'applicazione non ha accesso allo schema `pgagent`, e non deve averlo: lì c'è anche il registro
delle esecuzioni, con l'output dei comandi. La funzione è `SECURITY DEFINER` del proprietario,
col `search_path` fissato, e restituisce solo tre campi innocui di un job nominato. Basta il
proprietario degli oggetti, che su `pgagent` ha i diritti dal provisioning: nessun superuser.
Anche la guardia sull'esistenza della tabella gira coi suoi diritti, quindi dove `pgagent` c'è non
solleva.

⚠️ Il nome di un job pgAgent non è univoco per pgAgent stesso: due job con lo stesso nome darebbero
due righe, e il panorama mostrerebbe il processo due volte. Lato progetto l'univocità la garantisce
`dbops.processi`, che non lascia a due processi lo stesso job.

---

### Test

* `db/pgtap/dbops/test-vw-processi-programmazione.sql` — dove non sa, la funzione restituisce zero
  righe e non esplode; il panorama costruito sopra di lei.
* `db/pgtap/dbops/test-vw-processi-programmazione-da-guardare.sql`,
  `db/pgtap/dbops/test-presidio-processi-testo-per-causa-v1.sql` — i presidi che leggono il
  panorama.
* `db/pgtap/dbops/test-riferimenti-morti-v1.sql` — il 42501 che l'applicazione vedrebbe su
  `pgagent` dentro questa `SECURITY DEFINER` non è un riferimento morto; dove `pgagent` manca,
  l'esenzione è dichiarata.

---

### Note di migrazione

* 2026-09-06 — nasce con il panorama della programmazione dei processi, `SECURITY INVOKER`, e lo
  stesso giorno diventa `SECURITY DEFINER`: come `INVOKER` il panorama era illeggibile proprio
  dall'applicazione, che non ha accesso allo schema `pgagent`. L'ha trovato il presidio dei
  riferimenti morti, non una prova a mano.

---

{% include-markdown "signature-core.md" %}
