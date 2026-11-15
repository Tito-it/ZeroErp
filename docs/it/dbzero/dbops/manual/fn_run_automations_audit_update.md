## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_audit_update`

> **Ultimo aggiornamento**: 13 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — le regole `AUDIT_UPDATE`: ambito e modello del nome
> * [dbops.automation_scope](/dbzero/dbops/tabelle/automation_scope) — le tabelle che il framework guarda
>
> Approfondimento funzioni:
>
> * [maintenance.proc_automations_audit_update_job](/dbzero/maintenance/funzioni/proc_automations_audit_update_job) — il processo che la lancia, dalla convergenza del rilascio e dal suo job pgAgent
> * [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic) — il trigger che monta
> * [dbops.fn_trigger_exists_by_function](/dbzero/dbops/funzioni/fn_trigger_exists_by_function) — riconosce il trigger dalla funzione
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

Il trigger si monta solo se la tabella ha **entrambe** le colonne di audit, `data_update` e
`user_update`. I nomi sono fissi per contratto ([linee guida SQL](/linee-guida-sql) §7): il trigger
generico li scrive per nome (e, all'inserimento, `user_insert`), quindi non si sostituiscono per
tabella e la regola non ha parametri (`params = {}`).

---

### Il nome del trigger e la sua esistenza

Il trigger «c'è già» se sulla tabella un trigger esegue già `script.trgfn_audit_data_user_generic`,
qualunque nome abbia (`dbops.fn_trigger_exists_by_function`). Il nome serve solo a crearne uno
nuovo, e viene dal modello della regola, obbligatorio (`trg_{table}_audit_data_user_upd` nel seed):
la funzione non ha un nome di ripiego.

---

### La simulazione

Con la simulazione accesa la funzione non esegue DDL: per ogni trigger mancante scrive una riga
`DRYRUN` in `dbops.audit_log`, con tipo di regola `AUDIT_UPDATE`, la tabella e il nome che avrebbe
creato. La riga è firmata col nome di questa funzione, `dbops.fn_run_automations_audit_update`.

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
* 2026-11-04 — ritirato l'orchestratore `dbops.fn_run_automations`, che la chiamava come modulo
  `AUDIT_UPDATE`; la firma della simulazione ne porta ancora il nome (`brief-db-revisione-dbops`).
* 2026-11-08 — il trigger si riconosce dalla funzione: la strategia d'esistenza della regola esce;
  il nome viene solo dal registro; le colonne di audit hanno nome fisso (escono gli override
  `AUDIT_TS`/`AUDIT_USER` e i parametri `audit_ts`/`audit_user`); la simulazione firma col proprio
  nome (`20261109-69`, brief-db-revisione-dbops D17, D20, D27, R1).
* 2026-11-13 — la regola vale per la tabella che nomina: `target_table` si confronta con `=`,
  non più con `ILIKE`, che faceva del `_` di un nome un jolly (una regola su `event_log` copriva
  anche una `eventXlog`). `*all` ha una forma sola, garantita dal CHECK
  `chk_automation_rules_tbl_target_table_nome_esatto` (`90_end/20261112-66`). Testata ri-ancorata
  con `%TYPE`, firma invariata (`20261112-68`).

---

{% include-markdown "signature-core.md" %}
