## 📘 Documentazione Concettuale – Funzione `dbops.fn_run_automations_storico`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_rules_tbl](/dbzero/dbops/tabelle/automation_rules_tbl) — la regola `STORICO`: bersaglio e template del nome
> * [dbops.automation_overrides_cols](/dbzero/dbops/tabelle/automation_overrides_cols) — l'override `STORICO_FK` della colonna di legame
> * [dbops.audit_log](/dbzero/dbops/tabelle/audit_log) — simulazioni e salti
>
> Approfondimento funzioni:
>
> * [script.trgfn_storico_generic](/dbzero/script/funzioni/trgfn_storico_generic) — il trigger che la funzione monta
> * [dbops.fn_run_automations_storico_provision](/dbzero/dbops/funzioni/fn_run_automations_storico_provision) — crea le shadow; questa funzione monta il trigger solo dove la shadow c'è
> * [dbops.fn_resolve_scope](/dbzero/dbops/funzioni/fn_resolve_scope) — l'ambito degli schemi
> * [dbops.fn_table_in_scope](/dbzero/dbops/funzioni/fn_table_in_scope) — il filtro per tabella
> * [dbops.fn_get_override_col](/dbzero/dbops/funzioni/fn_get_override_col) — il nome della colonna di legame
> * [dbops.fn_name_from_template](/dbzero/dbops/funzioni/fn_name_from_template) — il nome del trigger
> * [dbops.fn_trigger_exists_by_function](/dbzero/dbops/funzioni/fn_trigger_exists_by_function) — il trigger riconosciuto dalla funzione
> * [maintenance.proc_automations_storico_job](/dbzero/maintenance/funzioni/proc_automations_storico_job) — il wrapper del job
>
> Guide:
>
> * [Storicizzazione delle tabelle](/guide/storicizzazione-tabelle) — il provisioning del trigger
> * [Automazione DB](/guide/automazione-db) — il framework delle regole

---

### 🎯 Scopo Principale

Monta il trigger generico di storicizzazione, `BEFORE UPDATE OR DELETE` su `script.trgfn_storico_generic`,
sulle tabelle che hanno già la loro shadow nello schema `storico`, passandogli il nome della colonna
della shadow che lega una versione alla madre. Aggiunge e non toglie.

È uno dei runner del framework delle automazioni. Lo chiamano il job pgAgent (tramite il suo
wrapper), la convergenza dei processi strutturali e la passata `ci_apply`, tutti e tre dopo il
runner che crea le shadow.

---

### Su quali tabelle

Le tabelle ordinarie degli schemi dell'ambito, tolto `storico`, che passano il filtro per tabella. Per
ciascuna valgono le regole `STORICO` attive del registro il cui bersaglio di schema e di tabella la
comprende (`*all`, o un pattern sul nome) e il cui modo di esecuzione è `AUTO` o quello della corsa.

Il trigger si monta solo se esiste `storico.<tabella>`: la shadow la crea un altro runner. Due madri
omonime in schemi diversi hanno la stessa shadow, e ricevono entrambe il trigger.

---

### ⛔ La colonna di legame deve esistere nella shadow

Il trigger riceve il nome della colonna che lega la versione alla madre: l'override `STORICO_FK`,
altrimenti `<tabella>_id`. Nel ramo di chiusura cerca la versione aperta per quella colonna: se la
colonna non c'è, ogni `UPDATE` o `DELETE` di una riga storicizzata della madre morirebbe alla chiusura
dello snapshot.

Per questo, **prima** di montare un trigger, la funzione verifica che la colonna esista nella shadow;
se no solleva `E_STORICO_FK_COL_ASSENTE` e la corsa si ferma. Vale anche in simulazione: un «verrebbe
creato» su un trigger rotto è una risposta sbagliata. Una shadow con un nome diverso da `<tabella>_id`
si dichiara con l'override `STORICO_FK`.

Il controllo guarda i trigger che **nascono**; quelli già montati li presidia un pgTAP a parte.

---

### ⚠️ Quando un trigger «c'è già»

Il trigger c'è se sulla madre esiste un trigger su `script.trgfn_storico_generic`, con qualunque
nome: si riconosce dalla **funzione**. Il nome serve solo a creare un trigger nuovo.

Il nome viene dal template della regola, obbligatorio: la funzione non ha un nome di ripiego. Il
seed usa la forma `trg_<tabella>_z90_storico_upd_dlt`, con l'infisso che fa scattare il trigger di
storico dopo i guard.

Se il controllo dice «assente» ma il nome è già preso da un altro trigger (un trigger col nome del
template su un'altra funzione), la creazione fallisce per nome duplicato: la
funzione salta la tabella e lo scrive nell'audit con status `WARN` e azione `SKIP_EXISTS`. Il salto non
ferma la corsa.

---

### Che cosa non fa

* Non crea le shadow e non le arma: è `fn_run_automations_storico_provision`, con
  `fn_ensure_storico_table`.
* Non toglie trigger: un trigger legacy con un'altra forma si toglie a mano.
* Non legge parametri dalla regola: la regola `STORICO` ha i parametri vuoti.

In simulazione non monta niente e registra nell'audit, per ogni trigger che monterebbe, la tabella e il
nome.

---

### Codici errore

* `E_STORICO_FK_COL_ASSENTE` — la colonna di legame che il trigger riceverebbe non esiste nella shadow.
  Si solleva prima del montaggio, anche in simulazione.
* `E_STORICO_UD` — il montaggio del trigger fallisce per un motivo diverso dal nome duplicato. ⚠️ Un
  guasto dell'**ambiente** (connessione, risorse, arresto, privilegio, lock) si scrive nel registro
  errori con questo codice e poi si rilancia **col suo SQLSTATE**.

---

### Test

* `db/pgtap/dbops/test-storico-automazione-colonna-fk-v1.sql` — colonna di legame assente nella shadow:
  la funzione solleva, anche in simulazione; rinominata la colonna, il trigger nasce con l'argomento
  giusto e un aggiornamento della madre scrive lo snapshot.
* `db/pgtap/dbops/test-storico-colonna-fk-dei-trigger-v1.sql` — su tutti i trigger di storico già
  montati, l'argomento è una colonna della shadow.
* `db/pgtap/dbops/test-storico-nome-funzione-ritirato-v1.sql` — una madre che ha già il trigger
  generico con un altro nome non ne riceve un secondo, perché il trigger si riconosce dalla
  funzione; la colonna `existence_strategy` non c'è; su una madre senza trigger, il trigger nasce.
* `db/pgtap/dbops/test-storico-salto-trigger-presente-v1.sql` — nome del template preso da un trigger
  su un'altra funzione: la corsa vive, l'audit ha `WARN` con `SKIP_EXISTS`, nessun trigger di storico
  nasce.
* `db/pgtap/dbops/test-automazioni-guasto-ambiente-rilanciato-v1.sql` — il ramo dell'ambiente nel
  gestore d'errore (presidio sul testo).

---

### Note di migrazione

* 2026-09-01 — tolto il ramo di pulizia dei trigger legacy separati: cercava nomi che nessun changelog
  aveva mai creato, e il flag che lo attivava era spento di default. Il dry run produceva lo stesso
  output di prima.
* 2026-09-25 — arriva il controllo della colonna di legame (`brief-db-storico-colonna-fk-dei-trigger`):
  cinque shadow del 2025 avevano la colonna al singolare, e sono state rinominate al nome
  dell'automazione.
* 2026-10-16 — un guasto dell'ambiente si rilancia col suo SQLSTATE (`brief-db-presidio-job-run-a-chi-tocca`).
* 2026-11-03 — il controllo per funzione cerca il nome vivo `script.trgfn_storico_generic`: prima cercava
  un nome ritirato e con `BY_FUNCTION` non trovava mai il trigger (`brief-db-revisione-maintenance`, D3).
  Lo stesso giorno il salto per nome duplicato si scrive con status `WARN`: prima lo status
  `SKIP_EXISTS` era rifiutato dal vincolo dell'audit e il salto fermava la corsa (R4).
* 2026-11-08 — il trigger si riconosce dalla funzione: la strategia d'esistenza della regola esce; il
  nome viene solo dal template della regola, senza il ripiego `trg_z90_<tabella>_storico_upd_dlt`,
  diverso dal seed (`20261109-70`, brief-db-revisione-dbops D17, D20).

---

{% include-markdown "signature-core.md" %}
