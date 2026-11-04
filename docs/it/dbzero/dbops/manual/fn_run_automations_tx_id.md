## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_tx_id`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole `TX_ID`: ambito, modello del nome, strategia
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — le tabelle che il framework guarda
>
> Approfondimento funzioni:
>
> * [maintenance.proc_automations_tx_id_job](/dbzero/maintenance/funzioni/proc_automations_tx_id_job) — il processo che la lancia, dalla convergenza del rilascio e dal suo job pgAgent
> * [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed) — il trigger che monta
> * [dbops.fn_name_from_template](/dbzero/dbops/funzioni/fn_name_from_template) — il nome del trigger dal modello
> * [dbops.fn_trigger_exists_by_name](/dbzero/dbops/funzioni/fn_trigger_exists_by_name) — l'esistenza per nome
> * [dbops.fn_trigger_exists_by_function](/dbzero/dbops/funzioni/fn_trigger_exists_by_function) — l'esistenza per funzione
> * [script.fn_sqlstate_di_ambiente](/dbzero/script/funzioni/fn_sqlstate_di_ambiente) — distingue un guasto dell'ambiente da un difetto
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework delle automazioni
> * [Transaction ID](/guide/tx_id_implementation_guide) — il disegno del `tx_id`

---

### 🎯 Scopo Principale

Il modulo `TX_ID` del framework delle automazioni: **monta il trigger `dbops.trgfn_tx_id_managed`**
(`BEFORE INSERT OR UPDATE`) sulle tabelle in ambito che hanno una colonna `tx_id` di tipo UUID e non
lo hanno ancora. In simulazione non crea niente e scrive nel registro delle esecuzioni che cosa
creerebbe.

Aggiunge e non toglie: non crea la colonna, non rinomina né rimuove trigger esistenti.

---

### Quali tabelle, con quale regola

Le tabelle sono quelle ordinarie degli schemi in ambito (risolti dal framework se il chiamante non
li passa) che lo scope delle automazioni include. Per ciascuna valgono le regole `TX_ID` abilitate
che ne combaciano schema e tabella, in ordine di priorità, e la cui modalità è `AUTO` o quella con
cui la funzione è stata lanciata.

Una tabella senza la colonna `tx_id` UUID si salta: la colonna la mette il changeSet della tabella,
non l'automazione.

---

### Il nome del trigger e la sua esistenza

Il nome viene dal modello della regola (in mancanza, `trg_{table}_gen_tx_id_ins_upd`). Se il
trigger c'è già, non si fa niente. Che cosa vuol dire «c'è già» lo dice la strategia della regola:

* `BY_NAME` (il default) — esiste un trigger con quel nome;
* `BY_FUNCTION` — esiste un trigger che esegue `dbops.trgfn_tx_id_managed`, con qualsiasi nome;
* `BOTH` — basta uno dei due.

La strategia per funzione serve a non montare un secondo trigger dove ce n'è già uno con un nome di
un'altra epoca.

---

### La simulazione

Con la simulazione accesa la funzione non esegue DDL: per ogni trigger mancante scrive una riga
`DRYRUN` in `dbops.audit_log` con la tabella e il nome che avrebbe creato. La riga porta il tipo di
regola `TX_ID` ed è firmata col nome di questa funzione, come le simulazioni degli altri moduli si
firmano col tipo della loro regola.

---

### Codici errore

* `E_TX_ID` — la creazione di un trigger fallisce. Un guasto dell'**ambiente** (connessione,
  risorse, arresto, sistema, privilegio, lock) si registra con questo codice e il suo contesto, e
  poi si rilancia **com'è**, con il suo SQLSTATE: chi guarda i job lo manda a chi cura l'ambiente.
  Ogni altro errore è un difetto di struttura, e si solleva con questo codice.

Il primo errore ferma l'intera corsa: le tabelle successive non si guardano.

---

### Note di migrazione

* 2026-10-16 — un guasto dell'ambiente si rilancia col suo SQLSTATE; prima diventava un errore di
  dominio del modulo, e il presidio dei job lo mandava allo sviluppo
  (`brief-db-presidio-job-run-a-chi-tocca`).
* 2026-11-04 — la riga `DRYRUN` porta il tipo di regola `TX_ID` e il nome di questa funzione; prima
  portava il codice d'errore `E_TX_ID` e il nome dell'orchestratore `dbops.fn_run_automations`,
  ritirato lo stesso giorno: chi filtrava l'audit per `TX_ID` non trovava le simulazioni
  (`brief-db-revisione-dbops`).

---

{% include-markdown "signature-core.md" %}
