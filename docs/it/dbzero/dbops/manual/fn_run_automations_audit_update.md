## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_audit_update`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole `AUDIT_UPDATE`: ambito, colonne, modello del nome, strategia
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — le tabelle che il framework guarda
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols) — i nomi di colonna sostituiti per tabella
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations](/dbzero/dbops/funzioni/fn_run_automations) — l'orchestratore che la chiama come modulo `AUDIT_UPDATE`
> * [maintenance.proc_automations_audit_update_job](/dbzero/maintenance/funzioni/proc_automations_audit_update_job) — il job che la lancia da sola
> * [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic) — il trigger che monta
> * [dbops.fn_get_override_col](/dbzero/dbops/funzioni/fn_get_override_col) — il nome di colonna sostituito, se c'è
> * [dbops.fn_name_from_template](/dbzero/dbops/funzioni/fn_name_from_template) — il nome del trigger dal modello
> * [script.fn_sqlstate_di_ambiente](/dbzero/script/funzioni/fn_sqlstate_di_ambiente) — distingue un guasto dell'ambiente da un difetto
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — il framework delle automazioni

---

### 🎯 Scopo Principale

Il modulo `AUDIT_UPDATE` del framework delle automazioni: **monta il trigger
`script.trgfn_audit_data_user_generic`** (`BEFORE INSERT OR UPDATE`) sulle tabelle in ambito che
hanno le colonne di audit e non lo hanno ancora. Il trigger scrive a ogni scrittura chi ha toccato
la riga e quando. In simulazione non crea niente e scrive nel registro delle esecuzioni che cosa
creerebbe.

Aggiunge e non toglie.

---

### Quali tabelle, con quale regola

Le tabelle sono quelle ordinarie degli schemi in ambito che lo scope delle automazioni include. Per
ciascuna valgono le regole `AUDIT_UPDATE` abilitate che ne combaciano schema e tabella, in ordine
di priorità, e la cui modalità è `AUTO` o quella con cui la funzione è stata lanciata.

Il trigger si monta solo se la tabella ha **entrambe** le colonne di audit: quella del momento e
quella dell'utente. I loro nomi vengono dai parametri della regola (`data_update` e `user_update`
se la regola non li dice), sostituiti dal nome della tabella quando
`dbops.automation_overrides_cols` ne dichiara uno per i ruoli `AUDIT_TS` e `AUDIT_USER`.

⚠️ Il nome sostituito serve **solo** a decidere se montare il trigger: il trigger generico scrive
sempre `data_update`, `user_update` e, all'inserimento, `user_insert`. Su una tabella con colonne
di audit dai nomi diversi, il trigger montato fallirebbe alla prima scrittura.

---

### Il nome del trigger e la sua esistenza

Il nome viene dal modello della regola (in mancanza, `trg_{table}_audit_data_user_upd`). La
strategia della regola dice quando il trigger «c'è già»: `BY_NAME` (il default) per nome,
`BY_FUNCTION` se un trigger esegue già la funzione di audit, `BOTH` se basta uno dei due.

---

### La simulazione

Con la simulazione accesa la funzione non esegue DDL: per ogni trigger mancante scrive una riga
`DRYRUN` in `dbops.audit_log`, con tipo di regola `AUDIT_UPDATE`, la tabella e il nome che avrebbe
creato.

---

### Codici errore

* `E_AUDIT_UPDATE` — la creazione di un trigger fallisce. Un guasto dell'**ambiente**
  (connessione, risorse, arresto, sistema, privilegio, lock) si registra con questo codice e il suo
  contesto, e poi si rilancia **com'è**, con il suo SQLSTATE. Ogni altro errore è un difetto di
  struttura, e si solleva con questo codice.

Il primo errore ferma l'intera corsa.

---

### Note di migrazione

* 2026-02-27 — il trigger montato scatta all'inserimento e all'aggiornamento, non più solo
  all'aggiornamento.
* 2026-10-16 — un guasto dell'ambiente si rilancia col suo SQLSTATE; prima diventava un errore di
  dominio del modulo, e il presidio dei job lo mandava allo sviluppo
  (`brief-db-presidio-job-run-a-chi-tocca`).

---

{% include-markdown "signature-core.md" %}
